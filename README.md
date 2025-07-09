# サイト更新検知 ✕ メール通知 — プロジェクト概要

> **目的だけをまとめた MD。実装詳細は Claude Code へ委譲します。**

---

## 🎯 何を実現したいか

| 項目 | 内容 |
|------|------|
| **監視対象** | `urls.txt` に列挙した **最大 100 URL** |
| **検知条件** | 新しい PDF や任意要素の **追加 / 削除 / 変化** |
| **通知方法** | Gmail SMTP で HTML メールを送付（To: クライアント、Cc: 開発者） |
| **実行頻度** | 6 時間ごとに GitHub Actions で自動実行（無料枠 2 000 min/月以内） |
| **拡張** | URL が 100 件超 or 間隔短縮時はワークフローを分割／cron 調整で対応 |

---

## 📁 推奨フォルダ構成（大枠）
repo-root/
├─ .github/
│ └─ workflows/
│ └─ monitor-sites.yml # GitHub Actions ワークフロー
├─ monitor/ # Python パッケージ
│ ├─ main.py # エントリーポイント
│ ├─ fetcher.py # HTTP 取得 & リトライ
│ ├─ detector.py # 差分判定ロジック
│ ├─ mailer.py # Gmail 送信ユーティリティ
│ ├─ state/ # 前回ハッシュ等を保存 (Actions Cache 対象)
│ └─ requirements.txt
└─ urls.txt # 監視 URL を 1 行ずつ記述



---

## ⚙️ GitHub Actions ワークフロー骨子

| ステップ | 役割 |
|----------|------|
| **Trigger** | `cron: "0 */6 * * *"`（UTC）＋ `workflow_dispatch` |
| **Checkout** | `actions/checkout` |
| **Python セットアップ** | `actions/setup-python@v4` (3.11 など) |
| **Cache** | `actions/cache` で `monitor/state/` を復元・保存 |
| **依存インストール** | `pip install -r monitor/requirements.txt` |
| **実行** | `python -m monitor.main` |
| **結果** | 変更があれば `mailer.py` がメール送信 |

---

## 🔐 必要な Secrets

| Name | 用途 |
|------|------|
| `SMTP_USER` | Gmail アカウント（例: `yourname@gmail.com`） |
| `SMTP_PASS` | Gmail **アプリパスワード** |
| `MAIL_TO`   | 送信先アドレス（カンマ区切り可） |

---

## 📝 Claude Code への指示例

> *「上記仕様を満たす Python 実装と `monitor-sites.yml` を作って」*  
> - フォルダ構成は本概要に準拠  
> - 依存は最小（`requests`, `beautifulsoup4` など）  
> - `monitor.main()` で差分検知 ➜ Gmail 送信まで完結  
> - ユニットテストしやすい関数分割を推奨  

---

この Markdown をそのまま `README.md` に置き、実装タスクは Claude Code にパスする想定です。
