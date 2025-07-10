# 🔍 Site Watchdog Action

**ウェブサイトの更新を自動監視し、変更をメール通知するGitHub Actionsプロジェクト**

[![Site Monitoring](https://github.com/kounoti/siteWatchdogAction/actions/workflows/monitor-sites.yml/badge.svg)](https://github.com/kounoti/siteWatchdogAction/actions/workflows/monitor-sites.yml)

## 🎯 機能概要

- **📄 PDFファイル監視**: 新しいPDFファイルの追加・削除を検知
- **🔗 コンテンツ変更検知**: ウェブページの内容変更を検知
- **📧 メール通知**: Gmail経由で変更をメール通知
- **⏰ 自動実行**: 6時間ごとに定期実行
- **🚀 無料運用**: GitHub Actions無料枠内で運用

## 📋 監視対象サイト

現在監視中のサイト：
- 厚生労働省（新型コロナウイルス関連）
- 東京大学（新着情報）
- 気象庁（予報情報）
- 内閣府（公式情報）
- Yahoo!ニュース（トピックス）

## 🔧 セットアップ方法

### 1. リポジトリのフォーク・クローン

```bash
git clone https://github.com/kounoti/siteWatchdogAction.git
cd siteWatchdogAction
```

### 2. GitHub Secretsの設定

リポジトリの **Settings** → **Secrets and variables** → **Actions** で以下を設定：

| Secret名 | 値 | 説明 |
|---------|---|------|
| `SMTP_SERVER` | `smtp.gmail.com` | Gmail SMTPサーバー |
| `SMTP_PORT` | `587` | SMTPポート番号 |
| `SMTP_USER` | `your-email@gmail.com` | 送信者Gmailアドレス |
| `SMTP_PASSWORD` | `your-app-password` | Gmailアプリパスワード |
| `RECIPIENT_EMAIL` | `notify@example.com` | 通知先メールアドレス |

### 3. Gmailアプリパスワードの生成

1. Googleアカウントで2段階認証を有効化
2. https://myaccount.google.com/apppasswords にアクセス
3. アプリパスワードを生成してSecretに設定

### 4. 監視URLの設定

`urls.txt` に監視したいURLを1行ずつ追加：

```
https://example.com/news
https://example.com/updates
```

## 📁 プロジェクト構造

```
├── .github/workflows/
│   └── monitor-sites.yml     # GitHub Actionsワークフロー
├── monitor/
│   ├── main.py              # メインエントリーポイント
│   ├── fetcher.py           # ウェブサイト取得
│   ├── detector.py          # 変更検知ロジック
│   ├── mailer.py            # メール送信
│   └── requirements.txt     # Python依存関係
├── urls.txt                 # 監視対象URL
└── README.md
```

## 🔄 実行方法

### 自動実行
- 6時間ごとに自動実行（UTC: 0, 6, 12, 18時）
- 日本時間: 9, 15, 21, 3時

### 手動実行
1. GitHubリポジトリの **Actions** タブに移動
2. **Site Monitoring** ワークフローを選択
3. **Run workflow** ボタンをクリック

## 📧 通知メール例

```
🔍 サイト更新検知通知
検知時刻: 2025-07-10 22:43:11

更新サイト数: 1件

📄 https://example.com/news
📄 新しいPDFファイル: 重要なお知らせ (https://example.com/file.pdf)
📝 コンテンツが更新されました (+120文字)
```

## 🛠️ 技術スタック

- **Python 3.11**: メイン開発言語
- **GitHub Actions**: CI/CDプラットフォーム
- **BeautifulSoup4**: HTML解析
- **Requests**: HTTP通信
- **Gmail SMTP**: メール送信

## 📊 実行ログ

GitHub Actionsの実行状況は[こちら](https://github.com/kounoti/siteWatchdogAction/actions)で確認できます。

## 🤝 貢献

プルリクエストや Issues での改善提案を歓迎します。

## 📄 ライセンス

このプロジェクトはMITライセンスの下で公開されています。
