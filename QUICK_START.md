# 🚀 Claude Bridge クイックスタートガイド

Discord経由でClaude Codeを操作するための最短手順です。

## ⚡ 5分で起動

### Step 1: Discord Botを作成
1. https://discord.com/developers/applications にアクセス
2. 「New Application」→ Bot名を入力（例：Claude Bridge）
3. 「Bot」タブ → **Tokenをコピー**して保存
4. 「OAuth2」→「URL Generator」:
   - Scopes: `bot`, `applications.commands`
   - Permissions: `Send Messages`, `Use Slash Commands`, `Embed Links`
5. 生成されたURLでBotをサーバーに招待

### Step 2: ID取得
1. Discord設定 → 詳細設定 → **開発者モード**をON
2. サーバーを右クリック → **「IDをコピー」**（Guild ID）
3. 使用するチャンネルを右クリック → **「IDをコピー」**（Channel ID）

### Step 3: 設定ファイル作成
```bash
mkdir -p config
```

`config/discord_config.json` を作成：
```json
{
  "discord": {
    "token": "あなたのBotトークン",
    "guild_id": "あなたのGuild ID",
    "channel_id": "あなたのChannel ID"
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

### Step 4: 起動
```bash
# 最も簡単な方法
./run_discord.sh

# または詳細な手順で
docker run -it --rm -v "$(pwd)":/workspace -w /workspace modern-python-base:latest bash
# コンテナ内で：
uv sync --dev && source .venv/bin/activate
python -m claude_bridge.main
```

### Step 5: Discord操作
Discordの指定チャンネルで：
```
/connect        # セッション開始
/send help      # Claude Codeヘルプ
/status         # 状態確認
/disconnect     # セッション終了
```

## 📱 基本的な使い方

### セッション開始
```
/connect
```
→ 「✅ Session SESSION123 connected successfully」

### Claude Codeにコマンド送信
```
/send create hello.py
/send edit hello.py
```

### 出力確認
```
/output         # 最新出力
/history        # コマンド履歴
```

### セッション終了
```
/disconnect
```

## 🔧 よくある質問

**Q: Botがオフラインになる**
A: トークンとインターネット接続を確認してください

**Q: スラッシュコマンドが出ない**
A: Bot権限を確認し、Discordを再起動してください

**Q: Claude Codeエラー**
A: `claude-code auth` で認証を設定してください

**Q: テスト方法は？**
A: `python comprehensive_test.py` で全機能をテストできます

## 🎯 次のステップ

- [DISCORD_SETUP.md](DISCORD_SETUP.md) - 詳細セットアップ
- [CLAUDE.md](CLAUDE.md) - 開発者向け情報
- [comprehensive_test.py](comprehensive_test.py) - システムテスト

## 🆘 問題が発生した場合

1. `./run_discord.sh --help` でオプション確認
2. `logs/claude_bridge.log` でログ確認
3. `python -m claude_bridge.main --test` でテスト実行