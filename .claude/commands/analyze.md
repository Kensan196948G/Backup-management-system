# コード分析コマンド

コードの品質、セキュリティ、パフォーマンスを総合的に分析します。

## 📋 概要

このコマンドは、複数の分析ツールを並列実行して、コードベースの状態を包括的に評価します。

## 🎯 分析項目

### 1. コード品質分析
- **Linting**: flake8による構文チェック
- **フォーマット**: blackによるコードスタイルチェック
- **インポート**: isortによるインポート順序チェック
- **型チェック**: mypyによる型アノテーション検証

### 2. セキュリティ分析
- **機密情報検出**: APIキー、パスワード等の検出
- **依存関係**: 既知の脆弱性チェック
- **インジェクション**: SQL/コマンドインジェクションの可能性

### 3. パフォーマンス分析
- **複雑度**: サイクロマティック複雑度の測定
- **重複コード**: コードの重複検出
- **最適化**: パフォーマンスのボトルネック特定

### 4. テストカバレッジ
- **カバレッジ率**: pytest-covによるカバレッジ測定
- **未テストコード**: テストが不足している箇所の特定

## 🚀 実行手順

### ステップ1: 環境確認

```bash
# Python仮想環境のアクティベート
source venv/bin/activate

# 必要なツールの確認
which flake8 black isort mypy pytest
```

### ステップ2: 並列分析実行

以下を並列実行：

```bash
# コード品質
flake8 . --statistics --format=json > reports/flake8.json

# フォーマット
black --check . --diff > reports/black.txt

# インポート
isort --check-only . --diff > reports/isort.txt

# 型チェック
mypy . --ignore-missing-imports > reports/mypy.txt

# テストカバレッジ
pytest --cov=. --cov-report=html --cov-report=json > reports/coverage.txt
```

### ステップ3: 結果の統合

各分析結果を統合して、包括的なレポートを作成します。

## 📊 レポート形式

分析完了後、以下の形式でレポートを提供します：

```markdown
# コード分析レポート

## 📈 サマリー

- **総合評価**: A / B / C / D / F
- **分析日時**: YYYY-MM-DD HH:MM:SS
- **分析対象**: [プロジェクト名]

## 🔍 詳細結果

### コード品質
- Flake8: ✅ エラー0件、警告3件
- Black: ⚠️ 5ファイルに要フォーマット
- Isort: ✅ 問題なし
- Mypy: ⚠️ 型エラー12件

### セキュリティ
- 機密情報: ✅ 検出なし
- 依存関係: ⚠️ 2件の古いパッケージ
- インジェクション: ✅ 問題なし

### パフォーマンス
- 複雑度: ✅ 平均3.5（良好）
- 重複コード: ⚠️ 2箇所で検出

### テストカバレッジ
- カバレッジ率: 78%
- 未カバー: 主にエラーハンドリング

## 🎯 推奨アクション

1. [ ] Blackでコードをフォーマット
2. [ ] Mypyの型エラーを修正
3. [ ] 依存関係を更新
4. [ ] テストカバレッジを85%以上に向上
```

## ⚙️ カスタマイズ

### 分析対象の指定

特定のディレクトリのみを分析：

```bash
# appディレクトリのみ
flake8 app/
black --check app/
pytest app/tests/
```

### 除外設定

`.flake8`, `pyproject.toml` で除外パターンを設定：

```ini
[flake8]
exclude = venv,migrations,__pycache__
max-line-length = 100
```

## 🔧 トラブルシューティング

### ツールが見つからない

```bash
pip install flake8 black isort mypy pytest pytest-cov
```

### 権限エラー

```bash
chmod +x scripts/analyze.sh
```

### メモリ不足

大規模プロジェクトの場合、分析を分割：

```bash
# ディレクトリごとに分析
for dir in app/ tests/ scripts/; do
    flake8 $dir
done
```

## 💡 ベストプラクティス

1. **定期実行**: CI/CDパイプラインに組み込む
2. **段階的改善**: 一度に全て修正しようとしない
3. **優先順位**: セキュリティ > 品質 > パフォーマンス
4. **継続的監視**: 定期的に分析を実行

## 🔗 関連コマンド

- `/commit` - 分析後のコミット
- `/pr` - 改善後のPR作成
- `/parallel-dev` - 並列で修正作業
