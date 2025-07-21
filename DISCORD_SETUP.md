# Discord連携セットアップガイド

Claude BridgeをDiscordで実際に使用するための完全な手順書です。

## 🎯 概要

このガイドでは以下を行います：
1. Discord Botの作成とトークン取得
2. 設定ファイルの作成
3. devcontainer環境でのシステム起動
4. Discord経由でのClaude Code操作

## 📋 前提条件

- ✅ システムが動作確認済み（comprehensive_test.pyで30/30テスト合格）
- ✅ Docker環境が利用可能
- ✅ modern-python-base:latest イメージが存在
- ⚠️ Discord開発者アカウント（これから作成）

## 🤖 Step 1: Discord Botの作成

### 1.1 Discord Developer Portalにアクセス
1. https://discord.com/developers/applications にアクセス
2. Discordアカウントでログイン
3. 「New Application」をクリック

### 1.2 アプリケーションの作成
1. アプリケーション名を入力（例：「Claude Bridge Bot」）
2. 利用規約に同意して「Create」をクリック

### 1.3 Botの設定
1. 左メニューから「Bot」を選択
2. 「Add Bot」をクリック（既にBotセクションがある場合はスキップ）
3. **重要**: 「Token」をコピーして安全な場所に保存
   ```
   例: YOUR_ACTUAL_BOT_TOKEN_HERE
   ```

### 1.4 Bot権限の設定
1. 「OAuth2」→「URL Generator」を選択
2. **Scopes**で以下を選択：
   - ✅ `bot`
   - ✅ `applications.commands`

3. **Bot Permissions**で以下を選択：
   - ✅ `Send Messages`
   - ✅ `Use Slash Commands`
   - ✅ `Embed Links`
   - ✅ `Attach Files`
   - ✅ `Read Message History`
   - ✅ `Add Reactions`

4. 生成されたURLをコピー

### 1.5 Botをサーバーに招待
1. 生成したURLをブラウザで開く
2. Botを追加したいサーバーを選択
3. 権限を確認して「認証」をクリック

## 🔧 Step 2: Discord情報の取得

### 2.1 サーバーID（Guild ID）の取得
1. Discordで開発者モードを有効化：
   - 設定 → 詳細設定 → 開発者モード をON
2. Botを追加したサーバーを右クリック
3. 「IDをコピー」を選択

### 2.2 チャンネルIDの取得
1. Botに使用したいチャンネルを右クリック
2. 「IDをコピー」を選択

## ⚙️ Step 3: 設定ファイルの作成

### 3.1 設定ファイルの作成
プロジェクトルートに設定ファイルを作成：

```bash
# config/discord_config.json を作成
mkdir -p config
```

### 3.2 設定ファイルの内容
`config/discord_config.json` を以下の内容で作成：

```json
{
  "discord": {
    "token": "YOUR_BOT_TOKEN_HERE",
    "guild_id": "YOUR_GUILD_ID_HERE",
    "channel_id": "YOUR_CHANNEL_ID_HERE"
  },
  "claude_code": {
    "command": "claude-code",
    "working_directory": "/workspace",
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
    "file": "logs/claude_bridge.log",
    "max_size": "10MB",
    "backup_count": 3
  }
}
```

### 3.3 実際の値に置き換え
設定ファイル内の以下を実際の値に置き換えてください：
- `YOUR_BOT_TOKEN_HERE` → Step 1.3でコピーしたBotトークン
- `YOUR_GUILD_ID_HERE` → Step 2.1で取得したサーバーID
- `YOUR_CHANNEL_ID_HERE` → Step 2.2で取得したチャンネルID

## 🚀 Step 4: システムの起動

### 4.1 devcontainer環境の起動
```bash
# devcontainer環境を起動
docker run -it --rm \
  -v "$(pwd)":/workspace \
  -w /workspace \
  modern-python-base:latest \
  bash
```

### 4.2 依存関係のインストール
```bash
# コンテナ内で実行
uv sync --dev
source .venv/bin/activate
```

### 4.3 Claude Code CLIのインストール
```bash
# コンテナ内で実行
npm install -g @anthropic-ai/claude-code@latest
```

### 4.4 Claude Bridgeの起動
```bash
# コンテナ内で実行
python -m claude_bridge.main --config config/discord_config.json
```

## 📱 Step 5: Discordでの操作

### 5.1 基本コマンド
Discordの指定チャンネルで以下のスラッシュコマンドが使用可能：

```
/connect        - Claude Codeセッションに接続
/disconnect     - セッションから切断
/status         - 現在のセッション状態を確認
/send <command> - Claude Codeにコマンドを送信
/output         - 最新の出力を表示
/history        - コマンド履歴を表示
```

### 5.2 使用例
```
# セッションに接続
/connect

# Claude Codeにコマンドを送信
/send help

# ファイルの作成
/send create hello.py

# セッション状態の確認
/status

# 切断
/disconnect
```

## 🔧 Step 6: 高度な設定（オプション）

### 6.1 Claude Code認証の設定
Claude Code CLIで認証を設定：
```bash
# Anthropic APIキーを設定
claude-code auth
```

### 6.2 ログの確認
```bash
# ログファイルの確認
tail -f logs/claude_bridge.log
```

### 6.3 パフォーマンス監視
```bash
# システムリソースの監視
docker stats
```

## 🚨 トラブルシューティング

### 問題1: Botがオンラインにならない
**症状**: DiscordでBotがオフライン表示
**解決策**:
1. Botトークンが正しいか確認
2. インターネット接続を確認
3. ログファイルでエラーを確認

### 問題2: スラッシュコマンドが表示されない
**症状**: `/connect` などのコマンドが補完されない
**解決策**:
1. Bot権限で `applications.commands` が有効か確認
2. Botを一度サーバーから削除して再招待
3. Discordクライアントを再起動

### 問題3: Claude Codeコマンドがエラー
**症状**: Claude Codeの実行でエラー
**解決策**:
1. Claude Code CLIが正しくインストールされているか確認
2. 認証が正しく設定されているか確認
3. ワーキングディレクトリのパーミッションを確認

### 問題4: セッションが切断される
**症状**: セッションが予期せず終了
**解決策**:
1. ネットワーク接続を確認
2. タイムアウト設定を調整
3. メモリ使用量を確認

## 📊 動作確認チェックリスト

### ✅ 基本動作確認
- [ ] Discord BotがDiscordでオンライン表示
- [ ] `/connect` でセッション接続成功
- [ ] `/send help` でClaude Codeのヘルプ表示
- [ ] `/status` で正しいセッション情報表示
- [ ] `/disconnect` で正常切断

### ✅ 高度な機能確認
- [ ] 長いテキストが複数メッセージに分割表示
- [ ] ANSIエスケープシーケンスが除去
- [ ] インタラクティブプロンプトがボタン変換
- [ ] プログレス表示が適切に更新
- [ ] エラー時に適切な復旧動作

## 🎉 成功！

すべてのステップが完了すると、DiscordからClaude Codeを操作できるようになります。

## 📝 参考情報

- **設定ファイル**: `config/discord_config.json`
- **ログファイル**: `logs/claude_bridge.log`
- **メインスクリプト**: `src/claude_bridge/main.py`
- **Discord Bot**: `src/claude_bridge/discord_bot/bot.py`

## 🆘 サポート

問題が発生した場合：
1. ログファイルを確認
2. comprehensive_test.pyで基本機能を再確認
3. 設定ファイルの値を再確認
4. Discord Developer Portalで権限を再確認