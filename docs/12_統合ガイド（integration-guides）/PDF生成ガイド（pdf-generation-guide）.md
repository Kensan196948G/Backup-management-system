# PDF生成機能 完全ガイド

## 概要

Backup Management SystemのPDF生成機能は、WeasyPrintを使用して高品質なPDFレポートを生成します。

## 実装済み機能

### 1. PDFジェネレータサービス (`app/services/pdf_generator.py`)

#### 主要クラス

```python
from app.services.pdf_generator import PDFGenerator, ChartGenerator

# PDFジェネレータのインスタンス化
pdf_gen = PDFGenerator()
```

#### 機能一覧

- **HTMLからPDF変換**: WeasyPrintによる高品質PDF生成
- **日本語フォント対応**: Noto Sans CJK JPフォント使用
- **CSSスタイリング**: プリント最適化されたスタイル
- **ページ番号**: 自動ページ番号付与
- **ヘッダー/フッター**: カスタマイズ可能
- **目次**: 自動生成対応
- **表紙ページ**: プロフェッショナルな表紙
- **グラフ埋め込み**: Base64エンコードでの画像埋め込み

### 2. PDFテンプレート

#### ISO 27001準拠レポート (`iso27001_template.html`)

情報セキュリティマネジメントシステムのバックアップ監査レポート

**セクション構成:**
1. エグゼクティブサマリー
2. 監査範囲
3. ISO 27001管理策評価
4. バックアップ統計
5. コンプライアンス分析
6. 検証テスト結果
7. リスクと推奨事項
8. 承認

**使用例:**
```python
from app.services.pdf_generator import PDFGenerator
from datetime import datetime

pdf_gen = PDFGenerator()

data = {
    'total_jobs': 50,
    'success_count': 48,
    'failed_count': 2,
    'compliance_rate': 96.0,
    'verification_rate': 98.0,
    'executions': [],
    'compliance_statuses': [],
    'verification_tests': []
}

pdf_bytes = pdf_gen.generate_iso27001_report(
    data=data,
    start_date=datetime(2025, 10, 1),
    end_date=datetime(2025, 10, 31)
)

# ファイルに保存
with open('iso27001_report.pdf', 'wb') as f:
    f.write(pdf_bytes)
```

#### ISO 19650準拠レポート (`iso19650_template.html`)

情報管理・BIMデータバックアップレポート

**セクション構成:**
1. 概要
2. 情報管理要求事項
3. 情報ライフサイクル管理
4. セキュリティと完全性
5. アーカイブと検索性
6. パフォーマンス指標
7. 改善計画

**使用例:**
```python
pdf_bytes = pdf_gen.generate_iso19650_report(
    data=data,
    start_date=datetime(2025, 10, 1),
    end_date=datetime(2025, 10, 31)
)
```

#### 3-2-1-1-0コンプライアンスレポート (`compliance_report_template.html`)

バックアップルール準拠状況の詳細分析レポート

**セクション構成:**
1. エグゼクティブサマリー
2. 3-2-1-1-0ルール説明
3. 準拠状況分析
4. 詳細評価結果
5. 非準拠項目と是正措置
6. トレンド分析
7. 推奨事項

**3-2-1-1-0ルール:**
- **3コピー**: データの3つのコピーを保持
- **2メディア**: 異なる2種類のメディアに保存
- **1オフサイト**: 最低1つは別の場所に保管
- **1オフライン**: 最低1つはオフライン保存
- **0エラー**: バックアップとリストアでエラーゼロ

**使用例:**
```python
# ReportGeneratorを使用
from app.services.report_generator import ReportGenerator

report_gen = ReportGenerator()
report = report_gen.generate_compliance_report(
    generated_by=1,  # User ID
    format='pdf'
)

print(f"レポート保存先: {report.file_path}")
```

#### 監査ログレポート (`audit_report_template.html`)

システムアクティビティとセキュリティ監査レポート

**セクション構成:**
1. 監査概要
2. アクティビティサマリー
3. ユーザー別アクティビティ
4. アクション種別分析
5. セキュリティイベント
6. 詳細ログ
7. 推奨事項

**使用例:**
```python
report = report_gen.generate_audit_report(
    generated_by=1,
    start_date=datetime(2025, 10, 1),
    end_date=datetime(2025, 10, 31),
    format='pdf'
)
```

### 3. グラフ・チャート生成

#### ChartGeneratorクラス

```python
from app.services.pdf_generator import ChartGenerator

# コンプライアンストレンドチャート
chart_path = ChartGenerator.generate_compliance_trend_chart(
    data={
        'dates': ['2025-10-01', '2025-10-08', '2025-10-15', '2025-10-22'],
        'compliance_rates': [92.0, 94.5, 96.0, 97.5]
    },
    output_path='/tmp/compliance_trend.png'
)

# バックアップステータス円グラフ
chart_path = ChartGenerator.generate_backup_status_pie_chart(
    data={
        'success_count': 480,
        'failed_count': 12,
        'warning_count': 8
    },
    output_path='/tmp/backup_status.png'
)

# PDFに埋め込む
base64_image = pdf_gen.embed_chart_as_base64(chart_path)
# テンプレートで使用: <img src="{{ chart_image }}" />
```

## CSSスタイリング

### ページ設定

```css
@page {
    size: A4;
    margin: 2.5cm 2cm 3cm 2cm;

    @top-left {
        content: string(header-title);
    }

    @bottom-center {
        content: "Page " counter(page) " of " counter(pages);
    }
}
```

### プリント最適化

- **改ページ制御**: `page-break-after`, `page-break-inside`
- **テーブルヘッダー繰り返し**: `thead { display: table-header-group; }`
- **日本語フォント**: Noto Sans CJK JP
- **カラーコード**: Bootstrap風のカラーパレット

### カスタムCSS追加

```python
custom_css = """
.custom-class {
    color: #ff0000;
}
"""

pdf_bytes = pdf_gen.generate_pdf_from_html(
    html_content="<h1>Custom Report</h1>",
    custom_css=custom_css
)
```

## ReportGeneratorとの統合

### 完全実装されたPDFメソッド

```python
from app.services.report_generator import ReportGenerator

generator = ReportGenerator()

# 日次レポート(PDF)
daily_report = generator.generate_daily_report(
    generated_by=1,
    date=datetime(2025, 10, 15),
    format='pdf'
)

# 週次レポート(PDF)
weekly_report = generator.generate_weekly_report(
    generated_by=1,
    end_date=datetime(2025, 10, 20),
    format='pdf'
)

# 月次レポート(PDF) - ISO 27001準拠
monthly_report = generator.generate_monthly_report(
    generated_by=1,
    year=2025,
    month=10,
    format='pdf'
)

# コンプライアンスレポート(PDF)
compliance_report = generator.generate_compliance_report(
    generated_by=1,
    format='pdf'
)

# 監査レポート(PDF)
audit_report = generator.generate_audit_report(
    generated_by=1,
    start_date=datetime(2025, 10, 1),
    end_date=datetime(2025, 10, 31),
    format='pdf'
)
```

## データベース保存

生成されたレポートは自動的にデータベースに記録されます:

```python
# Reportモデル
report = Report.query.filter_by(id=1).first()

print(f"レポート種別: {report.report_type}")
print(f"タイトル: {report.report_title}")
print(f"ファイルパス: {report.file_path}")
print(f"フォーマット: {report.file_format}")
print(f"生成日時: {report.created_at}")
```

## フォント設定

### 日本語フォントインストール

```bash
# Ubuntu/Debian
sudo apt-get install fonts-noto-cjk

# CentOS/RHEL
sudo yum install google-noto-sans-cjk-fonts

# macOS
brew install --cask font-noto-sans-cjk-jp
```

### フォントパス確認

```python
import os

font_paths = [
    '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
    '/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc',
    '/System/Library/Fonts/Supplemental/Arial Unicode.ttf'
]

for path in font_paths:
    if os.path.exists(path):
        print(f"フォント発見: {path}")
```

## トラブルシューティング

### 問題1: 日本語が文字化けする

**解決策:**
1. Noto Sans CJKフォントをインストール
2. フォントパスを確認
3. WeasyPrintのフォント設定を確認

### 問題2: 画像が表示されない

**解決策:**
1. 画像をBase64エンコードで埋め込む
2. 絶対パスを使用
3. データURIスキームを使用

```python
# 正しい方法
base64_image = pdf_gen.embed_chart_as_base64('/path/to/chart.png')
html = f'<img src="{base64_image}" />'
```

### 問題3: CSSが適用されない

**解決策:**
1. プリントメディア用CSSを使用
2. インラインスタイルを避ける
3. `@page` ルールを活用

### 問題4: ページ番号が表示されない

**解決策:**
```css
@page {
    @bottom-center {
        content: "Page " counter(page) " of " counter(pages);
    }
}
```

## パフォーマンス最適化

### 大規模レポート生成

```python
# 大量データの場合はページネーション
def generate_large_report(data, page_size=100):
    pages = []
    for i in range(0, len(data), page_size):
        chunk = data[i:i+page_size]
        page_html = render_template('report_page.html', data=chunk)
        pages.append(page_html)

    full_html = '\n'.join(pages)
    return pdf_gen.generate_pdf_from_html(full_html)
```

### キャッシュ戦略

```python
from functools import lru_cache

@lru_cache(maxsize=100)
def get_cached_pdf(report_id, format_type):
    # キャッシュされたPDFを返す
    pass
```

## セキュリティ考慮事項

### HTMLインジェクション対策

```python
from markupsafe import escape

# ユーザー入力をエスケープ
safe_input = escape(user_input)
html = f"<p>{safe_input}</p>"
```

### ファイルアクセス制限

```python
# レポートファイルへのアクセス制御
from flask_login import login_required, current_user

@login_required
def download_report(report_id):
    report = Report.query.get_or_404(report_id)

    # 権限チェック
    if report.generated_by != current_user.id and not current_user.is_admin:
        abort(403)

    return send_file(report.file_path, as_attachment=True)
```

## ベストプラクティス

1. **テンプレート設計**
   - セマンティックHTML使用
   - モジュール化されたCSS
   - 印刷に最適化されたレイアウト

2. **データ準備**
   - 必要なデータのみを渡す
   - 事前に計算・集計を行う
   - NULLチェックを徹底

3. **エラーハンドリング**
   - 適切な例外処理
   - ログ記録
   - ユーザーへのフィードバック

4. **パフォーマンス**
   - 必要な時のみPDF生成
   - 非同期処理の活用
   - キャッシュの活用

## API使用例

### REST API経由でのPDF生成

```python
from flask import Blueprint, send_file

@bp.route('/api/reports/<int:report_id>/download')
@login_required
def download_report_api(report_id):
    """レポートPDFをダウンロード"""
    report = Report.query.get_or_404(report_id)

    # 権限チェック
    if not current_user.can_access_report(report):
        return jsonify({'error': 'Unauthorized'}), 403

    return send_file(
        report.file_path,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f"{report.report_type}_{report.id}.pdf"
    )
```

### 非同期PDF生成

```python
from celery import Celery

@celery.task
def generate_pdf_async(report_id):
    """バックグラウンドでPDF生成"""
    report = Report.query.get(report_id)

    # PDF生成処理
    generator = ReportGenerator()
    pdf_bytes = generator._generate_monthly_pdf(
        data=report.data,
        start_date=report.date_from,
        end_date=report.date_to
    )

    # ファイル保存
    with open(report.file_path, 'wb') as f:
        f.write(pdf_bytes)

    return report_id
```

## まとめ

WeasyPrintを使用したPDF生成機能により、以下が実現されています:

- ✅ ISO 27001準拠レポート
- ✅ ISO 19650準拠レポート
- ✅ 3-2-1-1-0コンプライアンスレポート
- ✅ 監査ログレポート
- ✅ 日本語フォント対応
- ✅ グラフ・チャート埋め込み
- ✅ プロフェッショナルなレイアウト
- ✅ ページ番号・ヘッダー・フッター
- ✅ 目次自動生成
- ✅ 表紙ページ

これらの機能により、エンタープライズグレードのPDFレポート生成が可能になりました。
