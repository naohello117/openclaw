# Azure AI Agent (OpenClaw) Bicep インフラストラクチャ テンプレート

このディレクトリには、Azure上にOpenClaw実行環境を構築するための **Bicep Infrastructure as Code テンプレート** が格納されています。

詳細な**構築実行手順**は、[構築手順書](../documents/04_構築手順書.md)を参照してください。

---

## ディレクトリ構成

```
/Bicep/
  ├── main.bicep                # メインテンプレート（全リソース定義）
  ├── parameters.json           # パラメータファイル
  ├── vnet.bicep                # VNet・Subnet・NSG モジュール
  ├── vm.bicep                  # VM・NIC・Public IP モジュール
  ├── keyvault.bicep            # Key Vault モジュール
  ├── loganalytics.bicep        # Log Analytics・App Insights モジュール
  └── README.md                 # このファイル
```

---

## インフラストラクチャ構成概要

### システムアーキテクチャ図

```
┌─────────────────────────────────────────────────────────────────┐
│ Azure Region: Japan East                                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Azure Virtual Network (VNet): 10.0.0.0/16               │  │
│  │                                                          │  │
│  │ ┌────────────────────────┐  ┌────────────────────────┐ │  │
│  │ │ Management Subnet      │  │ Target Subnet          │ │  │
│  │ │ 10.0.1.0/24            │  │ 10.0.2.0/24            │ │  │
│  │ │                        │  │                        │ │  │
│  │ │ ┌──────────────────┐   │  │ ┌──────────────────┐   │ │  │
│  │ │ │ NSG (nsg-mgmt)   │   │  │ │ NSG (nsg-target) │   │ │  │
│  │ │ │ Allow Slack HTTPS│   │  │ │ Allow SSH        │   │ │  │
│  │ │ │ Allow SSH (Ops)  │   │  │ │ from Bastion     │   │ │  │
│  │ │ │                  │   │  │ │                  │   │ │  │
│  │ │ │ ┌──────────────┐ │   │  │ │ ┌──────────────┐ │   │ │  │
│  │ │ │ │ Bastion VM   │ │   │  │ │ │ Target VMs   │ │   │ │  │
│  │ │ │ │ OpenClaw     │ │   │  │ │ │ (existing)   │ │   │ │  │
│  │ │ │ │ Ubuntu 24.04 │ │   │  │ │ │ Linux        │ │   │ │  │
│  │ │ │ │ B2ms         │ │   │  │ │ │              │ │   │ │  │
│  │ │ │ │ 64GB OS disk │ │   │  │ │ │              │ │   │ │  │
│  │ │ │ │ 128GB data   │ │   │  │ │ │              │ │   │ │  │
│  │ │ │ │ /opt/openclaw│ │   │  │ │ │              │ │   │ │  │
│  │ │ │ └──────────────┘ │   │  │ │ └──────────────┘ │   │ │  │
│  │ │ └────────────────────┘   │  │ └────────────────────┘ │  │
│  │ │                          │  │                        │  │
│  │ └──────────────────────────────────────────────────────┘  │
│  │ Service Endpoints: KeyVault, Storage                      │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Managed Services (PaaS)                                 │   │
│  │ ┌──────────────┐ ┌──────────────┐ ┌────────────────┐   │   │
│  │ │ Key Vault    │ │Log Analytics │ │ App Insights   │   │   │
│  │ │ (Secrets)    │ │(Monitoring)  │ │ (APM)          │   │   │
│  │ └──────────────┘ └──────────────┘ └────────────────┘   │   │
│  │ ┌──────────────────────────────────────────────────┐    │   │
│  │ │ Azure AI Foundry (Claude Sonnet Deployment)     │    │   │
│  │ │ 30K TPM Quota, Custom Content Filters           │    │   │
│  │ └──────────────────────────────────────────────────┘    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

External Connectivity:
  ✓ Slack API (199.145.126.0/22) → HTTPS:443
  ✓ Operations Team (133.32.181.21) → SSH:22
```

---

## 構築されるリソース一覧

### ネットワークリソース
| リソース | 名称 | 説明 |
|---------|------|------|
| VNet | `vnet-prd-aiops-001` | アドレス空間: 10.0.0.0/16 |
| Subnet (Mgmt) | `snet-mgmt-001` | 10.0.1.0/24 - Bastion VM配置用 |
| Subnet (Target) | `snet-target-001` | 10.0.2.0/24 - 既存Linux VM群 |
| NSG (Management) | `nsg-mgmt-001` | Slack webhook, SSH Inbound |
| NSG (Target) | `nsg-target-001` | Bastion からの SSH を許可 |
| Public IP | `vm-openclaw-bastion-pip` | Static IP (Bastion用) |

### 仮想マシンリソース
| リソース | 名称 | スペック |
|---------|------|---------|
| VM | `vm-openclaw-bastion` | Ubuntu 24.04 LTS, Standard_B2ms |
| OS Disk | `vm-openclaw-bastion-osdisk` | Premium SSD 64GB |
| Data Disk | `vm-openclaw-bastion-datadisk` | Standard SSD 128GB (/opt/openclaw) |
| NIC | `vm-openclaw-bastion-nic` | Static Private IP: 10.0.1.4 |
| Managed Identity | System Assigned | Key Vault アクセス用 |

### 管理・監視リソース
| リソース | 名称 | 説明 |
|---------|------|------|
| Key Vault | `kv-prd-aiops-xxx` | API Key, SSH秘密鍵, Slack Token保存 |
| Log Analytics | `log-prd-aiops-001` | ログ・監査ログ収集（30日保持） |
| App Insights | `ai-prd-aiops-001` | アプリケーション監視・APM |
| Cognitive Services | `hub-prd-aiops-001` | Azure AI Foundry ハブ |
| Storage Account | `stprdaiops<suffix>` | AI Foundry データ保存 |
| Action Group | `ag-prd-aiops-alerts` | アラート送信先（Email等） |

---

## Bicep テンプレートモジュール説明

### main.bicep
**メインテンプレート - 全リソース統合**
- パラメータ定義（プロジェクト名、環境、リージョン、ネットワーク設定等）
- すべてのAzureリソース作成
- リソース間の依存関係管理
- 出力値の定義（VNet ID, VM IP, Key Vault URL等）

### vnet.bicep
**ネットワークインフラストラクチャ**
- VNet作成（10.0.0.0/16）
- 管理サブネット作成（10.0.1.0/24）
- 対象サブネット作成（10.0.2.0/24）
- NSG作成・セキュリティルール設定
  - Allow_Inbound_Slack: 199.145.126.0/22 → HTTPS 443
  - Allow_Inbound_SSH: 133.32.181.21 → TCP 22
- Service Endpoints設定（KeyVault, Storage）

### vm.bicep
**中継サーバーVM構築**
- VM リソース（Ubuntu 24.04 LTS）
- ディスク管理
  - OS ディスク：Premium SSD 64GB
  - データディスク：Standard SSD 128GB
- Network Interface（Static IP: 10.0.1.4）
- Public IP（Static割び当て）
- Managed Identity（System Assigned）
- SSH 公開鍵認証設定

### keyvault.bicep
**シークレット管理基盤**
- Key Vault リソース（Standard SKU）
- アクセスポリシー：VM Managed ID → Get/List権限
- Purge Protection有効化
- Soft Delete有効化（誤削除対策）

### loganalytics.bicep
**ログ・監視基盤**
- Log Analytics Workspace作成
- SKU: PerGB2018（従量課金）
- 保持期間：30日（カスタマイズ可）
- Application Insights作成
- App Insights ↔ Log Analytics リンク

---

## ネットワークセキュリティ構成

### Management NSG (nsg-mgmt-001) - Inbound Rules

| 優先度 | ルール名 | プロトコル | ポート | ソース | アクション |
|-------|---------|-----------|-------|--------|----------|
| 100 | Allow_Inbound_Slack | TCP | 443 | 199.145.126.0/22 | **許可** |
| 110 | Allow_Inbound_SSH | TCP | 22 | 133.32.181.21 | **許可** |
| 4096 | Deny_All_Inbound | Any | Any | Any | **拒否** |

**Outbound Rules:**
- HTTPS 443 → Azure Cloud Services (KeyVault, Storage)
- HTTPS 443 → Slack API
- TCP 22 → Target Subnet (対象VM へのSSH)

### Target NSG (nsg-target-001) - Inbound Rules

| 優先度 | ルール名 | プロトコル | ポート | ソース | アクション |
|-------|---------|-----------|-------|--------|----------|
| 100 | Allow_SSH_From_OpenClaw | TCP | 22 | 10.0.1.0/24 | **許可** |

**用途**: Bastion（10.0.1.4）からのSSH接続のみ許可

---

## VM リソース仕様

| 項目 | 値 | 説明 |
|------|-----|------|
| **OS** | Ubuntu 24.04 LTS | 標準Long-Term Support版 |
| **イメージ発行元** | Canonical | 公式提供イメージ |
| **VM サイズ** | Standard_B2ms | 2 vCPU, 8GB RAM, バーストキャップ |
| **OS ディスク** | Premium_LRS 64GB | 高性能SSD |
| **データディスク** | Standard_LRS 128GB | /opt/openclaw マウント |
| **認証** | SSH公開鍵のみ | パスワード認証無効 |
| **管理者ユーザー** | azureuser | システム初期化用 |
| **プライベート IP** | 10.0.1.4 | Static割り当て |
| **Managed Identity** | System Assigned | Key Vault アクセス用 |

---

## パラメータ詳細

### parameters.json の主要パラメータ

| パラメータ名 | デフォルト値 | 設定値範囲 | 説明 |
|-------------|------------|---------|------|
| `projectName` | aiops | 任意の文字列 | プロジェクト識別子 |
| `environment` | prod | prod/staging/dev | 環境区別用 |
| `location` | japaneast | Azure regions | デプロイ対象リージョン |
| `vnetAddressSpace` | 10.0.0.0/16 | /16 CIDR | VNet アドレス空間 |
| `mgmtSubnetAddressSpace` | 10.0.1.0/24 | /24 CIDR | 管理サブネット |
| `targetSubnetAddressSpace` | 10.0.2.0/24 | /24 CIDR | 対象サブネット |
| `vmSize` | Standard_B2ms | Azure VM sizes | 中継サーバーVM仕様 |
| `vmAdminUsername` | azureuser | 英数字 | VM管理者名 |
| `sshPublicKey` | (必須) | SSH公開鍵 | ユーザー認証用 |
| `logAnalyticsRetention` | 30 | 1-730日 | ログ保持期間 |

---

## デプロイメント時の注意事項

### 構築手順書への参照
- **パラメータ設定**: [構築手順書 セクション2](../documents/04_構築手順書.md#2-デプロイ準備と認証)
- **デプロイコマンド**: [構築手順書 セクション3](../documents/04_構築手順書.md#3-bicep-テンプレートのデプロイ)
- **デプロイ後設定**: [構築手順書 セクション5以降](../documents/04_構築手順書.md#5-中継サーバー-vm-の初期化)

### リソース命名規則
- VNet: `vnet-<env>-<project>-###`
- Subnet: `snet-<role>-###`
- NSG: `nsg-<role>-###`
- VM: `vm-<role>-<project>`
- Key Vault: `kv-<env>-<project>-<unique>`

---

## 運用上の留意点

### VM 自動シャットダウン
- **設定**: なし（24時間稼働）
- **オプション**: Azure Portal で自動シャットダウンポリシーを追加可

### Key Vault セキュリティ
- **Purge Protection**: 有効（削除後90日間回復可能）
- **Soft Delete**: 有効
- **ネットワークアクセス**: Allow All（VNetサービスエンドポイント使用）

### Log Analytics
- **SKU**: PerGB2018（従量課金）
- **保持期間**: 30日（可変）
- **クエリ言語**: KQL (Kusto Query Language)

### バックアップ・リカバリ
- **VM スナップショット**: ユーザーが定期的に作成
- **Key Vault シークレット**: Soft Delete により90日以内に回復可

---

## 参考リンク

- **[構築手順書](../documents/04_構築手順書.md)** - デプロイ実行手順（必読）
- **[詳細設計書](../documents/03_詳細設計書.md)** - インフラ詳細仕様
- **[基本設計書](../documents/02_基本設計書.md)** - システム設計方針
- **[Azure Bicep Documentation](https://learn.microsoft.com/ja-jp/azure/azure-resource-manager/bicep/)**
- **[Azure CLI リファレンス](https://learn.microsoft.com/ja-jp/cli/azure/)**

---

**更新日**: 2026年3月7日
