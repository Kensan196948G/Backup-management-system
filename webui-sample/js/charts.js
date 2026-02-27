export function drawDonut(canvas, slices) {
  const ctx = canvas.getContext("2d"), { width, height } = canvas;
  ctx.clearRect(0, 0, width, height); ctx.fillStyle = "#ffffff"; ctx.fillRect(0, 0, width, height);
  const total = slices.reduce((a, b) => a + b.value, 0) || 1; let ang = -Math.PI / 2;
  const cx = width * .34, cy = height * .5, r = Math.min(width, height) * .32, ri = r * .55;
  slices.forEach((s) => { const span = (s.value / total) * Math.PI * 2; ctx.beginPath(); ctx.moveTo(cx, cy); ctx.arc(cx, cy, r, ang, ang + span); ctx.closePath(); ctx.fillStyle = s.color; ctx.fill(); ang += span; });
  ctx.globalCompositeOperation = "destination-out"; ctx.beginPath(); ctx.arc(cx, cy, ri, 0, Math.PI * 2); ctx.fill(); ctx.globalCompositeOperation = "source-over";
  ctx.fillStyle = "#123044"; ctx.font = "700 18px sans-serif"; const t = String(total); ctx.fillText(t, cx - ctx.measureText(t).width / 2, cy + 6);
  ctx.font = "12px sans-serif"; let y = 34; slices.forEach((s) => { ctx.fillStyle = s.color; ctx.fillRect(width * .62, y - 10, 10, 10); ctx.fillStyle = "#244760"; ctx.fillText(`${s.label}: ${s.value}`, width * .62 + 16, y); y += 22; });
}

export function drawLine(canvas, seriesA, seriesB) {
  const ctx = canvas.getContext("2d"), { width, height } = canvas, pad = 28;
  ctx.clearRect(0, 0, width, height); ctx.fillStyle = "#ffffff"; ctx.fillRect(0, 0, width, height); drawGrid(ctx, width, height, pad);
  const draw = (arr, color, scale = 100) => {
    ctx.beginPath();
    arr.forEach((v, i) => { const x = pad + (i * (width - pad * 2)) / Math.max(1, arr.length - 1); const y = height - pad - (v / scale) * (height - pad * 2); i ? ctx.lineTo(x, y) : ctx.moveTo(x, y); });
    ctx.strokeStyle = color; ctx.lineWidth = 2; ctx.stroke();
    arr.forEach((v, i) => { const x = pad + (i * (width - pad * 2)) / Math.max(1, arr.length - 1); const y = height - pad - (v / scale) * (height - pad * 2); ctx.fillStyle = color; ctx.beginPath(); ctx.arc(x, y, 3, 0, Math.PI * 2); ctx.fill(); });
  };
  draw(seriesA, "#1dd4b3", 100); draw(seriesB.map((v) => v * 10), "#ff6b6b", 100);
  ctx.fillStyle = "#244760"; ctx.font = "11px sans-serif"; ctx.fillText("緑=成功率(%) / 赤=失敗件数×10", pad, 14);
}

export function drawBars(canvas, items) {
  const ctx = canvas.getContext("2d"), { width, height } = canvas, pad = 28;
  ctx.clearRect(0, 0, width, height); ctx.fillStyle = "#ffffff"; ctx.fillRect(0, 0, width, height); drawGrid(ctx, width, height, pad);
  const w = (width - pad * 2) / (items.length * 2);
  items.forEach((it, i) => {
    const x = pad + i * w * 2 + w * .35, h = (it.used / it.total) * (height - pad * 2), y = height - pad - h;
    ctx.fillStyle = it.used > 85 ? "#ff6b6b" : (it.used > 70 ? "#ffd166" : "#1dd4b3"); ctx.fillRect(x, y, w, h);
    ctx.fillStyle = "#244760"; ctx.font = "11px sans-serif"; ctx.fillText(it.label, x - 4, height - 10); ctx.fillText(`${it.used}%`, x, y - 6);
  });
}

function drawGrid(ctx, width, height, pad) {
  ctx.strokeStyle = "rgba(18,48,68,.08)"; ctx.lineWidth = 1;
  for (let i = 0; i < 4; i++) { const y = pad + (i * (height - pad * 2)) / 3; ctx.beginPath(); ctx.moveTo(pad, y); ctx.lineTo(width - pad, y); ctx.stroke(); }
}

export function drawPseudoQR(container, text, size) {
  container.innerHTML = "";
  const cv = document.createElement("canvas"); cv.width = size; cv.height = size; cv.style.width = `${size}px`; cv.style.height = `${size}px`;
  const c = cv.getContext("2d"); c.fillStyle = "#fff"; c.fillRect(0, 0, size, size);
  if (!text) { c.strokeStyle = "#777"; c.strokeRect(4, 4, size - 8, size - 8); c.fillStyle = "#222"; c.fillText("QR", size / 2 - 8, size / 2 + 4); container.appendChild(cv); return; }
  const n = 21, cell = Math.floor(size / n), seed = hash(text);
  for (let y = 0; y < n; y++) for (let x = 0; x < n; x++) {
    const finder = finderCell(x, y, n);
    const on = finder || ((seed + x * 17 + y * 31 + ((x ^ y) << 1)) % 11) < 5;
    c.fillStyle = on ? "#111" : "#fff";
    c.fillRect(x * cell, y * cell, cell, cell);
  }
  container.appendChild(cv);
}

function finderCell(x, y, n) {
  const boxes = [{ x: 0, y: 0 }, { x: n - 7, y: 0 }, { x: 0, y: n - 7 }];
  return boxes.some((b) => {
    if (x < b.x || y < b.y || x >= b.x + 7 || y >= b.y + 7) return false;
    const rx = x - b.x, ry = y - b.y;
    return rx === 0 || ry === 0 || rx === 6 || ry === 6 || (rx >= 2 && rx <= 4 && ry >= 2 && ry <= 4);
  });
}

function hash(s) { let h = 0; for (let i = 0; i < s.length; i++) h = ((h << 5) - h + s.charCodeAt(i)) | 0; return Math.abs(h); }
