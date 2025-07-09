# サイト監視システム実装ガイド

## 📋 概要

このシステムは、指定されたWebサイトの変更を自動的に検知し、Gmail経由で通知を送信するPythonアプリケーションです。GitHub Actionsを使用して6時間ごとに自動実行され、PDF追加・削除、コンテンツ変更、リンク変更などを検知します。

## 🏗️ システム構成

```
siteWatchdogAction/
├── .github/
│   └── workflows/
│       └── monitor-sites.yml    # GitHub Actions設定
├── monitor/                     # メインパッケージ
│   ├── __init__.py             # パッケージ初期化
│   ├── main.py                 # エントリーポイント
│   ├── fetcher.py              # HTTP取得・リトライ機能
│   ├── detector.py             # 変更検知ロジック
│   ├── mailer.py               # Gmail送信機能
│   ├── requirements.txt        # 依存関係
│   └── state/                  # 状態保存ディレクトリ
├── urls.txt                    # 監視対象URLリスト
└── README.md                   # プロジェクト概要
```

---

## 📁 ファイル詳細解説

### 1. `monitor/main.py` - メインエントリーポイント

**役割**: システム全体の制御とオーケストレーション

**主要クラス**: `SiteMonitor`

**重要な機能**:
```python
class SiteMonitor:
    def __init__(self, urls_file="urls.txt", state_dir="monitor/state"):
        # 各コンポーネントの初期化
        self.fetcher = SiteFetcher()
        self.detector = ChangeDetector(self.state_dir)
        self.mailer = GmailSender()
```

**処理フロー**:
1. `load_urls()`: URLリストの読み込み
2. `process_url()`: 各URLの処理（取得→変更検知）
3. `run()`: メインループ実行
4. 変更検知時の通知送信

**エラーハンドリング**:
- ファイル読み込みエラー
- URL処理エラー
- 致命的エラー時のシステム終了

**ログ出力**:
- INFO レベル: 正常な処理状況
- WARNING レベル: 軽微な問題
- ERROR レベル: 処理エラー

---

### 2. `monitor/fetcher.py` - HTTP取得・リトライ機能

**役割**: 安定したWebページ取得とエラー処理

**主要クラス**: `SiteFetcher`

**設定可能パラメータ**:
```python
def __init__(self, timeout=30, max_retries=3, retry_delay=1):
    self.timeout = timeout          # タイムアウト時間
    self.max_retries = max_retries  # 最大リトライ回数
    self.retry_delay = retry_delay  # リトライ間隔
```

**リトライ戦略**:
- **指数バックオフ**: `sleep_time = self.retry_delay * (2 ** attempt)`
- **最大3回リトライ**: 初回 + 3回リトライ = 計4回試行
- **段階的待機**: 1秒 → 2秒 → 4秒

**User-Agent設定**:
```python
'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
```
- ブラウザを模擬してアクセス制限を回避

**URL検証**:
- `_is_valid_url()`: URLフォーマットの妥当性チェック
- HTTP/HTTPS プロトコルのみ許可

**レスポンス情報取得**:
```python
def get_response_info(self, url):
    # HEADリクエストでメタデータのみ取得
    return {
        'status_code': response.status_code,
        'content_type': response.headers.get('content-type'),
        'last_modified': response.headers.get('last-modified'),
        'etag': response.headers.get('etag')
    }
```

---

### 3. `monitor/detector.py` - 変更検知ロジック

**役割**: Webページの変更を詳細に検知・分析

**主要クラス**: `ChangeDetector`

**状態管理**:
```python
def __init__(self, state_dir: Path):
    self.state_dir = state_dir
    self.state_dir.mkdir(exist_ok=True)
```

**コンテンツ抽出機能**:

#### A. PDF リンク抽出
```python
def _extract_pdf_links(self, soup, base_url):
    # .pdfで終わるリンクまたは'pdf'を含むリンクを検出
    for link in soup.find_all('a', href=True):
        if href.lower().endswith('.pdf') or 'pdf' in href.lower():
            # 絶対URLに変換してハッシュ付きで保存
```

#### B. コンテンツ正規化
```python
# 不要要素の除去
for element in soup(['script', 'style', 'nav', 'footer', 'header']):
    element.decompose()

# 空白文字の正規化
text_content = re.sub(r'\s+', ' ', text_content).strip()
```

#### C. 更新インジケーター検出
```python
def _extract_update_indicators(self, soup):
    # 日付要素の検出
    date_elements = soup.find_all(['time', 'span', 'div'], 
                                 class_=re.compile(r'date|time|updated', re.I))
    
    # 「新着」「更新」バッジの検出
    new_elements = soup.find_all(text=re.compile(r'new|updated|追加|更新', re.I))
    
    # バージョン情報の検出
    version_elements = soup.find_all(text=re.compile(r'version|v\d+', re.I))
```

**変更検知アルゴリズム**:

1. **コンテンツハッシュ比較**:
   ```python
   content_hash = hashlib.md5(text_content.encode('utf-8')).hexdigest()
   ```

2. **PDF変更検知**:
   - ハッシュベースの差分検出
   - 追加・削除の詳細情報

3. **リスト型データ比較**:
   ```python
   def _compare_lists(self, previous, current):
       prev_set = set(previous)
       curr_set = set(current)
       added = curr_set - prev_set
       removed = prev_set - curr_set
   ```

**状態永続化**:
```python
def _get_state_file_path(self, url):
    url_hash = hashlib.md5(url.encode()).hexdigest()
    return self.state_dir / f"state_{url_hash}.json"
```

**古い状態ファイルのクリーンアップ**:
```python
def cleanup_old_states(self, max_age_days=30):
    # 30日以上古いファイルを自動削除
```

---

### 4. `monitor/mailer.py` - Gmail送信機能

**役割**: 変更検知結果のHTML形式メール送信

**主要クラス**: `GmailSender`

**初期化と環境変数**:
```python
def __init__(self):
    self.smtp_user = os.getenv('SMTP_USER')    # Gmail アドレス
    self.smtp_pass = os.getenv('SMTP_PASS')    # アプリパスワード
    self.mail_to = os.getenv('MAIL_TO')        # 送信先（カンマ区切り）
```

**メール構成**:
```python
def _create_email_message(self, changes):
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"🔍 サイト更新検知通知 ({len(changes)}件)"
    msg['From'] = self.smtp_user
    msg['To'] = ', '.join(self.mail_to)
    
    # テキスト版とHTML版の両方を添付
    msg.attach(MIMEText(text_content, 'plain', 'utf-8'))
    msg.attach(MIMEText(html_content, 'html', 'utf-8'))
```

**HTML テンプレート設計**:

#### A. 基本スタイル
```css
.header { background-color: #f0f8ff; padding: 20px; }
.site-block { border: 1px solid #ddd; margin: 15px 0; }
.added { color: #008000; }      /* 緑色 - 追加 */
.removed { color: #cc0000; }    /* 赤色 - 削除 */
.modified { color: #ff6600; }   /* オレンジ - 変更 */
```

#### B. 変更タイプ別表示
```python
# PDF変更の表示
if 'pdf_changes' in changes:
    if 'added' in pdf_changes:
        html += '<div class="change-item added">📄 新しいPDFファイル:</div>'
        for pdf in pdf_changes['added']:
            html += f'<div class="pdf-link added">+ <a href="{pdf["url"]}">{pdf["text"]}</a></div>'
```

**SMTP接続設定**:
```python
def _send_email(self, msg):
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()  # TLS暗号化
    server.login(self.smtp_user, self.smtp_pass)
    server.sendmail(self.smtp_user, self.mail_to, msg.as_string())
```

**接続テスト機能**:
```python
def test_connection(self):
    # SMTP接続の事前テスト
    # 設定ミスの早期発見に有用
```

---

### 5. `monitor/requirements.txt` - 依存関係

**最小構成の依存関係**:
```txt
requests>=2.31.0      # HTTP クライアント
beautifulsoup4>=4.12.0 # HTML パーサー
lxml>=4.9.0           # XML/HTML パーサー (高速)
```

**選択理由**:
- **requests**: 標準的なHTTPライブラリ、リトライ機能内蔵
- **BeautifulSoup4**: HTML解析の定番、柔軟性が高い
- **lxml**: BeautifulSoupのバックエンド、高速処理

---

### 6. `urls.txt` - 監視対象URLリスト

**フォーマット**:
```txt
# コメント行（#で始まる）
https://example.com/news
https://example.com/updates

# 空行は無視される
https://example.com/documents
```

**制限事項**:
- 最大100URL（GitHub Actions の実行時間制限考慮）
- 1行1URL
- HTTP/HTTPS のみ対応
- 認証不要のページのみ

**推奨設定**:
```txt
# 政府機関（更新頻度: 低〜中）
https://www.mhlw.go.jp/

# 企業IR情報（更新頻度: 低）
https://www.company.co.jp/ir/

# ニュースサイト（更新頻度: 高 - 注意）
# https://news.example.com/  # 高頻度更新サイトはコメントアウト推奨
```

---

### 7. `.github/workflows/monitor-sites.yml` - GitHub Actions設定

**トリガー設定**:
```yaml
on:
  schedule:
    - cron: '0 */6 * * *'  # 6時間ごと (UTC)
  workflow_dispatch:       # 手動実行
```

**実行環境**:
```yaml
runs-on: ubuntu-latest
```

**Python セットアップ**:
```yaml
- name: Set up Python
  uses: actions/setup-python@v4
  with:
    python-version: '3.11'
```

**キャッシュ戦略**:

#### A. 依存関係キャッシュ
```yaml
- name: Cache dependencies
  uses: actions/cache@v3
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('monitor/requirements.txt') }}
```

#### B. 監視状態キャッシュ
```yaml
- name: Cache monitoring state
  uses: actions/cache@v3
  with:
    path: monitor/state/
    key: ${{ runner.os }}-monitor-state-${{ github.run_id }}
    restore-keys: |
      ${{ runner.os }}-monitor-state-
```

**環境変数設定**:
```yaml
env:
  SMTP_USER: ${{ secrets.SMTP_USER }}
  SMTP_PASS: ${{ secrets.SMTP_PASS }}
  MAIL_TO: ${{ secrets.MAIL_TO }}
```

**ログ保存**:
```yaml
- name: Upload monitoring logs
  if: always()
  uses: actions/upload-artifact@v3
  with:
    name: monitoring-logs
    path: monitor/state/
    retention-days: 7
```

---

## 🔧 セットアップ手順

### 1. GitHub Secrets 設定

**リポジトリ設定 → Secrets and variables → Actions**

```
SMTP_USER: your-gmail@gmail.com
SMTP_PASS: your-app-password
MAIL_TO: recipient@example.com,recipient2@example.com
```

### 2. Gmail アプリパスワード取得

1. Google アカウント設定
2. セキュリティ → 2段階認証プロセス
3. アプリパスワード → 「メール」選択
4. 生成されたパスワードを `SMTP_PASS` に設定

### 3. 監視URL設定

`urls.txt` を編集:
```txt
https://target-site1.com/news
https://target-site2.com/updates
```

### 4. 初回実行

- GitHub → Actions → "Site Monitoring" → "Run workflow"
- 初回は全サイトで「初回監視設定完了」通知

---

## 📊 監視内容詳細

### 1. PDF ファイル変更

**検知対象**:
- `href` 属性が `.pdf` で終わるリンク
- URL に `pdf` を含むリンク

**検知内容**:
- 新規PDFの追加
- 既存PDFの削除
- PDFリンクテキストの変更

### 2. コンテンツ変更

**検知方法**:
- HTML から script, style, nav, footer, header を除去
- テキスト内容の MD5 ハッシュ比較

**検知内容**:
- 文字数増減
- 実質的な内容変更

### 3. リンク変更

**検知対象**:
- 全ての `<a href="">` リンク
- 絶対URL に正規化後比較

**除外対象**:
- `javascript:` リンク
- `mailto:` リンク
- `tel:` リンク

### 4. 更新インジケーター

**検知対象**:
- 日付表示要素（`<time>`, class名に date/time/updated を含む要素）
- 「新着」「更新」「追加」「変更」テキスト
- バージョン情報

---

## 🚀 運用とメンテナンス

### 1. 実行時間の最適化

**現在の制限**:
- GitHub Actions 無料枠: 2,000分/月
- 6時間ごと実行: 月120回
- 1回あたり平均実行時間: 5-10分

**スケール対応**:
```yaml
# URLが多い場合の分割実行例
strategy:
  matrix:
    batch: [1, 2, 3]
env:
  URL_BATCH: ${{ matrix.batch }}
```

### 2. エラー監視

**ログ確認場所**:
- GitHub Actions → 実行履歴 → ログ
- Artifacts → monitoring-logs

**よくあるエラー**:
```
SMTP authentication failed → アプリパスワード確認
Connection timeout → 対象サイトのアクセス制限
Memory limit exceeded → URLs 数を削減
```

### 3. 状態ファイル管理

**自動クリーンアップ**:
```python
# 30日以上古い状態ファイルを削除
detector.cleanup_old_states(max_age_days=30)
```

**手動リセット**:
```bash
# 特定URLの状態リセット
rm monitor/state/state_<url_hash>.json
```

### 4. 通知内容カスタマイズ

**HTML テンプレート編集**:
```python
# monitor/mailer.py の _generate_html_content() を修正
# CSS スタイルやレイアウトを変更可能
```

**件名カスタマイズ**:
```python
msg['Subject'] = f"🔍 サイト更新検知通知 ({len(changes)}件)"
```

---

## 🔒 セキュリティ考慮事項

### 1. 認証情報管理

- **GitHub Secrets** でのみ認証情報を管理
- コードに直接記載しない
- アプリパスワードを使用（通常パスワード不使用）

### 2. アクセス制限

- **User-Agent** でブラウザを模擬
- **適切な間隔** での実行（6時間ごと）
- **リトライ回数制限** でサーバー負荷軽減

### 3. データ保護

- **状態ファイル** は GitHub 内でのみ保存
- **メール内容** に機密情報を含めない
- **ログ保存期間** を7日に制限

---

## 🐛 トラブルシューティング

### 1. メール送信エラー

**エラー**: `SMTP authentication failed`
**解決**: 
- Gmail の2段階認証を有効化
- アプリパスワードを再生成
- `SMTP_PASS` シークレットを更新

### 2. 取得エラー

**エラー**: `Connection timeout`
**解決**:
- 対象サイトのアクセス制限確認
- `timeout` パラメータを増加
- `max_retries` を調整

### 3. 実行時間エラー

**エラー**: `The job running on runner GitHub Actions exceeded the maximum execution time`
**解決**:
- URLs 数を削減
- バッチ処理に分割
- 実行頻度を調整

### 4. メモリエラー

**エラー**: `Memory limit exceeded`
**解決**:
- 大きなページをURLリストから除外
- 画像やスクリプトの除去処理を強化

---

## 🔄 拡張可能性

### 1. 追加検知機能

```python
# 新しい検知機能の追加例
def _detect_table_changes(self, soup):
    # テーブル構造の変更検知
    tables = soup.find_all('table')
    return self._analyze_table_structure(tables)
```

### 2. 通知チャネル拡張

```python
# Slack 通知の追加例
from slack_sdk import WebClient

class SlackNotifier:
    def send_notification(self, changes):
        # Slack メッセージ送信
```

### 3. 詳細分析機能

```python
# 変更内容の詳細分析
def _analyze_content_changes(self, old_content, new_content):
    # 差分の詳細分析
    # 追加された段落、削除された段落の特定
```

---

このシステムは、Webサイトの重要な変更を見逃さずに監視し、効率的な通知を提供します。運用開始後は、ログを確認しながら監視対象や通知内容を最適化していくことをお勧めします。