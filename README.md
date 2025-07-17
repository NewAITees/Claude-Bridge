# Claude Bridge

**Multi-Interface Session Bridge for Claude Code**

Claude Bridgeは、Claude Codeとのインタラクティブなセッションを、PCターミナルとDiscordアプリの両方で同時に操作できるようにするブリッジアプリケーションです。

## 🌟 特徴

### 🔄 マルチインターフェース対応
- **PC Terminal**: 詳細な開発作業に最適
- **Discord App**: 外出先でのモバイル確認・操作に対応
- **同期セッション**: 両方のインターフェースで同じClaude Codeセッションを操作

### 📱 モバイル開発継続
- スマートフォンのDiscordアプリから開発セッションにアクセス
- 外出先での進捗確認・簡単な指示出しが可能
- 帰宅後、PCで詳細作業に即座に復帰

### 🛡️ セキュアな認証
- セッション番号によるペアリング認証
- 個人利用専用設計（一人のユーザーのみ対応）
- 他のアプリケーションの背景機能として統合可能

### 🎯 Discord最適化
- 2000文字制限に対応した出力制御
- 長い出力は先頭+末尾表示で中間省略
- ANSIエスケープシーケンスの自動除去
- インタラクティブな確認をDiscordボタン・メニューに変換

## 🚀 使い方

### 1. セッション開始
```
PC Terminal: Claude Code セッション ABC123 が開始されました
Discord: /connect ABC123
Bot: セッション ABC123 に接続しました!
```

### 2. 開発作業（両方のインターフェースで同時操作可能）
```
PC Terminal: "Create a new user authentication system"
Discord: 同じ会話の続きを確認・操作

PC Terminal: ファイル変更を確認
Discord: 外出先から進捗チェック・追加指示
```

### 3. セッション終了
```
Discord: /disconnect
Bot: セッションを終了しました
```

## 📋 主要コマンド

### Discord Bot コマンド
- `/connect <session_id>` - セッションに接続
- `/disconnect` - セッションから切断
- `/status` - 現在のセッション状態を確認
- `/output` - 最新の出力を取得
- `/history` - コマンド履歴を表示

### Claude Code セッション制御
- 標準的なClaude Codeコマンドをすべてサポート
- リアルタイム出力の両方のインターフェースへの同時配信
- インタラクティブな確認のDiscord UI変換

## 🛠️ 技術スタック

### Core Technologies
- **Python** - メインプログラミング言語
- **discord.py** - Discord Bot API
- **subprocess/pexpect** - Claude Codeプロセス制御
- **asyncio** - 非同期処理

### セッション管理
- **セッション番号生成** - ランダムトークンベース
- **状態同期** - リアルタイム入出力中継
- **永続化** - セッション状態の保存・復帰

### 出力制御
- **ANSIエスケープシーケンス除去**
- **文字数制限対応** - 分割・要約処理
- **リアルタイムバッファリング**
- **プログレス表示のDiscord適応**

## 🏗️ アーキテクチャ

```
PC Terminal ↘
              ↘ Claude Code Session ↗
Discord App ↗
```

**中間ブリッジアプリ**が、Claude Codeプロセスとの永続的な通信を管理し、入出力を両方のインターフェースに中継します。

## 🔧 インストール

```bash
# リポジトリをクローン
git clone https://github.com/username/claude-bridge.git
cd claude-bridge

# 依存関係をインストール
pip install -r requirements.txt

# 設定ファイルを作成
cp config.example.json config.json

# 設定を編集
nano config.json

# アプリケーションを起動
python claude_bridge.py
```

## ⚙️ 設定

### config.json
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

## 🎯 使用例

### 典型的な開発フロー
1. **朝**: PCでClaude Codeセッションを開始
2. **通勤中**: Discordで進捗確認・簡単な指示
3. **昼休み**: スマホから追加のリクエスト
4. **帰宅後**: PCで詳細作業に即座に復帰
5. **夜**: 最終確認をDiscordで

### 実用的なシナリオ
- **バグレポート対応**: 外出先でDiscordから確認→帰宅後即座に修正
- **コードレビュー**: 移動中にDiscordでチェック→PCで詳細修正
- **長時間処理**: 進捗をDiscordで監視→完了通知を受信

## 🔮 今後の予定

### Phase 1: 基本機能
- [x] 要件定義・調査
- [ ] Claude Codeプロセス制御
- [ ] Discord Bot基本機能
- [ ] セッション管理システム

### Phase 2: 出力制御
- [ ] ANSIエスケープシーケンス除去
- [ ] 文字数制限対応
- [ ] リアルタイム出力バッファリング
- [ ] プログレス表示のDiscord適応

### Phase 3: UI/UX向上
- [ ] インタラクティブな確認のDiscord UI変換
- [ ] ファイル編集時の差分表示要約
- [ ] 長時間処理中の進捗表示
- [ ] コマンド補完・履歴機能

### Phase 4: 拡張機能
- [ ] セッション履歴の永続化
- [ ] 複数セッションの同時管理
- [ ] 他のアプリケーションとの統合API
- [ ] カスタムコマンドの追加

## 📄 ライセンス

MIT License

## 🤝 コントリビューション

プルリクエストやイシューの報告を歓迎します！

## 📞 サポート

質問や問題がございましたら、Issuesまでお気軽にお寄せください。

---

**Claude Bridge** - Code anywhere, anytime. 🚀
