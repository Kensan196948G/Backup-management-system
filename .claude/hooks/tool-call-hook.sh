#!/bin/bash
# Tool Call Hook
# このフックは、ツールが呼び出される前に自動実行されます

TOOL_NAME="$1"
TOOL_ARGS="$2"

echo "🔧 ツール呼び出し: $TOOL_NAME"

# 特定のツールに対する追加チェック
case "$TOOL_NAME" in
    "Bash")
        # Bashコマンドの安全性チェック
        if echo "$TOOL_ARGS" | grep -Eq "(rm -rf|dd|mkfs|format)"; then
            echo "⚠️  危険なコマンドを検出しました: $TOOL_ARGS"
            echo "実行前に確認してください"
        fi
        ;;
    "Write"|"Edit")
        # ファイル操作の通知
        echo "📝 ファイル操作を実行します"
        ;;
    "Task")
        # SubAgent起動の通知
        echo "🤖 SubAgentを起動します"
        ;;
esac

exit 0
