# Azure AI Agent (OpenClaw) Bicep テンプレート

このリポジトリでは、Azure上にAIエージェント環境を **Bicep による Infrastructure as Code** でデプロイします。

## ディレクトリ構成

```
/infrastructure/
  ├── main.bicep                # メインテンプレート（すべてのリソースを定義）
  ├── parameters.json           # パラメータファイル（環境値を定義）
  ├── vnet.bicep               # VNet・Subnet・NSG モジュール
  ├── vm.bicep                 # VM・NIC・Public IP モジュール
  ├── keyvault.bicep           # Key Vault モジュール
  ├── loganalytics.bicep       # Log Analytics・App Insights モジュール
  └── README.md                # このファイル
```

## 前提条件

- Azure CLI v2.45.0 以上
- Bicep CLI v0.20.0 以上
- PowerShell 7.0 以上またはbash
- Azure サブスクリプション（Contributor 権限以上）
- SSH 公開鍵（`~/.ssh/id_rsa.pub` など）

## インストール

### 1. Azure CLI と Bicep のインストール

```bash
# Azure CLI をインストール
# https://learn.microsoft.com/cli/azure/install-azure-cli

# Bicep をインストール
az bicep install
az bicep upgrade  # 最新版に更新
```

### 2. このリポジトリをクローン

```bash
git clone <your-repo-url>
cd openclaw-infrastructure/infrastructure
```

## デプロイ手順

### ステップ1: SSH 公開鍵の準備

```bash
# 既存の公開鍵を確認
cat ~/.ssh/id_rsa.pub

# または新規作成
ssh-keygen -t rsa -N "" -f ~/.ssh/id_rsa
```

公開鍵の内容をコピー。

### ステップ2: パラメータファイルの編集

`parameters.json` を開いて、環境に合わせて値を設定：

```json
{
  "parameters": {
    "sshPublicKey": {
      "value": "ssh-rsa AAAA... user@hostname"  // ← この部分に公開鍵を貼り付け
    },
    "projectName": {
      "value": "aiops"  // プロジェクト名（任意）
    },
    "environment": {
      "value": "prod"   // 環境（prod/staging/dev）
    }
  }
}
```

### ステップ3: Azure への認証

```powershell
# PowerShell の場合
az login
az account set --subscription "<SubscriptionID>"

# 確認
az account show
```

### ステップ4: リソースグループの作成

```powershell
$resourceGroupName = "rg-aiops-prod"
$location = "japaneast"

az group create `
  --name $resourceGroupName `
  --location $location
```

### ステップ5: テンプレートの検証

デプロイ前に、テンプレートが正しいか確認：

```powershell
az deployment group validate `
  --resource-group $resourceGroupName `
  --template-file .\main.bicep `
  --parameters .\parameters.json
```

### ステップ6: デプロイのドライラン

`--what-if` で何が起こるか確認：

```powershell
az deployment group create `
  --resource-group $resourceGroupName `
  --template-file .\main.bicep `
  --parameters .\parameters.json `
  --what-if
```

### ステップ7: 本デプロイ

```powershell
az deployment group create `
  --resource-group $resourceGroupName `
  --template-file .\main.bicep `
  --parameters .\parameters.json
```

デプロイには約 10～15 分かかります。

### ステップ8: デプロイ結果の確認

```powershell
# リソースの一覧表示
az resource list --resource-group $resourceGroupName -o table

# 特定リソースの詳細確認
az vm show --resource-group $resourceGroupName --name "vm-openclaw-bastion"
```

## Bicep テンプレートの説明

### main.bicep

全リソースを定義するメインテンプレート。以下を含む：

| 項目 | リソース名 | 説明 |
| :--- | :--- | :--- |
| ネットワーク | `vnet-prd-aiops-001` | VNet、Subnet、NSG |
| 仮想マシン | `vm-openclaw-bastion` | Bastion VM (Ubuntu 24.04) |
| Key Vault | `kv-prd-aiops-xxx` | シークレット管理 |
| Log Analytics | `log-prd-aiops-001` | ログ収集・監視 |
| App Insights | `ai-prd-aiops-001` | アプリケーション監視 |
| Cognitive Services | `hub-prd-aiops-001` | Azure AI Foundry 基盤 |

### モジュール化テンプレート

より大規模な環境では、モジュール化されたテンプレートを使用：

```powershell
# vnet.bicep, vm.bicep, keyvault.bicep などを使用する場合
az deployment group create `
  --resource-group $resourceGroupName `
  --template-file .\modular-main.bicep `
  --parameters .\parameters.json
```

## Key Vault へのシークレット登録

デプロイ後、以下のコマンドでシークレットを登録：

```powershell
# AI Foundry API キー
az keyvault secret set `
  --vault-name "kv-prd-aiops-001" `
  --name "AIFoundry-API-Key" `
  --value "<your-api-key>"

# Slack Bot トークン
az keyvault secret set `
  --vault-name "kv-prd-aiops-001" `
  --name "Slack-Bot-Token" `
  --value "xoxb-..."

# SSH 秘密鍵
az keyvault secret set `
  --vault-name "kv-prd-aiops-001" `
  --name "SSH-Key-TargetVMs" `
  --file ~/.ssh/id_rsa
```

## トラブルシューティング

### エラー: "Bicep CLI not found"

```powershell
az bicep upgrade
```

### エラー: "Insufficient privileges"

Contributor 権限があるか確認：

```powershell
az role assignment list --scope /subscriptions/<SubscriptionID> --query "[].roleDefinitionName" -o table
```

### エラー: "The name is not available"

リソース名が既に存在しています。`parameters.json` の `projectName` や `environment` を変更してください。

### VM への接続テスト

```bash
# パブリック IP を取得
$publicIp = az vm show --resource-group $resourceGroupName --name vm-openclaw-bastion --show-details --query publicIps -o tsv

# SSH で接続
ssh -i ~/.ssh/id_rsa azureuser@$publicIp
```

## 設定のアップデート

構成を変更する場合：

```powershell
# parameters.json を編集した後

az deployment group create `
  --resource-group $resourceGroupName `
  --template-file .\main.bicep `
  --parameters .\parameters.json
```

変更は冪等です。既に存在するリソースは上書きされず、変更部分のみ更新されます。

## リソースの削除

すべてのリソースを削除する場合：

```powershell
az group delete --name $resourceGroupName --yes
```

⚠️ **注意**: この操作は取り消せません。

## 参考リンク

- [Azure Bicep Documentation](https://learn.microsoft.com/ja-jp/azure/azure-resource-manager/bicep/)
- [Azure CLI リファレンス](https://learn.microsoft.com/ja-jp/cli/azure/)
- [詳細設計書](../詳細設計書.md)
- [構築手順書](../構築手順書.md)

## サポート

質問や問題がある場合は、GitHub Issues を作成してください。