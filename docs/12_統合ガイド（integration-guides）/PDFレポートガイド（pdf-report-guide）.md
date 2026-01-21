# WeasyPrint PDF生成機能 - クイックスタート

## 📄 概要

WeasyPrintを使用した高品質PDF生成機能が完全実装されました。

## ✅ 実装済み

### コアファイル
- ✅ `app/services/pdf_generator.py` - PDFジェネレータサービス
- ✅ `app/templates/reports/iso27001_template.html` - ISO 27001準拠
- ✅ `app/templates/reports/iso19650_template.html` - ISO 19650準拠
- ✅ `app/templates/reports/compliance_report_template.html` - 3-2-1-1-0ルール
- ✅ `app/templates/reports/audit_report_template.html` - 監査ログ
- ✅ `app/services/report_generator.py` - 全PDFメソッド実装済み

### 機能
- ✅ HTML→PDF変換
- ✅ 日本語フォント対応
- ✅ ページ番号・ヘッダー・フッター
- ✅ 表紙・目次
- ✅ グラフ埋め込み
- ✅ ISO準拠テンプレート

## 🚀 クイックスタート

### 1. 依存パッケージインストール

```bash
# Pythonパッケージ
pip install -r requirements.txt

# システムフォント (Ubuntu)
sudo apt-get install fonts-noto-cjk

# WeasyPrint依存ライブラリ (Ubuntu)
sudo apt-get install libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0
```

### 2. 基本的な使用方法

```python
from app.services.report_generator import ReportGenerator

# PDFレポート生成
generator = ReportGenerator()
report = generator.generate_compliance_report(
    generated_by=current_user.id,
    format='pdf'
)

print(f"PDF生成完了: {report.file_path}")
```

### 3. 利用可能なレポート

```python
# 日次レポート
generator.generate_daily_report(generated_by=1, format='pdf')

# 週次レポート
generator.generate_weekly_report(generated_by=1, format='pdf')

# 月次レポート (ISO 27001)
generator.generate_monthly_report(generated_by=1, year=2025, month=11, format='pdf')

# コンプライアンスレポート (3-2-1-1-0)
generator.generate_compliance_report(generated_by=1, format='pdf')

# 監査ログレポート
generator.generate_audit_report(generated_by=1, format='pdf')
```

## 📚 レポートタイプ

| レポート | テンプレート | 説明 |
|---------|-------------|------|
| ISO 27001 | `iso27001_template.html` | 情報セキュリティマネジメント監査 |
| ISO 19650 | `iso19650_template.html` | 情報管理・BIMデータバックアップ |
| 3-2-1-1-0 | `compliance_report_template.html` | バックアップルール準拠分析 |
| 監査ログ | `audit_report_template.html` | システムアクティビティ監査 |

## 🎨 特徴

### 日本語対応
- Noto Sans CJK JPフォント使用
- 日英バイリンガルレイアウト
- UTF-8エンコーディング

### プロフェッショナルレイアウト
- A4サイズ自動設定
- ページ番号 "Page X of Y"
- カスタマイズ可能なヘッダー・フッター
- 表紙ページ・目次

### データ可視化
- メトリクスボックス
- カラーコード済みテーブル
- ステータスバッジ
- グラフ・チャート埋め込み

## 📊 グラフ生成

```python
from app.services.pdf_generator import ChartGenerator

# トレンドチャート
chart_path = ChartGenerator.generate_compliance_trend_chart(
    data={'dates': [...], 'compliance_rates': [...]},
    output_path='/tmp/trend.png'
)

# 円グラフ
chart_path = ChartGenerator.generate_backup_status_pie_chart(
    data={'success_count': 480, 'failed_count': 12, 'warning_count': 8},
    output_path='/tmp/status.png'
)

# PDFに埋め込み
from app.services.pdf_generator import PDFGenerator
pdf_gen = PDFGenerator()
base64_image = pdf_gen.embed_chart_as_base64(chart_path)
```

## 🧪 テスト

```bash
# 全テスト実行
pytest tests/test_pdf_generation.py -v

# 特定テスト
pytest tests/test_pdf_generation.py::TestPDFGenerator -v
```

## 📖 ドキュメント

詳細なドキュメントは以下を参照:
- **完全ガイド**: `/docs/PDF_GENERATION_GUIDE.md`
- **実装サマリー**: `/PDF_IMPLEMENTATION_SUMMARY.md`

## ⚙️ 設定

### フォントパス (自動検出)
```python
font_paths = [
    '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',  # Ubuntu
    '/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc',       # Alternative
]
```

### CSSカスタマイズ
```python
custom_css = """
.my-class { color: red; }
"""

pdf_bytes = pdf_gen.generate_pdf_from_html(
    html_content=html,
    custom_css=custom_css
)
```

## 🔒 セキュリティ

- ✅ 入力検証・エスケープ
- ✅ アクセス制御
- ✅ ファイルパス制限
- ✅ SQLインジェクション対策 (ORM)

## 📦 必須パッケージ

```txt
WeasyPrint==62.3
matplotlib==3.9.0
Pillow==11.0.0
Flask==3.0.0
```

## 🛠️ トラブルシューティング

### 日本語が文字化け
```bash
sudo apt-get install fonts-noto-cjk
```

### PDFが生成されない
```bash
sudo apt-get install libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0
```

### matplotlibエラー
```python
import matplotlib
matplotlib.use('Agg')  # 非GUIバックエンド
```

## 📝 使用例

### 1. 簡単なPDF生成
```python
from app.services.pdf_generator import PDFGenerator

pdf_gen = PDFGenerator()
html = "<h1>Hello PDF</h1><p>This is a test.</p>"
pdf_bytes = pdf_gen.generate_pdf_from_html(html)

with open('output.pdf', 'wb') as f:
    f.write(pdf_bytes)
```

### 2. テンプレート使用
```python
context = {
    'report_title': 'My Report',
    'data': {'total_jobs': 10},
    'start_date': datetime.now(),
    'end_date': datetime.now(),
    'generated_date': datetime.now()
}

pdf_bytes = pdf_gen.generate_pdf_from_template(
    'compliance_report_template.html',
    context
)
```

### 3. データベース連携
```python
from app.services.report_generator import ReportGenerator

# 自動的にデータベースから取得・保存
generator = ReportGenerator()
report = generator.generate_monthly_report(
    generated_by=current_user.id,
    year=2025,
    month=11,
    format='pdf'
)

# レポートレコード作成済み
print(f"Report ID: {report.id}")
print(f"File: {report.file_path}")
```

## 🎯 主要クラス

### PDFGenerator
```python
class PDFGenerator:
    def generate_pdf_from_html(html, custom_css=None) -> bytes
    def generate_pdf_from_template(template_name, context) -> bytes
    def generate_iso27001_report(data, start_date, end_date) -> bytes
    def generate_iso19650_report(data, start_date, end_date) -> bytes
    def embed_chart_as_base64(chart_path) -> str
```

### ChartGenerator
```python
class ChartGenerator:
    @staticmethod
    def generate_compliance_trend_chart(data, output_path) -> str

    @staticmethod
    def generate_backup_status_pie_chart(data, output_path) -> str
```

## 📞 サポート

問題が発生した場合:
1. `/docs/PDF_GENERATION_GUIDE.md` のトラブルシューティングを確認
2. テストを実行して動作確認: `pytest tests/test_pdf_generation.py -v`
3. ログを確認: `logs/app.log`

## 📄 ライセンス

Backup Management Systemのライセンスに準拠

---

**実装日**: 2025-11-02
**バージョン**: 1.0
**ステータス**: ✅ 完全実装済み
