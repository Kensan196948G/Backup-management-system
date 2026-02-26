const state = {
  currentView: "dashboard",
  role: "operator",
  apiExampleIndex: 0,
  selectedJobId: 1,
  selectedReportId: 501,
  loginVisible: false,
  dashboard: {
    summary: {
      jobs: { total: 50, active: 48, inactive: 2 },
      compliance: { compliant: 45, non_compliant: 3, warning: 2 },
      executions_24h: { total: 120, success: 115, failed: 3, warning: 2 },
      alerts: { critical: 2, error: 5, warning: 10, total_unacknowledged: 17 },
      media: { total: 34, stored: 23, borrowed: 3, due_rotation: 4 }
    },
    successTrend: [96, 95, 97, 94, 98, 96, 97],
    failedTrend: [2, 3, 1, 4, 2, 3, 2],
    storageUsage: [
      { label: "オンサイト", used: 72, total: 100 },
      { label: "オフサイト", used: 58, total: 100 },
      { label: "オフライン", used: 43, total: 100 }
    ]
  },
  jobs: [
    {
      id: 1, job_name: "Daily SQL Server Backup", job_type: "database",
      target_server: "SQL-SERVER-01", target_path: "C:\\SQLBackup", backup_tool: "veeam",
      schedule_type: "daily", run_time: "02:00", retention_days: 30, owner: "operator01",
      description: "本番DB日次バックアップ", status: "active", compliance: "compliant",
      complianceChecks: { copies: true, mediaTypes: true, offsite: true, offline: true, zeroError: true },
      copies: [
        { type: "primary", media: "disk", path: "\\\\nas01\\backup", encrypted: true, compressed: true, lastUpdate: "2026-02-24 02:13" },
        { type: "offsite", media: "cloud", path: "s3://corp-backup/sql", encrypted: true, compressed: true, lastUpdate: "2026-02-24 02:30" },
        { type: "offline", media: "tape", path: "Vault-A/LTO-024", encrypted: false, compressed: false, lastUpdate: "2026-02-23 18:00" }
      ],
      executionHistory: [{ time: "2026-02-24 02:13", result: "success", size: "512 GB", duration: "21m", source: "veeam" }],
      verificationHistory: [{ date: "2026-02-10", type: "full_restore", result: "success", by: "operator02" }]
    },
    {
      id: 2, job_name: "Weekly File Server Backup", job_type: "file",
      target_server: "FS-01", target_path: "D:\\Shares", backup_tool: "aomei",
      schedule_type: "weekly", run_time: "03:00", retention_days: 60, owner: "operator02",
      description: "ファイルサーバー週次バックアップ", status: "active", compliance: "warning",
      complianceChecks: { copies: true, mediaTypes: true, offsite: true, offline: false, zeroError: true },
      copies: [
        { type: "primary", media: "disk", path: "D:\\Backups\\FS01", encrypted: true, compressed: true, lastUpdate: "2026-02-23 03:58" },
        { type: "offsite", media: "cloud", path: "azure://archive/fs01", encrypted: true, compressed: true, lastUpdate: "2026-02-23 05:10" }
      ],
      executionHistory: [{ time: "2026-02-23 03:58", result: "warning", size: "1.2 TB", duration: "43m", source: "aomei_powershell" }],
      verificationHistory: [{ date: "2025-12-01", type: "partial_restore", result: "success", by: "operator02" }]
    },
    {
      id: 3, job_name: "Monthly VM Snapshot Export", job_type: "vm",
      target_server: "VCenter-01", target_path: "N/A", backup_tool: "custom",
      schedule_type: "monthly", run_time: "01:30", retention_days: 180, owner: "admin01",
      description: "VMエクスポートとオフサイト保存", status: "inactive", compliance: "non_compliant",
      complianceChecks: { copies: false, mediaTypes: false, offsite: true, offline: false, zeroError: false },
      copies: [{ type: "primary", media: "disk", path: "\\\\hvrepo\\exports", encrypted: false, compressed: true, lastUpdate: "2026-01-31 04:00" }],
      executionHistory: [{ time: "2026-01-31 04:00", result: "failed", size: "0 GB", duration: "18m", source: "custom" }],
      verificationHistory: []
    }
  ],
  alerts: [
    { id: 101, severity: "critical", type: "BACKUP_FAILURE", jobId: 3, jobName: "Monthly VM Snapshot Export", createdAt: "2026/02/24 07:40", message: "Export failed: datastore full", acknowledged: false },
    { id: 102, severity: "error", type: "RULE_VIOLATION", jobId: 3, jobName: "Monthly VM Snapshot Export", createdAt: "2026/02/24 07:42", message: "3-2-1-1-0 rule not satisfied", acknowledged: false },
    { id: 103, severity: "warning", type: "OFFLINE_MEDIA_UPDATE_WARNING", jobId: 2, jobName: "Weekly File Server Backup", createdAt: "2026/02/23 12:10", message: "Offline media missing for last 7 days", acknowledged: false },
    { id: 104, severity: "warning", type: "VERIFICATION_REMINDER", jobId: 2, jobName: "Weekly File Server Backup", createdAt: "2026/02/22 09:00", message: "Quarterly restore test due", acknowledged: false },
    { id: 105, severity: "info", type: "DAILY_REPORT_READY", jobId: 1, jobName: "Daily SQL Server Backup", createdAt: "2026/02/24 08:00", message: "Daily report generated", acknowledged: true }
  ],
  upcomingJobs: [
    { id: 1, jobName: "Daily SQL Server Backup", jobType: "database", nextRun: "2026/02/25 02:00", owner: "operator01", status: "active" },
    { id: 2, jobName: "Weekly File Server Backup", jobType: "file", nextRun: "2026/03/01 03:00", owner: "operator02", status: "active" },
    { id: 6, jobName: "AOMEI Workstation Backup", jobType: "system_image", nextRun: "2026/02/25 01:00", owner: "operator03", status: "active" }
  ],
  executions: [
    { at: "2026/02/24 07:38", job: "Monthly VM Snapshot Export", result: "failed", size: "0 GB", duration: "18m", source: "custom" },
    { at: "2026/02/24 03:58", job: "Weekly File Server Backup", result: "warning", size: "1.2 TB", duration: "43m", source: "aomei_powershell" },
    { at: "2026/02/24 02:13", job: "Daily SQL Server Backup", result: "success", size: "512 GB", duration: "21m", source: "veeam" },
    { at: "2026/02/24 01:18", job: "Log Archive Backup", result: "success", size: "88 GB", duration: "8m", source: "powershell" }
  ],
  media: [
    { id: 1, media_id: "LTO-024", media_type: "tape", capacity_gb: 12288, storage_location: "本社ビル-1F-R1", current_status: "stored", updated_at: "2026-02-23", label_name: "営業部バックアップ用" },
    { id: 2, media_id: "HDD-OFF-008", media_type: "external_hdd", capacity_gb: 4096, storage_location: "別拠点-2F-R2", current_status: "borrowed", updated_at: "2026-02-20", label_name: "復旧テスト用" },
    { id: 3, media_id: "S3-ARCHIVE", media_type: "cloud", capacity_gb: 20480, storage_location: "AWS-ap-northeast-1", current_status: "stored", updated_at: "2026-02-24", label_name: "S3 Glacier" }
  ],
  rotations: [
    { mediaId: "LTO-024", method: "GFS", nextDate: "2026-02-28", note: "月末ローテーション", overdue: false },
    { mediaId: "HDD-OFF-008", method: "Custom", nextDate: "2026-02-22", note: "返却後に別拠点へ移送", overdue: true }
  ],
  lendingHistory: [
    { mediaId: "HDD-OFF-008", event: "貸出", who: "監査担当", date: "2026-02-18", detail: "復旧テスト" },
    { mediaId: "LTO-022", event: "返却", who: "operator02", date: "2026-02-12", detail: "金庫へ返却" }
  ],
  verificationTests: [
    { id: 1, jobName: "Daily SQL Server Backup", type: "full_restore", result: "success", date: "2026-02-10", by: "operator02", durationSec: 1800 },
    { id: 2, jobName: "Weekly File Server Backup", type: "partial_restore", result: "failed", date: "2026-01-04", by: "operator03", durationSec: 2400 }
  ],
  verificationSchedules: [
    { id: 1, jobName: "Daily SQL Server Backup", frequency: "quarterly", nextDate: "2026-03-10", assignedTo: "operator02" },
    { id: 2, jobName: "Weekly File Server Backup", frequency: "quarterly", nextDate: "2026-02-20", assignedTo: "operator03" },
    { id: 3, jobName: "Monthly VM Snapshot Export", frequency: "monthly", nextDate: "2026-02-15", assignedTo: "admin01" }
  ],
  verificationIssues: [
    { id: "VER-0008", jobName: "Weekly File Server Backup", severity: "high", status: "対応中", detail: "容量不足で部分復元失敗", sla: "残り1日" },
    { id: "VER-0006", jobName: "Monthly VM Snapshot Export", severity: "critical", status: "未対応", detail: "最新イメージ復元不可", sla: "超過" }
  ],
  reports: [
    { id: 501, type: "compliance", from: "2026-02-01", to: "2026-02-24", format: "pdf", status: "completed", createdBy: "auditor01", fileName: "compliance_20260224.pdf" },
    { id: 502, type: "daily", from: "2026-02-23", to: "2026-02-23", format: "html", status: "completed", createdBy: "system", fileName: "daily_20260223.html" },
    { id: 503, type: "audit", from: "2026-01-01", to: "2026-01-31", format: "pdf", status: "completed", createdBy: "auditor01", fileName: "audit_202601.pdf" }
  ],
  notificationChannels: [
    { name: "Dashboard", health: "healthy", sent24h: 124, failed24h: 0, latencyMs: 18 },
    { name: "Email", health: "degraded", sent24h: 37, failed24h: 2, latencyMs: 680 },
    { name: "Teams", health: "healthy", sent24h: 15, failed24h: 0, latencyMs: 420 }
  ],
  notificationHistory: [
    { at: "2026/02/24 07:42", channels: ["Teams", "Email", "Dashboard"], severity: "critical", title: "VM Export Failure", result: "Teams=OK Email=Retry成功 Dashboard=OK" },
    { at: "2026/02/24 08:00", channels: ["Email", "Dashboard"], severity: "info", title: "Daily Report Ready", result: "送信完了" }
  ],
  performance: {
    metrics: [
      { label: "API p95", value: "150ms", meta: "Target < 200ms" },
      { label: "DB最適化", value: "65% faster", meta: "Target 50%" },
      { label: "Cache Hit Rate", value: "85%", meta: "Target > 80%" },
      { label: "Uptime", value: "99.95%", meta: "Target > 99.9%" }
    ],
    endpoints: [
      { endpoint: "GET /api/jobs", p50: "45ms", p95: "120ms", p99: "180ms", rps: 245, status: "Excellent" },
      { endpoint: "GET /api/jobs/{id}", p50: "35ms", p95: "95ms", p99: "145ms", rps: 312, status: "Excellent" },
      { endpoint: "POST /api/jobs", p50: "85ms", p95: "175ms", p99: "245ms", rps: 156, status: "Good" },
      { endpoint: "GET /api/alerts", p50: "42ms", p95: "115ms", p99: "165ms", rps: 267, status: "Excellent" },
      { endpoint: "GET /api/reports", p50: "125ms", p95: "285ms", p99: "395ms", rps: 98, status: "Acceptable" }
    ],
    errorStats: [
      { label: "総エラー数", value: "142", meta: "7日間集計" },
      { label: "一時的エラー", value: "37", meta: "Invoke-WithRetry 対象" },
      { label: "永続的エラー", value: "12", meta: "認証/入力/ファイル未検出" },
      { label: "API成功率改善", value: "80% → 95%+", meta: "エラーハンドリング強化" }
    ],
    errorContextExample: {
      timestamp: "2026-02-24T07:42:10.431+09:00",
      function_name: "Send-BackupStatus",
      error_message: "Connection timeout",
      error_type: "System.Net.WebException",
      script_stack_trace: "at Send-BackupStatus line 245",
      context: { job_id: 3, operation: "backup_status" },
      is_transient: true
    }
  },
  auditLogs: [
    { at: "2026/02/24 08:01", user: "operator01", action: "api_login", resource: "auth", ip: "10.0.1.15", result: "success", details: "JWT issued role=operator" },
    { at: "2026/02/24 07:43", user: "system", action: "alert_create", resource: "alert#101", ip: "localhost", result: "success", details: "BACKUP_FAILURE critical" },
    { at: "2026/02/24 07:42", user: "system", action: "notification_send", resource: "teams", ip: "localhost", result: "success", details: "AdaptiveCard alert#101" },
    { at: "2026/02/24 07:42", user: "system", action: "notification_send", resource: "email", ip: "localhost", result: "failed", details: "SMTP timeout retry=1" },
    { at: "2026/02/23 16:22", user: "auditor01", action: "report_generate", resource: "report#501", ip: "10.0.2.33", result: "success", details: "compliance pdf" }
  ],
  apiExamples: [
    { title: "GET /api/v1/dashboard/summary", body: { jobs: { total: 50, active: 48, inactive: 2 }, compliance: { compliant: 45, non_compliant: 3, warning: 2 }, executions_24h: { total: 120, success: 115, failed: 3, warning: 2 }, alerts: { critical: 2, error: 5, warning: 10, total_unacknowledged: 17 } } },
    { title: "POST /api/v1/jobs", body: { job_name: "Daily SQL Server Backup", job_type: "database", target_server: "SQL-SERVER-01", backup_tool: "veeam", schedule_type: "daily", retention_days: 30 } },
    { title: "POST /api/v1/aomei/status", body: { job_id: 123, status: "success", backup_size: 10737418240, duration: 3600, task_name: "System Backup Daily" } },
    { title: "POST /api/v1/reports/generate", body: { report_type: "compliance", date_from: "2026-02-01", date_to: "2026-02-24", file_format: "pdf", options: { include_charts: true, include_details: true } } }
  ]
};

const locationData = {
  "本社ビル": { floors: ["1F", "2F", "3F", "B1F"], racks: { "1F": ["R1", "R2", "R3", "R4"], "2F": ["R1", "R2", "R3", "R4"], "3F": ["R1", "R2", "R3", "R4"], "B1F": ["R1", "R2", "R3", "R4"] }, occupied: { "1F": ["R2", "R4"], "2F": ["R3"], "3F": [], "B1F": ["R1"] } },
  "別拠点": { floors: ["1F", "2F"], racks: { "1F": ["R1", "R2", "R3"], "2F": ["R1", "R2", "R3"] }, occupied: { "1F": ["R1"], "2F": ["R3"] } },
  "外部倉庫": { floors: ["Zone-A", "Zone-B"], racks: { "Zone-A": ["R1", "R2"], "Zone-B": ["R1", "R2"] }, occupied: { "Zone-A": ["R2"], "Zone-B": [] } }
};

const dom = {};

document.addEventListener("DOMContentLoaded", () => {
  cacheDom();
  bindBaseEvents();
  initDefaults();
  initLocationPicker();
  initMediaFormInteractive();
  renderAll();
  setInterval(() => { if (document.getElementById("liveMode").checked) simulateTick(true); }, 15000);
});

function cacheDom() {
  dom.navItems = [...document.querySelectorAll(".nav-item")];
  dom.views = [...document.querySelectorAll(".view")];
  dom.viewTitle = document.getElementById("viewTitle");
  dom.alertBadge = document.getElementById("alertBadge");
  dom.toastRegion = document.getElementById("toastRegion");
  dom.loginPanel = document.getElementById("loginPanel");
}

function bindBaseEvents() {
  dom.navItems.forEach((n) => n.addEventListener("click", () => setView(n.dataset.view, n.textContent)));
  document.getElementById("simulateTick").addEventListener("click", () => simulateTick(false));
  document.getElementById("alertBell").addEventListener("click", () => { setView("dashboard", "ダッシュボード"); toast("未確認アラートを表示", "ダッシュボード", "warning"); });
  document.getElementById("loginToggle").addEventListener("click", () => dom.loginPanel.classList.toggle("hidden"));
  document.getElementById("roleSelect").addEventListener("change", (e) => { state.role = e.target.value; applyRoleRestrictions(); toast(`ロール: ${state.role}`, "権限", "info"); });
  document.getElementById("loginForm").addEventListener("submit", onLogin);

  document.getElementById("bulkAckBtn").addEventListener("click", () => {
    state.alerts.forEach((a) => a.acknowledged = true);
    renderDashboard();
    renderNotifications();
    toast("未確認アラートを一括確認", "アラート", "success");
  });

  ["jobSearch", "jobTypeFilter", "jobStatusFilter", "jobComplianceFilter"].forEach((id) => document.getElementById(id).addEventListener("input", renderJobs));
  ["jobTypeFilter", "jobStatusFilter", "jobComplianceFilter"].forEach((id) => document.getElementById(id).addEventListener("change", renderJobs));
  document.getElementById("openJobFormBtn").addEventListener("click", () => openJobForm());
  document.getElementById("closeJobFormBtn").addEventListener("click", closeJobForm);
  document.getElementById("fillSampleJobBtn").addEventListener("click", fillSampleJob);
  document.getElementById("jobForm").addEventListener("submit", saveJob);
  document.getElementById("editJobBtn").addEventListener("click", () => openJobForm(state.selectedJobId));
  document.getElementById("toggleJobActiveBtn").addEventListener("click", toggleSelectedJobActive);
  document.getElementById("runComplianceCheckAll").addEventListener("click", recalcCompliance);
}

function initDefaults() {
  const now = new Date();
  const from = new Date(now);
  from.setDate(now.getDate() - 30);
  document.querySelector("#reportForm [name=date_to]").value = toDateInputValue(now);
  document.querySelector("#reportForm [name=date_from]").value = toDateInputValue(from);
  document.getElementById("label-preview-date").textContent = formatDate(now);
  updateCapacity();
  updateMediaPreview();
}

function setView(view, label) {
  state.currentView = view;
  dom.navItems.forEach((n) => n.classList.toggle("active", n.dataset.view === view));
  dom.views.forEach((v) => v.classList.toggle("active", v.id === `view-${view}`));
  if (label) dom.viewTitle.textContent = label;
}

function renderAll() {
  renderDashboard();
  renderJobs();
  renderMedia();
  renderVerification();
  renderReports();
  renderNotifications();
  renderMonitoring();
  renderAudit();
  renderApi();
  applyRoleRestrictions();
}

function renderDashboard() {
  const s = state.dashboard.summary;
  const unacked = state.alerts.filter((a) => !a.acknowledged).length;
  dom.alertBadge.textContent = String(unacked);
  s.alerts.total_unacknowledged = unacked;
  const compliancePct = Math.round((s.compliance.compliant / Math.max(1, s.jobs.total)) * 100);
  const successPct = Math.round((s.executions_24h.success / Math.max(1, s.executions_24h.total)) * 100);
  document.getElementById("dashboardMetrics").innerHTML = [
    card("3-2-1-1-0準拠率", `${compliancePct}%`, `準拠 ${s.compliance.compliant} / 警告 ${s.compliance.warning} / 非準拠 ${s.compliance.non_compliant}`),
    card("直近24h 成功率", `${successPct}%`, `成功 ${s.executions_24h.success} / 失敗 ${s.executions_24h.failed}`),
    card("未確認アラート", String(unacked), `critical ${countSeverity("critical")} / error ${countSeverity("error")} / warning ${countSeverity("warning")}`),
    card("オフラインメディア", String(s.media.total), `保管 ${s.media.stored} / 貸出 ${s.media.borrowed} / ローテ要対応 ${s.media.due_rotation}`)
  ].join("");

  drawDonut(document.getElementById("complianceDonut"), [
    { label: "compliant", value: s.compliance.compliant, color: "#6fe3a3" },
    { label: "warning", value: s.compliance.warning, color: "#ffd166" },
    { label: "non_compliant", value: s.compliance.non_compliant, color: "#ff6b6b" }
  ]);
  drawLine(document.getElementById("successLine"), state.dashboard.successTrend, state.dashboard.failedTrend);
  drawBars(document.getElementById("storageBars"), state.dashboard.storageUsage);

  document.querySelector("#alertsTable tbody").innerHTML = state.alerts.filter((a) => !a.acknowledged).map((a) => `
    <tr>
      <td>${sevChip(a.severity)}</td>
      <td>${esc(a.type)}</td>
      <td><button class="link-btn" data-job-open="${a.jobId}">${esc(a.jobName)}</button></td>
      <td>${esc(a.createdAt)}</td>
      <td><button class="btn btn-secondary btn-sm" data-ack="${a.id}">確認</button></td>
    </tr>`).join("") || `<tr><td colspan="5" class="muted">未確認アラートはありません</td></tr>`;
  document.querySelectorAll("[data-ack]").forEach((b) => b.addEventListener("click", () => {
    const item = state.alerts.find((a) => a.id === Number(b.dataset.ack));
    if (item) item.acknowledged = true;
    renderDashboard(); renderNotifications();
  }));
  bindJobOpenLinks();

  document.querySelector("#upcomingTable tbody").innerHTML = state.upcomingJobs.map((j) => `
    <tr><td>${esc(j.jobName)}</td><td>${esc(j.jobType)}</td><td>${esc(j.nextRun)}</td><td>${esc(j.owner)}</td><td>${statusChip(j.status)}</td></tr>`).join("");
  document.querySelector("#executionsTable tbody").innerHTML = state.executions.map((e) => `
    <tr><td>${esc(e.at)}</td><td>${esc(e.job)}</td><td>${resultChip(e.result)}</td><td>${esc(e.size)}</td><td>${esc(e.duration)}</td><td>${esc(e.source)}</td></tr>`).join("");
}

function renderJobs() {
  const search = document.getElementById("jobSearch").value.trim().toLowerCase();
  const type = document.getElementById("jobTypeFilter").value;
  const status = document.getElementById("jobStatusFilter").value;
  const comp = document.getElementById("jobComplianceFilter").value;
  const list = state.jobs.filter((j) => {
    if (search && !(`${j.job_name} ${j.target_server}`.toLowerCase().includes(search))) return false;
    if (type && j.job_type !== type) return false;
    if (status && j.status !== status) return false;
    if (comp && j.compliance !== comp) return false;
    return true;
  });
  document.getElementById("jobsCount").textContent = `${list.length}件 / 全${state.jobs.length}件`;
  document.querySelector("#jobsTable tbody").innerHTML = list.map((j) => `
    <tr data-job-row="${j.id}" class="${j.id === state.selectedJobId ? "selected" : ""}">
      <td>${esc(j.job_name)}</td><td>${esc(j.job_type)}</td><td>${esc(j.backup_tool)}</td>
      <td>${esc(j.schedule_type)} ${esc(j.run_time || "")}</td><td>${esc(j.owner)}</td>
      <td>${compChip(j.compliance)}</td><td>${statusChip(j.status)}</td>
    </tr>`).join("");
  document.querySelectorAll("[data-job-row]").forEach((row) => row.addEventListener("click", () => { state.selectedJobId = Number(row.dataset.jobRow); renderJobs(); }));
  renderJobDetail();
}

function renderJobDetail() {
  const j = state.jobs.find((x) => x.id === state.selectedJobId) || state.jobs[0];
  if (!j) return;
  state.selectedJobId = j.id;
  const alerts = state.alerts.filter((a) => a.jobId === j.id);
  const checks = [
    ["コピー数3つ以上", j.complianceChecks.copies], ["メディア種別2種類以上", j.complianceChecks.mediaTypes],
    ["オフサイト1つ以上", j.complianceChecks.offsite], ["オフライン1つ以上", j.complianceChecks.offline], ["検証エラー0", j.complianceChecks.zeroError]
  ];
  document.getElementById("jobDetailContent").innerHTML = `
    <section class="detail-card">
      <h4>基本情報</h4>
      <dl class="kv-grid">${kv("ID", j.id)}${kv("ジョブ名", j.job_name)}${kv("種別", j.job_type)}${kv("ツール", j.backup_tool)}${kv("対象サーバー", j.target_server)}${kv("対象パス", j.target_path)}${kv("スケジュール", `${j.schedule_type} ${j.run_time}`)}${kv("保持期間", `${j.retention_days}日`)}${kv("担当者", j.owner)}${kv("状態", j.status)}</dl>
      <p class="muted">${esc(j.description)}</p>
    </section>
    <section class="detail-card"><h4>3-2-1-1-0 準拠状況</h4><div class="stack-list">${checks.map(([k,v]) => `<div class="stack-item"><div class="title">${esc(k)}</div><div class="meta">${v ? "○ 達成" : "× 未達"}</div></div>`).join("")}</div></section>
    <section class="detail-card"><h4>バックアップコピー</h4><div class="table-wrap"><table class="data-table"><thead><tr><th>type</th><th>media</th><th>path</th><th>暗号化</th><th>圧縮</th><th>最終更新</th></tr></thead><tbody>${j.copies.map(c => `<tr><td>${c.type}</td><td>${c.media}</td><td>${esc(c.path)}</td><td>${c.encrypted ? "Yes":"No"}</td><td>${c.compressed ? "Yes":"No"}</td><td>${c.lastUpdate}</td></tr>`).join("")}</tbody></table></div></section>
    <section class="detail-card"><h4>関連イベント</h4><div class="stack-list">
      ${j.executionHistory.map(e => `<div class="stack-item"><div class="title">実行 ${e.time}</div><div class="meta">${e.result} / ${e.size} / ${e.duration} / ${e.source}</div></div>`).join("")}
      ${j.verificationHistory.map(v => `<div class="stack-item"><div class="title">検証 ${v.date}</div><div class="meta">${v.type} / ${v.result} / ${v.by}</div></div>`).join("") || `<div class="stack-item"><div class="meta">検証履歴なし</div></div>`}
      ${alerts.map(a => `<div class="stack-item"><div class="title">${a.type}</div><div class="meta">${a.createdAt} / ack=${a.acknowledged}</div></div>`).join("") || `<div class="stack-item"><div class="meta">関連アラートなし</div></div>`}
    </div></section>`;
}

function openJobForm(jobId) {
  const panel = document.getElementById("jobFormPanel");
  const form = document.getElementById("jobForm");
  panel.classList.remove("hidden");
  if (!jobId) {
    document.getElementById("jobFormTitle").textContent = "ジョブ作成";
    form.reset();
    form.querySelector("[name=run_time]").value = "02:00";
    form.querySelector("[name=retention_days]").value = "30";
    form.querySelector("[name=owner]").value = "operator01";
    delete form.dataset.editingId;
    return;
  }
  const j = state.jobs.find((x) => x.id === jobId);
  if (!j) return;
  document.getElementById("jobFormTitle").textContent = `ジョブ編集 #${j.id}`;
  form.dataset.editingId = String(j.id);
  form.querySelector("[name=job_name]").value = j.job_name;
  form.querySelector("[name=job_type]").value = j.job_type;
  form.querySelector("[name=target_server]").value = j.target_server;
  form.querySelector("[name=target_path]").value = j.target_path;
  form.querySelector("[name=backup_tool]").value = j.backup_tool;
  form.querySelector("[name=schedule_type]").value = j.schedule_type;
  form.querySelector("[name=run_time]").value = j.run_time;
  form.querySelector("[name=retention_days]").value = String(j.retention_days);
  form.querySelector("[name=owner]").value = j.owner;
  form.querySelector("[name=description]").value = j.description;
  form.querySelector("[name=is_active]").checked = j.status === "active";
}

function closeJobForm() { document.getElementById("jobFormPanel").classList.add("hidden"); }

function fillSampleJob() {
  const f = document.getElementById("jobForm");
  f.querySelector("[name=job_name]").value = "AOMEI Workstation Backup";
  f.querySelector("[name=job_type]").value = "system_image";
  f.querySelector("[name=target_server]").value = "WS-011";
  f.querySelector("[name=target_path]").value = "D:\\AOMEI\\System";
  f.querySelector("[name=backup_tool]").value = "aomei";
  f.querySelector("[name=schedule_type]").value = "daily";
  f.querySelector("[name=run_time]").value = "01:00";
  f.querySelector("[name=retention_days]").value = "14";
  f.querySelector("[name=owner]").value = "operator03";
  f.querySelector("[name=description]").value = "AOMEI連携テスト用ジョブ";
}

function saveJob(e) {
  e.preventDefault();
  const f = e.currentTarget;
  const fd = new FormData(f);
  const payload = {
    job_name: `${fd.get("job_name") || ""}`.trim(),
    job_type: `${fd.get("job_type")}`, target_server: `${fd.get("target_server") || ""}`.trim(),
    target_path: `${fd.get("target_path") || ""}`.trim(), backup_tool: `${fd.get("backup_tool")}`,
    schedule_type: `${fd.get("schedule_type")}`, run_time: `${fd.get("run_time") || ""}`,
    retention_days: Number(fd.get("retention_days") || 0), owner: `${fd.get("owner") || ""}`.trim(),
    description: `${fd.get("description") || ""}`.trim(), status: fd.get("is_active") ? "active" : "inactive"
  };
  if (!payload.job_name || !payload.target_server || payload.retention_days < 1) {
    toast("必須項目と保持期間を確認してください", "VALIDATION_ERROR", "danger");
    return;
  }
  if (f.dataset.editingId) {
    const j = state.jobs.find((x) => x.id === Number(f.dataset.editingId));
    if (j) Object.assign(j, payload);
    toast("ジョブを更新しました", "ジョブ", "success");
  } else {
    const id = Math.max(...state.jobs.map((j) => j.id), 0) + 1;
    state.jobs.unshift({ id, ...payload, compliance: "warning", complianceChecks: { copies: false, mediaTypes: false, offsite: false, offline: false, zeroError: true }, copies: [], executionHistory: [], verificationHistory: [] });
    state.selectedJobId = id;
    toast(`ジョブ #${id} を作成しました`, "ジョブ", "success");
  }
  closeJobForm();
  renderJobs();
  renderDashboard();
}

function toggleSelectedJobActive() {
  if (!canOperate()) return toast("operator/admin のみ実行可能", "AUTHORIZATION_FAILED", "warning");
  const j = state.jobs.find((x) => x.id === state.selectedJobId);
  if (!j) return;
  j.status = j.status === "active" ? "inactive" : "active";
  renderJobs();
  renderDashboard();
}

function recalcCompliance() {
  if (!canOperate()) return toast("operator/admin のみ実行可能", "AUTHORIZATION_FAILED", "warning");
  state.jobs.forEach((j) => {
    const ok = Object.values(j.complianceChecks).filter(Boolean).length;
    j.compliance = ok === 5 ? "compliant" : ok >= 3 ? "warning" : "non_compliant";
  });
  renderJobs();
  renderDashboard();
  toast("全件準拠チェックを再計算", "3-2-1-1-0", "success");
}

function initLocationPicker() {
  const building = document.getElementById("building_select");
  const floor = document.getElementById("floor_select");
  const rack = document.getElementById("rack_select");
  Object.keys(locationData).forEach((k) => building.insertAdjacentHTML("beforeend", `<option value="${esc(k)}">${esc(k)}</option>`));

  building.addEventListener("change", () => {
    floor.innerHTML = `<option value="">フロア</option>`;
    rack.innerHTML = `<option value="">ラック</option>`;
    floor.disabled = !building.value;
    rack.disabled = true;
    document.getElementById("rack_grid").innerHTML = "";
    document.getElementById("location_text").value = "";
    if (!building.value) return;
    locationData[building.value].floors.forEach((f) => floor.insertAdjacentHTML("beforeend", `<option value="${esc(f)}">${esc(f)}</option>`));
    updateMediaPreview();
  });

  floor.addEventListener("change", () => {
    rack.innerHTML = `<option value="">ラック</option>`;
    document.getElementById("rack_grid").innerHTML = "";
    rack.disabled = !(building.value && floor.value);
    if (!(building.value && floor.value)) return;
    locationData[building.value].racks[floor.value].forEach((r) => rack.insertAdjacentHTML("beforeend", `<option value="${esc(r)}">${esc(r)}</option>`));
    renderRackGrid(building.value, floor.value);
  });

  rack.addEventListener("change", () => {
    markRack(rack.value);
    syncLocation();
  });

  function renderRackGrid(b, f) {
    const wrap = document.getElementById("rack_grid");
    const occupied = new Set(locationData[b].occupied[f] || []);
    wrap.innerHTML = "";
    locationData[b].racks[f].forEach((slot) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = `rack-slot${occupied.has(slot) ? " occupied" : ""}`;
      btn.textContent = slot;
      if (!occupied.has(slot)) btn.addEventListener("click", () => { rack.value = slot; markRack(slot); syncLocation(); });
      wrap.appendChild(btn);
    });
  }

  function markRack(value) {
    [...document.querySelectorAll("#rack_grid .rack-slot")].forEach((el) => el.classList.toggle("selected", el.textContent === value));
  }

  function syncLocation() {
    const parts = [building.value, floor.value, rack.value].filter(Boolean);
    document.getElementById("location_text").value = parts.join("-");
    updateMediaPreview();
  }
}

function initMediaFormInteractive() {
  ["media_id", "label_name", "media_type", "media_status", "location_text", "mediaPurchaseDate", "mediaOwner", "mediaNotes"].forEach((id) => {
    document.getElementById(id).addEventListener("input", updateMediaPreview);
    document.getElementById(id).addEventListener("change", updateMediaPreview);
  });
  document.getElementById("media_id").addEventListener("input", renderMediaQr);
  document.getElementById("media_type").addEventListener("change", () => {
    showTypeFields();
    autoSuggestMediaPrefix();
    updateMediaPreview();
  });
  document.getElementById("capacity_value").addEventListener("input", () => updateCapacity(false));
  document.getElementById("capacity_unit").addEventListener("change", () => updateCapacity(false));
  document.getElementById("capacity_slider").addEventListener("input", () => updateCapacity(true));
  document.getElementById("mediaForm").addEventListener("submit", saveMedia);
  document.getElementById("borrowMediaBtn").addEventListener("click", borrowMedia);
  document.getElementById("returnMediaBtn").addEventListener("click", returnMedia);
  document.getElementById("addMediaBtn").addEventListener("click", () => setView("media", "オフラインメディア"));
  document.getElementById("download-qr").addEventListener("click", () => toast("QRダウンロード（モック）", "QR", "info"));
  document.getElementById("print-qr").addEventListener("click", () => window.print());
  renderMediaQr();
  showTypeFields();
}

function showTypeFields() {
  const type = document.getElementById("media_type").value;
  ["tape_fields", "disk_fields", "optical_fields", "cloud_fields"].forEach((id) => document.getElementById(id).classList.remove("show"));
  if (type === "tape") document.getElementById("tape_fields").classList.add("show");
  if (type === "disk" || type === "external_hdd") document.getElementById("disk_fields").classList.add("show");
  if (type === "optical") document.getElementById("optical_fields").classList.add("show");
  if (type === "cloud") document.getElementById("cloud_fields").classList.add("show");
}

function autoSuggestMediaPrefix() {
  const input = document.getElementById("media_id");
  if (input.value.trim()) return;
  const type = document.getElementById("media_type").value;
  const map = { tape: "LTO-", disk: "DISK-", optical: "BD-", cloud: "S3-", external_hdd: "HDD-OFF-", usb: "USB-" };
  input.value = map[type] || "";
  renderMediaQr();
}

function updateCapacity(fromSlider = false) {
  const valEl = document.getElementById("capacity_value");
  const unitEl = document.getElementById("capacity_unit");
  const slider = document.getElementById("capacity_slider");
  let gb;
  if (fromSlider) {
    gb = Number(slider.value || 0);
    valEl.value = unitEl.value === "tb" ? String(Math.round((gb / 1024) * 10) / 10) : String(gb);
  } else {
    const n = Number(valEl.value || 0);
    gb = unitEl.value === "tb" ? Math.round(n * 1024) : Math.round(n);
    slider.value = String(Math.min(20480, gb));
  }
  const pct = Math.min((gb / 20480) * 100, 100);
  document.getElementById("capacity_indicator").style.width = `${pct}%`;
  document.getElementById("capacitySummary").textContent = `${formatCapacity(gb)} / 20 TB 上限想定 (${pct.toFixed(1)}%)`;
  updateMediaPreview();
}

function renderMediaQr() {
  const text = document.getElementById("media_id").value.trim();
  drawPseudoQR(document.getElementById("qr-preview"), text, 180);
  drawPseudoQR(document.getElementById("preview-qr-small"), text, 80);
}

function updateMediaPreview() {
  const mediaId = document.getElementById("media_id").value.trim() || "---";
  const label = document.getElementById("label_name").value.trim() || "ラベル名";
  const typeText = document.getElementById("media_type").selectedOptions[0]?.textContent || "種別";
  const cap = `${document.getElementById("capacity_value").value || "0"} ${document.getElementById("capacity_unit").value.toUpperCase()}`;
  const location = document.getElementById("location_text").value || "場所未設定";
  document.getElementById("label-preview-id").textContent = mediaId;
  document.getElementById("label-preview-name").textContent = label;
  document.getElementById("label-preview-type").textContent = typeText;
  document.getElementById("label-preview-capacity").textContent = cap;
  document.getElementById("label-preview-location").textContent = location;
  document.getElementById("label-preview-date").textContent = formatDate(new Date());
}

function renderMedia() {
  const tbody = document.querySelector("#mediaTable tbody");
  tbody.innerHTML = state.media.map((m) => `
    <tr data-media="${m.id}">
      <td>${esc(m.media_id)}</td><td>${esc(m.media_type)}</td><td>${formatCapacity(m.capacity_gb)}</td>
      <td>${esc(m.storage_location)}</td><td>${statusChip(m.current_status === "borrowed" ? "warning" : (m.current_status === "retired" ? "muted" : "ok"), m.current_status)}</td><td>${esc(m.updated_at)}</td>
    </tr>`).join("");
  tbody.querySelectorAll("[data-media]").forEach((row) => row.addEventListener("click", () => fillMediaForm(state.media.find((m) => m.id === Number(row.dataset.media)))));
  document.getElementById("rotationScheduleList").innerHTML = state.rotations.map((r) => `<div class="stack-item ${r.overdue ? "overdue" : ""}"><div class="title">${esc(r.mediaId)} / ${esc(r.method)}</div><div class="meta">次回 ${esc(r.nextDate)} / ${esc(r.note)}</div></div>`).join("");
  document.getElementById("lendingHistoryList").innerHTML = state.lendingHistory.map((l) => `<div class="stack-item"><div class="title">${esc(l.mediaId)} - ${esc(l.event)}</div><div class="meta">${esc(l.date)} / ${esc(l.who)} / ${esc(l.detail)}</div></div>`).join("");
}

function fillMediaForm(m) {
  if (!m) return;
  document.getElementById("media_id").value = m.media_id;
  document.getElementById("label_name").value = m.label_name || "";
  document.getElementById("media_type").value = m.media_type;
  document.getElementById("media_status").value = m.current_status;
  document.getElementById("capacity_unit").value = "gb";
  document.getElementById("capacity_value").value = String(m.capacity_gb);
  document.getElementById("location_text").value = m.storage_location;
  showTypeFields();
  updateCapacity(false);
  renderMediaQr();
  updateMediaPreview();
}

function saveMedia(e) {
  e.preventDefault();
  const media_id = document.getElementById("media_id").value.trim();
  const media_type = document.getElementById("media_type").value;
  if (!media_id || !media_type) return toast("Media ID と種別は必須", "VALIDATION_ERROR", "danger");
  const gb = document.getElementById("capacity_unit").value === "tb"
    ? Math.round(Number(document.getElementById("capacity_value").value || 0) * 1024)
    : Math.round(Number(document.getElementById("capacity_value").value || 0));
  const payload = {
    media_id, media_type, capacity_gb: gb, storage_location: document.getElementById("location_text").value || "未設定",
    current_status: document.getElementById("media_status").value, updated_at: toDateInputValue(new Date()), label_name: document.getElementById("label_name").value.trim() || media_id
  };
  const existing = state.media.find((m) => m.media_id === media_id);
  if (existing) Object.assign(existing, payload); else state.media.unshift({ id: Math.max(...state.media.map((m) => m.id), 0) + 1, ...payload });
  renderMedia();
  toast(existing ? "メディアを更新しました" : "メディアを登録しました", "FR-020", "success");
}

function borrowMedia() {
  if (!canOperate()) return toast("operator/admin のみ実行可能", "AUTHORIZATION_FAILED", "warning");
  const id = document.getElementById("media_id").value.trim();
  const m = state.media.find((x) => x.media_id === id);
  if (!m) return toast("メディアが見つかりません", "RESOURCE_NOT_FOUND", "warning");
  if (m.current_status === "borrowed") return toast("Media is already borrowed", "MEDIA_ALREADY_BORROWED", "danger");
  m.current_status = "borrowed"; m.updated_at = toDateInputValue(new Date());
  state.lendingHistory.unshift({ mediaId: m.media_id, event: "貸出", who: state.role, date: m.updated_at, detail: "UIサンプル操作" });
  renderMedia();
}

function returnMedia() {
  if (!canOperate()) return toast("operator/admin のみ実行可能", "AUTHORIZATION_FAILED", "warning");
  const id = document.getElementById("media_id").value.trim();
  const m = state.media.find((x) => x.media_id === id);
  if (!m) return toast("メディアが見つかりません", "RESOURCE_NOT_FOUND", "warning");
  m.current_status = "stored"; m.updated_at = toDateInputValue(new Date());
  state.lendingHistory.unshift({ mediaId: m.media_id, event: "返却", who: state.role, date: m.updated_at, detail: "状態確認: normal" });
  renderMedia();
}

document.getElementById("addVerificationBtn").addEventListener("click", () => {
  if (!canOperate()) return toast("operator/admin のみ実行可能", "AUTHORIZATION_FAILED", "warning");
  state.verificationTests.unshift({ id: Date.now(), jobName: "Daily SQL Server Backup", type: "integrity_check", result: Math.random() < .8 ? "success" : "failed", date: toDateInputValue(new Date()), by: "operator01", durationSec: 320 });
  renderVerification();
  toast("検証テスト記録を追加しました", "FR-030", "success");
});

document.getElementById("createScheduleBtn").addEventListener("click", () => {
  if (!canOperate()) return toast("operator/admin のみ実行可能", "AUTHORIZATION_FAILED", "warning");
  const d = new Date(); d.setDate(d.getDate() + 90);
  state.verificationSchedules.unshift({ id: Date.now(), jobName: "AOMEI Workstation Backup", frequency: "quarterly", nextDate: toDateInputValue(d), assignedTo: "operator03" });
  renderVerification();
});

function renderVerification() {
  document.querySelector("#verificationTable tbody").innerHTML = state.verificationTests.map((t) => `
    <tr><td>${esc(t.jobName)}</td><td>${esc(t.type)}</td><td>${resultChip(t.result)}</td><td>${esc(t.date)}</td><td>${esc(t.by)}</td><td>${fmtSec(t.durationSec)}</td></tr>`).join("");
  const now = new Date();
  document.querySelector("#verificationScheduleTable tbody").innerHTML = state.verificationSchedules.map((s) => {
    const overdue = new Date(s.nextDate) < now;
    return `<tr><td>${esc(s.jobName)}</td><td>${esc(s.frequency)}</td><td>${esc(s.nextDate)}</td><td>${esc(s.assignedTo)}</td><td>${statusChip(overdue ? "danger" : "ok", overdue ? "overdue" : "scheduled")}</td></tr>`;
  }).join("");
  document.getElementById("verificationIssues").innerHTML = state.verificationIssues.map((i) => `<div class="stack-item ${i.sla === "超過" ? "overdue" : ""}"><div class="title">${esc(i.id)} / ${esc(i.jobName)}</div><div class="meta">Severity ${esc(i.severity)} / ${esc(i.status)} / SLA ${esc(i.sla)}</div><div class="meta">${esc(i.detail)}</div></div>`).join("");
}

document.getElementById("reportForm").addEventListener("submit", (e) => {
  e.preventDefault();
  const fd = new FormData(e.currentTarget);
  const rec = {
    id: Math.max(...state.reports.map((r) => r.id), 500) + 1,
    type: `${fd.get("report_type")}`, from: `${fd.get("date_from")}`, to: `${fd.get("date_to")}`,
    format: `${fd.get("file_format")}`.toLowerCase(), status: "completed", createdBy: state.role,
    fileName: `${fd.get("report_type")}_${fd.get("date_to")}.${`${fd.get("file_format")}`.toLowerCase()}`
  };
  state.reports.unshift(rec);
  state.selectedReportId = rec.id;
  renderReports();
  toast(`レポート生成: ${rec.fileName}`, "FR-012/041/042", "success");
});

document.getElementById("generateDailyReportBtn").addEventListener("click", () => {
  const f = document.getElementById("reportForm");
  f.querySelector("[name=report_type]").value = "daily";
  f.querySelector("[name=file_format]").value = "html";
  f.requestSubmit();
});

function renderReports() {
  document.getElementById("reportCountPill").textContent = `${state.reports.length}件`;
  document.querySelector("#reportsTable tbody").innerHTML = state.reports.map((r) => `
    <tr data-report="${r.id}" class="${r.id === state.selectedReportId ? "selected" : ""}">
      <td>${r.id}</td><td>${esc(r.type)}</td><td>${esc(r.from)} - ${esc(r.to)}</td><td>${esc(r.format)}</td><td>${statusChip(r.status)}</td><td>${esc(r.createdBy)}</td>
    </tr>`).join("");
  document.querySelectorAll("[data-report]").forEach((row) => row.addEventListener("click", () => { state.selectedReportId = Number(row.dataset.report); renderReports(); }));
  const r = state.reports.find((x) => x.id === state.selectedReportId) || state.reports[0];
  if (!r) return;
  document.getElementById("reportPreview").innerHTML = `
    <div class="detail-card">
      <h4>レポート詳細</h4>
      <dl class="kv-grid">${kv("ID", r.id)}${kv("種別", r.type)}${kv("期間", `${r.from} - ${r.to}`)}${kv("形式", r.format)}${kv("ステータス", r.status)}${kv("作成者", r.createdBy)}${kv("ファイル", r.fileName)}${kv("Download API", `/api/v1/reports/${r.id}/download`)}</dl>
      <div class="form-actions"><button class="btn btn-secondary btn-sm" id="downloadReportBtn">ダウンロード</button><button class="btn btn-secondary btn-sm" id="deleteReportBtn">削除</button></div>
    </div>`;
  document.getElementById("downloadReportBtn").addEventListener("click", () => toast(`${r.fileName} をダウンロード（モック）`, "レポート", "info"));
  document.getElementById("deleteReportBtn").addEventListener("click", () => {
    if (state.role !== "admin") return toast("レポート削除は admin のみ", "AUTHORIZATION_FAILED", "warning");
    state.reports = state.reports.filter((x) => x.id !== r.id);
    state.selectedReportId = state.reports[0]?.id;
    renderReports();
  });
  applyRoleRestrictions();
}

document.getElementById("notificationTestForm").addEventListener("submit", (e) => {
  e.preventDefault();
  const fd = new FormData(e.currentTarget);
  const channels = [];
  if (fd.get("useEmail")) channels.push("Email");
  if (fd.get("useTeams")) channels.push("Teams");
  if (fd.get("useDashboard")) channels.push("Dashboard");
  if (!channels.length) return toast("チャネルを選択してください", "VALIDATION_ERROR", "danger");
  state.notificationHistory.unshift({ at: `${formatDate(new Date())} 10:10`, channels, severity: `${fd.get("severity")}`, title: `${fd.get("title")}`, result: channels.map((c) => `${c}=OK`).join(" ") });
  renderNotifications();
  toast(`通知テスト送信: ${channels.join("/")}`, "MultiChannelNotificationOrchestrator", "success");
});

document.getElementById("testAllChannelsBtn").addEventListener("click", () => {
  state.notificationChannels.forEach((c) => { c.health = Math.random() < .8 ? "healthy" : "degraded"; c.latencyMs = Math.max(10, c.latencyMs + Math.round((Math.random() - .5) * 200)); });
  renderNotifications();
});

function renderNotifications() {
  document.getElementById("channelHealthCards").innerHTML = state.notificationChannels.map((c) => card(c.name, c.health, `sent ${c.sent24h}/24h • fail ${c.failed24h} • ${c.latencyMs}ms`)).join("");
  document.getElementById("notificationHistory").innerHTML = state.notificationHistory.map((h) => `<div class="stack-item"><div class="title">${esc(h.title)} ${sevChip(h.severity)}</div><div class="meta">${esc(h.at)} / ${esc(h.channels.join(", "))}</div><div class="meta">${esc(h.result)}</div></div>`).join("");
}

function renderMonitoring() {
  document.getElementById("performanceMetrics").innerHTML = state.performance.metrics.map((m) => card(m.label, m.value, m.meta)).join("");
  document.querySelector("#performanceTable tbody").innerHTML = state.performance.endpoints.map((p) => `<tr><td>${esc(p.endpoint)}</td><td>${p.p50}</td><td>${p.p95}</td><td>${p.p99}</td><td>${p.rps}</td><td>${statusChip(p.status === "Acceptable" ? "warning" : "ok", p.status)}</td></tr>`).join("");
  document.getElementById("errorStatsList").innerHTML = state.performance.errorStats.map((s) => `<div class="stack-item"><div class="title">${esc(s.label)}: ${esc(s.value)}</div><div class="meta">${esc(s.meta)}</div></div>`).join("");
  document.getElementById("errorContextPreview").textContent = JSON.stringify(state.performance.errorContextExample, null, 2);
}

document.getElementById("auditSearch").addEventListener("input", renderAudit);
document.getElementById("auditResultFilter").addEventListener("change", renderAudit);
function renderAudit() {
  const q = document.getElementById("auditSearch").value.trim().toLowerCase();
  const rf = document.getElementById("auditResultFilter").value;
  const rows = state.auditLogs.filter((r) => (!rf || r.result === rf) && (!q || `${r.user} ${r.action} ${r.resource} ${r.details}`.toLowerCase().includes(q)));
  document.querySelector("#auditTable tbody").innerHTML = rows.map((r) => `<tr><td>${esc(r.at)}</td><td>${esc(r.user)}</td><td>${esc(r.action)}</td><td>${esc(r.resource)}</td><td>${esc(r.ip)}</td><td>${statusChip(r.result)}</td><td>${esc(r.details)}</td></tr>`).join("");
}

document.getElementById("cycleApiExampleBtn").addEventListener("click", () => { state.apiExampleIndex = (state.apiExampleIndex + 1) % state.apiExamples.length; renderApi(); });
function renderApi() {
  const groups = [
    ["Auth", ["POST /api/v1/auth/login", "POST /api/v1/auth/logout", "POST /api/v1/auth/refresh", "GET /api/v1/auth/me"]],
    ["Jobs", ["GET /api/v1/jobs", "GET /api/v1/jobs/{id}", "POST /api/v1/jobs", "PUT /api/v1/jobs/{id}", "DELETE /api/v1/jobs/{id}", "POST /api/v1/jobs/{id}/copies"]],
    ["Alerts", ["GET /api/v1/alerts", "GET /api/v1/alerts/{id}", "POST /api/v1/alerts/{id}/acknowledge", "POST /api/v1/alerts/bulk-acknowledge"]],
    ["Reports", ["GET /api/v1/reports", "POST /api/v1/reports/generate", "GET /api/v1/reports/{id}/download"]],
    ["Dashboard", ["GET /api/v1/dashboard/summary", "GET /api/v1/dashboard/recent-executions", "GET /api/v1/dashboard/storage-usage"]],
    ["Media", ["GET /api/v1/media", "POST /api/v1/media", "POST /api/v1/media/{id}/borrow", "POST /api/v1/media/{id}/return"]],
    ["Verification", ["GET /api/v1/verification/tests", "POST /api/v1/verification/tests", "GET /api/v1/verification/schedules"]],
    ["AOMEI", ["POST /api/v1/aomei/register (X-API-Key)", "POST /api/v1/aomei/status (X-API-Key)", "GET /api/v1/aomei/jobs"]]
  ];
  document.getElementById("apiEndpointList").innerHTML = groups.map(([g, list]) => `<div class="stack-item"><div class="title">${g}</div><div class="meta">${list.map(esc).join(" | ")}</div></div>`).join("");
  const ex = state.apiExamples[state.apiExampleIndex];
  document.getElementById("apiExampleViewer").textContent = `${ex.title}\n\n${JSON.stringify(ex.body, null, 2)}`;
  document.getElementById("apiErrorViewer").textContent = JSON.stringify({ error: { code: "VALIDATION_ERROR", message: "Validation failed", details: { fields: { job_name: "job_name is required", retention_days: "Must be at least 1 day" } } } }, null, 2);
  document.getElementById("authFlowViewer").textContent = JSON.stringify({ request: { username: "user", password: "pass" }, response: { access_token: "eyJ...mock", refresh_token: "eyJ...mock", token_type: "Bearer", expires_in: 3600, user: { id: 1, username: "user", role: state.role } } }, null, 2);
}

function onLogin(e) {
  e.preventDefault();
  const user = document.getElementById("loginUser").value.trim() || "user";
  const mode = document.getElementById("loginAuthMode").value;
  const token = `eyJ...${btoa(user).replace(/=+$/,"")}.mock`;
  document.getElementById("tokenPreview").textContent = mode === "api"
    ? JSON.stringify({ access_token: token, refresh_token: `${token}.refresh`, token_type: "Bearer", expires_in: 3600, user: { username: user, role: state.role } }, null, 2)
    : `Session login success\nuser=${user}\nrole=${state.role}\nsession_timeout=30m`;
  state.auditLogs.unshift({ at: `${formatDate(new Date())} 10:12`, user, action: mode === "api" ? "api_login" : "login", resource: "auth", ip: "127.0.0.1", result: "success", details: mode === "api" ? "JWT issued" : "Session established" });
  renderAudit();
  toast("ログイン成功（モック）", mode === "api" ? "JWT" : "Session", "success");
}

function applyRoleRestrictions() {
  const can = canOperate();
  ["openJobFormBtn","editJobBtn","toggleJobActiveBtn","runComplianceCheckAll","addVerificationBtn","createScheduleBtn","addMediaBtn","borrowMediaBtn","returnMediaBtn"].forEach((id) => { const el = document.getElementById(id); if (el) el.disabled = !can; });
  const delBtn = document.getElementById("deleteReportBtn"); if (delBtn) delBtn.disabled = state.role !== "admin";
}
function canOperate() { return state.role === "admin" || state.role === "operator"; }

function simulateTick(silent) {
  const d = state.dashboard;
  d.successTrend.push(clamp(d.successTrend.at(-1) + (Math.random() < .5 ? -1 : 1), 90, 99)); d.successTrend.shift();
  d.failedTrend.push(clamp(Math.round(Math.random() * 4), 0, 6)); d.failedTrend.shift();
  d.storageUsage = d.storageUsage.map((s) => ({ ...s, used: clamp(s.used + Math.round((Math.random() - .35) * 4), 25, 95) }));
  if (Math.random() < .3) state.performance.endpoints[0].p95 = `${clamp(parseInt(state.performance.endpoints[0].p95, 10) + Math.round((Math.random() - .5) * 10), 100, 180)}ms`;
  renderDashboard(); renderMonitoring();
  if (!silent) toast("メトリクスを更新しました", "Live Update", "info");
}

function bindJobOpenLinks() {
  document.querySelectorAll("[data-job-open]").forEach((b) => b.addEventListener("click", () => {
    state.selectedJobId = Number(b.dataset.jobOpen);
    setView("jobs", "ジョブ管理");
    renderJobs();
  }));
}

function drawDonut(canvas, slices) {
  const ctx = canvas.getContext("2d"), { width, height } = canvas;
  ctx.clearRect(0,0,width,height); ctx.fillStyle = "#ffffff"; ctx.fillRect(0,0,width,height);
  const total = slices.reduce((a,b) => a + b.value, 0) || 1; let ang = -Math.PI/2;
  const cx = width * .34, cy = height * .5, r = Math.min(width, height) * .32, ri = r * .55;
  slices.forEach((s) => { const span = (s.value/total) * Math.PI * 2; ctx.beginPath(); ctx.moveTo(cx,cy); ctx.arc(cx,cy,r,ang,ang+span); ctx.closePath(); ctx.fillStyle = s.color; ctx.fill(); ang += span; });
  ctx.globalCompositeOperation = "destination-out"; ctx.beginPath(); ctx.arc(cx,cy,ri,0,Math.PI*2); ctx.fill(); ctx.globalCompositeOperation = "source-over";
  ctx.fillStyle = "#123044"; ctx.font = "700 18px sans-serif"; const t = String(total); ctx.fillText(t, cx - ctx.measureText(t).width/2, cy+6);
  ctx.font = "12px sans-serif"; let y = 34; slices.forEach((s) => { ctx.fillStyle = s.color; ctx.fillRect(width*.62, y-10, 10, 10); ctx.fillStyle = "#244760"; ctx.fillText(`${s.label}: ${s.value}`, width*.62 + 16, y); y += 22; });
}

function drawLine(canvas, seriesA, seriesB) {
  const ctx = canvas.getContext("2d"), { width, height } = canvas, pad = 28;
  ctx.clearRect(0,0,width,height); ctx.fillStyle = "#ffffff"; ctx.fillRect(0,0,width,height); drawGrid(ctx,width,height,pad);
  const draw = (arr, color, scale = 100) => {
    ctx.beginPath();
    arr.forEach((v,i) => { const x = pad + (i*(width-pad*2))/Math.max(1, arr.length-1); const y = height-pad - (v/scale)*(height-pad*2); i ? ctx.lineTo(x,y) : ctx.moveTo(x,y); });
    ctx.strokeStyle = color; ctx.lineWidth = 2; ctx.stroke();
    arr.forEach((v,i) => { const x = pad + (i*(width-pad*2))/Math.max(1, arr.length-1); const y = height-pad - (v/scale)*(height-pad*2); ctx.fillStyle = color; ctx.beginPath(); ctx.arc(x,y,3,0,Math.PI*2); ctx.fill(); });
  };
  draw(seriesA, "#1dd4b3", 100); draw(seriesB.map((v) => v*10), "#ff6b6b", 100);
  ctx.fillStyle = "#244760"; ctx.font = "11px sans-serif"; ctx.fillText("緑=成功率(%) / 赤=失敗件数×10", pad, 14);
}

function drawBars(canvas, items) {
  const ctx = canvas.getContext("2d"), { width, height } = canvas, pad = 28;
  ctx.clearRect(0,0,width,height); ctx.fillStyle = "#ffffff"; ctx.fillRect(0,0,width,height); drawGrid(ctx,width,height,pad);
  const w = (width - pad*2) / (items.length * 2);
  items.forEach((it,i) => {
    const x = pad + i*w*2 + w*.35, h = (it.used/it.total) * (height-pad*2), y = height-pad-h;
    ctx.fillStyle = it.used > 85 ? "#ff6b6b" : (it.used > 70 ? "#ffd166" : "#1dd4b3"); ctx.fillRect(x,y,w,h);
    ctx.fillStyle = "#244760"; ctx.font = "11px sans-serif"; ctx.fillText(it.label, x-4, height-10); ctx.fillText(`${it.used}%`, x, y-6);
  });
}

function drawGrid(ctx, width, height, pad) {
  ctx.strokeStyle = "rgba(18,48,68,.08)"; ctx.lineWidth = 1;
  for (let i=0;i<4;i++) { const y = pad + (i*(height-pad*2))/3; ctx.beginPath(); ctx.moveTo(pad,y); ctx.lineTo(width-pad,y); ctx.stroke(); }
}

function drawPseudoQR(container, text, size) {
  container.innerHTML = "";
  const cv = document.createElement("canvas"); cv.width = size; cv.height = size; cv.style.width = `${size}px`; cv.style.height = `${size}px`;
  const c = cv.getContext("2d"); c.fillStyle = "#fff"; c.fillRect(0,0,size,size);
  if (!text) { c.strokeStyle = "#777"; c.strokeRect(4,4,size-8,size-8); c.fillStyle = "#222"; c.fillText("QR", size/2-8, size/2+4); container.appendChild(cv); return; }
  const n = 21, cell = Math.floor(size/n), seed = hash(text);
  for (let y=0;y<n;y++) for (let x=0;x<n;x++) {
    const finder = finderCell(x,y,n);
    const on = finder || ((seed + x*17 + y*31 + ((x^y)<<1)) % 11) < 5;
    c.fillStyle = on ? "#111" : "#fff";
    c.fillRect(x*cell, y*cell, cell, cell);
  }
  container.appendChild(cv);
}

function finderCell(x, y, n) {
  const boxes = [{x:0,y:0},{x:n-7,y:0},{x:0,y:n-7}];
  return boxes.some((b) => {
    if (x < b.x || y < b.y || x >= b.x + 7 || y >= b.y + 7) return false;
    const rx = x - b.x, ry = y - b.y;
    return rx === 0 || ry === 0 || rx === 6 || ry === 6 || (rx >= 2 && rx <= 4 && ry >= 2 && ry <= 4);
  });
}

function hash(s) { let h = 0; for (let i=0;i<s.length;i++) h = ((h<<5)-h + s.charCodeAt(i))|0; return Math.abs(h); }
function countSeverity(sev) { return state.alerts.filter((a) => !a.acknowledged && a.severity === sev).length; }
function card(label, value, meta) { return `<article class="metric-card"><div class="label">${esc(label)}</div><div class="value">${esc(String(value))}</div><div class="meta">${esc(meta || "")}</div></article>`; }
function kv(k, v) { return `<div><dt>${esc(String(k))}</dt><dd>${esc(String(v ?? "-"))}</dd></div>`; }
function statusChip(kind, label) { const k = (kind || "").toLowerCase(); const cls = k.includes("danger") || k === "failed" ? "status-danger" : (k.includes("warn") || k === "borrowed" ? "status-warning" : (k === "inactive" || k === "retired" || k === "muted" ? "status-muted" : "status-ok")); return `<span class="status-chip ${cls}">${esc(label || kind)}</span>`; }
function sevChip(sev) { const cls = sev === "critical" ? "severity-critical" : sev === "error" ? "severity-error" : sev === "warning" ? "severity-warning" : "severity-info"; return `<span class="severity-chip ${cls}">${esc(sev)}</span>`; }
function compChip(v) { return v === "compliant" ? statusChip("ok","compliant") : v === "warning" ? statusChip("warning","warning") : statusChip("danger","non_compliant"); }
function resultChip(v) { return v === "success" ? statusChip("ok","success") : v === "warning" ? statusChip("warning","warning") : statusChip("danger","failed"); }
function fmtSec(s) { return s >= 3600 ? `${Math.floor(s/3600)}h ${Math.floor((s%3600)/60)}m` : `${Math.floor(s/60)}m`; }
function formatCapacity(gb) { return gb >= 1024 ? `${(gb/1024).toFixed(Number.isInteger(gb/1024) ? 0 : 1)} TB` : `${gb} GB`; }
function formatDate(d) { return `${d.getFullYear()}/${String(d.getMonth()+1).padStart(2,"0")}/${String(d.getDate()).padStart(2,"0")}`; }
function toDateInputValue(d) { return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}-${String(d.getDate()).padStart(2,"0")}`; }
function clamp(v,min,max){ return Math.min(max, Math.max(min, v)); }
function esc(v) { return String(v ?? "").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;").replaceAll("'","&#39;"); }
function toast(msg, title = "通知", kind = "info") { const el = document.createElement("div"); el.className = `toast toast-${kind}`; el.innerHTML = `<div class="title">${esc(title)}</div><div class="message">${esc(msg)}</div>`; dom.toastRegion.prepend(el); setTimeout(() => el.remove(), 2800); }
