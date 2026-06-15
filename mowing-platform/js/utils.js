// Utility functions and shared state / 工具函数和共享状态
let orders = [];
let workers = [];
let selectedId = "";
let storeMeta = { mode: "fallback", databaseEnabled: false, error: null };
let activeView = "orders";
let selectedArchiveOrderIds = new Set();

const orderList = document.getElementById("orderList");
const detailBody = document.getElementById("detailBody");
const detailStatus = document.getElementById("detailStatus");
const searchInput = document.getElementById("searchInput");
const statusFilter = document.getElementById("statusFilter");
const dataMode = document.getElementById("dataMode");
const dataHint = document.getElementById("dataHint");
const orderModal = document.getElementById("orderModal");
const createOrderForm = document.getElementById("createOrderForm");
const workerModal = document.getElementById("workerModal");
const workerProfileForm = document.getElementById("workerProfileForm");
const workersView = document.getElementById("workersView");
const ordersView = document.getElementById("ordersView");
const dispatchView = document.getElementById("dispatchView");
const archiveView = document.getElementById("archiveView");
const acceptanceView = document.getElementById("acceptanceView");
const metricsSection = document.getElementById("metricsSection");
const opsDashboard = document.getElementById("opsDashboard");
const pageTitle = document.getElementById("pageTitle");
const pageSubtitle = document.getElementById("pageSubtitle");
const priorityFilter = document.getElementById("priorityFilter");
const opsTagFilter = document.getElementById("opsTagFilter");
const dispatchStatusFilter = document.getElementById("dispatchStatusFilter");
const dispatchAreaFilter = document.getElementById("dispatchAreaFilter");
const dispatchPriorityFilter = document.getElementById("dispatchPriorityFilter");
const dispatchOpsTagFilter = document.getElementById("dispatchOpsTagFilter");
const dispatchSortFilter = document.getElementById("dispatchSortFilter");
const dispatchDateFilter = document.getElementById("dispatchDateFilter");
const archiveSearchInput = document.getElementById("archiveSearchInput");
const archiveWorkerFilter = document.getElementById("archiveWorkerFilter");
const archiveSettlementFilter = document.getElementById("archiveSettlementFilter");
const archiveDateFilter = document.getElementById("archiveDateFilter");
const archiveMinAmount = document.getElementById("archiveMinAmount");
const archiveMaxAmount = document.getElementById("archiveMaxAmount");
const archiveSelectAll = document.getElementById("archiveSelectAll");
const archiveExportBtn = document.getElementById("archiveExportBtn");
const archiveBatchSettleBtn = document.getElementById("archiveBatchSettleBtn");

function parseRequestedWindow(requestedTime) {
  const value = String(requestedTime || "").trim();
  const rangeMatch = value.match(/^(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})(?::\d{2})?-(\d{2}:\d{2})(?::\d{2})?$/);
  if (rangeMatch) {
    const [, date, start, end] = rangeMatch;
    return { date, start, end, label: `${start}-${end}` };
  }
  const pointMatch = value.match(/^(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})(?::\d{2})?$/);
  if (pointMatch) {
    const [, date, start] = pointMatch;
    return { date, start, end: start, label: start };
  }
  return { date: value.slice(0, 10), start: "", end: "", label: value || "待确认时段" };
}

function timeToMinutes(text) {
  if (!text) return null;
  const [hour, minute] = text.split(":").map(Number);
  if (Number.isNaN(hour) || Number.isNaN(minute)) return null;
  return hour * 60 + minute;
}

function buildConflictInfo(order, scheduledOrder) {
  const currentWindow = parseRequestedWindow(order.requestedTime);
  const scheduledWindow = parseRequestedWindow(scheduledOrder.requestedTime);
  if (!currentWindow.date || !scheduledWindow.date || currentWindow.date !== scheduledWindow.date) {
    return null;
  }
  const currentStart = timeToMinutes(currentWindow.start);
  const currentEnd = timeToMinutes(currentWindow.end);
  const scheduledStart = timeToMinutes(scheduledWindow.start);
  const scheduledEnd = timeToMinutes(scheduledWindow.end);
  const hasTimeRange =
    currentStart !== null && currentEnd !== null && scheduledStart !== null && scheduledEnd !== null;
  if (hasTimeRange) {
    if (currentStart <= scheduledEnd && scheduledStart <= currentEnd) {
      return {
        orderId: scheduledOrder.id,
        label: `${scheduledOrder.id} ${scheduledWindow.label}`.trim(),
      };
    }
    return null;
  }
  if (currentWindow.label && scheduledWindow.label && currentWindow.label === scheduledWindow.label) {
    return {
      orderId: scheduledOrder.id,
      label: `${scheduledOrder.id} ${scheduledWindow.label}`.trim(),
    };
  }
  return null;
}

function workerConflicts(order, workerId) {
  return orders
    .filter((scheduledOrder) => scheduledOrder.id !== order.id)
    .filter((scheduledOrder) => scheduledOrder.assignedWorkerId === workerId)
    .filter(
      (scheduledOrder) =>
        scheduledOrder.status === "assigned" || scheduledOrder.status === "accepted_by_worker",
    )
    .map((scheduledOrder) => buildConflictInfo(order, scheduledOrder))
    .filter(Boolean);
}

function orderDate(order) {
  return String(order.requestedTime || "").slice(0, 10);
}

function orderArea(order) {
  const address = `${order.address || ""} ${order.condition || ""}`.toLowerCase();
  if (address.includes("mt eden") || address.includes("epsom")) return "Mt Eden / Epsom";
  if (address.includes("north shore") || address.includes("albany")) return "North Shore";
  if (address.includes("henderson") || address.includes("westgate")) return "Henderson / Westgate";
  if (address.includes("howick") || address.includes("botany")) return "Howick / Botany";
  return "待人工判断";
}

function orderPriority(order) {
  if (order.status === "pending_review") return "待报价";
  if (order.status === "quoted") return "待派单";
  if (order.status === "assigned") return "待服务商确认";
  if (order.status === "accepted_by_worker") return "已确认待上门";
  if (order.status === "in_service") return "服务进行中";
  if (order.status === "pending_quality_review") return "待平台审核";
  if (order.status === "exception_open") return "异常待处理";
  if (order.status === "completed") return "已完成待归档";
  return statusLabels[order.status] || "待处理";
}

function normalizedPriority(level) {
  return level || "normal";
}

function priorityWeight(level) {
  const weights = {
    urgent: 0,
    high: 1,
    normal: 2,
    low: 3,
  };
  return weights[normalizedPriority(level)] ?? weights.normal;
}

function orderSortKey(order) {
  return `${orderDate(order)} ${order.requestedTime || ""}`;
}

function orderTag(order) {
  return (order.opsTag || "").trim();
}

function exceptionSummary(order) {
  if (!order.exceptionType && !order.exceptionNote) return "当前无异常";
  const parts = [order.exceptionType || "现场异常"];
  if (order.exceptionNote) parts.push(order.exceptionNote);
  return parts.join(" / ");
}

function populateTagFilter(selectElement, currentValue, includeUntaggedLabel = false) {
  const tags = [...new Set(orders.map((order) => orderTag(order)).filter(Boolean))].sort((a, b) =>
    a.localeCompare(b, "zh-CN"),
  );
  const options = [`<option value="all">全部运营标签</option>`];
  if (includeUntaggedLabel) {
    options.push(`<option value="__untagged__">未标记</option>`);
  }
  options.push(...tags.map((tag) => `<option value="${tag}">${tag}</option>`));
  selectElement.innerHTML = options.join("");
  const values = new Set(["all", ...(includeUntaggedLabel ? ["__untagged__"] : []), ...tags]);
  selectElement.value = values.has(currentValue) ? currentValue : "all";
}

function suggestWorkers(order) {
  const area = orderArea(order);
  const assigned = order.assignedWorkerId;
  const candidates = workers.filter((worker) => worker.available || worker.id === assigned);
  const matched = candidates.filter((worker) => worker.area === area);
  return (matched.length ? matched : candidates).slice(0, 3);
}

let workerSuggestCache = null;

async function suggestWorkersByDistance(address) {
  if (!address || address.trim().length < 3) return null;
  try {
    const result = await request("/api/workers/suggest", {
      method: "POST",
      body: JSON.stringify({ q: address }),
    });
    workerSuggestCache = result;
    return result;
  } catch (_err) {
    return null;
  }
}

function workerDistance(workerId) {
  if (!workerSuggestCache) return null;
  const w = workerSuggestCache.workers.find((item) => item.id === workerId);
  return w ? w.distance_km : null;
}

function formatDistance(km) {
  if (km === null || km === undefined) return "";
  if (km < 1) return `${(km * 1000).toFixed(0)}m`;
  return `${km}km`;
}

