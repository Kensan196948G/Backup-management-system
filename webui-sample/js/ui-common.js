export function esc(v) { return String(v ?? "").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;").replaceAll("'","&#39;"); }

export function card(label, value, meta) {
  return `<article class="metric-card"><div class="label">${esc(label)}</div><div class="value">${esc(String(value))}</div><div class="meta">${esc(meta || "")}</div></article>`;
}

export function kv(k, v) {
  return `<div><dt>${esc(String(k))}</dt><dd>${esc(String(v ?? "-"))}</dd></div>`;
}

export function statusChip(kind, label) {
  const k = (kind || "").toLowerCase();
  const cls = k.includes("danger") || k === "failed"
    ? "status-danger"
    : (k.includes("warn") || k === "borrowed"
      ? "status-warning"
      : (k === "inactive" || k === "retired" || k === "muted" ? "status-muted" : "status-ok"));
  return `<span class="status-chip ${cls}">${esc(label || kind)}</span>`;
}

export function sevChip(sev) {
  const cls = sev === "critical" ? "severity-critical" : sev === "error" ? "severity-error" : sev === "warning" ? "severity-warning" : "severity-info";
  return `<span class="severity-chip ${cls}">${esc(sev)}</span>`;
}

export function compChip(v) {
  return v === "compliant" ? statusChip("ok", "compliant") : v === "warning" ? statusChip("warning", "warning") : statusChip("danger", "non_compliant");
}

export function resultChip(v) {
  return v === "success" ? statusChip("ok", "success") : v === "warning" ? statusChip("warning", "warning") : statusChip("danger", "failed");
}

export function fmtSec(s) {
  return s >= 3600 ? `${Math.floor(s / 3600)}h ${Math.floor((s % 3600) / 60)}m` : `${Math.floor(s / 60)}m`;
}

export function formatCapacity(gb) {
  return gb >= 1024 ? `${(gb / 1024).toFixed(Number.isInteger(gb / 1024) ? 0 : 1)} TB` : `${gb} GB`;
}

export function formatDate(d) {
  return `${d.getFullYear()}/${String(d.getMonth() + 1).padStart(2, "0")}/${String(d.getDate()).padStart(2, "0")}`;
}

export function toDateInputValue(d) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

export function clamp(v, min, max) {
  return Math.min(max, Math.max(min, v));
}
