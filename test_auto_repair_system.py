#!/usr/bin/env python3
"""
Claude Code 自動修復ループシステムのテストスクリプト

このスクリプトは以下をテストします：
1. 必須ファイルの存在確認
2. JSONファイルの構文チェック
3. Bashスクリプトの構文チェック
4. state.jsonのスキーマバリデーション
"""

import os
import sys
import json
import subprocess
from pathlib import Path

# カラー出力
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
RESET = '\033[0m'

def print_success(msg):
    print(f"{GREEN}✅ {msg}{RESET}")

def print_error(msg):
    print(f"{RED}❌ {msg}{RESET}")

def print_info(msg):
    print(f"{YELLOW}ℹ️  {msg}{RESET}")

def check_file_exists(filepath):
    """ファイルの存在確認"""
    if Path(filepath).exists():
        print_success(f"{filepath} が存在します")
        return True
    else:
        print_error(f"{filepath} が見つかりません")
        return False

def check_json_valid(filepath):
    """JSONファイルの構文チェック"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            json.load(f)
        print_success(f"{filepath} は有効なJSONです")
        return True
    except json.JSONDecodeError as e:
        print_error(f"{filepath} のJSON構文エラー: {e}")
        return False
    except Exception as e:
        print_error(f"{filepath} の読み込みエラー: {e}")
        return False

def check_bash_syntax(filepath):
    """Bashスクリプトの構文チェック"""
    try:
        result = subprocess.run(
            ['bash', '-n', filepath],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print_success(f"{filepath} の構文は正しいです")
            return True
        else:
            print_error(f"{filepath} の構文エラー:\n{result.stderr}")
            return False
    except Exception as e:
        print_error(f"{filepath} のチェックエラー: {e}")
        return False

def check_executable(filepath):
    """実行権限の確認"""
    if os.access(filepath, os.X_OK):
        print_success(f"{filepath} は実行可能です")
        return True
    else:
        print_error(f"{filepath} に実行権限がありません")
        return False

def main():
    print("\n" + "="*60)
    print("Claude Code 自動修復ループシステム - テスト")
    print("="*60 + "\n")
    
    all_passed = True
    
    # 必須ファイルのチェック
    print("【1】必須ファイルの存在確認\n")
    
    required_files = [
        'CLAUDE.md',
        '.claude/commands/review-all.md',
        '.claude/commands/auto-fix.md',
        '.claude/settings.json',
        'scripts/local-auto-repair.sh',
        'state.json',
        'state.json.schema',
        '.github/workflows/claude-auto-repair-loop.yml',
        'docs/13_開発環境（development-environment）/claude-auto-repair-v3.md',
    ]
    
    for file in required_files:
        if not check_file_exists(file):
            all_passed = False
    
    print()
    
    # JSONファイルの構文チェック
    print("【2】JSONファイルの構文チェック\n")
    
    json_files = [
        '.claude/settings.json',
        'state.json',
        'state.json.schema',
    ]
    
    for file in json_files:
        if Path(file).exists():
            if not check_json_valid(file):
                all_passed = False
    
    print()
    
    # Bashスクリプトの構文チェック
    print("【3】Bashスクリプトの構文チェック\n")
    
    if Path('scripts/local-auto-repair.sh').exists():
        if not check_bash_syntax('scripts/local-auto-repair.sh'):
            all_passed = False
        if not check_executable('scripts/local-auto-repair.sh'):
            all_passed = False
    
    print()
    
    # state.jsonのスキーマチェック
    print("【4】state.jsonのスキーマバリデーション\n")
    
    try:
        with open('state.json', 'r') as f:
            state_data = json.load(f)
        
        required_keys = ['repair_count', 'last_hash', 'last_error']
        missing_keys = [key for key in required_keys if key not in state_data]
        
        if missing_keys:
            print_error(f"state.json に必須キーが不足: {missing_keys}")
            all_passed = False
        else:
            print_success("state.json のスキーマは正しいです")
    except Exception as e:
        print_error(f"state.json のバリデーションエラー: {e}")
        all_passed = False
    
    print()
    
    # 依存コマンドのチェック
    print("【5】依存コマンドの確認\n")
    
    required_commands = ['jq', 'git', 'bash']
    
    for cmd in required_commands:
        try:
            result = subprocess.run(
                ['which', cmd],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                print_success(f"{cmd} がインストールされています")
            else:
                print_error(f"{cmd} が見つかりません")
                all_passed = False
        except Exception as e:
            print_error(f"{cmd} のチェックエラー: {e}")
            all_passed = False
    
    print()
    
    # 最終結果
    print("="*60)
    if all_passed:
        print_success("\n🎉 すべてのテストに合格しました！")
        print_info("\nシステムは正常に動作する準備ができています。")
        print()
        return 0
    else:
        print_error("\n⚠️  いくつかのテストに失敗しました。")
        print_info("\n上記のエラーを修正してから再度実行してください。")
        print()
        return 1

if __name__ == '__main__':
    sys.exit(main())
