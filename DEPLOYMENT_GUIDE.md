# 🚀 Claude Bridge デプロイメントガイド

他のプロジェクトでClaude Bridgeを使用するための方法を説明します。

## 📋 使用方法の選択肢

### 方法1: スタンドアローン実行（推奨）
他のプロジェクトフォルダから独立してClaude Bridgeを実行する方法

### 方法2: プロジェクト内統合
各プロジェクトにClaude Bridgeを組み込む方法

### 方法3: パッケージ化インストール
PyPIパッケージとして配布・インストールする方法（将来対応）

---

## 🎯 方法1: スタンドアローン実行（推奨）

### メリット
- ✅ プロジェクトファイルを汚染しない
- ✅ 一度セットアップすれば全プロジェクトで使用可能
- ✅ Claude Bridgeの更新が簡単
- ✅ 複数プロジェクト間の切り替えが容易

### セットアップ手順

#### Step 1: Claude Bridgeのクローン
```bash
# 専用ディレクトリに配置
cd ~/tools  # または任意の場所
git clone https://github.com/NewAITees/Claude-Bridge.git
cd Claude-Bridge
```

#### Step 2: Discord設定（一回のみ）
```bash
# 設定ファイル作成
mkdir -p config
cp config/discord_config.json.example config/discord_config.json
# discord_config.jsonを編集してトークンとIDを設定
```

#### Step 3: 起動スクリプト作成
`~/bin/claude-bridge`（またはPATHの通った場所）を作成：

```bash
#!/bin/bash
# Claude Bridge Launcher

BRIDGE_PATH="$HOME/tools/Claude-Bridge"
WORK_DIR="$(pwd)"

echo "🌉 Claude Bridge - Project: $(basename "$WORK_DIR")"
echo "🔗 Working Directory: $WORK_DIR"

cd "$BRIDGE_PATH"

# 設定ファイルを動的に更新
CONFIG_FILE="config/discord_config_dynamic.json"
cat > "$CONFIG_FILE" << EOF
{
  "discord": {
    "token": "$(jq -r '.discord.token' config/discord_config.json)",
    "guild_id": "$(jq -r '.discord.guild_id' config/discord_config.json)",
    "channel_id": "$(jq -r '.discord.channel_id' config/discord_config.json)"
  },
  "claude_code": {
    "command": "claude-code",
    "working_directory": "$WORK_DIR",
    "timeout": 30
  },
  "session": {
    "timeout": 3600,
    "max_output_length": 1900,
    "max_history": 100,
    "cleanup_interval": 60
  },
  "logging": {
    "level": "INFO",
    "file": "logs/claude_bridge_$(basename "$WORK_DIR").log",
    "max_size": "10MB",
    "backup_count": 3
  }
}
EOF

# Claude Bridge実行
./run_discord.sh --config "$CONFIG_FILE"
```

#### Step 4: 実行権限付与
```bash
chmod +x ~/bin/claude-bridge
# PATHに~/binが含まれていることを確認
echo 'export PATH="$HOME/bin:$PATH"' >> ~/.bashrc  # または ~/.zshrc
source ~/.bashrc
```

#### Step 5: 任意のプロジェクトで使用
```bash
# 任意のプロジェクトディレクトリで
cd /path/to/your/project
claude-bridge
```

---

## 🔧 方法2: プロジェクト内統合

### メリット
- ✅ プロジェクト固有の設定が可能
- ✅ チーム開発での共有が容易
- ✅ プロジェクトと一体化した管理

### セットアップ手順

#### Step 1: Claude Bridgeをサブモジュールとして追加
```bash
cd /path/to/your/project
git submodule add https://github.com/NewAITees/Claude-Bridge.git tools/claude-bridge
git submodule update --init --recursive
```

#### Step 2: プロジェクト設定作成
```bash
mkdir -p .claude-bridge
cp tools/claude-bridge/config/discord_config.json .claude-bridge/
# .claude-bridge/discord_config.json を編集
```

#### Step 3: 起動スクリプト作成
`scripts/start-claude-bridge.sh`:
```bash
#!/bin/bash
cd tools/claude-bridge

# プロジェクト固有の設定で実行
./run_discord.sh --config "../../.claude-bridge/discord_config.json"
```

#### Step 4: .gitignore設定
```bash
echo ".claude-bridge/discord_config.json" >> .gitignore
echo "tools/claude-bridge/logs/" >> .gitignore
```

#### Step 5: 実行
```bash
./scripts/start-claude-bridge.sh
```

---

## 📦 方法3: Docker Compose統合

### メリット
- ✅ 環境の完全な分離
- ✅ 依存関係の問題なし
- ✅ 本番環境での安定動作

### セットアップ手順

#### Step 1: docker-compose.yml作成
```yaml
version: '3.8'
services:
  claude-bridge:
    build:
      context: https://github.com/NewAITees/Claude-Bridge.git
      dockerfile: Dockerfile
    volumes:
      - .:/workspace
      - ./claude-bridge-config:/app/config
      - ./claude-bridge-logs:/app/logs
    environment:
      - CLAUDE_BRIDGE_WORK_DIR=/workspace
    networks:
      - bridge
    restart: unless-stopped

networks:
  bridge:
    driver: bridge
```

#### Step 2: 設定ディレクトリ作成
```bash
mkdir -p claude-bridge-config claude-bridge-logs
cp path/to/discord_config.json claude-bridge-config/
```

#### Step 3: 実行
```bash
docker-compose up claude-bridge
```

---

## 🛠️ 高度な使用方法

### 複数プロジェクト同時実行

#### 方法A: 異なるDiscordチャンネル使用
```bash
# プロジェクトA用設定
cp config/discord_config.json config/project_a_config.json
# channel_idを変更

# プロジェクトB用設定  
cp config/discord_config.json config/project_b_config.json
# channel_idを変更

# 同時実行
claude-bridge --config config/project_a_config.json &
claude-bridge --config config/project_b_config.json &
```

#### 方法B: セッション管理UI
```bash
# セッション管理機能（今後実装予定）
claude-bridge --session-manager
# Web UIで複数プロジェクトを管理
```

### CI/CD統合

#### GitHub Actions例
```yaml
name: Claude Bridge Integration
on: [push, pull_request]

jobs:
  claude-bridge:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Claude Bridge
        run: |
          git clone https://github.com/NewAITees/Claude-Bridge.git /tmp/claude-bridge
          cd /tmp/claude-bridge
          docker build -t claude-bridge .
      
      - name: Run with Claude Bridge
        env:
          DISCORD_TOKEN: ${{ secrets.DISCORD_TOKEN }}
          DISCORD_GUILD_ID: ${{ secrets.DISCORD_GUILD_ID }}
          DISCORD_CHANNEL_ID: ${{ secrets.DISCORD_CHANNEL_ID }}
        run: |
          docker run --rm \
            -v "$PWD":/workspace \
            -e DISCORD_TOKEN \
            -e DISCORD_GUILD_ID \
            -e DISCORD_CHANNEL_ID \
            claude-bridge
```

---

## 📋 設定のカスタマイズ

### プロジェクト固有設定

#### `.claude-bridge.json` (プロジェクトルート)
```json
{
  "claude_code": {
    "command": "claude-code",
    "timeout": 60,
    "auto_save": true
  },
  "features": {
    "code_review": true,
    "auto_test": true,
    "git_integration": true
  },
  "ui": {
    "theme": "dark",
    "compact_mode": false
  }
}
```

### 環境変数での設定
```bash
export CLAUDE_BRIDGE_TOKEN="your-discord-token"
export CLAUDE_BRIDGE_GUILD_ID="your-guild-id"
export CLAUDE_BRIDGE_CHANNEL_ID="your-channel-id"
export CLAUDE_BRIDGE_WORK_DIR="/path/to/project"

claude-bridge --env-config
```

---

## 🚨 注意事項とベストプラクティス

### セキュリティ
- ✅ Discord設定ファイルは`.gitignore`に追加
- ✅ 環境変数でのトークン管理を推奨
- ✅ 本番環境では専用のBotアカウントを使用

### パフォーマンス
- ✅ 長時間実行時はログローテーション設定
- ✅ メモリ使用量の監視
- ✅ 複数セッション時のリソース管理

### チーム開発
- ✅ プロジェクトごとの設定ファイル管理
- ✅ チャンネル分離による衝突回避
- ✅ ドキュメント化された起動手順

### トラブルシューティング
- ✅ ログファイルの定期確認
- ✅ Claude Codeとの互換性確認
- ✅ Discord API制限の監視

---

## 🎉 まとめ

**推奨使用方法**：
1. **単発プロジェクト**: 方法1（スタンドアローン実行）
2. **チーム開発**: 方法2（プロジェクト内統合）
3. **本番環境**: 方法3（Docker Compose統合）

どの方法でも、一度セットアップすれば任意のプロジェクトでClaude CodeをDiscord経由で操作できるようになります！