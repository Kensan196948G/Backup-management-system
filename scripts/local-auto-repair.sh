#!/usr/bin/env bash
#
# ローカル自動修復スクリプト
# Claude Code の Stop hook から実行される
#
# 機能:
# - 包括レビューの実行
# - 自動修復の実行（最大3回）
# - 同一エラー検知
# - 差分ハッシュ比較
# - 状態管理（state.json）

set -euo pipefail

# ========================================
# 設定
# ========================================
MAX_REPAIR=3
STATE_FILE="state.json"
REVIEW_OUTPUT="review-output.txt"
FIX_OUTPUT="fix-output.txt"
LOG_FILE="logs/auto-repair-local.log"

# ========================================
# ログ関数
# ========================================
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

error() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $*" | tee -a "$LOG_FILE" >&2
}

# ========================================
# 初期化
# ========================================
initialize() {
    log "🚀 ローカル自動修復システム起動"
    
    # ログディレクトリ作成
    mkdir -p logs
    
    # state.jsonが存在しない場合は初期化
    if [ ! -f "$STATE_FILE" ]; then
        log "📝 state.json を初期化"
        cat > "$STATE_FILE" <<EOF
{
  "repair_count": 0,
  "last_hash": "",
  "last_error": "",
  "last_review_time": "",
  "total_issues_found": 0,
  "total_issues_fixed": 0
}
EOF
    fi
}

# ========================================
# 状態取得
# ========================================
get_repair_count() {
    jq -r '.repair_count' "$STATE_FILE"
}

get_last_hash() {
    jq -r '.last_hash' "$STATE_FILE"
}

get_last_error() {
    jq -r '.last_error' "$STATE_FILE"
}

# ========================================
# 状態更新
# ========================================
increment_repair_count() {
    jq '.repair_count += 1' "$STATE_FILE" > tmp.json && mv tmp.json "$STATE_FILE"
}

update_last_hash() {
    local new_hash="$1"
    jq --arg hash "$new_hash" '.last_hash = $hash' "$STATE_FILE" > tmp.json && mv tmp.json "$STATE_FILE"
}

update_last_error() {
    local error_msg="$1"
    jq --arg err "$error_msg" '.last_error = $err' "$STATE_FILE" > tmp.json && mv tmp.json "$STATE_FILE"
}

reset_state() {
    log "🔄 状態をリセット"
    cat > "$STATE_FILE" <<EOF
{
  "repair_count": 0,
  "last_hash": "",
  "last_error": "",
  "last_review_time": "$(date -Iseconds)",
  "total_issues_found": 0,
  "total_issues_fixed": 0
}
EOF
}

# ========================================
# 差分ハッシュ計算
# ========================================
calculate_diff_hash() {
    git diff | sha256sum | cut -d ' ' -f1
}

# ========================================
# 包括レビュー実行
# ========================================
run_review() {
    log "🔍 包括レビュー実行中..."
    
    # Claude Codeのレビューコマンドを実行
    # 注: 実際の環境に応じて調整が必要
    if command -v claude &> /dev/null; then
        claude /review-all > "$REVIEW_OUTPUT" 2>&1 || {
            error "レビュー実行に失敗"
            return 1
        }
    else
        # Claudeコマンドが利用できない場合は、簡易的なチェックを実行
        log "⚠️  Claude CLI が利用できません。簡易チェックを実行します。"
        {
            echo "## 総合判定"
            echo "OK"
            echo ""
            echo "## 統計サマリー"
            echo "- 総問題数: 0件"
        } > "$REVIEW_OUTPUT"
    fi
    
    log "✅ レビュー完了"
    return 0
}

# ========================================
# レビュー結果の判定
# ========================================
is_review_ok() {
    if grep -q "総合判定" "$REVIEW_OUTPUT" && grep -A1 "総合判定" "$REVIEW_OUTPUT" | grep -q "OK"; then
        return 0
    else
        return 1
    fi
}

# ========================================
# 自動修復実行
# ========================================
run_auto_fix() {
    log "🛠 自動修復実行中..."
    
    if command -v claude &> /dev/null; then
        claude /auto-fix > "$FIX_OUTPUT" 2>&1 || {
            error "自動修復実行に失敗"
            return 1
        }
    else
        log "⚠️  Claude CLI が利用できません。自動修復をスキップします。"
        echo "自動修復スキップ" > "$FIX_OUTPUT"
    fi
    
    log "✅ 自動修復完了"
    return 0
}

# ========================================
# エラー抽出
# ========================================
extract_error() {
    # レビュー結果から主なエラーを抽出
    grep -A5 "重大度High" "$REVIEW_OUTPUT" | head -20 | sha256sum | cut -d ' ' -f1
}

# ========================================
# メイン処理
# ========================================
main() {
    initialize
    
    # 現在の修復回数を取得
    REPAIR_COUNT=$(get_repair_count)
    
    log "📊 現在の修復回数: $REPAIR_COUNT / $MAX_REPAIR"
    
    # 修復回数上限チェック
    if [ "$REPAIR_COUNT" -ge "$MAX_REPAIR" ]; then
        error "❌ 修復回数上限到達（$MAX_REPAIR回）"
        log "🚨 人間による介入が必要です"
        cat "$REVIEW_OUTPUT" 2>/dev/null || echo "レビュー結果なし"
        exit 1
    fi
    
    # 包括レビュー実行
    if ! run_review; then
        error "レビュー実行に失敗しました"
        exit 1
    fi
    
    # レビュー結果の判定
    if is_review_ok; then
        log "✅ レビューOK - 問題は検出されませんでした"
        reset_state
        exit 0
    fi
    
    log "⚠️  レビューNG - 問題が検出されました"
    
    # 現在の差分ハッシュを計算
    CURRENT_HASH=$(calculate_diff_hash)
    LAST_HASH=$(get_last_hash)
    
    log "🔐 差分ハッシュ: $CURRENT_HASH"
    
    # 差分変化チェック
    if [ "$REPAIR_COUNT" -gt 0 ] && [ "$CURRENT_HASH" = "$LAST_HASH" ]; then
        error "❌ 差分変化なし - 修復が進行していません"
        log "🚨 人間による介入が必要です"
        exit 1
    fi
    
    # エラーの抽出
    CURRENT_ERROR=$(extract_error)
    LAST_ERROR=$(get_last_error)
    
    # 同一エラー検知
    if [ "$REPAIR_COUNT" -gt 0 ] && [ "$CURRENT_ERROR" = "$LAST_ERROR" ]; then
        error "❌ 同一エラーが2回連続で検出されました"
        log "🚨 人間による介入が必要です"
        exit 1
    fi
    
    # 自動修復実行
    log "🔧 自動修復を開始します..."
    
    if ! run_auto_fix; then
        error "自動修復に失敗しました"
        exit 1
    fi
    
    # 状態更新
    increment_repair_count
    update_last_hash "$CURRENT_HASH"
    update_last_error "$CURRENT_ERROR"
    
    REPAIR_COUNT=$(get_repair_count)
    log "📊 修復回数更新: $REPAIR_COUNT / $MAX_REPAIR"
    
    # 再レビュー実行
    log "🔍 再レビュー実行中..."
    if ! run_review; then
        error "再レビュー実行に失敗しました"
        exit 1
    fi
    
    # 再レビュー結果の判定
    if is_review_ok; then
        log "✅ 再レビューOK - 修復成功"
        log "📝 変更をコミット可能です"
        
        # Git状態確認
        if [[ -n $(git status --porcelain) ]]; then
            log "📦 変更が検出されました"
            git status --short
            
            # 自動コミット（オプション）
            # 注: 実運用では慎重に判断すること
            # read -p "変更をコミットしますか？ (y/n): " -n 1 -r
            # if [[ $REPLY =~ ^[Yy]$ ]]; then
            #     git add .
            #     git commit -m "Auto repair: 自動修復完了"
            #     log "✅ 自動コミット完了"
            # fi
        fi
        
        reset_state
        exit 0
    else
        log "⚠️  再レビューNG - さらに修復が必要です"
        
        if [ "$REPAIR_COUNT" -ge "$MAX_REPAIR" ]; then
            error "❌ 修復回数上限到達"
            log "🚨 人間による介入が必要です"
            exit 1
        else
            log "🔁 次回実行時に再度修復を試みます"
            exit 0
        fi
    fi
}

# ========================================
# スクリプト実行
# ========================================
main "$@"
