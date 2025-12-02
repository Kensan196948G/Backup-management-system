#!/bin/bash
# Pre-commit Hook
# このフックは、git commitの前に自動実行されます

echo "🔍 コミット前チェックを実行中..."

# Python環境の確認
if [ -d "venv" ]; then
    source venv/bin/activate 2>/dev/null || true
fi

# 1. コードフォーマットチェック（Black）
echo "📋 コードフォーマットをチェック中..."
if command -v black &> /dev/null; then
    black --check . 2>/dev/null || {
        echo "⚠️  コードフォーマットの問題を検出しました"
        echo "自動修正を実行しますか？ (black --fix を実行)"
    }
fi

# 2. インポート順序チェック（isort）
echo "📦 インポート順序をチェック中..."
if command -v isort &> /dev/null; then
    isort --check-only . 2>/dev/null || {
        echo "⚠️  インポート順序の問題を検出しました"
    }
fi

# 3. Lintチェック（flake8）
echo "🔎 Lintチェック中..."
if command -v flake8 &> /dev/null; then
    flake8 . 2>/dev/null || {
        echo "⚠️  Lint警告を検出しました"
    }
fi

# 4. 機密情報チェック
echo "🔒 機密情報チェック中..."
SECRET_PATTERNS=(
    "ghp_[A-Za-z0-9]{36}"  # GitHub Personal Access Token
    "sk-[A-Za-z0-9]{48}"   # OpenAI API Key
    "BSA[A-Za-z0-9-]{32}"  # Brave Search API Key
    "password\s*=\s*['\"][^'\"]{8,}"  # Password
    "api_key\s*=\s*['\"][^'\"]{16,}"  # API Key
)

for pattern in "${SECRET_PATTERNS[@]}"; do
    if git diff --cached | grep -Eq "$pattern"; then
        echo "❌ 機密情報の可能性がある文字列を検出しました！"
        echo "パターン: $pattern"
        echo "コミットを中止してください"
        exit 1
    fi
done

# 5. 大きなファイルのチェック
echo "📊 ファイルサイズをチェック中..."
LARGE_FILES=$(git diff --cached --name-only | xargs -I {} du -h {} 2>/dev/null | awk '$1 ~ /M$/ && $1+0 > 5 {print}')
if [ -n "$LARGE_FILES" ]; then
    echo "⚠️  大きなファイル（>5MB）を検出しました:"
    echo "$LARGE_FILES"
    echo "本当にコミットしますか？"
fi

echo "✅ コミット前チェック完了"
exit 0
