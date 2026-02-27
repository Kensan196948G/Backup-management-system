#!/usr/bin/env bash
# ============================================================
# pre-commit.sh - コミット前の機密情報スキャン
# ============================================================

set -euo pipefail

echo "🔍 pre-commit hook: 機密情報スキャン"

# 機密情報パターン
declare -a PATTERNS=(
    "ghp_[A-Za-z0-9]{36}"                           # GitHub Personal Access Token
    "github_pat_[A-Za-z0-9_]{82}"                    # GitHub fine-grained PAT
    "sk-[A-Za-z0-9]{48}"                            # OpenAI API Key
    "sk-proj-[A-Za-z0-9\-_]{48,}"                   # OpenAI Project API Key
    "AKIA[0-9A-Z]{16}"                              # AWS Access Key ID
    "(?<![0-9a-fA-F-])[0-9]{4}[- ][0-9]{4}[- ][0-9]{4}[- ][0-9]{4}(?![0-9a-fA-F-])" # Credit Card (UUID除外)
    "-----BEGIN (RSA|DSA|EC|OPENSSH) PRIVATE KEY-----" # SSH秘密鍵
    "AIza[0-9A-Za-z\-_]{35}"                        # Google API Key
    "sq0csp-[0-9A-Za-z\-_]{43}"                     # Square Access Token
    "sk_live_[0-9a-zA-Z]{24,}"                      # Stripe Live Key
)

declare -a PATTERN_NAMES=(
    "GitHub Token (ghp_)"
    "GitHub Token (fine-grained)"
    "OpenAI API Key (sk-)"
    "OpenAI API Key (project)"
    "AWS Access Key"
    "クレジットカード番号"
    "SSH 秘密鍵"
    "Google API Key"
    "Square Token"
    "Stripe Live Key"
)

FOUND_SECRETS=false
FOUND_COUNT=0

# ステージングされたファイルを取得（null区切りで特殊文字・日本語ファイル名対応）
STAGED_FILES=$(git diff --cached --name-only --diff-filter=ACM -z 2>/dev/null | tr '\0' '\n' || echo "")

if [ -z "$STAGED_FILES" ]; then
    echo "  ℹ️  ステージングされたファイルがありません"
    exit 0
fi

# 各パターンでスキャン
for i in "${!PATTERNS[@]}"; do
    pattern="${PATTERNS[$i]}"
    pattern_name="${PATTERN_NAMES[$i]}"

    # ステージングされた差分から検索（PCRE: lookbehind/lookahead対応）
    if git diff --cached | grep -P "$pattern" >/dev/null 2>&1; then
        echo "  ❌ 機密情報が検出されました: $pattern_name"
        echo "     パターン: $pattern"

        # 具体的なファイル名を特定（while readで特殊文字・日本語ファイル名対応）
        while IFS= read -r file; do
            [ -z "$file" ] && continue
            if git diff --cached -- "$file" | grep -P "$pattern" >/dev/null 2>&1; then
                echo "     ファイル: $file"
            fi
        done <<< "$STAGED_FILES"

        FOUND_SECRETS=true
        FOUND_COUNT=$((FOUND_COUNT + 1))
    fi
done

if [ "$FOUND_SECRETS" = true ]; then
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "⚠️  コミットを中断しました"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "検出された機密情報: ${FOUND_COUNT}件"
    echo ""
    echo "💡 対処方法:"
    echo "  1. 機密情報を削除または環境変数に置き換えてください"
    echo "  2. config.json の Token は Base64 エンコード済みであることを確認"
    echo "  3. 修正後、再度 git add してコミットしてください"
    echo ""
    echo "意図的にコミットする場合（非推奨）:"
    echo "  git commit --no-verify -m \"your message\""
    echo ""
    exit 1
fi

echo "  ✅ 機密情報スキャン完了（問題なし）"
STAGED_FILE_COUNT=$(echo "${STAGED_FILES}" | wc -l)
echo "  スキャン対象: ${STAGED_FILE_COUNT} ファイル"
exit 0
