# 熟練Linuxエンジニア育成（AIエージェント化）プロジェクト

このリポジトリは、Azure上にAIエージェント（OpenClaw）を構築・運用するための完全なパッケージです。

## 🎯 プロジェクト概要

Claude Sonnet 4.6 を LLM 基盤として、Slackを介してAIエージェントが Linux サーバーの運用タスク（調査、トラブルシューティング、復旧）を自律的に実行できるシステムです。

**主な目標:**
- Linuxエンジニアの育成と運用効率化
- トラブルシューティングの自動化・標準化
- セキュリティと人間による承認を担保した運用

## 📁 リポジトリ構成

```
openclaw/
├── infrastructure/              # Bicep テンプレート（IaC）
│   ├── main.bicep              # メインテンプレート
│   ├── parameters.json         # パラメータファイル
│   ├── vnet.bicep
│   ├── vm.bicep
│   ├── keyvault.bicep
│   ├── loganalytics.bicep
│   └── README_Bicep.md         # Bicep デプロイガイド
│
├── application/                # OpenClaw アプリケーション
│   ├── config/
│   │   └── settings.yaml       # アプリケーション設定
│   ├── prompts/
│   │   ├── system_prompt.md    # AI ペルソナ・基本原則
│   │   └── guardrails.md       # ガードレール（禁止操作）
│   ├── inventory/
│   │   └── targets.yaml        # 対象 VM リスト
│   ├── skills/
│   │   ├── ssh_executor.py     # SSH コマンド実行
│   │   └── log_parser.py       # ログ解析・要約
│   ├── core/
│   │   ├── command_filter.py   # コマンドフィルタリング
│   │   └── hitl_manager.py     # Human-in-the-Loop 制御
│   ├── requirements.txt        # Python 依存ライブラリ
│   ├── .gitignore
│   └── main.py                 # アプリケーションエントリポイント（TODO）
│
├── documents/                   # 設計・手順書
│   ├── 01_要件定義書.md
│   ├── 02_基本設計書.md
│   ├── 03_詳細設計書.md
│   ├── 04_構築手順書.md        # ⭐ こちらから開始
│   ├── 05_試験成績書.md
│   └── README.md
│
├── .gitignore
└── README.md                   # このファイル
```

## 🚀 クイックスタート

### 1. リポジトリをクローン

```bash
git clone <your-repo-url>
cd openclaw
```

### 2. Bicep テンプレートでインフラをデプロイ

```bash
cd infrastructure
# README_Bicep.md の手順に従う
az login
az deployment group create --resource-group rg-aiops-prod --template-file main.bicep --parameters parameters.json
```

### 3. アプリケーションをセットアップ

```bash
cd ../application
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

pip install -r requirements.txt
```

### 4. 設定ファイルを編集

```bash
nano config/settings.yaml
# 環境に合わせて以下を編集：
# - LLM エンドポイント
# - Slack Webhook URL
# - Key Vault リソース情報
```

### 5. 対象 VM インベントリを設定

```bash
nano inventory/targets.yaml
# 対象となる Linux VM を登録
```

### 6. アプリケーション実行（開発モード）

```bash
python3 main.py  # 実装待ち
```

## 📖 ドキュメント

セクション別ガイド：

| ドキュメント | 内容 | 対象者 |
| :--- | :--- | :--- |
| **01_要件定義書.md** | プロジェクトの背景・目的・機能要件 | PM, ステークホルダー |
| **02_基本設計書.md** | システムアーキテクチャ・ネットワーク設計 | 設計者, アーキテクト |
| **03_詳細設計書.md** | Azure リソース詳細・Bicep パラメータ・実装仕様 | インフラ担当, 開発者 |
| **04_構築手順書.md** | ステップバイステップ デプロイ手順 | インフラ構築担当 |
| **05_試験成績書.md** | 機能・非機能テスト項目と結果記録 | QA, テスター |
| **infrastructure/README_Bicep.md** | Bicep テンプレートの詳細ガイド | インフラ担当 |

## 🛠️ Bicep テンプレートについて

このプロジェクトは **Infrastructure as Code (IaC)** として Bicep を採用しています。

**主な リソース:**
- Virtual Network (VNet) + Subnets
- Network Security Groups (NSG)
- OpenClaw 実行用 VM（Ubuntu 24.04 LTS）
- Azure Key Vault（シークレット管理）
- Azure Log Analytics（ロギング）
- Azure AI Foundry（LLM 推論基盤）

詳細は [infrastructure/README_Bicep.md](infrastructure/README_Bicep.md) を参照してください。

## 🔧 アプリケーション構成

### Skills（機能モジュール）
- **ssh_executor.py**: 対象 VM での SSH コマンド実行
- **log_parser.py**: ログ解析・要約・トークン圧縮

### Core Logic（核心ロジック）
- **command_filter.py**: コマンドのブラックリスト検証（ガードレール）
- **hitl_manager.py**: Human-in-the-Loop（人間承認）制御

### Configuration
- **config/settings.yaml**: LLM、Slack、SSH接続設定
- **prompts/system_prompt_.md**: AI ペルソナ定義
- **prompts/guardrails.md**: 禁止操作・安全ルール
- **inventory/targets.yaml**: 対象 VM リスト

## 🔐 セキュリティ

このシステムは複数レイヤーのセキュリティを備えています：

1. **ネットワークセキュリティ**: NSG による通信制御
2. **シークレット管理**: Azure Key Vault で API キー、SSH 鍵を暗号化保存
3. **コマンドフィルタリング**: ガードレール（禁止操作ブロック）
4. **Human-in-the-Loop**: 危険な操作は人間承認が必須
5. **監査ログ**: すべての操作を Log Analytics に記録

詳細は各設計書を参照。

## 📊 ロードマップ

- **Phase 1 (Read-Only)**: 参照系コマンドのみ実行
- **Phase 2 (Human-in-the-Loop)**: 更新系操作は人間承認後に実行
- **Phase 3 (Autonomous)**: 監視アラート契機で完全自律実行（将来）

## 🧪 テスト・検証

試験成績書（[documents/05_試験成績書.md](documents/05_試験成績書.md)）で機能・非機能要件の検証を記録します。

実機テスト前に必ず以下を確認：
- Bicep デプロイの成功
- Key Vault シークレット登録
- SSH 接続テスト
- Slack 連携テスト

## 📞 サポート・問い合わせ

- Issue: GitHub Issues で機能リクエスト・バグ報告
- Discussion: 設計・実装についての議論
- Wiki: よくある質問・トラブルシューティング

## 📄 ライセンス

（プロジェクトのライセンスを記入してください）

## 👥 貢献

プルリクエスト大歓迎です。大きな変更の場合は、事前に Issue で提案してください。

---

**最終更新**: 2026年3月3日  
**バージョン**: 1.0.0-dev
