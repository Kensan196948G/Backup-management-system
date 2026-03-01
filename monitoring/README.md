# Monitoring System Setup Guide

3-2-1-1-0 Backup Management System の監視基盤セットアップガイド。

## Prerequisites

- Python 3.11+ (アプリケーション)
- Prometheus (メトリクス収集)
- Grafana (ダッシュボード)

## Application Configuration

アプリケーション側で Prometheus メトリクスを有効化する:

```bash
# 環境変数で有効化
export PROMETHEUS_ENABLED=true

# または config.py で直接設定
# PROMETHEUS_ENABLED = True
```

有効化後、`/metrics` エンドポイントで Prometheus 形式のメトリクスが公開される。

## Prometheus Setup (Docker不使用)

### 1. インストール

```bash
# Linux (amd64)
wget https://github.com/prometheus/prometheus/releases/download/v2.51.0/prometheus-2.51.0.linux-amd64.tar.gz
tar xvfz prometheus-2.51.0.linux-amd64.tar.gz
cd prometheus-2.51.0.linux-amd64

# macOS
brew install prometheus
```

### 2. 設定

```bash
# 設定ファイルとアラートルールをコピー
cp monitoring/prometheus/prometheus.yml ./prometheus.yml
cp monitoring/prometheus/alert_rules.yml ./alert_rules.yml
```

### 3. 起動

```bash
./prometheus --config.file=prometheus.yml --web.listen-address=:9090
```

### 4. 確認

ブラウザで `http://localhost:9090` にアクセスし、Targets ページで `backup-management-system` が `UP` 状態であることを確認。

## Grafana Setup (Docker不使用)

### 1. インストール

```bash
# Linux (Debian/Ubuntu)
sudo apt-get install -y adduser libfontconfig1 musl
wget https://dl.grafana.com/oss/release/grafana_10.4.0_amd64.deb
sudo dpkg -i grafana_10.4.0_amd64.deb

# macOS
brew install grafana
```

### 2. データソース設定

```bash
# Provisioning ディレクトリにコピー
sudo cp monitoring/grafana/datasource.yml /etc/grafana/provisioning/datasources/
```

### 3. 起動

```bash
# Linux (systemd)
sudo systemctl start grafana-server

# macOS
brew services start grafana
```

### 4. ダッシュボードインポート

1. ブラウザで `http://localhost:3000` にアクセス (初期: admin/admin)
2. Dashboards > Import を選択
3. `monitoring/grafana/dashboard.json` をアップロード
4. Prometheus データソースを選択して Import

## Available Metrics

### Business Metrics
| Metric | Type | Description |
|--------|------|-------------|
| `backup_jobs_total` | Gauge | バックアップジョブ総数 (status: active/inactive) |
| `backup_executions_total` | Counter | バックアップ実行総数 (result: success/failed/warning) |
| `backup_execution_duration_seconds` | Histogram | バックアップ実行時間 |
| `backup_success_rate` | Gauge | バックアップ成功率 (period: daily/weekly/monthly) |
| `backup_size_bytes` | Histogram | バックアップサイズ |

### Compliance Metrics
| Metric | Type | Description |
|--------|------|-------------|
| `compliance_status` | Gauge | コンプライアンス状態 (1=準拠, 0=非準拠) |
| `compliance_rate` | Gauge | 全体コンプライアンス率 |

### Alert Metrics
| Metric | Type | Description |
|--------|------|-------------|
| `alerts_total` | Counter | アラート生成総数 |
| `alerts_unacknowledged` | Gauge | 未確認アラート数 |

### Verification Metrics
| Metric | Type | Description |
|--------|------|-------------|
| `verification_tests_total` | Counter | 検証テスト実行総数 |
| `verification_duration_seconds` | Histogram | 検証テスト実行時間 |

### System Metrics
| Metric | Type | Description |
|--------|------|-------------|
| `db_query_duration_seconds` | Histogram | DBクエリ実行時間 |
| `cache_hits_total` | Counter | キャッシュヒット数 |
| `cache_misses_total` | Counter | キャッシュミス数 |

## Alert Rules

| Alert | Condition | Severity |
|-------|-----------|----------|
| BackupJobFailureRateHigh | 失敗率 > 20% (1h) | critical |
| ComplianceViolationDetected | コンプライアンス率 < 100% | warning |
| NoBackupJobsRunning | アクティブジョブゼロ (24h) | warning |
| HighUnacknowledgedAlerts | 未確認アラート >= 10件 | warning |
| BackupExecutionSlow | p95実行時間 > 1時間 | warning |
| VerificationTestFailureRateHigh | 検証失敗率 > 30% | critical |
