# ISO 19650 コンプライアンス要件

## 情報コンテナステータス

| ステータス | 説明 | バックアップ頻度 | 保持期間 |
|-----------|------|----------------|---------|
| **WIP** | 作業中 | 日次 | 30日 |
| **SHARED** | 共有済み | 日次 | 90日 |
| **PUBLISHED** | 発行済み | 即時 | 10年+ |
| **ARCHIVED** | アーカイブ | 月次 | 永久 |

## プロジェクトステージ別要件

| ステージ | 説明 | 頻度 | 保管年数 | LOD | イミュータブル |
|---------|------|------|---------|-----|-----------|
| **Stage 0** | 戦略的定義 | 週次 | 7 | 100 | 不要 |
| **Stage 1** | 準備 | 週次 | 7 | 100 | 不要 |
| **Stage 2** | コンセプト設計 | 日次 | 10 | 200 | 不要 |
| **Stage 3** | 空間調整 | 日次 | 10 | 300 | 不要 |
| **Stage 4** | 技術設計 | 日次 | 15 | 350 | 必須 |
| **Stage 5** | 製造・施工 | 日2回 | 15 | 400 | 必須 |
| **Stage 6** | 引渡し | 日次 | 15 | 500 | 必須 |
| **Stage 7** | 使用・運用 | 週次 | 30 | 500 | 必須 |

## ファイル命名規則

### 形式
```
PROJECT-ORIG-VOL-LEVEL-TYPE-ROLE-CLASS-NUMBER-STATUS-REVISION.EXT

例: ABC123-ARC-01-00-M3-DR-A-1001-S-P01.rvt
```

### 要素定義

- **PROJECT**: プロジェクトコード (6桁)
- **ORIG**: 作成組織 (ARC, STR, MEP等)
- **VOL**: ボリューム/建物 (01-99, ZZ=全体)
- **LEVEL**: 階層 (00=全体, 01-99=階)
- **TYPE**: タイプ (M3=モデル, DR=図面)
- **ROLE**: 役割 (DR, MD, SP)
- **CLASS**: 分類 (A=建築, S=構造, M=機械)
- **NUMBER**: 番号 (1001-9999)
- **STATUS**: ステータス (W/S/P/A)
- **REVISION**: リビジョン (P01, C01)

## ISO 19650-5 セキュリティレベル

| レベル | 名称 | 暗号化 | アクセス制御 | 監査 |
|--------|------|--------|------------|------|
| **PL0** | Public | 不要 | 不要 | 不要 |
| **PL1** | Stakeholder | 不要 | 必須 | 必須 |
| **PL2** | Commercial | AES-256 | 必須 | 必須 |
| **PL3** | Personal Data | AES-256 | MFA必須 | 必須 |
| **PL4** | Secret | AES-256+HSM | MFA必須 | 必須 |
| **PL5** | Top Secret | AES-256+HSM | 生体認証 | 必須 |

## CDE構造

```
CDE/
├── WIP/              # 作業中
│   ├── Architecture/
│   ├── Structure/
│   └── MEP/
├── Shared/           # 共有
│   ├── Architecture/
│   ├── Structure/
│   └── MEP/
├── Published/        # 発行済
│   ├── Stage_0/
│   ├── Stage_1/
│   └── ...
└── Archive/          # アーカイブ
    └── Historical/
```

## 実装例

```python
# 情報コンテナモデル
class InformationContainer(db.Model):
    container_code = db.Column(db.String(100), unique=True)
    status = db.Column(db.String(20))  # WIP, SHARED, PUBLISHED, ARCHIVED
    project_stage = db.Column(db.String(50))
    security_classification = db.Column(db.String(20))  # PL0-PL5

    def generate_filename(self):
        """ISO 19650準拠のファイル名生成"""
        return f"{self.project_code}-{self.originator}-{self.volume}-" \
               f"{self.level}-{self.type_code}-{self.role}-" \
               f"{self.classification}-{self.number}-" \
               f"{self.status[0]}-{self.revision}.{self.file_format}"
```
