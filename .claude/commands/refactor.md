# リファクタリングコマンド

コードの品質を向上させるためのリファクタリングを支援します。

## 📋 概要

このコマンドは、コードの動作を変えずに内部構造を改善するリファクタリングを実行します。

## 🎯 リファクタリングパターン

### 1. 関数の抽出
長い関数を複数の小さな関数に分割

**Before:**
```python
def process_backup(data):
    # 100行の処理...
    pass
```

**After:**
```python
def process_backup(data):
    validated_data = validate_data(data)
    prepared_data = prepare_backup(validated_data)
    result = execute_backup(prepared_data)
    return finalize_backup(result)

def validate_data(data):
    # 検証ロジック
    pass

def prepare_backup(data):
    # 準備ロジック
    pass
```

### 2. マジックナンバーの定数化

**Before:**
```python
if age >= 18:
    # 処理
```

**After:**
```python
ADULT_AGE = 18

if age >= ADULT_AGE:
    # 処理
```

### 3. 重複コードの削除

**Before:**
```python
def backup_file(path):
    if not os.path.exists(path):
        raise FileNotFoundError
    # バックアップ処理

def restore_file(path):
    if not os.path.exists(path):
        raise FileNotFoundError
    # リストア処理
```

**After:**
```python
def validate_path(path):
    if not os.path.exists(path):
        raise FileNotFoundError

def backup_file(path):
    validate_path(path)
    # バックアップ処理

def restore_file(path):
    validate_path(path)
    # リストア処理
```

### 4. クラスへの抽出

関連する関数をクラスにまとめる

**Before:**
```python
def create_backup(data): pass
def restore_backup(data): pass
def verify_backup(data): pass
```

**After:**
```python
class BackupManager:
    def create(self, data): pass
    def restore(self, data): pass
    def verify(self, data): pass
```

### 5. 条件分岐の簡素化

**Before:**
```python
if status == "active":
    return True
else:
    return False
```

**After:**
```python
return status == "active"
```

## 🚀 実行フロー

### ステップ1: コード分析

```bash
# 複雑度の測定
radon cc . -a

# 重複コードの検出
pylint --disable=all --enable=duplicate-code .
```

### ステップ2: リファクタリング候補の特定

以下の基準で候補を特定：
- 関数の長さ > 50行
- サイクロマティック複雑度 > 10
- 重複コード > 3箇所
- ネストレベル > 4

### ステップ3: リファクタリング実行

優先順位：
1. **高**: セキュリティ改善
2. **中**: 可読性向上
3. **低**: パフォーマンス最適化

### ステップ4: テスト実行

```bash
# リファクタリング後のテスト
pytest tests/ -v

# カバレッジ確認
pytest --cov=app tests/
```

## 📊 リファクタリングレポート

```markdown
# リファクタリングレポート

## サマリー
- **対象ファイル**: app/backup.py
- **リファクタリング数**: 5箇所
- **複雑度改善**: 15 → 8
- **行数削減**: -45行

## 実施内容

### 1. 関数の抽出
**場所**: backup.py:123-187
**改善**: `create_backup()` を4つの関数に分割
**効果**:
- 複雑度: 12 → 4
- 可読性向上
- テスト容易性向上

### 2. 重複コードの削除
**場所**: backup.py:45-67, restore.py:34-56
**改善**: 共通ロジックを `utils.py` に移動
**効果**:
- -34行のコード削減
- 保守性向上

### 3. マジックナンバーの定数化
**場所**: backup.py:全体
**改善**: 8個の数値を定数化
**効果**:
- 意図が明確に
- 変更が容易に

## テスト結果

✅ **全テスト成功**: 150/150
✅ **カバレッジ維持**: 82% → 85%
✅ **パフォーマンス**: 影響なし

## ビフォーアフター

### 複雑度
- Before: 平均 12.3
- After: 平均 6.8
- 改善: 44.7%

### 行数
- Before: 1,245行
- After: 1,089行
- 削減: 156行 (12.5%)

### 保守性インデックス
- Before: 68
- After: 82
- 改善: +14ポイント
```

## ⚙️ リファクタリングツール

### Rope (Python)
```bash
# インストール
pip install rope

# 使用例（関数の抽出）
rope extract_method backup.py 123 187
```

### Black (自動フォーマット)
```bash
black .
```

### Autoflake (不要コードの削除)
```bash
autoflake --remove-all-unused-imports --in-place .
```

## ⚠️ 注意事項

### リファクタリング前の確認

1. ✅ **テストが存在する**
   - リファクタリング前に十分なテストカバレッジを確保

2. ✅ **バージョン管理**
   - git commit でセーフティネットを作成

3. ✅ **小さなステップ**
   - 一度に大きく変更しない

4. ✅ **テストを頻繁に実行**
   - 各変更後にテストを実行

### やってはいけないこと

❌ **動作の変更**
- リファクタリングは構造のみを変更

❌ **テストなしで実施**
- 必ずテストを実行

❌ **複数の変更を同時に**
- 機能追加とリファクタリングを分離

## 💡 ベストプラクティス

1. **レッド・グリーン・リファクター**
   - テスト → 実装 → リファクタリング

2. **段階的改善**
   - 完璧を目指さず、継続的に改善

3. **レビュー**
   - リファクタリング後もコードレビュー

4. **ドキュメント更新**
   - 構造が変わったらドキュメントも更新

## 🔗 関連コマンド

- `/analyze` - リファクタリング候補の特定
- `/test` - リファクタリング後のテスト
- `/review` - リファクタリング結果のレビュー
- `/commit` - リファクタリングのコミット
