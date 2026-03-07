#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Log Parser Skill

長大なログファイルをAIが解釈可能なサイズに要約・抽出するSkill。
LLM のトークン使用量（枯渇防止）とコンテキスト圧縮を目的とする。
"""

import logging
import re
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class LogParser:
    """ログファイル解析・要約クラス"""
    
    # ログレベルの定義
    LOG_LEVELS = {
        'CRITICAL': 50,
        'ERROR': 40,
        'WARNING': 30,
        'INFO': 20,
        'DEBUG': 10
    }
    
    def __init__(self, max_output_tokens: int = 2000):
        """
        初期化
        
        Args:
            max_output_tokens: 最大出力トークン数（超過時は切り詰め）
        """
        self.max_output_tokens = max_output_tokens
        self.max_chars = max_output_tokens * 4  # トークン数を文字数に変換（概ね1トークン=4文字）
    
    def extract_tail_lines(
        self,
        log_content: str,
        num_lines: int = 50
    ) -> str:
        """
        ログの末尾N行を抽出（tail コマンドの代替）
        
        Args:
            log_content: ログファイルの全内容
            num_lines: 抽出する行数
        
        Returns:
            末尾N行（改行区切り）
        """
        lines = log_content.splitlines()
        
        if len(lines) <= num_lines:
            return log_content
        
        tail_lines = lines[-num_lines:]
        return "\n".join(tail_lines)
    
    def filter_by_keyword(
        self,
        log_content: str,
        keyword: str,
        context_lines: int = 2
    ) -> str:
        """
        特定キーワードを含む行を抽出（grep の代替）
        
        Args:
            log_content: ログファイルの内容
            keyword: フィルタリングキーワード（正規表現対応）
            context_lines: マッチ行の前後に含める行数
        
        Returns:
            マッチした行のみ（前後コンテキスト付き）
        """
        lines = log_content.splitlines()
        matching_indices = []
        
        try:
            pattern = re.compile(keyword, re.IGNORECASE)
        except re.error as e:
            logger.warning(f"Invalid regex pattern: {e}")
            return ""
        
        # マッチ行を探す
        for i, line in enumerate(lines):
            if pattern.search(line):
                matching_indices.append(i)
        
        if not matching_indices:
            return f"# キーワード '{keyword}' にマッチする行がありません"
        
        # コンテキスト付きで出力
        output_lines = []
        output_indices = set()
        
        for idx in matching_indices:
            start = max(0, idx - context_lines)
            end = min(len(lines), idx + context_lines + 1)
            output_indices.update(range(start, end))
        
        for i in sorted(output_indices):
            if i in matching_indices:
                output_lines.append(f"> {lines[i]}")  # > をマーク
            else:
                output_lines.append(f"  {lines[i]}")  # コンテキスト行
        
        return "\n".join(output_lines)
    
    def summarize_errors(
        self,
        log_content: str,
        error_level: str = "ERROR"
    ) -> Dict[str, Any]:
        """
        エラー/警告を要約
        
        Args:
            log_content: ログファイルの内容
            error_level: 抽出するレベル ("ERROR", "WARNING" など)
        
        Returns:
            エラー情報を含む辞書
        """
        lines = log_content.splitlines()
        errors = []
        warnings = []
        
        # 一般的なログフォーマット対応（journalctl, syslog など）
        error_patterns = [
            r'\berror\b|\berror occurred\b',
            r'\bfailed\b|\bfailure\b',
            r'\bexception\b',
            r'\bfatal\b',
        ]
        warning_patterns = [
            r'\bwarning\b|\bwarn\b',
            r'\bdeprecated\b',
        ]
        
        for line in lines:
            line_lower = line.lower()
            
            if any(re.search(p, line_lower) for p in error_patterns):
                errors.append(line)
            elif any(re.search(p, line_lower) for p in warning_patterns):
                warnings.append(line)
        
        return {
            "total_lines": len(lines),
            "error_count": len(errors),
            "warning_count": len(warnings),
            "recent_errors": errors[-10:],  # 最新10件
            "recent_warnings": warnings[-10:]  # 最新10件
        }
    
    def extract_time_range(
        self,
        log_content: str,
        minutes_ago: int = 60
    ) -> str:
        """
        指定された時間範囲内のログを抽出
        
        Args:
            log_content: ログファイルの内容
            minutes_ago: 現在から何分前までを対象とするか
        
        Returns:
            時間範囲内のログ
        """
        lines = log_content.splitlines()
        cutoff_time = datetime.now() - timedelta(minutes=minutes_ago)
        
        # ISO 8601 フォーマット（YYYY-MM-DDTHH:MM:SS）を探す
        iso_pattern = re.compile(r'(\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2})')
        
        filtered_lines = []
        for line in lines:
            match = iso_pattern.search(line)
            if match:
                try:
                    log_time_str = match.group(1).replace('T', ' ')
                    log_time = datetime.strptime(log_time_str, '%Y-%m-%d %H:%M:%S')
                    if log_time >= cutoff_time:
                        filtered_lines.append(line)
                except ValueError:
                    # パース失敗時はスキップ
                    continue
        
        if not filtered_lines:
            return f"# {minutes_ago} 分以内のログがありません"
        
        return "\n".join(filtered_lines)
    
    def truncate_to_max_length(self, text: str) -> str:
        """
        テキストを最大長に切り詰める
        
        Args:
            text: 入力テキスト
        
        Returns:
            切り詰めたテキスト（超過時は末尾に"[TRUNCATED]"を追加）
        """
        if len(text) <= self.max_chars:
            return text
        
        return text[:self.max_chars] + "\n\n... [TRUNCATED - 詳細はログファイルを直接確認]"
    
    def parse_and_summarize(
        self,
        log_content: str,
        keyword: Optional[str] = None,
        tail_lines: int = 50,
        max_output: bool = True
    ) -> Dict[str, Any]:
        """
        ログを包括的に解析・要約
        
        Args:
            log_content: ログファイルの内容
            keyword: フィルタリングキーワード（オプション）
            tail_lines: tail コマンドの行数
            max_output: 最大長制限を適用するか
        
        Returns:
            解析結果を含む辞書
        """
        # エラー要約
        summary = self.summarize_errors(log_content)
        
        # キーワードでフィルタされたログ
        filtered_log = ""
        if keyword:
            filtered_log = self.filter_by_keyword(log_content, keyword)
        else:
            filtered_log = self.extract_tail_lines(log_content, tail_lines)
        
        # 長さ制限を適用
        if max_output:
            filtered_log = self.truncate_to_max_length(filtered_log)
        
        return {
            "status": "success",
            "error_summary": summary,
            "filtered_content": filtered_log,
            "keyword": keyword,
            "note": "ログが長い場合は自動的に切り詰められています。詳細はサーバーのログファイルを直接確認してください。"
        }


# 使用例
if __name__ == "__main__":
    parser = LogParser(max_output_tokens=2000)
    
    # サンプルログ
    sample_log = """2026-03-03T10:00:00 INFO: System started
2026-03-03T10:01:00 INFO: Service initialized
2026-03-03T10:02:00 WARNING: Low disk space on /var
2026-03-03T10:03:00 ERROR: Connection timeout to database
2026-03-03T10:04:00 ERROR: Retry attempt 1
2026-03-03T10:05:00 ERROR: Retry attempt 2
2026-03-03T10:06:00 INFO: Connection restored
2026-03-03T10:07:00 INFO: Service recovered
"""
    
    # 使用例
    result = parser.parse_and_summarize(sample_log, keyword="ERROR")
    print(result)
