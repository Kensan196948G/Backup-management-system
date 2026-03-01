#!/bin/bash
# User Prompt Submit Hook
# このフックは、ユーザーがプロンプトを送信する前に自動実行されます

# 環境変数の確認
if [ -z "$PROMPT" ]; then
    echo "⚠️  警告: プロンプトが空です"
    exit 1
fi

# プロンプトの前処理（必要に応じてカスタマイズ）
# 例: 特定のキーワードを検出して追加情報を提供
if echo "$PROMPT" | grep -qi "test"; then
    echo "ℹ️  テスト関連のリクエストを検出しました"
    echo "pytest を使用してテストを実行します"
fi

if echo "$PROMPT" | grep -qi "deploy\|デプロイ"; then
    echo "⚠️  デプロイ関連のリクエストを検出しました"
    echo "本番環境への影響に注意してください"
fi

# セキュリティチェック
if echo "$PROMPT" | grep -Eq "(password|secret|token|api_key|private_key)"; then
    echo "🔒 機密情報の可能性がある単語を検出しました"
    echo "機密情報を含まないように注意してください"
fi

# 成功
exit 0
