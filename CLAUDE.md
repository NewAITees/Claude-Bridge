# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## プロジェクト概要

Claude Bridgeは、Claude CodeとのインタラクティブなセッションをPCターミナルとDiscordアプリの両方で同時に操作できるようにするブリッジアプリケーションです。

## 技術スタック

- **メイン言語**: Python 3.12+ (uvパッケージマネージャー推奨)
- **Discord API**: discord.py 2.0+
- **プロセス制御**: subprocess, pexpect
- **非同期処理**: asyncio
- **設定管理**: JSON/YAML
- **開発環境**: Docker + modern-python-base:latest
- **AIツール**: Claude Code CLI, Gemini CLI

## 主要コンポーネント

### 1. セッション管理システム
- セッション番号によるペアリング認証
- セッション状態の監視・管理
- 複数インターフェース間の状態同期

### 2. プロセス制御システム
- Claude Codeプロセスの起動・監視・制御
- 異常終了時の自動復旧機能
- リアルタイム入出力の中継

### 3. Discord Bot インターフェース
- 基本コマンド（/connect、/disconnect、/status、/output、/history）
- インタラクティブUI変換（確認ダイアログ、選択メニュー）
- Discord制限対応（2000文字制限、ANSIエスケープシーケンス除去）

### 4. 出力制御システム
- 文字数制限対応（分割・要約処理）
- プログレス表示のDiscord適応
- リアルタイムバッファリング

## 開発時の注意事項

### セキュリティ
- 個人利用専用設計（単一ユーザー対応）
- セッション番号による認証
- 機密情報の取り扱いに注意

### パフォーマンス制約
- Discord API制限の考慮
- メモリ使用量200MB以下
- CPU使用率平均5%以下

### 互換性
- 主にLinux/macOS対応
- Python 3.9以上必須
- Claude Code公式ツールとの互換性維持

## 開発フェーズ

### Phase 1: 基本機能
- Claude Codeプロセス制御
- Discord Bot基本機能
- セッション管理システム

### Phase 2: 出力制御
- ANSIエスケープシーケンス除去
- 文字数制限対応
- リアルタイム出力バッファリング

### Phase 3: UI/UX向上
- インタラクティブUI変換
- 長時間処理の進捗表示
- コマンド補完・履歴機能

## 設定例

```json
{
  "discord": {
    "token": "YOUR_DISCORD_BOT_TOKEN",
    "guild_id": "YOUR_GUILD_ID",
    "channel_id": "YOUR_CHANNEL_ID"
  },
  "claude_code": {
    "command": "claude-code",
    "working_directory": "/path/to/your/project"
  },
  "session": {
    "timeout": 3600,
    "max_output_length": 1900
  }
}
```

## 制約事項

### Discord制限
- メッセージ長さ: 2000文字
- 添付ファイル: 8MB（通常）/50MB（Nitro）
- レート制限: API呼び出し頻度制限

### Claude Code制限
- プロセス制御の制約
- インタラクティブモードの制限
- 出力フォーマットの制約

## 開発環境のセットアップ

### Docker開発環境（推奨）

#### 1. ベースイメージの確認
```bash
# ベースイメージが利用可能か確認
docker images | grep modern-python-base

# 利用可能でない場合はビルド
cd /path/to/modern-vibecoding-devcontainer/base
./build.sh
```

#### 2. Docker Compose設定
プロジェクトルートに`compose.yml`を作成：

```yaml
version: '3.8'
services:
  dev:
    image: modern-python-base:latest
    container_name: claude-bridge-dev
    working_dir: /workspace
    volumes:
      - .:/workspace
      - ~/.cache/uv:/home/dev/.cache/uv
      - claude-bridge-config:/home/dev/.config
      - claude-bridge-npm:/home/dev/.npm-global
    ports:
      - "8000:8000"
      - "3000:3000"
    environment:
      - PYTHONUNBUFFERED=1
      - PYTHONDONTWRITEBYTECODE=1
      - UV_CACHE_DIR=/home/dev/.cache/uv
      - NPM_CONFIG_PREFIX=/home/dev/.npm-global
      - PATH=/home/dev/.npm-global/bin:${PATH}
    user: dev
    command: tail -f /dev/null
    stdin_open: true
    tty: true

volumes:
  claude-bridge-config:
  claude-bridge-npm:
```

#### 3. 開発環境の起動
```bash
# 開発環境を起動
docker compose up -d

# 開発環境に接続
docker compose exec dev bash

# 開発環境を停止
docker compose down
```

### CLIツールのセットアップ

#### 自動インストールスクリプト
プロジェクトルートに`setup-cli.sh`を作成：

```bash
#!/bin/bash
set -e

echo "🚀 Installing CLI tools for Claude Bridge..."

# npm configuration
mkdir -p ~/.npm-global
npm config set prefix '~/.npm-global'
export PATH="~/.npm-global/bin:$PATH"

# Claude Code CLI
if ! command -v claude &> /dev/null; then
    echo "🤖 Installing Claude Code CLI..."
    npm install -g @anthropic-ai/claude-code@latest
fi

# Gemini CLI
if ! command -v gemini &> /dev/null; then
    echo "💎 Installing Gemini CLI..."
    npm install -g @google/gemini-cli@latest
fi

# Python dependencies
echo "🐍 Installing Python dependencies..."
uv add discord.py pexpect asyncio-mqtt
uv add --dev pytest pytest-cov pytest-mock pytest-asyncio
uv add --dev ruff black mypy vulture safety bandit

echo "✅ CLI tools setup complete!"
```

### VS Code Dev Container統合

`.devcontainer/devcontainer.json`を作成：

```json
{
  "name": "Claude Bridge Development",
  "image": "modern-python-base:latest",
  "workspaceFolder": "/workspace",
  "mounts": [
    "source=${localWorkspaceFolder},target=/workspace,type=bind",
    "source=${localWorkspaceFolder}/.devcontainer/cache,target=/home/dev/.cache,type=bind"
  ],
  "forwardPorts": [8000, 3000],
  "postCreateCommand": "bash -c 'if [ -f setup-cli.sh ]; then chmod +x setup-cli.sh && ./setup-cli.sh; fi && uv sync --dev'",
  "remoteUser": "dev",
  "customizations": {
    "vscode": {
      "extensions": [
        "ms-python.python",
        "ms-python.black-formatter",
        "charliermarsh.ruff",
        "ms-python.mypy-type-checker",
        "ms-python.pylint"
      ],
      "settings": {
        "python.defaultInterpreterPath": "/usr/local/bin/python",
        "python.linting.enabled": true,
        "python.linting.ruffEnabled": true,
        "python.formatting.provider": "black",
        "python.terminal.activateEnvironment": false
      }
    }
  }
}
```

## 開発コマンド

### 基本的な開発ワークフロー

```bash
# 1. プロジェクトのセットアップ
uv init
uv add discord.py pexpect asyncio-mqtt
uv add --dev pytest pytest-cov pytest-asyncio ruff black mypy

# 2. コード品質チェック
ruff check .                    # リンター
ruff format .                   # フォーマッター
mypy .                         # 型チェック

# 3. テスト実行
pytest                         # 基本テスト
pytest --cov=src tests/        # カバレッジ付きテスト
pytest -v tests/               # 詳細出力テスト

# 4. セキュリティチェック
safety check                   # 脆弱性チェック
bandit -r src/                 # セキュリティ静的解析

# 5. AIツールの活用
claude help                    # Claude Code CLI
gemini --help                  # Gemini CLI
```

### 実行コマンド

```bash
# 開発用実行
uv run python src/claude_bridge.py

# 本番用実行
uv run python -m claude_bridge

# デバッグ用実行
uv run python -m pdb src/claude_bridge.py
```

### 便利なエイリアス

```bash
# ~/.bashrc または ~/.zshrc に追加
alias cb-dev='docker compose exec dev bash'
alias cb-up='docker compose up -d'
alias cb-down='docker compose down'
alias cb-logs='docker compose logs -f dev'
alias cb-test='docker compose exec dev pytest'
alias cb-lint='docker compose exec dev ruff check .'
alias cb-format='docker compose exec dev ruff format .'
```

## 成功指標

- セッション接続成功率: 95%以上
- 出力遅延: 平均1秒以内
- セッション継続時間: 平均2時間以上
- プロセス安定性: 異常終了率5%以下