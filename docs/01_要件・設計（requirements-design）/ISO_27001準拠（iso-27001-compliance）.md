# ISO 27001 コンプライアンス要件

## A.12.3 情報のバックアップ

### データ分類別バックアップ要件

| 分類 | 最小コピー数 | 暗号化 | オフサイト | オフライン | 保持期間 |
|------|-------------|--------|-----------|-----------|---------|
| **RESTRICTED** | 3 | AES-256必須 | 必須 | 必須 | 7年 |
| **CONFIDENTIAL** | 3 | AES-256必須 | 必須 | 推奨 | 5年 |
| **INTERNAL** | 2 | AES-256推奨 | 推奨 | 不要 | 3年 |
| **PUBLIC** | 1 | 不要 | 不要 | 不要 | 1年 |

### 3-2-1-1-0 ルール実装

**3**: 最低3つのコピー
**2**: 2つの異なるメディアタイプ
**1**: 1つはオフサイト保管
**1**: 1つはオフライン/イミュータブル
**0**: 検証エラーゼロ

```python
def validate_32110_rule(backup_job):
    """3-2-1-1-0ルールの検証"""
    copies = count_backup_copies(backup_job.id)
    media_types = get_unique_media_types(backup_job.id)
    offsite = count_offsite_copies(backup_job.id)
    offline = count_offline_copies(backup_job.id)
    errors = count_verification_errors(backup_job.id)

    return {
        'compliant': copies >= 3 and len(media_types) >= 2
                     and offsite >= 1 and offline >= 1 and errors == 0
    }
```

## A.12.4 ログ取得及び監視

### 監査ログ必須フィールド

- timestamp: 操作時刻 (ISO 8601)
- event_type: イベントタイプ
- user_id: 実行者
- resource_id: リソースID
- action: アクション (create/read/update/delete)
- result: 結果 (success/failure)
- source_ip: 送信元IPアドレス
- data_classification: データ分類
- details: 詳細情報 (JSON)

```python
class AuditLog(db.Model):
    timestamp = db.Column(db.DateTime, nullable=False, index=True)
    event_type = db.Column(db.String(50), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    resource_type = db.Column(db.String(50), nullable=False)
    resource_id = db.Column(db.String(100), nullable=False)
    action = db.Column(db.String(50), nullable=False)
    result = db.Column(db.String(20), nullable=False)
    source_ip = db.Column(db.String(45))
    data_classification = db.Column(db.String(20))
    details = db.Column(db.JSON)
```

## A.9 アクセス制御

### ロール定義

| ロール | バックアップ実行 | 削除 | リストア | 暗号鍵管理 | 監査ログ |
|--------|----------------|------|---------|-----------|---------|
| backup_operator | ✅ | ❌ | ❌ | ❌ | ❌ |
| backup_admin | ✅ | ✅ | ✅ | ❌ | ✅ |
| security_admin | ❌ | ❌ | ❌ | ✅ | ✅ |
| auditor | ❌ | ❌ | ❌ | ❌ | ✅ |

```python
@require_permission('can_delete_backups')
def delete_backup(backup_id):
    """バックアップ削除 (backup_admin権限必要)"""
    backup = Backup.query.get_or_404(backup_id)

    AuditService.log_event(
        'backup.delete',
        'backup',
        backup_id,
        'delete',
        before_value={'size': backup.size}
    )

    db.session.delete(backup)
    db.session.commit()
```

## 監査チェックリスト

### A.12.3 バックアップ
- [ ] バックアップポリシー文書化済み
- [ ] データ分類別要件定義済み
- [ ] 3-2-1-1-0ルール準拠
- [ ] 暗号化実装済み
- [ ] オフサイト保管実施中
- [ ] 定期検証テスト実施中

### A.12.4 ログ
- [ ] 監査ログポリシー文書化済み
- [ ] 全重要イベント記録中
- [ ] ログ改ざん防止機能あり
- [ ] 定期レビュー実施中

### A.9 アクセス制御
- [ ] RBAC実装済み
- [ ] 職務分離適用済み
- [ ] 最小権限適用済み
- [ ] MFA実装済み
