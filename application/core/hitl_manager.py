#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Human-in-the-Loop (HITL) Manager

更新系コマンド実行時に処理を一時停止し、Slack に承認ボタン付きメッセージを送信する制御ロジック。
"""

import time
import logging
import json
from typing import Dict, Optional, Any
from enum import Enum
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class ApprovalStatus(Enum):
    """承認ステータス"""
    PENDING = "PENDING"        # 承認待機中
    APPROVED = "APPROVED"      # 承認済み
    REJECTED = "REJECTED"      # 拒否
    TIMEOUT = "TIMEOUT"        # タイムアウト


class HITLManager:
    """HITL 制御と承認管理クラス"""
    
    def __init__(
        self,
        slack_client,
        approval_timeout_sec: int = 300,
        slack_channel: str = "#aiops-requests"
    ):
        """
        初期化
        
        Args:
            slack_client: Slack API クライアント
            approval_timeout_sec: 承認リクエストのタイムアウト（秒）
            slack_channel: 承認リクエスト送信先チャネル
        """
        self.slack_client = slack_client
        self.approval_timeout_sec = approval_timeout_sec
        self.slack_channel = slack_channel
        self.pending_approvals: Dict[str, Dict[str, Any]] = {}
    
    def request_approval(
        self,
        request_id: str,
        command: str,
        target_ip: str,
        target_name: str,
        reason: str,
        impact_description: str = ""
    ) -> Dict[str, Any]:
        """
        Slack に承認リクエストを送信
        
        Args:
            request_id: ユニークなリクエスト ID
            command: 実行予定のコマンド
            target_ip: 対象 VM IP
            target_name: 対象 VM 名
            reason: 実行理由
            impact_description: 想定される影響
        
        Returns:
            {
                "status": "sent",
                "request_id": str,
                "timestamp": datetime,
                "slack_message_ts": str (メッセージタイムスタンプ)
            }
        """
        try:
            # メッセージビルド
            blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "⚠️ *AI エージェント - 承認リクエスト*\n以下の操作について、人間の承認が必要です"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*対象サーバー*\n{target_name} ({target_ip})"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*リクエスト ID*\n`{request_id}`"
                        }
                    ]
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*実行予定コマンド*\n```{command}```"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*実行理由*\n{reason}"
                    }
                }
            ]
            
            # 影響説明を追加
            if impact_description:
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*想定される影響*\n{impact_description}"
                    }
                })
            
            # 承認/拒否ボタン
            blocks.append({
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "✅ Approve"
                        },
                        "value": f"{request_id}::approve",
                        "action_id": "hitl_approve_button",
                        "style": "primary"
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "❌ Reject"
                        },
                        "value": f"{request_id}::reject",
                        "action_id": "hitl_reject_button",
                        "style": "danger"
                    }
                ]
            })
            
            blocks.append({
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"⏱️ タイムアウト: {self.approval_timeout_sec} 秒後に自動拒否"
                    }
                ]
            })
            
            # Slack に送信
            response = self.slack_client.chat_postMessage(
                channel=self.slack_channel,
                blocks=blocks
            )
            
            message_ts = response['ts']
            
            # キャッシュに保存
            self.pending_approvals[request_id] = {
                "status": ApprovalStatus.PENDING,
                "command": command,
                "target_ip": target_ip,
                "target_name": target_name,
                "reason": reason,
                "created_at": datetime.now(),
                "timeout_at": datetime.now() + timedelta(seconds=self.approval_timeout_sec),
                "slack_message_ts": message_ts,
                "approved_by": None,
                "decision_at": None
            }
            
            logger.info(f"HITL approval requested: {request_id} (ts: {message_ts})")
            
            return {
                "status": "sent",
                "request_id": request_id,
                "timestamp": datetime.now(),
                "slack_message_ts": message_ts
            }
        
        except Exception as e:
            logger.error(f"Failed to send HITL approval request: {e}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    def wait_for_approval(
        self,
        request_id: str,
        poll_interval_sec: int = 5
    ) -> Dict[str, Any]:
        """
        承認結果を待機（ポーリング）
        
        Args:
            request_id: リクエスト ID
            poll_interval_sec: ポーリング間隔（秒）
        
        Returns:
            {
                "status": ApprovalStatus,
                "approved_by": str (ユーザー ID),
                "decision_at": datetime,
                "reason": str
            }
        """
        request = self.pending_approvals.get(request_id)
        
        if not request:
            return {
                "status": ApprovalStatus.REJECTED,
                "reason": f"Request ID '{request_id}' not found"
            }
        
        # タイムアウトチェック
        if datetime.now() >= request["timeout_at"]:
            request["status"] = ApprovalStatus.TIMEOUT
            logger.warning(f"HITL approval timeout: {request_id}")
            return {
                "status": ApprovalStatus.TIMEOUT,
                "reason": "承認リクエストがタイムアウトしました"
            }
        
        # 承認ステータスチェック
        while request["status"] == ApprovalStatus.PENDING:
            if datetime.now() >= request["timeout_at"]:
                request["status"] = ApprovalStatus.TIMEOUT
                logger.warning(f"HITL approval timeout: {request_id}")
                return {
                    "status": ApprovalStatus.TIMEOUT,
                    "reason": "承認リクエストがタイムアウトしました"
                }
            
            # ポーリング待機
            time.sleep(poll_interval_sec)
        
        return {
            "status": request["status"],
            "approved_by": request.get("approved_by"),
            "decision_at": request.get("decision_at"),
            "reason": f"Request {request_id}"
        }
    
    def record_decision(
        self,
        request_id: str,
        approved: bool,
        user_id: str
    ) -> bool:
        """
        ユーザーの決定を記録（Slack ボタン押下時に呼び出し）
        
        Args:
            request_id: リクエスト ID
            approved: True なら承認、False なら拒否
            user_id: 決定ユーザーの ID
        
        Returns:
            True なら記録成功
        """
        request = self.pending_approvals.get(request_id)
        
        if not request:
            logger.warning(f"Request ID not found: {request_id}")
            return False
        
        request["status"] = ApprovalStatus.APPROVED if approved else ApprovalStatus.REJECTED
        request["approved_by"] = user_id
        request["decision_at"] = datetime.now()
        
        decision_str = "✅ 承認" if approved else "❌ 拒否"
        logger.info(f"HITL decision recorded: {request_id} -> {decision_str} by {user_id}")
        
        return True
    
    def get_pending_requests(self) -> list:
        """
        すべての保留中リクエストを取得
        
        Returns:
            保留中のリクエスト情報リスト
        """
        return [
            {
                "request_id": rid,
                "command": req["command"],
                "target_name": req["target_name"],
                "created_at": req["created_at"].isoformat(),
                "timeout_at": req["timeout_at"].isoformat()
            }
            for rid, req in self.pending_approvals.items()
            if req["status"] == ApprovalStatus.PENDING
        ]
    
    def cleanup_old_requests(self, older_than_minutes: int = 60) -> int:
        """
        古いリクエストをクリーンアップ
        
        Args:
            older_than_minutes: このミニッターション以上古いリクエストを削除
        
        Returns:
            削除したリクエスト数
        """
        cutoff_time = datetime.now() - timedelta(minutes=older_than_minutes)
        to_delete = [
            rid for rid, req in self.pending_approvals.items()
            if req["created_at"] < cutoff_time
        ]
        
        for rid in to_delete:
            del self.pending_approvals[rid]
        
        if to_delete:
            logger.info(f"Cleaned up {len(to_delete)} old HITL requests")
        
        return len(to_delete)


# 使用例（Slack イベント ハンドラー）
def handle_hitl_button_press(body: Dict, hitl_manager: HITLManager):
    """
    Slack ボタン押下時のイベントハンドラー
    
    Args:
        body: Slack イベス ボディ
        hitl_manager: HITLManager インスタンス
    """
    try:
        action_value = body['actions'][0]['value']
        request_id, decision = action_value.split("::")
        user_id = body['user']['id']
        
        approved = (decision == "approve")
        hitl_manager.record_decision(request_id, approved, user_id)
        
        logger.info(f"Button pressed: {request_id} by {user_id} -> {decision}")
    
    except Exception as e:
        logger.error(f"Error handling HITL button press: {e}")
