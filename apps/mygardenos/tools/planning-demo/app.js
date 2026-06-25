import { PlanningApi } from "./api.js";
import { demoEmail, demoPassword, dockPosition, flowSteps, noGoZone, robotId, workZone } from "./demo-data.js";
import { drawMap } from "./map-view.js";

const elements = {
  apiBase: document.querySelector("#apiBase"),
  steps: document.querySelector("#steps"),
  runSetup: document.querySelector("#runSetup"),
  simulateRun: document.querySelector("#simulateRun"),
  simulateRtk: document.querySelector("#simulateRtk"),
  refreshState: document.querySelector("#refreshState"),
  taskFacts: document.querySelector("#taskFacts"),
  idFacts: document.querySelector("#idFacts"),
  eventLog: document.querySelector("#eventLog"),
  canvas: document.querySelector("#mapCanvas"),
};

const state = {
  property: null,
  map: null,
  workZone: null,
  noGoZone: null,
  dock: null,
  path: null,
  task: null,
  events: [],
  telemetry: [],
  robotPosition: null,
  completedSteps: new Set(),
};

const api = new PlanningApi(elements.apiBase.value);

init();

function init() {
  renderSteps();
  render();
  elements.apiBase.addEventListener("change", () => api.setBaseUrl(elements.apiBase.value));
  elements.runSetup.addEventListener("click", () => withBusy(runSetup));
  elements.simulateRun.addEventListener("click", () => withBusy(simulateRunning));
  elements.simulateRtk.addEventListener("click", () => withBusy(simulateRtkLoss));
  elements.refreshState.addEventListener("click", () => withBusy(refreshState));
  window.addEventListener("resize", () => drawMap(elements.canvas, state));
}

async function runSetup() {
  api.clearSession();
  await api.ensureSession(demoEmail, demoPassword);
  done("Login");

  state.property = await api.post("/properties", {
    name: "Demo Backyard",
    address: "123 Garden Road",
    latitude: -36.8485,
    longitude: 174.7633,
  });
  done("Property");

  state.map = await api.post(`/properties/${state.property.id}/maps`, {
    map_type: "point_cloud_top_view",
    image_url: "/maps/demo-backyard.png",
    coordinate_transform: { scale: 0.05, origin: { x: 0, y: 0 } },
  });
  done("Map");

  state.workZone = await api.post(`/maps/${state.map.id}/zones`, {
    name: "Rear lawn",
    zone_type: "WORK_AREA",
    polygon_coordinates: workZone,
    metadata: { mow_allowed: true, rtk_required: true },
  });
  state.noGoZone = await api.post(`/maps/${state.map.id}/zones`, {
    name: "Tree base",
    zone_type: "NO_GO",
    polygon_coordinates: noGoZone,
  });
  done("Zones");

  state.dock = await api.post(`/maps/${state.map.id}/docks`, {
    position: dockPosition,
    heading: 90,
    related_zone_id: state.workZone.id,
  });
  done("Dock");

  state.path = await api.post(`/maps/${state.map.id}/paths/generate`, {
    work_zone_id: state.workZone.id,
    no_go_zone_ids: [state.noGoZone.id],
    dock_id: state.dock.id,
    blade_width: 1,
    overlap_ratio: 0,
    path_angle: 0,
  });
  done("Path");

  state.task = await api.post(`/maps/${state.map.id}/tasks`, {
    path_id: state.path.id,
    work_zone_id: state.workZone.id,
  });
  done("Task");

  state.task = await api.post(`/tasks/${state.task.id}/customer-confirm`, {
    yard_cleared: true,
    allowed_start_time: "09:00",
    allowed_end_time: "12:30",
  });
  done("Confirm");

  state.task = await api.post(`/tasks/${state.task.id}/dispatch`, {});
  done("Dispatch");
  await refreshState();
}

async function simulateRunning() {
  requireTask();
  const point = pathPointAt(3);
  const telemetry = await api.post(`/robots/${robotId}/heartbeat`, {
    task_id: state.task.id,
    position: point,
    battery_level: 86,
    task_status: "RUNNING",
    current_path_index: 3,
    rtk_status: { fix_type: "RTK_FIXED", accuracy: 0.02, is_reliable: true, allowed_to_work: true },
    network_status: "online",
  });
  state.robotPosition = telemetry.position;
  done("Heartbeat");
  await refreshState();
}

async function simulateRtkLoss() {
  requireTask();
  const point = pathPointAt(4);
  const telemetry = await api.post(`/robots/${robotId}/heartbeat`, {
    task_id: state.task.id,
    position: point,
    battery_level: 84,
    task_status: "RUNNING",
    current_path_index: 4,
    rtk_status: { fix_type: "NONE", accuracy: 99, is_reliable: false, allowed_to_work: false },
    network_status: "online",
  });
  state.robotPosition = telemetry.position;
  done("RTK pause");
  await refreshState();
}

async function refreshState() {
  if (state.map) {
    const tasks = await api.get(`/maps/${state.map.id}/tasks`);
    state.task = tasks.at(-1) || state.task;
  }
  if (state.task) {
    state.events = await api.get(`/tasks/${state.task.id}/events`);
  }
  if (state.path) {
    state.telemetry = await api.get(`/robots/${robotId}/telemetry`);
    const latest = state.telemetry.at(-1);
    if (latest) state.robotPosition = latest.position;
  }
  render();
}

function pathPointAt(index) {
  return state.path?.path_points?.[index] || dockPosition;
}

function requireTask() {
  if (!state.task || !state.path) throw new Error("Run setup first.");
}

async function withBusy(action) {
  setButtons(true);
  try {
    await action();
  } catch (error) {
    logError(error);
  } finally {
    setButtons(false);
    render();
  }
}

function done(step) {
  state.completedSteps.add(step);
  renderSteps();
}

function setButtons(disabled) {
  [elements.runSetup, elements.simulateRun, elements.simulateRtk, elements.refreshState].forEach((button) => {
    button.disabled = disabled;
  });
}

function render() {
  renderFacts();
  renderEvents();
  drawMap(elements.canvas, {
    ...state,
    workZone: state.workZone?.polygon_coordinates || workZone,
    noGoZone: state.noGoZone?.polygon_coordinates || noGoZone,
  });
}

function renderSteps() {
  elements.steps.innerHTML = flowSteps.map((step, index) => {
    const doneClass = state.completedSteps.has(step) ? " done" : "";
    const marker = state.completedSteps.has(step) ? "✓" : index + 1;
    return `<div class="step${doneClass}"><i>${marker}</i><span>${step}</span></div>`;
  }).join("");
}

function renderFacts() {
  const taskRows = [
    ["Status", state.task?.status || "Not started"],
    ["Confirm", state.task?.customer_confirmation_status || "-"],
    ["Progress", state.task ? `${state.task.progress_percent}%` : "-"],
    ["Window", state.task?.allowed_start_time ? `${state.task.allowed_start_time} - ${state.task.allowed_end_time}` : "-"],
  ];
  const idRows = [
    ["Property", state.property?.id || "-"],
    ["Map", state.map?.id || "-"],
    ["Work", state.workZone?.id || "-"],
    ["No-go", state.noGoZone?.id || "-"],
    ["Dock", state.dock?.id || "-"],
    ["Path", state.path?.id || "-"],
    ["Task", state.task?.id || "-"],
  ];
  elements.taskFacts.innerHTML = factsHtml(taskRows);
  elements.idFacts.innerHTML = factsHtml(idRows);
}

function renderEvents() {
  elements.eventLog.innerHTML = state.events.length
    ? state.events.map((event) => `<li><strong>${event.event_type}</strong><br>${event.message}</li>`).join("")
    : "<li>No events yet</li>";
}

function factsHtml(rows) {
  return rows.map(([label, value]) => `<dt>${label}</dt><dd>${value}</dd>`).join("");
}

function logError(error) {
  state.events = [{
    event_type: "DEMO_ERROR",
    message: error.message,
  }, ...state.events];
}
