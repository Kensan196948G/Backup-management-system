# Commit & PR作成 & 自動マージコマンド

以下の手順で、変更をコミット→プッシュ→PR作成→自動マージまで一括実行してください：

## ⚙️ 実行フロー

1. ✅ Git状態確認
2. ✅ セキュリティチェック（機密情報検出）
3. ✅ 変更をステージング
4. ✅ コミット作成（適切なメッセージ生成）
5. ✅ リモートにプッシュ
6. ✅ プルリクエスト作成
7. ✅ CI/CDチェック待機
8. ✅ ブランチ保護ルール一時無効化
9. ✅ PRを自動マージ
10. ✅ ブランチ保護ルール再有効化
11. ✅ 結果レポート表示

---

## 📝 ステップ1: Git状態の確認

以下を並列実行してください：
- `git status` - 変更ファイル一覧
- `git diff --stat` - 変更統計
- `git branch --show-current` - 現在のブランチ名
- `git log origin/main..HEAD --oneline` - mainブランチからの差分コミット

---

## 🔒 ステップ2: セキュリティチェック

以下のパターンをチェックして、機密情報が含まれていないか確認：
- APIキー（`ghp_`, `BSA`, `sk-`等）
- パスワード（`password=`, `PASSWORD=`）
- トークン（`token=`, `TOKEN=`）
- シークレット（`secret=`, `SECRET=`）

**見つかった場合**: コミットを中止し、ユーザーに警告してください

---

## ✅ ステップ3: 変更のステージングとコミット

1. **すべての変更をステージング**:
   ```bash
   git add .
   ```

2. **コミットメッセージを生成**:
   - 変更内容を分析
   - 以下の形式で作成：
   ```
   [種類] 簡潔な変更内容（50文字以内）

   主な変更内容:
   - 詳細な変更1
   - 詳細な変更2
   - 詳細な変更3

   技術詳細:
   - 使用技術・ライブラリ
   - 変更理由・目的

   影響範囲:
   - 変更ファイル数: X files
   - 追加行数: +X lines
   - 削除行数: -X lines

   🤖 Generated with [Claude Code](https://claude.com/claude-code)

   Co-Authored-By: Claude <noreply@anthropic.com>
   ```

   **コミット種類の選択**:
   - `feat`: 新機能追加
   - `fix`: バグ修正
   - `docs`: ドキュメントのみの変更
   - `style`: コードフォーマット（機能に影響なし）
   - `refactor`: リファクタリング
   - `perf`: パフォーマンス改善
   - `test`: テスト追加・修正
   - `build`: ビルドシステム・依存関係の変更
   - `ci`: CI/CD設定の変更
   - `chore`: その他の変更

3. **コミット実行**:
   ```bash
   git commit -m "$(cat <<'EOF'
   [生成されたコミットメッセージ]
   EOF
   )"
   ```

---

## 🚀 ステップ4: リモートへのプッシュ

現在のブランチをリモートにプッシュしてください：

```bash
git push origin [current-branch]
```

**pre-push hook**が自動実行されます（テストチェック）

---

## 📋 ステップ5: プルリクエストの作成

1. **mainブランチからの差分を確認**:
   ```bash
   git log origin/main..HEAD --oneline
   git diff origin/main..HEAD --stat
   ```

2. **PRタイトルとボディを生成**:

   **タイトル**: 最新コミットのタイトルを使用、または複数コミットの場合は総括タイトル

   **ボディ**:
   ```markdown
   ## 📋 概要
   [変更の総括を3-5項目で箇条書き]

   ## ✨ 主な変更内容
   [カテゴリー別の詳細な変更点]

   ## 📊 変更統計
   - ファイル数: X files
   - 追加行数: +X lines
   - 削除行数: -X lines

   ## 🧪 テスト
   - [x] ローカルでテスト済み
   - [x] ビルドが成功
   - [x] 既存機能に影響なし
   - [ ] レビュー完了

   ## ✅ チェックリスト
   - [x] コード品質チェック（flake8/black/isort）
   - [x] セキュリティチェック（機密情報除外）
   - [x] ドキュメント更新
   - [ ] テストコード追加

   ## 📚 関連ドキュメント
   [関連するドキュメントファイルへのリンク]

   🤖 Generated with [Claude Code](https://claude.com/claude-code)
   ```

3. **PR作成**:
   ```bash
   gh pr create --base main --head [current-branch] --title "[タイトル]" --body "[ボディ]"
   ```

4. **PR URLを取得・表示**

---

## ⏳ ステップ6: CI/CDチェック待機

PRが作成されると、GitHub Actionsが自動実行されます。

1. **CI/CDの状態を監視**:
   ```bash
   gh pr checks [PR番号]
   ```

2. **完了を待機**（最大5分）:
   - Lint Code
   - Run Tests
   - Security Scan
   - Build Application

3. **失敗した場合**:
   - ログを確認: `gh run view [run-id] --log-failed`
   - エラーを修正
   - 再度プッシュ（PRは自動更新される）

---

## 🔓 ステップ7: ブランチ保護ルール一時無効化

PRをマージするために、リポジトリルールセットを一時的に無効化します：

1. **ルールセットID取得**:
   ```bash
   gh api repos/Kensan196948G/backup-management-system/rulesets --jq '.[0].id'
   ```

2. **一時的に無効化**:
   ```bash
   gh api -X PUT repos/Kensan196948G/backup-management-system/rulesets/[ruleset-id] -f enforcement=disabled
   ```

---

## ✅ ステップ8: PRマージ

CI/CDが成功したらPRをマージします：

```bash
gh pr merge [PR番号] --merge
```

**マージ方法**:
- `--merge`: 通常のマージコミット（推奨）
- `--squash`: スカッシュマージ
- `--rebase`: リベースマージ

---

## 🔒 ステップ9: ブランチ保護ルール再有効化

マージ完了後、セキュリティのためにルールセットを再度有効化します：

```bash
gh api -X PUT repos/Kensan196948G/backup-management-system/rulesets/[ruleset-id] -f enforcement=active
```

---

## 📊 ステップ10: 結果レポート

最終的な結果を表示してください：

1. **マージ情報**:
   ```bash
   gh pr view [PR番号] --json state,mergedAt,mergedBy,url
   ```

2. **mainブランチの最新コミット**:
   ```bash
   git fetch origin main
   git log origin/main --oneline -3
   ```

3. **サマリー表示**:
   ```markdown
   ## 🎉 コミット&PR&マージ完了

   ✅ コミット: [コミットハッシュ] - [メッセージ]
   ✅ プッシュ: origin/[ブランチ名]
   ✅ PR作成: #[PR番号]
   ✅ CI/CD: 全チェック成功
   ✅ マージ: mainブランチに反映完了
   ✅ ルール: ブランチ保護再有効化

   リポジトリURL: https://github.com/Kensan196948G/backup-management-system
   PR URL: [PR URL]
   ```

---

## ⚠️ エラーハンドリング

### セキュリティチェック失敗
- 機密情報が見つかった場合、コミットを中止
- ユーザーに該当ファイルと行番号を通知

### CI/CD失敗
- 失敗したジョブのログを表示
- 修正方法を提案
- 再実行を提案

### マージ失敗
- コンフリクトがある場合、解決方法を提示
- ルールセット無効化の確認

### ルールセット操作失敗
- 権限エラーの場合、手動での対応を依頼
- 代替手段を提示

---

## 🔧 重要な注意事項

1. **ブランチ保護ルールの扱い**:
   - 一時無効化は最小限の時間のみ
   - マージ後は必ず再有効化
   - 失敗時の自動復旧処理を含める

2. **CI/CD待機**:
   - タイムアウト: 最大5分
   - ステータスチェックの完了を確認してからマージ

3. **機密情報保護**:
   - コミット前に必ずチェック
   - 検出パターンの定期更新

4. **エラー時の対応**:
   - 詳細なエラーメッセージを表示
   - 次のアクションを明確に提示
   - ロールバック手順を用意

---

## 📖 使用例

ユーザーが `/commit-and-pr` と入力した場合：

1. 自動的に全ステップを実行
2. 各ステップの進捗を表示
3. エラーがあれば即座に報告・対処
4. 最終的にmainブランチへのマージまで完了
5. 結果サマリーを表示

---

**このコマンドは、開発者の手間を最小限にし、安全かつ確実にコード変更をmainブランチに反映します。**
