#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SSH Command Executor Skill

対象の Linux VM に SSH 接続し、コマンドを実行して結果を返す Skill。
Azure Key Vault から SSH 秘密鍵を動的に取得して利用する。
"""

import paramiko
import logging
from typing import Dict, Any, Optional
from azure.identity import ManagedIdentityCredential
from azure.keyvault.secrets import SecretClient
from datetime import datetime

logger = logging.getLogger(__name__)


class SSHExecutor:
    """SSH コマンド実行の管理クラス"""
    
    def __init__(self, key_vault_url: str, key_name: str, username: str = "ai_agent", timeout: int = 30):
        """
        初期化
        
        Args:
            key_vault_url: Azure Key Vault の URL（例: https://kv-prd-aiops-001.vault.azure.net/）
            key_name: Key Vault に保存された SSH 秘密鍵のシークレット名
            username: SSH 接続ユーザー名（デフォルト: ai_agent）
            timeout: SSH 接続タイムアウト（秒）
        """
        self.key_vault_url = key_vault_url
        self.key_name = key_name
        self.username = username
        self.timeout = timeout
        self.ssh_key = None  # キャッシュ用
        self._load_ssh_key()
    
    def _load_ssh_key(self) -> None:
        """マネージド ID を用いて Key Vault から SSH 秘密鍵を取得"""
        try:
            credential = ManagedIdentityCredential()
            client = SecretClient(vault_url=self.key_vault_url, credential=credential)
            secret = client.get_secret(self.key_name)
            self.ssh_key = paramiko.RSAKey.from_private_key_file(
                secret.value  # ※実際は一時ファイルに書き込む必要があります
            )
            logger.info(f"SSH key loaded from Key Vault: {self.key_name}")
        except Exception as e:
            logger.error(f"Failed to load SSH key from Key Vault: {e}")
            raise
    
    def execute_command(
        self, 
        target_ip: str, 
        command: str,
        command_timeout: int = 60
    ) -> Dict[str, Any]:
        """
        対象 VM でコマンドを実行
        
        Args:
            target_ip: 対象 VM の IP アドレス
            command: 実行するコマンド
            command_timeout: コマンド実行タイムアウト（秒）
        
        Returns:
            実行結果を含む辞書：
            {
                "status": "success" | "error" | "timeout" | "exception",
                "exit_code": int or None,
                "stdout": str,
                "stderr": str,
                "error_message": str (exception の場合のみ),
                "duration_sec": float
            }
        """
        start_time = datetime.now()
        ssh = None
        
        try:
            # SSH クライアントの初期化
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # 接続
            logger.info(f"Connecting to {target_ip}:{self.username}")
            ssh.connect(
                hostname=target_ip,
                username=self.username,
                pkey=self.ssh_key,
                timeout=self.timeout,
                auth_timeout=self.timeout
            )
            
            # コマンド実行
            logger.info(f"Executing command: {command}")
            stdin, stdout, stderr = ssh.exec_command(command, timeout=command_timeout)
            exit_code = stdout.channel.recv_exit_status()
            
            # 結果取得
            stdout_text = stdout.read().decode('utf-8', errors='ignore')
            stderr_text = stderr.read().decode('utf-8', errors='ignore')
            
            duration = (datetime.now() - start_time).total_seconds()
            
            result = {
                "status": "success" if exit_code == 0 else "error",
                "exit_code": exit_code,
                "stdout": stdout_text,
                "stderr": stderr_text,
                "duration_sec": duration,
                "target_ip": target_ip,
                "command": command
            }
            
            if exit_code != 0:
                logger.warning(f"Command failed with exit code {exit_code}: {stderr_text[:100]}")
            else:
                logger.info(f"Command succeeded (duration: {duration:.2f}s)")
            
            return result
            
        except paramiko.SSHException as e:
            duration = (datetime.now() - start_time).total_seconds()
            logger.error(f"SSH error: {e}")
            return {
                "status": "exception",
                "exit_code": None,
                "stdout": "",
                "stderr": "",
                "error_message": f"SSH Error: {str(e)}",
                "duration_sec": duration,
                "target_ip": target_ip,
                "command": command
            }
        
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            logger.error(f"Unexpected error: {e}")
            return {
                "status": "exception",
                "exit_code": None,
                "stdout": "",
                "stderr": "",
                "error_message": f"Unexpected Error: {str(e)}",
                "duration_sec": duration,
                "target_ip": target_ip,
                "command": command
            }
        
        finally:
            if ssh:
                ssh.close()
    
    def execute_multiple_commands(
        self, 
        target_ip: str, 
        commands: list
    ) -> Dict[str, Any]:
        """
        複数のコマンドを順に実行
        
        Args:
            target_ip: 対象 VM の IP アドレス
            commands: コマンドのリスト
        
        Returns:
            すべての実行結果のリスト
        """
        results = []
        for cmd in commands:
            result = self.execute_command(target_ip, cmd)
            results.append(result)
            
            # エラーの場合は中断
            if result["status"] != "success":
                logger.warning(f"Stopping further commands due to error: {result['error_message']}")
                break
        
        return {
            "status": "complete",
            "total_commands": len(commands),
            "successful_commands": sum(1 for r in results if r["status"] == "success"),
            "results": results
        }


# 使用例
if __name__ == "__main__":
    # 設定
    KEY_VAULT_URL = "https://kv-prd-aiops-001.vault.azure.net/"
    KEY_SECRET_NAME = "SSH-Key-TargetVMs"
    
    # インスタンス化
    executor = SSHExecutor(KEY_VAULT_URL, KEY_SECRET_NAME)
    
    # 単一コマンド実行
    result = executor.execute_command("10.0.2.10", "uname -a")
    print(result)
    
    # 複数コマンド実行
    commands = ["hostname", "free -h", "df -h"]
    results = executor.execute_multiple_commands("10.0.2.10", commands)
    print(results)
