# E2E Tests

Playwrightを使ったブラウザE2Eテスト。

## セットアップ

```bash
pip install -r requirements-dev.txt
playwright install chromium
```

## 実行

```bash
# 全E2Eテスト
pytest tests/e2e/ -v

# テスト収集確認（ブラウザ不要）
pytest tests/e2e/ -v --co
```

## 構成

- `conftest.py` - Flaskライブサーバー + Playwright フィクスチャ
- `test_auth_e2e.py` - 認証フロー（ログイン / ログアウト）
- `test_dashboard_e2e.py` - ダッシュボード表示
