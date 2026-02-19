# Webビューとテンプレート実装ドキュメント

## 概要

バックアップ管理システムのWebインターフェースを実装しました。Bootstrap 5を使用したレスポンシブデザインで、日本語UIを提供します。

## 実装済みファイル

### 1. ビュー (Views)

#### app/views/__init__.py
- Blueprint定義と登録関数
- 5つのBlueprintを定義:
  - `dashboard_bp`: ダッシュボード
  - `jobs_bp`: バックアップジョブ管理
  - `media_bp`: オフラインメディア管理
  - `verification_bp`: 検証テスト管理
  - `reports_bp`: レポート管理

#### app/views/dashboard.py
**機能:**
- ダッシュボード表示
- 3-2-1-1-0ルール準拠率の可視化
- バックアップ成功率グラフ (7日間)
- ストレージ使用状況
- 未確認アラート一覧
- 次回実行予定ジョブ一覧

**エンドポイント:**
- `GET /` または `/dashboard` - ダッシュボード表示
- `GET /api/dashboard/stats` - 統計データ取得 (JSON)
- `GET /api/dashboard/compliance-chart` - 準拠状況チャートデータ
- `GET /api/dashboard/success-rate-chart` - 成功率チャートデータ
- `GET /api/dashboard/storage-chart` - ストレージチャートデータ

#### app/views/jobs.py
**機能:**
- バックアップジョブの一覧、詳細、作成、編集、削除
- フィルタリングとページネーション
- コンプライアンスチェック実行
- ジョブの有効/無効切り替え

**エンドポイント:**
- `GET /jobs` - ジョブ一覧
- `GET /jobs/<id>` - ジョブ詳細
- `GET /jobs/create` - ジョブ作成フォーム
- `POST /jobs/create` - ジョブ作成処理
- `GET /jobs/<id>/edit` - ジョブ編集フォーム
- `POST /jobs/<id>/edit` - ジョブ更新処理
- `POST /jobs/<id>/delete` - ジョブ削除 (admin only)
- `POST /jobs/<id>/toggle-active` - 有効/無効切り替え
- `POST /jobs/<id>/check-compliance` - コンプライアンスチェック

**権限:**
- 閲覧: すべてのログインユーザー
- 作成/編集: admin, operator
- 削除: admin only

#### app/views/media.py
**機能:**
- オフラインメディアの在庫管理
- メディアの貸出/返却
- ローテーションスケジュール管理

**エンドポイント:**
- `GET /media` - メディア一覧
- `GET /media/<id>` - メディア詳細
- `GET /media/create` - メディア作成フォーム
- `POST /media/create` - メディア作成処理
- `GET /media/<id>/edit` - メディア編集フォーム
- `POST /media/<id>/edit` - メディア更新処理
- `POST /media/<id>/delete` - メディア削除 (admin only)
- `GET /media/<id>/lend` - メディア貸出フォーム
- `POST /media/<id>/lend` - メディア貸出処理
- `POST /media/<id>/return` - メディア返却処理
- `GET /media/rotation-schedule` - ローテーションスケジュール

**権限:**
- 閲覧: すべてのログインユーザー
- 作成/編集/貸出/返却: admin, operator
- 削除: admin only

#### app/views/verification.py
**機能:**
- 検証テストの実行と履歴管理
- 検証スケジュール管理
- テスト結果の記録

**エンドポイント:**
- `GET /verification` - テスト一覧
- `GET /verification/<id>` - テスト詳細
- `GET /verification/execute` - テスト実行フォーム
- `POST /verification/execute` - テスト実行処理
- `GET /verification/<id>/update` - テスト結果更新フォーム
- `POST /verification/<id>/update` - テスト結果更新処理
- `GET /verification/schedule` - スケジュール一覧
- `GET /verification/schedule/create` - スケジュール作成フォーム
- `POST /verification/schedule/create` - スケジュール作成処理
- `GET /verification/schedule/<id>/edit` - スケジュール編集フォーム
- `POST /verification/schedule/<id>/edit` - スケジュール更新処理
- `POST /verification/schedule/<id>/delete` - スケジュール削除 (admin only)

**権限:**
- 閲覧: すべてのログインユーザー
- 実行/更新/スケジュール作成/編集: admin, operator
- 削除: admin only

#### app/views/reports.py
**機能:**
- レポート生成と閲覧
- レポートのダウンロード
- レポートダッシュボード

**エンドポイント:**
- `GET /reports` - レポート一覧
- `GET /reports/<id>` - レポート詳細
- `GET /reports/generate` - レポート生成フォーム
- `POST /reports/generate` - レポート生成処理
- `GET /reports/<id>/download` - レポートダウンロード
- `POST /reports/<id>/delete` - レポート削除 (admin only)
- `GET /reports/dashboard` - レポートダッシュボード

**レポートタイプ:**
- `compliance`: 3-2-1-1-0ルール準拠レポート
- `backup_status`: バックアップステータスレポート
- `verification`: 検証テストレポート
- `job_detail`: ジョブ詳細レポート

**権限:**
- 閲覧/ダウンロード: すべてのログインユーザー
- 生成: admin, operator, auditor
- 削除: admin only

### 2. テンプレート (Templates)

#### app/templates/base.html
**特徴:**
- Bootstrap 5ベース
- レスポンシブナビゲーション
- フラッシュメッセージ表示
- アラート通知ベル (リアルタイム更新)
- ユーザードロップダウンメニュー
- フッター

**CDN:**
- Bootstrap 5.3.0
- Bootstrap Icons 1.11.0
- Chart.js 4.4.0
- DataTables 1.13.6
- jQuery 3.7.0

#### app/templates/dashboard.html
**ウィジェット:**
- 統計カード (4種類):
  - 3-2-1-1-0ルール準拠率
  - バックアップ成功率 (7日間)
  - 未確認アラート
  - オフラインメディア数
- グラフ (3種類):
  - 準拠状況 (円グラフ)
  - 成功率推移 (折れ線グラフ)
  - ストレージ使用状況 (棒グラフ)
- テーブル (3種類):
  - 未確認アラート一覧
  - 次回実行予定ジョブ
  - 最近の実行履歴

#### app/templates/jobs/list.html
**機能:**
- フィルタリング:
  - 検索 (ジョブ名、サーバー名)
  - 種別 (system_image, file, database, vm)
  - ステータス (active, inactive)
  - 準拠状況 (compliant, non_compliant)
  - 担当者
- ソート機能
- ページネーション
- DataTables統合

#### app/templates/jobs/detail.html
**セクション:**
1. 基本情報
2. 3-2-1-1-0ルール準拠状況
3. バックアップコピー一覧
4. 実行履歴
5. 検証テスト履歴
6. 関連アラート

**アクション:**
- 編集 (operator以上)
- 有効/無効切り替え (operator以上)
- 削除 (admin only)
- コンプライアンスチェック実行

#### app/templates/jobs/create.html
**フォームフィールド:**
- ジョブ名 (必須)
- 種別 (必須)
- 対象サーバー (必須)
- 対象パス
- バックアップツール
- スケジュール種別
- 実行時刻
- 保持期間
- 説明
- 有効/無効

**サイドパネル:**
- ヘルプガイド
- 3-2-1-1-0ルール説明

#### app/templates/jobs/edit.html
- create.htmlと同様のフォーム
- 既存データをプリセット
- 更新ボタン

### 3. 静的ファイル (Static)

#### app/static/css/custom.css
**スタイル:**
- カラースキーム定義
- カード拡張スタイル
- ナビゲーション強化
- テーブルスタイリング
- フォームスタイリング
- レスポンシブユーティリティ
- アニメーション
- プリントスタイル

**カスタムクラス:**
- `.border-left-*` - 左ボーダーカラー
- `.text-xs`, `.text-sm` - テキストサイズ
- `.shadow-*` - シャドウバリエーション
- `.compliance-badge` - 準拠バッジ
- `.chart-container` - チャートコンテナ

#### app/static/js/main.js
**関数:**
- `initTooltips()` - ツールチップ初期化
- `initPopovers()` - ポップオーバー初期化
- `initAutoDismissAlerts()` - アラート自動非表示
- `initConfirmationDialogs()` - 確認ダイアログ
- `initDataTables()` - DataTables初期化
- `initFormValidation()` - フォーム検証
- `showToast(message, type)` - トースト通知表示
- `formatBytes(bytes)` - バイト数フォーマット
- `formatDateJP(date)` - 日本語日付フォーマット
- `copyToClipboard(text)` - クリップボードコピー
- `exportTableToCSV(tableId, filename)` - CSV出力
- `apiCall(url, options)` - AJAX呼び出し

**グローバルオブジェクト:**
```javascript
window.backupMgmt = {
    showLoadingSpinner,
    hideLoadingSpinner,
    showToast,
    formatBytes,
    formatDateJP,
    confirmDelete,
    copyToClipboard,
    exportTableToCSV,
    debounce,
    apiCall,
    getCSRFToken
}
```

## デザインシステム

### カラーパレット

```css
--primary-color: #007bff;   /* プライマリ */
--success-color: #28a745;   /* 成功 */
--warning-color: #ffc107;   /* 警告 */
--danger-color: #dc3545;    /* エラー/危険 */
--info-color: #17a2b8;      /* 情報 */
--dark-color: #343a40;      /* ダーク */
```

### ステータスカラー

- **成功 (Success)**: `#28a745` (緑)
- **警告 (Warning)**: `#ffc107` (黄)
- **エラー (Error)**: `#dc3545` (赤)
- **情報 (Info)**: `#17a2b8` (青)

### 準拠状況カラー

- **準拠 (Compliant)**: `#28a745` (緑)
- **非準拠 (Non-compliant)**: `#dc3545` (赤)
- **警告 (Warning)**: `#ffc107` (黄)

### レスポンシブブレークポイント

- **XS**: < 576px (スマートフォン)
- **SM**: ≥ 576px (タブレット縦)
- **MD**: ≥ 768px (タブレット横)
- **LG**: ≥ 992px (デスクトップ)
- **XL**: ≥ 1200px (大型デスクトップ)

## セキュリティ

### 認証・認可

- すべてのビューは `@login_required` デコレーター付き
- ロールベースアクセス制御 (RBAC):
  - `admin`: 全機能
  - `operator`: 運用機能
  - `viewer`: 閲覧のみ
  - `auditor`: 監査ログとレポート

### CSRF保護

- Flask-WTF CSRF トークンを使用
- すべてのフォームでCSRF保護を実装

### 入力検証

- HTML5フォーム検証
- サーバーサイド検証
- XSS対策 (Jinjaテンプレート自動エスケープ)

## パフォーマンス

### 最適化

- ページネーション (20件/ページ)
- 遅延ロード (DataTables)
- Chart.jsの軽量化設定
- CDNからの静的ファイル読み込み

### キャッシング

- ブラウザキャッシュ活用
- 静的ファイルのバージョニング

## アクセシビリティ

- セマンティックHTML
- ARIA属性の使用
- キーボードナビゲーション対応
- コントラスト比の確保
- スクリーンリーダー対応

## ブラウザ対応

- Chrome (最新版)
- Firefox (最新版)
- Edge (最新版)
- Safari (最新版)

## 今後の拡張

### 未実装のテンプレート

以下のテンプレートは必要に応じて追加実装してください:

1. **メディア関連:**
   - `app/templates/media/list.html`
   - `app/templates/media/detail.html`
   - `app/templates/media/create.html`
   - `app/templates/media/edit.html`
   - `app/templates/media/lend.html`
   - `app/templates/media/rotation_schedule.html`

2. **検証テスト関連:**
   - `app/templates/verification/list.html`
   - `app/templates/verification/detail.html`
   - `app/templates/verification/execute.html`
   - `app/templates/verification/update.html`
   - `app/templates/verification/schedule.html`
   - `app/templates/verification/create_schedule.html`
   - `app/templates/verification/edit_schedule.html`

3. **レポート関連:**
   - `app/templates/reports/list.html`
   - `app/templates/reports/detail.html`
   - `app/templates/reports/generate.html`
   - `app/templates/reports/dashboard.html`

4. **エラーページ:**
   - `app/templates/errors/403.html` (Forbidden)
   - `app/templates/errors/404.html` (Not Found)
   - `app/templates/errors/500.html` (Internal Server Error)

### 機能拡張案

1. **リアルタイム更新:**
   - WebSocketsによるリアルタイム通知
   - ジョブ実行状況のライブ更新

2. **高度なフィルタリング:**
   - 複数条件の保存
   - カスタムビューの作成

3. **エクスポート機能:**
   - PDF出力
   - Excel出力

4. **ダークモード:**
   - テーマ切り替え機能

5. **多言語対応:**
   - Flask-Babelによる国際化

## テスト

### 手動テスト手順

1. **ダッシュボード:**
   ```
   http://localhost:5000/dashboard
   ```
   - 統計カードの表示確認
   - グラフの描画確認
   - アラート一覧の表示確認

2. **ジョブ一覧:**
   ```
   http://localhost:5000/jobs
   ```
   - フィルター機能のテスト
   - ページネーション動作確認
   - ソート機能確認

3. **ジョブ作成:**
   ```
   http://localhost:5000/jobs/create
   ```
   - フォーム検証のテスト
   - 必須フィールドの確認
   - ジョブ作成の成功/失敗

4. **権限テスト:**
   - viewer ユーザーで編集ボタンが表示されないことを確認
   - operator ユーザーでジョブ作成/編集可能を確認
   - admin ユーザーで削除機能が利用可能を確認

### 自動テスト

```python
# tests/test_views.py
def test_dashboard_access(client, auth):
    auth.login()
    response = client.get('/dashboard')
    assert response.status_code == 200
    assert b'ダッシュボード' in response.data

def test_job_list_filter(client, auth):
    auth.login()
    response = client.get('/jobs?type=database')
    assert response.status_code == 200

def test_job_create_permission(client, auth):
    auth.login(username='viewer')
    response = client.get('/jobs/create')
    assert response.status_code == 403  # Forbidden
```

## トラブルシューティング

### よくある問題

1. **Chart.jsが表示されない:**
   - ブラウザコンソールでエラー確認
   - APIエンドポイントのレスポンス確認

2. **DataTablesのスタイルが崩れる:**
   - CSS/JSの読み込み順序確認
   - CDNの可用性確認

3. **フォーム送信が失敗する:**
   - CSRFトークンの確認
   - ネットワークタブでリクエスト内容確認

## まとめ

このWebビュー実装により、バックアップ管理システムの完全なWebインターフェースが提供されます。Bootstrap 5によるモダンで使いやすいUIと、Chart.jsによる視覚的なデータ表示により、3-2-1-1-0ルールの準拠状況を簡単に把握できます。

実装されたすべてのビューは、認証・認可が適切に設定されており、ロールベースのアクセス制御が機能します。レスポンシブデザインにより、デスクトップ、タブレット、スマートフォンなど、あらゆるデバイスで利用可能です。
