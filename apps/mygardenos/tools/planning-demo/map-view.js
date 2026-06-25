const colors = {
  workFill: "rgba(47, 125, 87, 0.28)",
  workStroke: "#2f7d57",
  noGoFill: "rgba(195, 74, 58, 0.32)",
  noGoStroke: "#c34a3a",
  path: "#315e9c",
  dock: "#c89424",
  robot: "#1d2622",
  grid: "#d4ddd6",
};

export function drawMap(canvas, state) {
  const ctx = canvas.getContext("2d");
  const rect = canvas.getBoundingClientRect();
  canvas.width = Math.max(600, Math.floor(rect.width * window.devicePixelRatio));
  canvas.height = Math.max(420, Math.floor(rect.height * window.devicePixelRatio));
  ctx.scale(window.devicePixelRatio, window.devicePixelRatio);

  const width = canvas.width / window.devicePixelRatio;
  const height = canvas.height / window.devicePixelRatio;
  const viewport = makeViewport(width, height);
  ctx.clearRect(0, 0, width, height);
  drawGrid(ctx, width, height, viewport);

  if (state.workZone) drawPolygon(ctx, state.workZone, viewport, colors.workFill, colors.workStroke);
  if (state.noGoZone) drawPolygon(ctx, state.noGoZone, viewport, colors.noGoFill, colors.noGoStroke);
  if (state.path?.path_points?.length) drawPath(ctx, state.path.path_points, viewport);
  if (state.dock?.position) drawDock(ctx, state.dock.position, viewport);
  if (state.robotPosition) drawRobot(ctx, state.robotPosition, viewport, state.task?.status);
}

function makeViewport(width, height) {
  const padding = Math.max(28, Math.min(width, height) * 0.08);
  const scale = Math.min((width - padding * 2) / 16, (height - padding * 2) / 11);
  return { padding, scale, height };
}

function project(point, viewport) {
  return {
    x: viewport.padding + point.x * viewport.scale,
    y: viewport.height - viewport.padding - point.y * viewport.scale,
  };
}

function drawGrid(ctx, width, height, viewport) {
  ctx.strokeStyle = colors.grid;
  ctx.lineWidth = 1;
  for (let x = 0; x <= 16; x += 1) {
    const from = project({ x, y: 0 }, viewport);
    const to = project({ x, y: 11 }, viewport);
    ctx.beginPath();
    ctx.moveTo(from.x, from.y);
    ctx.lineTo(to.x, to.y);
    ctx.stroke();
  }
  for (let y = 0; y <= 11; y += 1) {
    const from = project({ x: 0, y }, viewport);
    const to = project({ x: 16, y }, viewport);
    ctx.beginPath();
    ctx.moveTo(from.x, from.y);
    ctx.lineTo(to.x, to.y);
    ctx.stroke();
  }
  ctx.strokeStyle = "#b8c4bd";
  ctx.strokeRect(viewport.padding, viewport.padding, width - viewport.padding * 2, height - viewport.padding * 2);
}

function drawPolygon(ctx, points, viewport, fill, stroke) {
  if (!points.length) return;
  ctx.beginPath();
  points.forEach((point, index) => {
    const p = project(point, viewport);
    if (index === 0) ctx.moveTo(p.x, p.y);
    else ctx.lineTo(p.x, p.y);
  });
  ctx.closePath();
  ctx.fillStyle = fill;
  ctx.strokeStyle = stroke;
  ctx.lineWidth = 2;
  ctx.fill();
  ctx.stroke();
}

function drawPath(ctx, points, viewport) {
  ctx.strokeStyle = colors.path;
  ctx.lineWidth = 2;
  ctx.beginPath();
  points.forEach((point, index) => {
    const p = project(point, viewport);
    if (index === 0) ctx.moveTo(p.x, p.y);
    else ctx.lineTo(p.x, p.y);
  });
  ctx.stroke();
}

function drawDock(ctx, point, viewport) {
  const p = project(point, viewport);
  ctx.fillStyle = colors.dock;
  ctx.strokeStyle = "#7d5b15";
  ctx.lineWidth = 2;
  ctx.fillRect(p.x - 8, p.y - 8, 16, 16);
  ctx.strokeRect(p.x - 8, p.y - 8, 16, 16);
}

function drawRobot(ctx, point, viewport, status) {
  const p = project(point, viewport);
  ctx.fillStyle = status === "PAUSED" ? colors.noGoStroke : colors.robot;
  ctx.beginPath();
  ctx.arc(p.x, p.y, 8, 0, Math.PI * 2);
  ctx.fill();
}
