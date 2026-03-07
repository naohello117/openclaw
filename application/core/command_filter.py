#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Command Filter & Guardrails

AIが生成したコマンドをSSH実行する直前にインターセプトし、
正規表現ブラックリスト/ホワイトリストで安全性を検証するロジック。
"""

import re
import logging
from typing import Dict, List, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class CommandStatus(Enum):
    """コマンドステータス"""
    SAFE = "SAFE"                    # 実行可能
    BLOCKED = "BLOCKED"              # ブロック対象
    REQUIRES_HITL = "REQUIRES_HITL"  # HITL承認が必要


class CommandFilter:
    """コマンドフィルタリング・ガードレール実装"""
    
    def __init__(self):
        """初期化：ブラックリスト・HITL対象パターンを定義"""
        
        # === Tier 1: 絶対ブロック対象（危険）===
        self.blacklist_patterns = [
            # ディレクトリ・ファイル削除
            r"rm\s+(-r|-f|-rf)?.*\/\s*($|;|&&|\|)",  # rm -rf / など
            r"rm\s+(-r|-f|-rf)?.*\/etc\b",
            r"rm\s+(-r|-f|-rf)?.*\/opt\/openclaw\b",
            
            # ファイルシステム操作
            r"mkfs\.\w+",
            r"fdisk|parted",
            
            # OS 制御
            r"^\s*(reboot|shutdown|halt|poweroff|init\s+[06])",
            r"systemctl\s+(reboot|shutdown|halt|poweroff|isolate)\b",
            
            # ネットワーク無効化
            r"iptables\s+-F",
            r"ufw\s+disable",
            r"ip\s+link\s+set\s+\w+\s+down",
            
            # 権限・ユーザー操作
            r"chmod\s+(-R\s+)?777",
            r"chmod\s+000\s+/etc/sudoers",
            r"userdel\s+-r\s+root",
            r"chpasswd.*root",
            
            # コア ライブラリ削除
            r"(apt|yum).*remove.*(linux-image|systemd|glibc)",
            
            # Key Vault・シークレット漏洩
            r"echo.*\$.*SECRET|echo.*\$.*API_KEY",
            r"cat.*\.pem|cat.*\.key",
        ]
        
        # === Tier 2: HITL 承認が必要 ===
        self.hitl_patterns = [
            # sudo コマンド一般
            r"^\s*sudo\b",
            
            # サービス制御
            r"systemctl\s+(restart|stop|reload|start|disable|enable)\b",
            r"service\s+\w+\s+(restart|stop|reload|start)",
            
            # プロセス制御
            r"kill(all)?\s+",
            r"pkill\s+",
            
            # パッケージ管理
            r"(apt|apt-get|yum|dnf)\s+(install|remove|purge|upgrade|update)",
            
            # ファイル編集
            r"(vi|nano|vim|sed\s+-i|ed)\s+",
            
            # データベース・ファイルシステム操作
            r"(mysql|psql|mongo)\s+-",
            r"fsck|mount|umount",
            
            # ネットワーク設定変更
            r"ip\s+route|ip\s+addr\s+",
            r"ifconfig|ip\s+link",
            
            # ホスト名変更
            r"hostnamectl|hostname\s+",
            
            # 大量ファイル操作
            r"find.*-exec|xargs.*rm",
        ]
    
    def check_command_safety(self, command: str) -> Dict[str, any]:
        """
        コマンドの安全性をチェック
        
        Args:
            command: 実行予定のコマンド
        
        Returns:
            {
                "status": CommandStatus,
                "reason": str,
                "matched_pattern": str (マッチした場合)
            }
        """
        command_stripped = command.strip()
        
        # 空コマンドチェック
        if not command_stripped:
            return {
                "status": CommandStatus.SAFE,
                "reason": "Empty command (no-op)",
                "matched_pattern": None
            }
        
        # === Step 1: ブラックリストチェック ===
        for pattern in self.blacklist_patterns:
            if re.search(pattern, command_stripped, re.IGNORECASE | re.MULTILINE):
                logger.warning(f"Blocked by blacklist: {pattern} -> {command}")
                return {
                    "status": CommandStatus.BLOCKED,
                    "reason": f"危険操作がブロックされました: パターン '{pattern}' に合致します。",
                    "matched_pattern": pattern
                }
        
        # === Step 2: HITL対象チェック ===
        for pattern in self.hitl_patterns:
            if re.search(pattern, command_stripped, re.IGNORECASE):
                logger.info(f"HITL required: {pattern} -> {command}")
                return {
                    "status": CommandStatus.REQUIRES_HITL,
                    "reason": f"この操作は人間の承認が必要です (パターン: {pattern})",
                    "matched_pattern": pattern
                }
        
        # === Step 3: セーフ ===
        logger.info(f"Safe command: {command}")
        return {
            "status": CommandStatus.SAFE,
            "reason": "コマンドはガードレール検査に合格しました",
            "matched_pattern": None
        }
    
    def check_batch_commands(self, commands: List[str]) -> Dict[str, any]:
        """
        複数のコマンドをチェック
        
        Args:
            commands: コマンドのリスト
        
        Returns:
            {
                "total": int,
                "safe": int,
                "blocked": int,
                "requires_hitl": int,
                "results": [...]
            }
        """
        results = []
        counters = {"SAFE": 0, "BLOCKED": 0, "REQUIRES_HITL": 0}
        
        for cmd in commands:
            result = self.check_command_safety(cmd)
            results.append({
                "command": cmd,
                "result": result
            })
            counters[result["status"].name] += 1
        
        return {
            "total": len(commands),
            "safe": counters["SAFE"],
            "blocked": counters["BLOCKED"],
            "requires_hitl": counters["REQUIRES_HITL"],
            "results": results
        }
    
    def update_blacklist_pattern(self, pattern: str, add: bool = True) -> None:
        """
        ブラックリストパターンを動的に追加/削除（テンプレート用）
        
        Args:
            pattern: 正規表現パターン
            add: True なら追加、False なら削除
        """
        if add:
            if pattern not in self.blacklist_patterns:
                self.blacklist_patterns.append(pattern)
                logger.info(f"Blacklist pattern added: {pattern}")
        else:
            if pattern in self.blacklist_patterns:
                self.blacklist_patterns.remove(pattern)
                logger.info(f"Blacklist pattern removed: {pattern}")
    
    def update_hitl_pattern(self, pattern: str, add: bool = True) -> None:
        """
        HITL対象パターンを動的に追加/削除（テンプレート用）
        
        Args:
            pattern: 正規表現パターン
            add: True なら追加、False なら削除
        """
        if add:
            if pattern not in self.hitl_patterns:
                self.hitl_patterns.append(pattern)
                logger.info(f"HITL pattern added: {pattern}")
        else:
            if pattern in self.hitl_patterns:
                self.hitl_patterns.remove(pattern)
                logger.info(f"HITL pattern removed: {pattern}")


# 使用例
if __name__ == "__main__":
    filter = CommandFilter()
    
    # テストコマンド
    test_commands = [
        "ls -la",                           # ✓ SAFE
        "top",                              # ✓ SAFE
        "cat /var/log/syslog",             # ✓ SAFE
        "sudo systemctl restart nginx",     # ⚠️ REQUIRES_HITL
        "rm -rf /etc",                     # ✗ BLOCKED
        "reboot",                          # ✗ BLOCKED
    ]
    
    for cmd in test_commands:
        result = filter.check_command_safety(cmd)
        print(f"{cmd:40s} -> {result['status'].value:15s} ({result['reason'][:40]}...)")
