#!/bin/bash
# Pre-push Hook
# このフックは、git pushの前に自動実行されます

echo "🚀 プッシュ前チェックを実行中..."

# Python環境の確認
if [ -d "venv" ]; then
    source venv/bin/activate 2>/dev/null || true
fi

# 1. テストの実行
echo "🧪 テストを実行中..."
if [ -f "pytest.ini" ] || [ -d "tests" ]; then
    if command -v pytest &> /dev/null; then
        pytest tests/ -v --tb=short 2>/dev/null || {
            echo "❌ テストに失敗しました！"
            echo "プッシュを中止することをお勧めします"
            exit 1
        }
    fi
fi

# 2. ビルドチェック（該当する場合）
if [ -f "setup.py" ] || [ -f "pyproject.toml" ]; then
    echo "🔨 ビルドチェック中..."
    # 必要に応じてビルドコマンドを追加
fi

# 3. ブランチ保護チェック
CURRENT_BRANCH=$(git branch --show-current)
PROTECTED_BRANCHES=("main" "master" "production")

for branch in "${PROTECTED_BRANCHES[@]}"; do
    if [ "$CURRENT_BRANCH" = "$branch" ]; then
        echo "⚠️  保護されたブランチ '$branch' への直接プッシュを検出しました"
        echo "プルリクエストを使用してください"
        # 警告のみで継続（必要に応じてexit 1で中止）
    fi
done

# 4. リモートとの同期チェック
echo "🔄 リモートとの同期状態を確認中..."
git fetch origin "$CURRENT_BRANCH" 2>/dev/null
LOCAL=$(git rev-parse @)
REMOTE=$(git rev-parse @{u} 2>/dev/null || echo "")
BASE=$(git merge-base @ @{u} 2>/dev/null || echo "")

if [ -n "$REMOTE" ]; then
    if [ "$LOCAL" = "$REMOTE" ]; then
        echo "✅ ローカルとリモートが同期しています"
    elif [ "$LOCAL" = "$BASE" ]; then
        echo "⚠️  リモートに新しい変更があります（pull が必要）"
    elif [ "$REMOTE" = "$BASE" ]; then
        echo "✅ ローカルの変更をプッシュできます"
    else
        echo "⚠️  ローカルとリモートが分岐しています（merge/rebase が必要）"
    fi
fi

echo "✅ プッシュ前チェック完了"
exit 0
