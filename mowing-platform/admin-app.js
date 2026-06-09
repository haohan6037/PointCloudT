const statusLabels = {
  pending_review: "待平台确认",
  quoted: "已报价",
  assigned: "已派单",
  accepted_by_worker: "服务商已接单",
  in_service: "服务中",
  pending_quality_review: "待质量审核",
  completed: "已完成",
  exception_open: "异常处理中",
  cancelled: "已取消",
};

const workerApprovalLabels = {
  approved: "已审核",
  probation: "观察中",
  pending_info: "资料待补充",
};

const settlementLabels = {
  pending: "待结算",
  settled: "已结算",
};

const priorityLabels = {
  low: "低优先级",
  normal: "常规",
  high: "优先处理",
  urgent: "紧急",
};

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

// ── Address autocomplete ──

let autocompleteTimer = null;
const AUTOCOMPLETE_DEBOUNCE_MS = 300;

function setupAddressAutocomplete(inputEl, dropdownEl) {
  let activeIndex = -1;

  function hide() {
    dropdownEl.classList.remove("open");
    dropdownEl.innerHTML = "";
    activeIndex = -1;
  }

  function select(item) {
    inputEl.value = item.address;
    hide();
    inputEl.focus();
    // Trigger suggest update for dispatch
    suggestWorkersByDistance(item.address);
  }

  async function fetchSuggestions(query) {
    if (query.length < 3) {
      hide();
      return;
    }
    dropdownEl.innerHTML = '<div class="autocomplete-loading">搜索地址中…</div>';
    dropdownEl.classList.add("open");
    try {
      const results = await request("/api/address/autocomplete", {
        method: "POST",
        body: JSON.stringify({ q: query }),
      });
      if (!results.length) {
        dropdownEl.innerHTML = '<div class="autocomplete-loading">未找到匹配地址</div>';
        return;
      }
      activeIndex = -1;
      dropdownEl.innerHTML = results
        .map(
          (item, idx) =>
            `<button class="autocomplete-item" type="button" data-idx="${idx}">${item.address}</button>`,
        )
        .join("");
      dropdownEl.querySelectorAll(".autocomplete-item").forEach((btn) => {
        btn.addEventListener("mousedown", (e) => {
          e.preventDefault();
          select(results[Number(btn.dataset.idx)]);
        });
      });
    } catch (_err) {
      dropdownEl.innerHTML = '<div class="autocomplete-loading">地址服务暂不可用</div>';
    }
  }

  inputEl.addEventListener("input", () => {
    clearTimeout(autocompleteTimer);
    autocompleteTimer = setTimeout(() => fetchSuggestions(inputEl.value.trim()), AUTOCOMPLETE_DEBOUNCE_MS);
  });

  inputEl.addEventListener("keydown", (e) => {
    const items = dropdownEl.querySelectorAll(".autocomplete-item");
    if (!items.length) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      activeIndex = Math.min(activeIndex + 1, items.length - 1);
      items.forEach((item, idx) => item.classList.toggle("active", idx === activeIndex));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      activeIndex = Math.max(activeIndex - 1, 0);
      items.forEach((item, idx) => item.classList.toggle("active", idx === activeIndex));
    } else if (e.key === "Enter" && activeIndex >= 0) {
      e.preventDefault();
      items[activeIndex].click();
    } else if (e.key === "Escape") {
      hide();
    }
  });

  inputEl.addEventListener("blur", () => {
    setTimeout(hide, 200);
  });
}

function initAutocomplete() {
  const addressInput = document.getElementById("createAddress");
  const addressDropdown = document.getElementById("createAddressDropdown");
  if (addressInput && addressDropdown) {
    setupAddressAutocomplete(addressInput, addressDropdown);
  }
}

function serviceChecklistItems(order) {
  const items = [];
  items.push(`确认上门时间窗：${order.requestedTime || "待确认"}`);
  items.push(`确认联系人与电话：${order.user || "客户"} / ${order.phone || "待补充"}`);
  if (order.note) {
    items.push(`客户提醒：${order.note}`);
  }
  if (order.condition) {
    items.push(`现场重点：${order.condition}`);
  }
  if (order.opsTag) {
    items.push(`运营标签重点：${order.opsTag}`);
  }
  if (normalizedPriority(order.priorityLevel) === "urgent") {
    items.push("这是紧急订单，优先确认出发和到场时间。");
  }
  if ((order.condition || "").includes("树") || (order.opsTag || "").includes("树下")) {
    items.push("提醒服务商重点处理树下和遮挡区域的人工作业。");
  }
  if ((order.condition || "").includes("围栏") || (order.condition || "").includes("边")) {
    items.push("提醒服务商重点处理围栏边、墙边和草坪边缘收尾。");
  }
  return items;
}

function completionNoteTemplate(order) {
  const parts = [];
  if (order.opsTag) {
    parts.push(`已完成 ${order.opsTag}`);
  } else {
    parts.push("已完成本次草坪服务");
  }
  if ((order.condition || "").includes("树") || (order.opsTag || "").includes("树下")) {
    parts.push("已处理树下区域");
  }
  if ((order.condition || "").includes("围栏") || (order.condition || "").includes("边")) {
    parts.push("已处理边缘收尾");
  }
  return `${parts.join("，")}，待平台确认结算。`;
}

function filteredDispatchOrders() {
  const selectedStatus = dispatchStatusFilter.value;
  const selectedArea = dispatchAreaFilter.value;
  const selectedPriority = dispatchPriorityFilter.value;
  const selectedTag = dispatchOpsTagFilter.value;
  const selectedDate = dispatchDateFilter.value;
  const sortMode = dispatchSortFilter.value || "priority_time";
  return orders
    .filter((order) => !["cancelled", "completed"].includes(order.status))
    .filter((order) => {
      if (selectedStatus === "needs_quote") return order.status === "pending_review";
      if (selectedStatus === "needs_assign") return order.status === "quoted";
      if (selectedStatus === "assigned") {
        return order.status === "assigned" || order.status === "accepted_by_worker";
      }
      if (selectedStatus === "in_service") return order.status === "in_service";
      if (selectedStatus === "pending_quality_review") return order.status === "pending_quality_review";
      if (selectedStatus === "exception_open") return order.status === "exception_open";
      return true;
    })
    .filter((order) => selectedArea === "all" || orderArea(order) === selectedArea)
    .filter((order) => selectedPriority === "all" || normalizedPriority(order.priorityLevel) === selectedPriority)
    .filter((order) => {
      if (selectedTag === "all") return true;
      if (selectedTag === "__untagged__") return !orderTag(order);
      return orderTag(order) === selectedTag;
    })
    .filter((order) => !selectedDate || orderDate(order) === selectedDate)
    .sort((a, b) => {
      const byPriority = priorityWeight(a.priorityLevel) - priorityWeight(b.priorityLevel);
      const byTime = orderSortKey(a).localeCompare(orderSortKey(b));
      return sortMode === "time_priority" ? byTime || byPriority : byPriority || byTime;
    });
}

function renderDispatchSummary(items) {
  const summary = [
    { label: "待报价", value: orders.filter((order) => order.status === "pending_review").length },
    { label: "待派单", value: orders.filter((order) => order.status === "quoted").length },
    {
      label: "今日已排",
      value: orders.filter(
        (order) =>
          ["assigned", "accepted_by_worker", "in_service"].includes(order.status) &&
          orderDate(order) === dispatchDateFilter.value,
      ).length,
    },
    { label: "今日完成", value: orders.filter((order) => order.status === "completed").length },
    { label: "可接单服务商", value: workers.filter((worker) => worker.available).length },
  ];
  document.getElementById("dispatchSummary").innerHTML = summary
    .map(
      (item) => `
        <article class="metric">
          <span>${item.label}</span>
          <strong>${item.value}</strong>
        </article>
      `,
    )
    .join("");
  document.getElementById("dispatchResultCount").textContent = `${items.length} 单`;
}

function renderDispatchOrders(items) {
  const target = document.getElementById("dispatchOrderList");
  if (!items.length) {
    target.innerHTML = `<div class="empty">当前筛选下没有需要处理的订单</div>`;
    return;
  }
  target.innerHTML = items
    .map((order) => {
      const candidates = suggestWorkers(order);
      const disabledAssign = !order.price;
      const candidateConflicts = candidates
        .map((worker) => ({
          worker,
          conflicts: workerConflicts(order, worker.id),
        }))
        .filter((item) => item.conflicts.length);
      return `
        <article class="dispatch-card">
          <header>
            <div>
              <h4>${order.id} · ${order.user}</h4>
              <p>${order.address}</p>
            </div>
            <span class="badge ${order.status}">${orderPriority(order)}</span>
          </header>
          <div class="dispatch-grid">
            <span>预约时间</span><strong>${order.requestedTime}</strong>
            <span>区域判断</span><strong>${orderArea(order)}</strong>
            <span>优先级</span><strong>${priorityLabel(order.priorityLevel)}</strong>
            <span>运营标签</span><strong>${orderTag(order) || "未标记"}</strong>
            <span>当前报价</span><strong>${money(order.price)}</strong>
            <span>已派服务商</span><strong>${workerName(order.assignedWorkerId)}</strong>
          </div>
          <div>
            <div class="suggestion-row">
              ${candidates
                .map((worker) => {
                  const dist = workerDistance(worker.id);
                  const distText = dist !== null ? ` ${formatDistance(dist)}` : "";
                  return `<span class="suggestion-chip">${worker.name} · ${worker.area}${distText}</span>`;
                })
                .join("")}
            </div>
          </div>
          ${
            candidateConflicts.length
              ? `
                <div class="dispatch-hint conflict">
                  时间冲突提醒：${candidateConflicts
                    .map(
                      (item) =>
                        `${item.worker.name} 已有 ${item.conflicts.map((conflict) => conflict.label).join("、")}`,
                    )
                    .join("；")}
                </div>
              `
              : `<div class="dispatch-hint">当前建议服务商在该时段没有发现已排冲突。</div>`
          }
          <div class="dispatch-actions">
            <div class="field">
              <label for="dispatchAssign-${order.id}">快速派单</label>
              <select class="select" id="dispatchAssign-${order.id}" data-dispatch-select="${order.id}">
                <option value="">请选择服务商</option>
                ${candidates
                  .map(
                    (worker) => {
                      const dist = workerDistance(worker.id);
                      const distText = dist !== null ? ` (${formatDistance(dist)})` : "";
                      return `
                        <option value="${worker.id}" ${worker.id === order.assignedWorkerId ? "selected" : ""}>
                          ${worker.name} · ${worker.area}${distText}
                        </option>
                      `;
                    },
                  )
                  .join("")}
              </select>
            </div>
            <button class="btn primary" type="button" data-dispatch-assign="${order.id}" ${disabledAssign ? "disabled" : ""}>
              保存派单
            </button>
          </div>
          <div class="worker-actions">
            ${order.status === "assigned" ? `<button class="btn" type="button" data-dispatch-status="${order.id}" data-next-status="accepted_by_worker">标记已接单</button>` : ""}
            ${order.status === "accepted_by_worker" ? `<button class="btn" type="button" data-dispatch-status="${order.id}" data-next-status="in_service">标记服务中</button>` : ""}
            ${order.status === "in_service" ? `<button class="btn primary" type="button" data-dispatch-status="${order.id}" data-next-status="pending_quality_review">提交待审核</button>` : ""}
          </div>
          <div class="dispatch-hint">
            ${disabledAssign ? "还没有报价，先在订单详情保存价格后再派单。" : "派单后可以继续推进到“已接单”、“服务中”和“待质量审核”。"}
          </div>
        </article>
      `;
    })
    .join("");

  target.querySelectorAll("[data-dispatch-assign]").forEach((button) => {
    button.addEventListener("click", async () => {
      const orderId = button.dataset.dispatchAssign;
      const select = document.querySelector(`[data-dispatch-select="${orderId}"]`);
      if (!select.value) {
        alert("请先选择服务商。");
        return;
      }
      const order = orders.find((item) => item.id === orderId);
      const conflicts = workerConflicts(order, select.value);
      if (conflicts.length) {
        const confirmed = window.confirm(
          `该服务商在同时间段已有：${conflicts.map((conflict) => conflict.label).join("、")}。仍然继续派单吗？`,
        );
        if (!confirmed) {
          return;
        }
      }
      try {
        const payload = await request(`/api/orders/${orderId}/assign`, {
          method: "POST",
          body: JSON.stringify({ workerId: select.value }),
        });
        hydrate(payload);
      } catch (error) {
        alert(error.message);
      }
    });
  });

  target.querySelectorAll("[data-dispatch-status]").forEach((button) => {
    button.addEventListener("click", async () => {
      try {
        const payload = await request(`/api/orders/${button.dataset.dispatchStatus}/status`, {
          method: "POST",
          body: JSON.stringify({ status: button.dataset.nextStatus }),
        });
        hydrate(payload);
      } catch (error) {
        alert(error.message);
      }
    });
  });
}

function renderDispatchSchedules(items) {
  const target = document.getElementById("dispatchScheduleList");
  const dateLabel = dispatchDateFilter.value || "全部日期";
  document.getElementById("scheduleCaption").textContent = `${dateLabel} · ${items.length} 单`;
  const jobsByWorker = workers.map((worker) => {
    const jobs = orders
      .filter((order) => order.assignedWorkerId === worker.id)
      .filter((order) => ["assigned", "accepted_by_worker", "in_service"].includes(order.status))
      .filter((order) => !dispatchDateFilter.value || orderDate(order) === dispatchDateFilter.value)
      .sort((a, b) => `${orderDate(a)} ${a.requestedTime}`.localeCompare(`${orderDate(b)} ${b.requestedTime}`));
    return { worker, jobs };
  });

  target.innerHTML = jobsByWorker
    .map(({ worker, jobs }) => {
      const conflictingOrderIds = new Set();
      jobs.forEach((job, index) => {
        jobs.slice(index + 1).forEach((otherJob) => {
          if (buildConflictInfo(job, otherJob)) {
            conflictingOrderIds.add(job.id);
            conflictingOrderIds.add(otherJob.id);
          }
        });
      });
      return `
        <article class="schedule-card">
          <header>
            <div>
              <h4>${worker.name}</h4>
              <p>${worker.area}</p>
            </div>
            <span class="worker-badge ${worker.available ? "available" : "unavailable"}">
              ${worker.available ? "可接单" : "暂停接单"}
            </span>
          </header>
          <div class="schedule-grid">
            <span>今日任务</span><strong>${jobs.length} 单</strong>
            <span>联系电话</span><strong>${worker.phone || "待补充"}</strong>
          </div>
          ${
            conflictingOrderIds.size
              ? `<div class="dispatch-hint conflict">当前日程里有时间重叠，请优先调整 ${[...conflictingOrderIds].join("、")}。</div>`
              : ""
          }
          <div class="schedule-jobs">
            ${
              jobs.length
                ? jobs
                    .map(
                      (order) => `
                        <div class="schedule-job ${conflictingOrderIds.has(order.id) ? "conflict" : ""}">
                          <strong>${order.id} · ${order.user}</strong>
                          <span>${order.requestedTime}</span>
                          <span>${priorityLabel(order.priorityLevel)}${orderTag(order) ? ` · ${orderTag(order)}` : ""}</span>
                          <span>${statusLabels[order.status]}</span>
                          <span>${order.address}</span>
                        </div>
                      `,
                    )
                    .join("")
                : `<div class="dispatch-hint">当前筛选下没有已安排任务，可优先派新单。</div>`
            }
          </div>
        </article>
      `;
    })
    .join("");
}

function populateDispatchAreaFilter() {
  const current = dispatchAreaFilter.value || "all";
  const areas = [...new Set([...workers.map((worker) => worker.area), ...orders.map((order) => orderArea(order))])];
  dispatchAreaFilter.innerHTML = [
    `<option value="all">全部区域</option>`,
    ...areas.filter(Boolean).sort().map((area) => `<option value="${area}">${area}</option>`),
  ].join("");
  dispatchAreaFilter.value = areas.includes(current) ? current : "all";
}

function renderDispatchView() {
  populateDispatchAreaFilter();
  populateTagFilter(dispatchOpsTagFilter, dispatchOpsTagFilter.value, true);
  if (!dispatchDateFilter.value) {
    dispatchDateFilter.value = orders[0] ? orderDate(orders[0]) : "";
  }
  const items = filteredDispatchOrders();
  renderDispatchSummary(items);
  renderDispatchOrders(items);
  renderDispatchSchedules(items);
}

function populateArchiveWorkerFilter() {
  const current = archiveWorkerFilter.value || "all";
  archiveWorkerFilter.innerHTML = [
    `<option value="all">全部服务商</option>`,
    ...workers.map((worker) => `<option value="${worker.id}">${worker.name}</option>`),
  ].join("");
  archiveWorkerFilter.value = workers.some((worker) => worker.id === current) ? current : "all";
}

function filteredArchivedOrders() {
  const keyword = archiveSearchInput.value.trim().toLowerCase();
  const workerId = archiveWorkerFilter.value;
  const settlement = archiveSettlementFilter.value;
  const date = archiveDateFilter.value;
  const minAmount = Number(archiveMinAmount.value || 0);
  const maxAmount = archiveMaxAmount.value ? Number(archiveMaxAmount.value) : null;
  return orders
    .filter((order) => order.status === "completed")
    .filter((order) => workerId === "all" || order.assignedWorkerId === workerId)
    .filter((order) => settlement === "all" || (order.settlementStatus || "pending") === settlement)
    .filter((order) => !date || orderDate(order) === date)
    .filter((order) => archiveAmountValue(order) >= minAmount)
    .filter((order) => maxAmount === null || archiveAmountValue(order) <= maxAmount)
    .filter((order) => {
      const source = `${order.id} ${order.user} ${order.address}`.toLowerCase();
      return !keyword || source.includes(keyword);
    })
    .sort((a, b) => `${orderDate(b)} ${b.updatedAt}`.localeCompare(`${orderDate(a)} ${a.updatedAt}`));
}

function renderArchiveSummary(items) {
  const totalRevenue = items.reduce((sum, order) => sum + archiveAmountValue(order), 0);
  const totalPlatformShare = items.reduce((sum, order) => sum + Number(order.platformShare || 0), 0);
  const totalWorkerPayout = items.reduce((sum, order) => sum + Number(order.workerPayout || 0), 0);
  const uniqueWorkers = new Set(items.map((order) => order.assignedWorkerId).filter(Boolean)).size;
  const pendingSettlement = items.filter((order) => (order.settlementStatus || "pending") !== "settled").length;
  const summary = [
    { label: "已完成订单", value: items.length },
    { label: "已完成金额", value: money(totalRevenue).replace(".00", "") },
    { label: "平台分成", value: money(totalPlatformShare).replace(".00", "") },
    { label: "服务商应结", value: money(totalWorkerPayout).replace(".00", "") },
    { label: "待结算", value: pendingSettlement },
    { label: "参与服务商", value: uniqueWorkers },
  ];
  document.getElementById("archiveSummary").innerHTML = summary
    .map(
      (item) => `
        <article class="metric">
          <span>${item.label}</span>
          <strong>${item.value}</strong>
        </article>
      `,
    )
    .join("");
  document.getElementById("archiveResultCount").textContent = `${items.length} 单`;
}

function renderArchiveOrders(items) {
  const target = document.getElementById("archiveOrderList");
  syncArchiveSelection(items);
  renderArchiveSelectionSummary(items);
  if (!items.length) {
    target.innerHTML = `<div class="empty">当前筛选下还没有已完成订单</div>`;
    return;
  }
  target.innerHTML = items
    .map((order) => `
      <article class="archive-card ${selectedArchiveOrderIds.has(order.id) ? "selected" : ""} ${order.settlementStatus === "settled" ? "" : "pending"}">
        <header>
          <div>
            <h4>${order.id} · ${order.user}</h4>
            <p>${order.address}</p>
          </div>
          <div class="worker-actions">
            <span class="badge completed">已完成</span>
            <span class="worker-badge ${order.settlementStatus === "settled" ? "available" : "probation"}">
              ${settlementLabel(order.settlementStatus)}
            </span>
          </div>
        </header>
        <label class="order-meta">
          <input type="checkbox" data-archive-select="${order.id}" ${selectedArchiveOrderIds.has(order.id) ? "checked" : ""} />
          <span>加入本次批量结算</span>
        </label>
        <div class="archive-grid">
          <span>完成时间</span><strong>${order.updatedAt}</strong>
          <span>服务商</span><strong>${workerName(order.assignedWorkerId)}</strong>
          <span>报价金额</span><strong>${money(order.price)}</strong>
          <span>实收金额</span><strong>${archiveAmountDisplay(order)}</strong>
          <span>平台分成</span><strong>${payoutDisplay(order.platformShare)}</strong>
          <span>服务商应结</span><strong>${payoutDisplay(order.workerPayout)}</strong>
          <span>预约时间</span><strong>${order.requestedTime}</strong>
          <span>结算时间</span><strong>${order.settledAt || "未结算"}</strong>
          <span>完成备注</span><strong>${order.completionNote || "待补充"}</strong>
          <span>待结算原因</span><strong>${settlementPendingReason(order)}</strong>
        </div>
        <div class="form-grid archive-form">
          <div class="field">
            <label for="archiveActualAmount-${order.id}">实收金额 NZD</label>
            <input class="input" id="archiveActualAmount-${order.id}" type="number" min="0" step="0.01" value="${order.actualAmount || ""}" placeholder="${order.price || "0"}" />
          </div>
          <div class="field">
            <label for="archiveSettlementStatus-${order.id}">结算状态</label>
            <select class="select" id="archiveSettlementStatus-${order.id}">
              <option value="pending" ${order.settlementStatus !== "settled" ? "selected" : ""}>待结算</option>
              <option value="settled" ${order.settlementStatus === "settled" ? "selected" : ""}>已结算</option>
            </select>
          </div>
          <div class="field full">
            <label for="archiveCompletionNote-${order.id}">完成备注</label>
            <textarea class="textarea" id="archiveCompletionNote-${order.id}">${order.completionNote || ""}</textarea>
          </div>
          <div class="field">
            <label for="archivePlatformShare-${order.id}">平台分成 NZD</label>
            <input class="input" id="archivePlatformShare-${order.id}" type="number" min="0" step="0.01" value="${order.platformShare || ""}" />
          </div>
          <div class="field">
            <label for="archiveWorkerPayout-${order.id}">服务商应结 NZD</label>
            <input class="input" id="archiveWorkerPayout-${order.id}" type="number" min="0" step="0.01" value="${order.workerPayout || ""}" />
          </div>
          <div class="field full">
            <label>结算建议</label>
            <div class="dispatch-hint">${buildSettlementSuggestion(order).reason}</div>
          </div>
          <div class="inline-actions">
            <button class="btn" type="button" data-archive-suggest="${order.id}">自动填充建议</button>
            <button class="btn primary" type="button" data-archive-save="${order.id}">保存归档</button>
          </div>
        </div>
      </article>
    `)
    .join("");

  target.querySelectorAll("[data-archive-save]").forEach((button) => {
    button.addEventListener("click", async () => {
      try {
        await saveCompletion(button.dataset.archiveSave);
      } catch (error) {
        alert(error.message);
      }
    });
  });

  target.querySelectorAll("[data-archive-suggest]").forEach((button) => {
    button.addEventListener("click", () => {
      applySettlementSuggestionToArchive(button.dataset.archiveSuggest);
    });
  });

  target.querySelectorAll("[data-archive-select]").forEach((checkbox) => {
    checkbox.addEventListener("change", () => {
      if (checkbox.checked) {
        selectedArchiveOrderIds.add(checkbox.dataset.archiveSelect);
      } else {
        selectedArchiveOrderIds.delete(checkbox.dataset.archiveSelect);
      }
      renderArchiveSelectionSummary(items);
      target
        .querySelector(`[data-archive-select="${checkbox.dataset.archiveSelect}"]`)
        ?.closest(".archive-card")
        ?.classList.toggle("selected", checkbox.checked);
    });
  });
}

function renderArchiveRanking(items) {
  const target = document.getElementById("archiveRankingList");
  document.getElementById("archiveRankingCaption").textContent = archiveDateFilter.value || "全部完成日期";
  const ranking = workers
    .map((worker) => {
      const workerOrders = items.filter((order) => order.assignedWorkerId === worker.id);
      const total = workerOrders.reduce((sum, order) => sum + archiveAmountValue(order), 0);
      return { worker, count: workerOrders.length, total };
    })
    .filter((item) => item.count > 0)
    .sort((a, b) => b.count - a.count || b.total - a.total);
  if (!ranking.length) {
    target.innerHTML = `<div class="empty">当前筛选下还没有可统计的完成记录</div>`;
    return;
  }
  target.innerHTML = ranking
    .map(
      (item, index) => `
        <article class="archive-rank">
          <header>
            <div>
              <h4>${index + 1}. ${item.worker.name}</h4>
              <p>${item.worker.area}</p>
            </div>
            <span class="worker-badge available">${item.count} 单</span>
          </header>
          <div class="archive-grid">
            <span>完成单量</span><strong>${item.count}</strong>
            <span>完成金额</span><strong>${money(item.total).replace(".00", "")}</strong>
            <span>联系电话</span><strong>${item.worker.phone || "待补充"}</strong>
          </div>
        </article>
      `,
    )
    .join("");
}

function renderArchiveView() {
  populateArchiveWorkerFilter();
  const items = filteredArchivedOrders();
  renderArchiveSummary(items);
  renderArchiveOrders(items);
  renderArchiveRanking(items);
}

function syncArchiveSelection(items) {
  const visibleIds = new Set(items.map((order) => order.id));
  selectedArchiveOrderIds.forEach((id) => {
    if (!visibleIds.has(id)) {
      selectedArchiveOrderIds.delete(id);
    }
  });
}

function renderArchiveSelectionSummary(items) {
  const selectedVisibleCount = items.filter((order) => selectedArchiveOrderIds.has(order.id)).length;
  document.getElementById("archiveSelectionCount").textContent = `已选 ${selectedVisibleCount} 单`;
  archiveSelectAll.checked = !!items.length && selectedVisibleCount === items.length;
  archiveSelectAll.indeterminate = selectedVisibleCount > 0 && selectedVisibleCount < items.length;
  archiveBatchSettleBtn.disabled = selectedVisibleCount === 0;
}

function money(value) {
  if (value === "" || value === null || value === undefined) {
    return "未报价";
  }
  return `$${Number(value).toLocaleString("en-NZ")}`;
}

function archiveAmountValue(order) {
  return Number(order.actualAmount || order.price || 0);
}

function archiveAmountDisplay(order) {
  if (order.actualAmount) {
    return money(order.actualAmount);
  }
  if (order.price) {
    return `${money(order.price)}（按报价）`;
  }
  return "待录入";
}

function settlementLabel(status) {
  return settlementLabels[status] || "待结算";
}

function priorityLabel(level) {
  return priorityLabels[level] || "常规";
}

function payoutDisplay(value) {
  return value ? money(value) : "待录入";
}

function settlementBaseAmount(order, overrideActualAmount = "") {
  const raw = overrideActualAmount !== "" ? overrideActualAmount : order.actualAmount || order.price || 0;
  return Number(raw || 0);
}

function buildSettlementSuggestion(order, overrideActualAmount = "") {
  const baseAmount = settlementBaseAmount(order, overrideActualAmount);
  if (!baseAmount) {
    return {
      platformShare: "",
      workerPayout: "",
      reason: "还没有实收金额或报价，暂时无法生成结算建议。",
    };
  }
  const rate = order.opsTag && order.opsTag.includes("定期") ? 0.15 : 0.2;
  const platformShare = (Math.round(baseAmount * rate * 100) / 100).toFixed(2);
  const workerPayout = (Math.round((baseAmount - Number(platformShare)) * 100) / 100).toFixed(2);
  return {
    platformShare,
    workerPayout,
    reason: `${rate === 0.15 ? "定期客户" : "标准订单"}默认按 ${(rate * 100).toFixed(0)}% 平台分成估算。`,
  };
}

function settlementPendingReason(order) {
  if ((order.settlementStatus || "pending") === "settled") return "已完成结算。";
  if (!archiveAmountValue(order)) return "缺少实收金额，先补金额再结算。";
  if (!order.platformShare || !order.workerPayout) return "还没确认平台分成或服务商应结。";
  if (!order.completionNote) return "还没补完成备注，建议先补现场结果。";
  return "资料已基本齐全，可直接结算。";
}

function parseActivityItem(item) {
  const match = String(item || "").match(/^(\d{4}-\d{2}-\d{2} \d{2}:\d{2})\s+\|\s+(.+)$/);
  if (match) {
    return { time: match[1], message: match[2] };
  }
  return { time: "历史记录", message: String(item || "") };
}

function serviceTodoItems(order) {
  const baseItems = {
    pending_review: [
      { title: "先完成报价", detail: "确认草坪情况、边角复杂度和可服务时间窗。" },
    ],
    quoted: [
      { title: "安排服务商", detail: "结合区域、优先级和运营标签完成派单。" },
      { title: "确认上门条件", detail: "确认入场方式、宠物、树下和围栏边等人工收尾点。" },
    ],
    assigned: [
      { title: "等待接单确认", detail: "服务商确认前，优先检查是否存在时间冲突。" },
      { title: "补上门前提醒", detail: "将门禁、停车和重点收尾区域同步给服务商。" },
    ],
    accepted_by_worker: [
      { title: "记录上门前确认", detail: "确认出发时间、联系人和机器人覆盖范围。" },
      { title: "到场后切服务中", detail: "服务开始后及时推进到“服务中”。" },
    ],
    in_service: [
      { title: "补服务中记录", detail: "记录边缘、树下、墙边等人工处理情况。" },
      { title: "提交平台审核", detail: "完工后先提交待质量审核，再由平台决定通过或补做。" },
    ],
    pending_quality_review: [
      { title: "平台审核结果", detail: "查看审核意见，等待平台通过、打回补做或转异常处理。" },
      { title: "保留现场说明", detail: "必要时补充服务记录，避免后续争议。" },
    ],
    exception_open: [
      { title: "等待异常处理", detail: "平台需要确认处理方案，再决定恢复服务、继续审核或关闭订单。" },
      { title: "补充证据说明", detail: "把现场情况、客户反馈和处理意见记录到时间线。" },
    ],
    completed: [
      { title: "完成归档", detail: "补齐实收、平台分成、服务商应结和完成备注。" },
      { title: "确认后续跟进", detail: "定期客户可补运营标签或安排下一次服务。" },
    ],
    cancelled: [{ title: "等待重新预约", detail: "如客户改期，后续创建新单继续跟进。" }],
  };
  return baseItems[order.status] || [{ title: "人工判断下一步", detail: "当前状态需要运营进一步确认。" }];
}

function defaultServiceLogStage(order) {
  if (order.status === "accepted_by_worker") return "pre_visit";
  if (order.status === "in_service") return "service_note";
  if (order.status === "exception_open") return "service_note";
  if (order.status === "pending_quality_review") return "completion_followup";
  if (order.status === "completed") return "completion_followup";
  return "arrival";
}

function workerOrders(workerId) {
  return orders.filter((order) => order.assignedWorkerId === workerId);
}

function workerActiveOrders(workerId) {
  return workerOrders(workerId)
    .filter((order) => ["assigned", "accepted_by_worker", "in_service", "pending_quality_review", "completed", "exception_open"].includes(order.status))
    .sort((a, b) => orderSortKey(a).localeCompare(orderSortKey(b)));
}

function workerLaneItems(workerId) {
  const items = workerActiveOrders(workerId);
  return {
    waitingDeparture: items.filter((order) => ["assigned", "accepted_by_worker"].includes(order.status)),
    inService: items.filter((order) => order.status === "in_service"),
    waitingWrapup: items.filter(
      (order) =>
        order.status === "pending_quality_review" ||
        order.status === "exception_open" ||
        (order.status === "completed" && (order.settlementStatus || "pending") !== "settled"),
    ),
  };
}

function workerSummary(workerId) {
  const items = workerActiveOrders(workerId);
  return {
    activeCount: items.filter((order) => ["assigned", "accepted_by_worker", "in_service"].includes(order.status)).length,
    completedPendingSettle: items.filter(
      (order) => order.status === "completed" && (order.settlementStatus || "pending") !== "settled",
    ).length,
    urgentCount: items.filter((order) => normalizedPriority(order.priorityLevel) === "urgent").length,
    totalRevenue: items.reduce((sum, order) => sum + Number(order.price || 0), 0),
  };
}

function workerTaskPrimaryAction(order) {
  if (order.status === "assigned") {
    return { action: "accept", label: "标记已接单" };
  }
  if (order.status === "accepted_by_worker") {
    return { action: "start", label: "标记服务中" };
  }
  if (order.status === "in_service") {
    return { action: "complete", label: "提交待审核" };
  }
  if (order.status === "completed" && (order.settlementStatus || "pending") !== "settled") {
    return { action: "archive", label: "去归档" };
  }
  return null;
}

function countUniqueCustomers() {
  return new Set(orders.map((order) => (order.user || "").trim()).filter(Boolean)).size;
}

function countUniqueAreas() {
  return new Set(orders.map((order) => orderArea(order))).size;
}

function ordersWithServiceLogs() {
  return orders.filter((order) => Array.isArray(order.activity) && order.activity.length > 0);
}

function acceptanceSummaryCards() {
  const uniqueCustomers = countUniqueCustomers();
  const uniqueAreas = countUniqueAreas();
  const completedOrders = orders.filter((order) => order.status === "completed");
  const pendingSettlement = completedOrders.filter(
    (order) => (order.settlementStatus || "pending") !== "settled",
  );
  const cards = [
    { label: "演示订单", value: `${orders.length} 单`, hint: `客户 ${uniqueCustomers} 个 · 区域 ${uniqueAreas} 个` },
    {
      label: "服务商样本",
      value: `${workers.length} 位`,
      hint: `${workers.filter((worker) => worker.available).length} 位当前可接单`,
    },
    {
      label: "流程覆盖",
      value: `${orders.filter((order) => ["quoted", "assigned", "accepted_by_worker", "in_service", "completed"].includes(order.status)).length} 单`,
      hint: "已进入报价或后续执行阶段",
    },
    {
      label: "待结算归档",
      value: `${pendingSettlement.length} 单`,
      hint: completedOrders.length ? `已完成 ${completedOrders.length} 单` : "当前暂无完工样本",
    },
  ];
  return cards;
}

function acceptanceChecklistItems() {
  const uniqueCustomers = countUniqueCustomers();
  const uniqueAreas = countUniqueAreas();
  const hasPendingReview = orders.some((order) => order.status === "pending_review");
  const hasQuoted = orders.some((order) => ["quoted", "assigned", "accepted_by_worker", "in_service", "completed"].includes(order.status));
  const hasAssigned = orders.some((order) => ["assigned", "accepted_by_worker", "in_service", "completed"].includes(order.status));
  const hasExecution = orders.some((order) => ["accepted_by_worker", "in_service", "completed"].includes(order.status));
  const hasServiceLogs = ordersWithServiceLogs().length > 0;
  const completedOrders = orders.filter((order) => order.status === "completed");
  const archiveReady = completedOrders.some(
    (order) => order.actualAmount || order.completionNote || order.platformShare || order.workerPayout,
  );
  const requiredFieldsComplete = orders.every(
    (order) => (order.user || "").trim() && (order.address || "").trim() && (order.requestedTime || "").trim(),
  );
  return [
    {
      title: "演示数据覆盖基础场景",
      status: orders.length >= 5 && workers.length >= 4 && uniqueCustomers >= 3 && uniqueAreas >= 3 ? "pass" : "warn",
      detail: `当前有 ${orders.length} 单订单、${workers.length} 位服务商、${uniqueCustomers} 个客户、${uniqueAreas} 个区域样本。`,
      meta: [
        ["建议基线", "5 单订单 / 4 位服务商 / 3 个客户 / 3 个区域"],
        ["当前判断", orders.length >= 5 && workers.length >= 4 ? "可用于内部演示" : "建议继续补样本"],
      ],
      action: "orders",
      actionLabel: "查看订单样本",
    },
    {
      title: "平台确认与报价流程可演示",
      status: hasPendingReview && hasQuoted ? "pass" : "warn",
      detail: hasPendingReview
        ? "当前有待平台确认订单，也有已报价或已进入后续阶段的订单。"
        : "待平台确认订单不足，领导演示时会少一个从录单到报价的起点。",
      meta: [
        ["待确认样本", hasPendingReview ? "已具备" : "未找到"],
        ["报价样本", hasQuoted ? "已具备" : "未找到"],
      ],
      action: "pending_review",
      actionLabel: "打开待确认订单",
    },
    {
      title: "派单与服务商接单流程可演示",
      status: hasAssigned && hasExecution ? "pass" : "warn",
      detail: hasAssigned
        ? "可从派单看板进入已派单、已接单或服务中的订单继续讲解。"
        : "当前缺少派单后样本，建议先补一单进入已派单状态。",
      meta: [
        ["已派单样本", hasAssigned ? "已具备" : "未找到"],
        ["执行样本", hasExecution ? "已具备" : "未找到"],
      ],
      action: "dispatch",
      actionLabel: "打开派单看板",
    },
    {
      title: "服务记录与现场回传已具备",
      status: hasServiceLogs ? "pass" : "warn",
      detail: hasServiceLogs
        ? `当前已有 ${ordersWithServiceLogs().length} 单带服务记录，可展示上门前确认、服务中记录和完工回传。`
        : "当前还没有服务记录样本，建议先通过工作台推进并补一条日志。",
      meta: [
        ["服务记录样本", hasServiceLogs ? `${ordersWithServiceLogs().length} 单` : "0 单"],
        ["适合展示", "当前待办、时间线、自动记录"],
      ],
      action: "workers",
      actionLabel: "打开服务商工作台",
    },
    {
      title: "归档与结算草稿可展示",
      status: completedOrders.length > 0 && archiveReady ? "pass" : "warn",
      detail:
        completedOrders.length > 0
          ? `当前已完成 ${completedOrders.length} 单，其中${archiveReady ? "已有" : "仍缺少"}金额/备注/分账示例。`
          : "当前没有已完成订单样本，无法完整演示归档与结算。",
      meta: [
        ["已完成订单", `${completedOrders.length} 单`],
        ["归档草稿", archiveReady ? "已具备" : "建议补齐一单"],
      ],
      action: "archive",
      actionLabel: "打开完成归档",
    },
    {
      title: "关键字段完整度可过验收",
      status: requiredFieldsComplete ? "pass" : "warn",
      detail: requiredFieldsComplete
        ? "当前所有订单都具备客户、地址和预约时间，页面不存在关键字段空白。"
        : "发现订单存在客户、地址或预约时间缺失，建议先补齐再汇报。",
      meta: [
        ["关键字段", "客户 / 地址 / 预约时间"],
        ["当前判断", requiredFieldsComplete ? "已完整" : "存在缺口"],
      ],
      action: "orders",
      actionLabel: "回到订单列表",
    },
  ];
}

function acceptanceActions() {
  return [
    {
      title: "从待确认单开始讲解",
      detail: "先展示客户信息、草坪说明、预约时间、报价录入和推荐服务商。",
      action: "pending_review",
      label: "打开待确认单",
    },
    {
      title: "切到派单看板讲排班",
      detail: "展示区域筛选、时间冲突提醒和快速派单能力。",
      action: "dispatch",
      label: "去派单看板",
    },
    {
      title: "切到服务商工作台讲执行",
      detail: "展示待出发、服务中、待回传三段任务和一键推进。",
      action: "workers",
      label: "去服务商工作台",
    },
    {
      title: "切到归档页讲结算",
      detail: "展示完工后自动跳转、分账建议、批量结算和 CSV 导出。",
      action: "archive",
      label: "去完成归档",
    },
  ];
}

function runAcceptanceAction(action) {
  if (action === "pending_review") {
    activeView = "orders";
    statusFilter.value = "pending_review";
    const target = orders.find((order) => order.status === "pending_review") || orders[0];
    if (target) {
      selectedId = target.id;
    }
    render();
    return;
  }
  if (action === "dispatch") {
    activeView = "dispatch";
    render();
    return;
  }
  if (action === "archive") {
    activeView = "archive";
    archiveSettlementFilter.value = "pending";
    render();
    return;
  }
  if (action === "workers") {
    activeView = "workers";
    render();
    return;
  }
  activeView = "orders";
  render();
}

function isOverdueOrder(order) {
  const date = orderDate(order);
  if (!date) return false;
  const today = new Date().toISOString().slice(0, 10);
  return date < today && !["completed", "cancelled"].includes(order.status);
}

function dashboardAlerts() {
  const urgentOrders = orders
    .filter((order) => normalizedPriority(order.priorityLevel) === "urgent")
    .filter((order) => !["completed", "cancelled"].includes(order.status));
  const overdueOrders = orders.filter((order) => isOverdueOrder(order));
  const noWorkerOrders = orders.filter((order) => order.status === "quoted" && !order.assignedWorkerId);
  const pendingSettlementOrders = orders.filter(
    (order) => order.status === "completed" && (order.settlementStatus || "pending") !== "settled",
  );
  const pendingQualityOrders = orders.filter((order) => order.status === "pending_quality_review");
  const exceptionOrders = orders.filter((order) => order.status === "exception_open");
  return [
    {
      level: "urgent",
      action: "urgent_orders",
      label: "紧急订单",
      count: urgentOrders.length,
      detail: urgentOrders.length ? `优先处理 ${urgentOrders.map((order) => order.id).join("、")}` : "当前没有未完成的紧急订单。",
    },
    {
      level: "warn",
      action: "overdue_orders",
      label: "逾期待处理",
      count: overdueOrders.length,
      detail: overdueOrders.length ? `这些订单日期已过：${overdueOrders.map((order) => order.id).join("、")}` : "当前没有逾期未处理订单。",
    },
    {
      level: "warn",
      action: "quoted_unassigned",
      label: "待派单",
      count: noWorkerOrders.length,
      detail: noWorkerOrders.length ? `已报价但还没派单：${noWorkerOrders.map((order) => order.id).join("、")}` : "当前没有卡在待派单的报价单。",
    },
    {
      level: "warn",
      action: "pending_settlement",
      label: "待结算",
      count: pendingSettlementOrders.length,
      detail: pendingSettlementOrders.length
        ? `已完成未结算：${pendingSettlementOrders.map((order) => order.id).join("、")}`
        : "当前没有待结算完成单。",
    },
    {
      level: "warn",
      action: "pending_quality_review",
      label: "待质量审核",
      count: pendingQualityOrders.length,
      detail: pendingQualityOrders.length
        ? `待平台审核：${pendingQualityOrders.map((order) => order.id).join("、")}`
        : "当前没有待质量审核订单。",
    },
    {
      level: "urgent",
      action: "exception_open",
      label: "异常处理中",
      count: exceptionOrders.length,
      detail: exceptionOrders.length
        ? `异常待处理：${exceptionOrders.map((order) => order.id).join("、")}`
        : "当前没有异常处理中订单。",
    },
  ];
}

function dashboardFocusGroups() {
  return [
    {
      title: "高优先级待处理",
      items: orders
        .filter((order) => ["pending_review", "quoted", "assigned"].includes(order.status))
        .filter((order) => ["urgent", "high"].includes(normalizedPriority(order.priorityLevel)))
        .slice(0, 4),
    },
    {
      title: "服务中订单",
      items: orders.filter((order) => order.status === "in_service").slice(0, 4),
    },
    {
      title: "待质量审核",
      items: orders.filter((order) => order.status === "pending_quality_review").slice(0, 4),
    },
    {
      title: "待结算完成单",
      items: orders
        .filter((order) => order.status === "completed" && (order.settlementStatus || "pending") !== "settled")
        .slice(0, 4),
    },
  ];
}

function renderOpsDashboard() {
  const alerts = dashboardAlerts();
  const focusGroups = dashboardFocusGroups();
  document.getElementById("opsAlertCount").textContent = `${alerts.reduce((sum, item) => sum + item.count, 0)} 条`;
  document.getElementById("opsAlertList").innerHTML = alerts
    .map(
      (item) => `
        <button class="ops-alert ${item.level}" type="button" data-alert-action="${item.action}">
          <strong>${item.label} · ${item.count}</strong>
          <span>${item.detail}</span>
        </button>
      `,
    )
    .join("");
  document.getElementById("opsFocusCaption").textContent = `${focusGroups.reduce((sum, group) => sum + group.items.length, 0)} 单重点订单`;
  document.getElementById("opsFocusList").innerHTML = focusGroups
    .map(
      (group) => `
        <article class="ops-focus">
          <div class="ops-focus-head">
            <strong>${group.title}</strong>
            <span>${group.items.length} 单</span>
          </div>
          ${
            group.items.length
              ? group.items
                  .map(
                    (order) => `
                      <button class="worker-task" type="button" data-dashboard-order="${order.id}">
                        <strong>${order.id} · ${order.user}</strong>
                        <span>${statusLabels[order.status]} · ${priorityLabel(order.priorityLevel)}</span>
                        <span>${order.requestedTime}</span>
                      </button>
                    `,
                  )
                  .join("")
              : `<div class="empty" style="padding: 8px 0;">当前没有需要重点跟进的订单</div>`
          }
        </article>
      `,
    )
    .join("");

  document.querySelectorAll("[data-dashboard-order]").forEach((button) => {
    button.addEventListener("click", () => {
      selectedId = button.dataset.dashboardOrder;
      activeView = "orders";
      render();
    });
  });

  document.querySelectorAll("[data-alert-action]").forEach((button) => {
    button.addEventListener("click", () => {
      applyDashboardAction(button.dataset.alertAction);
    });
  });
}

function clearOrderFilters() {
  searchInput.value = "";
  statusFilter.value = "all";
  priorityFilter.value = "all";
  opsTagFilter.value = "all";
}

function applyDashboardAction(action) {
  if (action === "pending_settlement") {
    activeView = "archive";
    archiveSettlementFilter.value = "pending";
    render();
    return;
  }

  activeView = "orders";
  clearOrderFilters();

  if (action === "urgent_orders") {
    priorityFilter.value = "urgent";
  } else if (action === "quoted_unassigned") {
    statusFilter.value = "quoted";
  } else if (action === "pending_quality_review") {
    statusFilter.value = "pending_quality_review";
  } else if (action === "exception_open") {
    statusFilter.value = "exception_open";
  } else if (action === "overdue_orders") {
    statusFilter.value = "all";
  }
  render();
}

function workerName(id) {
  const worker = workers.find((item) => item.id === id);
  return worker ? worker.name : "未派单";
}

function workerApprovalLabel(status) {
  return workerApprovalLabels[status] || "待确认";
}

function selectedOrder() {
  return orders.find((order) => order.id === selectedId) || orders[0];
}

function filteredOrders() {
  const keyword = searchInput.value.trim().toLowerCase();
  const status = statusFilter.value;
  const priority = priorityFilter.value;
  const tag = opsTagFilter.value;
  return orders.filter((order) => {
    const matchesStatus = status === "all" || order.status === status;
    const matchesPriority = priority === "all" || normalizedPriority(order.priorityLevel) === priority;
    const matchesTag = tag === "all" || (tag === "__untagged__" ? !orderTag(order) : orderTag(order) === tag);
    const source = `${order.id} ${order.user} ${order.address}`.toLowerCase();
    return matchesStatus && matchesPriority && matchesTag && (!keyword || source.includes(keyword));
  });
}

function renderMetrics() {
  const count = (status) => orders.filter((order) => order.status === status).length;
  const revenue = orders.reduce((sum, order) => sum + (Number(order.price) || 0), 0);
  document.getElementById("metricPending").textContent = count("pending_review");
  document.getElementById("metricQuoted").textContent = count("quoted");
  document.getElementById("metricAssigned").textContent =
    count("assigned") + count("accepted_by_worker") + count("in_service");
  document.getElementById("metricRevenue").textContent = money(revenue).replace(".00", "");
}

function renderStatusBanner() {
  dataMode.className = `status-pill ${storeMeta.mode}`;
  dataMode.textContent = storeMeta.mode === "postgres" ? "PostgreSQL" : "演示数据";
  if (storeMeta.mode === "postgres") {
    dataHint.textContent = "当前页面已接入 PostgreSQL 开发后端。";
    return;
  }
  dataHint.textContent = storeMeta.error
    ? `PostgreSQL 未连通，当前自动回退到演示数据。${storeMeta.error}`
    : "当前使用演示数据。配置 PGUSER 和 PGPASSWORD 后可尝试接入 PostgreSQL。";
}

function renderList() {
  const items = filteredOrders();
  document.getElementById("resultCount").textContent = `${items.length} 单`;
  orderList.innerHTML = items.length
    ? items
        .map(
          (order) => `
            <button class="order-row ${order.id === selectedId ? "active" : ""} ${normalizedPriority(order.priorityLevel) === "urgent" ? "urgent-row" : ""} ${isOverdueOrder(order) ? "overdue-row" : ""}" type="button" data-id="${order.id}">
              <span class="order-main">
                <span class="order-title">
                  <strong>${order.id}</strong>
                  <span class="badge ${order.status}">${statusLabels[order.status]}</span>
                  <span class="worker-badge ${order.priorityLevel || "normal"}">${priorityLabel(order.priorityLevel)}</span>
                  ${order.opsTag ? `<span class="suggestion-chip">${order.opsTag}</span>` : ""}
                </span>
                <span class="order-meta">
                  <span>${order.user}</span>
                  <span>${order.serviceType}</span>
                  <span>${order.requestedTime}</span>
                </span>
                <span class="order-meta">${order.address}</span>
              </span>
              <span class="price">${money(order.price)}</span>
            </button>
          `,
        )
        .join("")
    : `<div class="empty">没有符合条件的订单</div>`;

  orderList.querySelectorAll(".order-row").forEach((row) => {
    row.addEventListener("click", () => {
      selectedId = row.dataset.id;
      render();
    });
  });
}

function renderDetail() {
  const order = selectedOrder();
  if (!order) {
    detailBody.innerHTML = `<div class="empty">暂无订单</div>`;
    return;
  }
  const assignedWorker = order.assignedWorkerId ? workerName(order.assignedWorkerId) : "未派单";
  const latestRecord = order.activity[0] || "暂无处理记录";
  const recommendedWorkers = suggestWorkers(order);
  const checklistSection =
    order.assignedWorkerId && ["assigned", "accepted_by_worker", "in_service"].includes(order.status)
      ? `
        <section class="detail-section">
          <h4>服务前 Checklist</h4>
          <ul class="activity">
            ${serviceChecklistItems(order)
              .map((item) => `<li>${item}</li>`)
              .join("")}
          </ul>
        </section>
      `
      : "";
  const serviceLogSection =
    order.assignedWorkerId && order.status !== "cancelled"
      ? `
        <section class="detail-section">
          <h4>服务记录</h4>
          <div class="detail-grid">
            <span>当前服务商</span><strong>${assignedWorker}</strong>
            <span>推荐记录节点</span><strong>${defaultServiceLogStage(order) === "pre_visit" ? "上门前确认" : defaultServiceLogStage(order) === "arrival" ? "到场签到" : defaultServiceLogStage(order) === "service_note" ? "服务中记录" : "完工回传"}</strong>
          </div>
          <div class="form-grid" style="margin-top: 12px;">
            <div class="field">
              <label for="serviceLogStageInput">记录节点</label>
              <select class="select" id="serviceLogStageInput">
                <option value="pre_visit" ${defaultServiceLogStage(order) === "pre_visit" ? "selected" : ""}>上门前确认</option>
                <option value="arrival" ${defaultServiceLogStage(order) === "arrival" ? "selected" : ""}>到场签到</option>
                <option value="service_note" ${defaultServiceLogStage(order) === "service_note" ? "selected" : ""}>服务中记录</option>
                <option value="completion_followup" ${defaultServiceLogStage(order) === "completion_followup" ? "selected" : ""}>完工回传</option>
              </select>
            </div>
            <div class="field full">
              <label for="serviceLogNoteInput">记录内容</label>
              <textarea class="textarea" id="serviceLogNoteInput" placeholder="例如：已联系客户，侧门可进；树下和围栏边需要人工补刀。"></textarea>
            </div>
            <button class="btn" type="button" id="saveServiceLogBtn">保存服务记录</button>
          </div>
        </section>
      `
      : "";
  const exceptionSection =
    order.status !== "cancelled" && order.status !== "completed"
      ? `
        <section class="detail-section">
          <h4>异常处理</h4>
          <div class="detail-grid">
            <span>当前异常</span><strong>${exceptionSummary(order)}</strong>
            <span>处理结果</span><strong>${order.exceptionResolution || "待处理"}</strong>
          </div>
          <div class="form-grid" style="margin-top: 12px;">
            <div class="field">
              <label for="exceptionTypeInput">异常类型</label>
              <select class="select" id="exceptionTypeInput">
                <option value="树下遗漏" ${order.exceptionType === "树下遗漏" ? "selected" : ""}>树下遗漏</option>
                <option value="边缘未收干净" ${order.exceptionType === "边缘未收干净" ? "selected" : ""}>边缘未收干净</option>
                <option value="现场障碍物" ${order.exceptionType === "现场障碍物" ? "selected" : ""}>现场障碍物</option>
                <option value="客户临时变更" ${order.exceptionType === "客户临时变更" ? "selected" : ""}>客户临时变更</option>
                <option value="机器人异常" ${order.exceptionType === "机器人异常" ? "selected" : ""}>机器人异常</option>
                <option value="其他现场问题" ${order.exceptionType === "其他现场问题" ? "selected" : ""}>其他现场问题</option>
              </select>
            </div>
            <div class="field full">
              <label for="exceptionNoteInput">异常说明</label>
              <textarea class="textarea" id="exceptionNoteInput">${order.exceptionNote || ""}</textarea>
            </div>
            <button class="btn" type="button" id="openExceptionBtn">标记异常处理中</button>
          </div>
          ${
            order.status === "exception_open"
              ? `
                <div class="form-grid" style="margin-top: 12px; padding-top: 12px; border-top: 1px dashed var(--line);">
                  <div class="field">
                    <label for="exceptionNextStatusInput">恢复后状态</label>
                    <select class="select" id="exceptionNextStatusInput">
                      <option value="in_service">恢复服务中</option>
                      <option value="pending_quality_review">恢复待质量审核</option>
                      <option value="completed">直接审核完成</option>
                    </select>
                  </div>
                  <div class="field full">
                    <label for="exceptionResolutionInput">处理结果</label>
                    <textarea class="textarea" id="exceptionResolutionInput">${order.exceptionResolution || ""}</textarea>
                  </div>
                  <button class="btn" type="button" id="resumeExceptionBtn">处理后继续流转</button>
                  <button class="btn" type="button" id="closeExceptionBtn">关闭订单</button>
                </div>
              `
              : ""
          }
        </section>
      `
      : "";
  const qualitySection =
    ["pending_quality_review", "exception_open", "completed"].includes(order.status)
      ? `
        <section class="detail-section">
          <h4>质量审核</h4>
          <div class="detail-grid">
            <span>审核状态</span><strong>${order.status === "pending_quality_review" ? "待平台审核" : order.status === "exception_open" ? "异常中待处理" : "已审核完成"}</strong>
            <span>审核意见</span><strong>${order.reviewNote || "待填写"}</strong>
          </div>
          ${
            order.status === "pending_quality_review" || order.status === "exception_open"
              ? `
                <div class="form-grid" style="margin-top: 12px;">
                  <div class="field full">
                    <label for="qualityReviewNoteInput">审核说明</label>
                    <textarea class="textarea" id="qualityReviewNoteInput">${order.reviewNote || ""}</textarea>
                  </div>
                  <button class="btn primary" type="button" id="approveQualityBtn">审核通过</button>
                  <button class="btn" type="button" id="reworkQualityBtn">打回补做</button>
                </div>
              `
              : ""
          }
        </section>
      `
      : "";
  const completionSection =
    order.status === "completed"
      ? `
        <section class="detail-section">
          <h4>完成与结算</h4>
          <div class="detail-grid">
            <span>结算状态</span><strong>${settlementLabel(order.settlementStatus)}</strong>
            <span>实收金额</span><strong>${archiveAmountDisplay(order)}</strong>
            <span>平台分成</span><strong>${payoutDisplay(order.platformShare)}</strong>
            <span>服务商应结</span><strong>${payoutDisplay(order.workerPayout)}</strong>
            <span>结算时间</span><strong>${order.settledAt || "未结算"}</strong>
            <span>完成备注</span><strong>${order.completionNote || "待补充"}</strong>
            <span>审核说明</span><strong>${order.reviewNote || "待补充"}</strong>
            <span>待结算原因</span><strong>${settlementPendingReason(order)}</strong>
          </div>
          <div class="form-grid" style="margin-top: 12px;">
            <div class="field">
              <label for="detailActualAmount">实收金额 NZD</label>
              <input class="input" id="detailActualAmount" type="number" min="0" step="0.01" value="${order.actualAmount || ""}" placeholder="${order.price || "0"}" />
            </div>
            <div class="field">
              <label for="detailSettlementStatus">结算状态</label>
              <select class="select" id="detailSettlementStatus">
                <option value="pending" ${order.settlementStatus !== "settled" ? "selected" : ""}>待结算</option>
                <option value="settled" ${order.settlementStatus === "settled" ? "selected" : ""}>已结算</option>
              </select>
            </div>
            <div class="field full">
              <label for="detailCompletionNote">完成备注</label>
              <textarea class="textarea" id="detailCompletionNote">${order.completionNote || ""}</textarea>
            </div>
            <div class="field">
              <label for="detailPlatformShare">平台分成 NZD</label>
              <input class="input" id="detailPlatformShare" type="number" min="0" step="0.01" value="${order.platformShare || ""}" />
            </div>
            <div class="field">
              <label for="detailWorkerPayout">服务商应结 NZD</label>
              <input class="input" id="detailWorkerPayout" type="number" min="0" step="0.01" value="${order.workerPayout || ""}" />
            </div>
            <div class="field full">
              <label>结算建议</label>
              <div class="dispatch-hint">${buildSettlementSuggestion(order).reason}</div>
            </div>
            <button class="btn" type="button" id="fillCompletionSuggestionBtn">自动填充建议</button>
            <button class="btn primary" type="button" id="saveCompletionDetailBtn">保存完成信息</button>
          </div>
        </section>
      `
      : "";
  detailStatus.className = `badge ${order.status}`;
  detailStatus.textContent = statusLabels[order.status];

  detailBody.innerHTML = `
    <section class="detail-section">
      <h4>订单概览</h4>
      <div class="detail-summary">
        <div class="detail-stat">
        <span>当前状态</span>
          <strong>${statusLabels[order.status]}</strong>
        </div>
        <div class="detail-stat">
          <span>当前报价</span>
          <strong>${money(order.price)}</strong>
        </div>
        <div class="detail-stat">
          <span>派单结果</span>
          <strong>${assignedWorker}</strong>
        </div>
      </div>
    </section>

    <section class="detail-section">
      <h4>当前待办</h4>
      <div class="todo-list">
        ${serviceTodoItems(order)
          .map(
            (item) => `
              <div class="todo-item">
                <strong>${item.title}</strong>
                <span>${item.detail}</span>
              </div>
            `,
          )
          .join("")}
      </div>
    </section>

    <section class="detail-section">
      <h4>客户与草坪信息</h4>
      <div class="detail-stack">
        <div class="detail-grid">
          <span>客户</span><strong>${order.user}</strong>
          <span>电话</span><strong>${order.phone}</strong>
          <span>地址</span><strong>${order.address}</strong>
          <span>服务类型</span><strong>${order.serviceType}</strong>
          <span>期望时间</span><strong>${order.requestedTime}</strong>
          <span>草坪面积</span><strong>${order.lawnSize}</strong>
        </div>
        <div class="detail-grid">
          <span>现场情况</span><strong>${order.condition}</strong>
          <span>客户备注</span><strong>${order.note || "无"}</strong>
          <span>最新记录</span><strong>${latestRecord}</strong>
          <span>异常摘要</span><strong>${exceptionSummary(order)}</strong>
        </div>
      </div>
    </section>

    <section class="detail-section">
      <h4>草坪照片占位</h4>
      <div class="photo-strip">
        ${order.photos.map((photo) => `<div class="photo">${photo}</div>`).join("")}
      </div>
      <button class="btn" type="button" id="toggleEditBtn" style="margin-top: 10px;">编辑订单信息</button>
      <div id="editOrderForm" style="display: none; margin-top: 12px;">
        <div class="form-grid">
          <div class="field">
            <label for="editUser">客户姓名</label>
            <input class="input" id="editUser" type="text" value="${order.user || ""}" />
          </div>
          <div class="field">
            <label for="editPhone">联系电话</label>
            <input class="input" id="editPhone" type="text" value="${order.phone || ""}" />
          </div>
          <div class="field full">
            <label for="editAddress">服务地址</label>
            <input class="input" id="editAddress" type="text" value="${order.address || ""}" />
          </div>
          <div class="field">
            <label for="editServiceType">服务类型</label>
            <select class="select" id="editServiceType">
              <option value="一次性割草" ${order.serviceType === "一次性割草" ? "selected" : ""}>一次性割草</option>
              <option value="定期割草预约" ${order.serviceType === "定期割草预约" ? "selected" : ""}>定期割草预约</option>
            </select>
          </div>
          <div class="field">
            <label for="editRequestedDate">服务日期</label>
            <input class="input" id="editRequestedDate" type="date" value="${orderDate(order)}" />
          </div>
          <div class="field">
            <label for="editRequestedStart">开始时间</label>
            <input class="input" id="editRequestedStart" type="time" value="${parseRequestedWindow(order.requestedTime).start}" />
          </div>
          <div class="field">
            <label for="editRequestedEnd">结束时间</label>
            <input class="input" id="editRequestedEnd" type="time" value="${parseRequestedWindow(order.requestedTime).end}" />
          </div>
          <div class="field">
            <label for="editLawnSize">草坪面积</label>
            <input class="input" id="editLawnSize" type="text" value="${order.lawnSize || ""}" />
          </div>
          <div class="field full">
            <label for="editCondition">现场情况</label>
            <textarea class="textarea" id="editCondition">${order.condition || ""}</textarea>
          </div>
          <div class="field full">
            <label for="editNote">客户备注</label>
            <textarea class="textarea" id="editNote">${order.note || ""}</textarea>
          </div>
          <button class="btn primary" type="button" id="saveEditBtn">保存修改</button>
        </div>
      </div>
    </section>

    <section class="detail-section">
      <h4>内部备注</h4>
      <div class="form-grid">
        <textarea class="textarea" id="internalNoteInput" placeholder="运营人员内部备注，客户不可见。">${order.internalNote || ""}</textarea>
        <button class="btn" type="button" id="saveInternalNoteBtn">保存内部备注</button>
      </div>
    </section>

    <section class="detail-section">
      <h4>运营标记</h4>
      <div class="detail-grid">
        <span>优先级</span><strong>${priorityLabel(order.priorityLevel)}</strong>
        <span>运营标签</span><strong>${order.opsTag || "未标记"}</strong>
      </div>
      <div class="form-grid" style="margin-top: 12px;">
        <div class="field">
          <label for="priorityLevelInput">优先级</label>
          <select class="select" id="priorityLevelInput">
            <option value="low" ${order.priorityLevel === "low" ? "selected" : ""}>低优先级</option>
            <option value="normal" ${!order.priorityLevel || order.priorityLevel === "normal" ? "selected" : ""}>常规</option>
            <option value="high" ${order.priorityLevel === "high" ? "selected" : ""}>优先处理</option>
            <option value="urgent" ${order.priorityLevel === "urgent" ? "selected" : ""}>紧急</option>
          </select>
        </div>
        <div class="field">
          <label for="opsTagInput">运营标签</label>
          <input class="input" id="opsTagInput" type="text" value="${order.opsTag || ""}" placeholder="如：树下补刀 / 定期客户" />
        </div>
        <button class="btn" type="button" id="saveOpsBtn">保存运营标记</button>
      </div>
    </section>

    <section class="detail-section">
      <h4>人工报价</h4>
      <div class="detail-stack">
        <div class="detail-grid">
          <span>当前报价</span><strong>${money(order.price)}</strong>
          <span>价格说明</span><strong>${order.priceNote || "待平台录入"}</strong>
        </div>
      </div>
      <div class="form-grid" style="margin-top: 12px;">
        <div class="field">
          <label for="priceInput">最终价格 NZD</label>
          <input class="input" id="priceInput" type="number" min="0" step="1" value="${order.price}" />
        </div>
        <div class="field">
          <label for="priceNoteInput">价格说明</label>
          <textarea class="textarea" id="priceNoteInput">${order.priceNote}</textarea>
        </div>
        <button class="btn primary" type="button" id="saveQuoteBtn">保存报价</button>
      </div>
    </section>

    <section class="detail-section">
      <h4>手动派单</h4>
      <div class="detail-grid">
        <span>当前派单</span><strong>${assignedWorker}</strong>
        <span>服务商状态</span><strong>${statusLabels[order.status] || (order.assignedWorkerId ? "已分配" : "待分配")}</strong>
        <span>推荐服务商</span><strong>${recommendedWorkers.map((worker) => {
          const dist = workerDistance(worker.id);
          const distText = dist !== null ? ` (${formatDistance(dist)})` : "";
          return `${worker.name}${distText}`;
        }).join("、") || "暂无推荐"}</strong>
        <span>推荐依据</span><strong>${recommendedWorkers.length ? `${orderArea(order)} / 距离优先 / 当前可接单` : "当前没有可接单服务商"}</strong>
      </div>
      <div class="form-grid" style="margin-top: 12px;">
        <div class="field">
          <label for="workerSelect">选择服务商</label>
          <select class="select" id="workerSelect">
            <option value="">未派单</option>
            ${recommendedWorkers
              .map(
                (worker) => `
                  <option value="${worker.id}" ${worker.id === order.assignedWorkerId ? "selected" : ""}>
                    ${worker.name} · ${worker.area}
                  </option>
                `,
              )
              .join("")}
          </select>
        </div>
          <button class="btn primary" type="button" id="assignBtn">保存派单</button>
          ${order.assignedWorkerId && order.status !== "cancelled" && order.status !== "completed" ? '<button class="btn" type="button" id="reassignBtn">改派给选中服务商</button>' : ""}
          <button class="btn" type="button" id="acceptBtn">标记服务商已接单</button>
          ${order.status === "accepted_by_worker" ? '<button class="btn" type="button" id="startServiceBtn">标记服务中</button>' : ""}
          ${order.status === "in_service" ? '<button class="btn primary" type="button" id="completeServiceBtn">提交待审核</button>' : ""}
          ${order.assignedWorkerId && (order.status === "assigned" || order.status === "accepted_by_worker") ? '<button class="btn" type="button" id="rejectBtn" style="color: var(--danger); border-color: var(--danger);">标记服务商拒单</button>' : ""}
        </div>
      </section>

      ${order.status !== "cancelled" && order.status !== "completed" ? `
        <section class="detail-section">
          <h4>订单操作</h4>
          <div class="form-grid" style="margin-top: 0;">
            <button class="btn" type="button" id="cancelOrderBtn" style="color: var(--danger); border-color: var(--danger);">取消订单</button>
          </div>
        </section>
      ` : ""}

    ${checklistSection}

    ${serviceLogSection}

    ${exceptionSection}

    ${qualitySection}

    <section class="detail-section">
      <h4>处理时间线</h4>
      <ul class="activity">
        ${order.activity
          .map((item) => {
            const entry = parseActivityItem(item);
            return `
              <li class="timeline-item">
                <strong>${entry.message}</strong>
                <span class="timeline-time">${entry.time}</span>
              </li>
            `;
          })
          .join("")}
      </ul>
    </section>

    ${completionSection}
  `;

  document.getElementById("saveQuoteBtn").addEventListener("click", saveQuote);
  document.getElementById("saveOpsBtn").addEventListener("click", saveOrderOps);
  document.getElementById("assignBtn").addEventListener("click", assignWorker);
  document.getElementById("reassignBtn")?.addEventListener("click", reassignWorker);
  document.getElementById("acceptBtn").addEventListener("click", acceptByWorker);
  document.getElementById("startServiceBtn")?.addEventListener("click", startService);
  document.getElementById("completeServiceBtn")?.addEventListener("click", completeService);
  document.getElementById("rejectBtn")?.addEventListener("click", rejectOrder);
  document.getElementById("cancelOrderBtn")?.addEventListener("click", cancelOrder);
  document.getElementById("saveServiceLogBtn")?.addEventListener("click", saveServiceLog);
  document.getElementById("openExceptionBtn")?.addEventListener("click", openExceptionCase);
  document.getElementById("resumeExceptionBtn")?.addEventListener("click", resumeExceptionCase);
  document.getElementById("closeExceptionBtn")?.addEventListener("click", closeExceptionCase);
  document.getElementById("approveQualityBtn")?.addEventListener("click", approveQualityReview);
  document.getElementById("reworkQualityBtn")?.addEventListener("click", reworkQualityReview);
  document.getElementById("fillCompletionSuggestionBtn")?.addEventListener("click", applySettlementSuggestionToDetail);
  document.getElementById("saveCompletionDetailBtn")?.addEventListener("click", saveCompletionFromDetail);
  document.getElementById("toggleEditBtn")?.addEventListener("click", toggleEditForm);
  document.getElementById("saveEditBtn")?.addEventListener("click", saveOrderEdit);
  document.getElementById("saveInternalNoteBtn")?.addEventListener("click", saveInternalNote);

  // Trigger async distance lookup for worker suggestions
  if (order.address) {
    suggestWorkersByDistance(order.address).then(() => {
      // Refresh the worker select dropdown if still on the same order
      const current = selectedOrder();
      if (current && current.id === order.id) {
        const recommendedWorkers = suggestWorkers(order);
        const select = document.getElementById("workerSelect");
        if (select && recommendedWorkers.length) {
          const currentValue = select.value;
          select.innerHTML = [
            '<option value="">未派单</option>',
            ...recommendedWorkers.map(
              (worker) => {
                const dist = workerDistance(worker.id);
                const distText = dist !== null ? ` (${formatDistance(dist)})` : "";
                return `<option value="${worker.id}" ${worker.id === currentValue ? "selected" : ""}>${worker.name} · ${worker.area}${distText}</option>`;
              },
            ),
          ].join("");
          if (!select.value) select.value = recommendedWorkers[0].id;
        }
      }
    });
  }
}

function renderWorkersView() {
  workersView.innerHTML = workers
    .map(
      (worker) => {
        const summary = workerSummary(worker.id);
        const lanes = workerLaneItems(worker.id);
        const renderLane = (title, items, emptyText) => `
          <section class="worker-lane">
            <h4>${title}</h4>
            <div class="worker-task-list">
              ${
                items.length
                  ? items
                      .map(
                        (order) => {
                          const primaryAction = workerTaskPrimaryAction(order);
                          return `
                            <article class="worker-task">
                              <strong>${order.id} · ${order.user}</strong>
                              <span>${order.requestedTime}</span>
                              <span>${priorityLabel(order.priorityLevel)}${order.opsTag ? ` · ${order.opsTag}` : ""}</span>
                              <span>${statusLabels[order.status]}</span>
                              <div class="worker-task-actions">
                                <button class="btn" type="button" ${order.status === "completed" ? `data-open-archive="${order.id}"` : `data-open-order="${order.id}"`}>
                                  查看
                                </button>
                                ${
                                  primaryAction
                                    ? `<button class="btn primary" type="button" data-worker-progress="${order.id}" data-worker-progress-action="${primaryAction.action}">
                                        ${primaryAction.label}
                                      </button>`
                                    : ""
                                }
                              </div>
                            </article>
                          `;
                        },
                      )
                      .join("")
                  : `<div class="empty" style="padding: 16px 8px;">${emptyText}</div>`
              }
            </div>
          </section>
        `;
        return `
        <article class="worker-card">
          <div class="worker-head">
            <div class="worker-headline">
              <div>
                <h3>${worker.name}</h3>
                <p>${worker.id}</p>
              </div>
              <div class="worker-actions">
                <span class="worker-badge ${worker.approvalStatus || "approved"}">
                  ${workerApprovalLabel(worker.approvalStatus)}
                </span>
              </div>
            </div>
            <span class="worker-badge ${worker.available ? "available" : "unavailable"}">
              ${worker.available ? "可接单" : "暂停接单"}
            </span>
          </div>
          <div class="worker-meta">
            <div><span>服务区域</span><br /><strong>${worker.area}</strong></div>
            <div><span>联系电话</span><br /><strong>${worker.phone || "待补充"}</strong></div>
            <div><span>当前状态</span><br /><strong>${worker.available ? "平台可派单" : "暂不参与派单"}</strong></div>
          </div>
          <p class="worker-note">${worker.serviceNote || "暂无派单备注"}</p>
          <div class="worker-board">
            <div class="worker-board-summary">
              <div class="worker-board-stat">
                <span>执行中任务</span>
                <strong>${summary.activeCount} 单</strong>
              </div>
              <div class="worker-board-stat">
                <span>待结算完成单</span>
                <strong>${summary.completedPendingSettle} 单</strong>
              </div>
              <div class="worker-board-stat">
                <span>紧急任务</span>
                <strong>${summary.urgentCount} 单</strong>
              </div>
              <div class="worker-board-stat">
                <span>关联报价额</span>
                <strong>${money(summary.totalRevenue).replace(".00", "")}</strong>
              </div>
            </div>
            <div class="worker-lanes">
              ${renderLane("待出发 / 待确认", lanes.waitingDeparture, "当前没有待出发任务")}
              ${renderLane("服务中", lanes.inService, "当前没有服务中任务")}
              ${renderLane("待审核 / 待结算", lanes.waitingWrapup, "当前没有待审核或待结算任务")}
            </div>
          </div>
          <div class="worker-actions">
            <button class="btn" type="button" data-worker-edit="${worker.id}">
              编辑资料
            </button>
            <button class="btn ${worker.available ? "" : "primary"}" type="button" data-worker-action="enable" data-worker-id="${worker.id}">
              恢复接单
            </button>
            <button class="btn ${worker.available ? "primary" : ""}" type="button" data-worker-action="disable" data-worker-id="${worker.id}">
              暂停接单
            </button>
          </div>
        </article>
      `;
      },
    )
    .join("");

  workersView.querySelectorAll("[data-worker-action]").forEach((button) => {
    button.addEventListener("click", async () => {
      try {
        await updateWorkerAvailability(
          button.dataset.workerId,
          button.dataset.workerAction === "enable",
        );
      } catch (error) {
        alert(error.message);
      }
    });
  });

  workersView.querySelectorAll("[data-worker-edit]").forEach((button) => {
    button.addEventListener("click", () => openWorkerModal(button.dataset.workerEdit));
  });

  workersView.querySelectorAll("[data-open-order]").forEach((button) => {
    button.addEventListener("click", () => {
      selectedId = button.dataset.openOrder;
      activeView = "orders";
      render();
    });
  });

  workersView.querySelectorAll("[data-open-archive]").forEach((button) => {
    button.addEventListener("click", () => {
      openArchiveForOrder(button.dataset.openArchive);
    });
  });

  workersView.querySelectorAll("[data-worker-progress]").forEach((button) => {
    button.addEventListener("click", async () => {
      try {
        await workerQuickAdvance(button.dataset.workerProgress, button.dataset.workerProgressAction);
      } catch (error) {
        alert(error.message);
      }
    });
  });
}

function renderAcceptanceView() {
  document.getElementById("acceptanceSummary").innerHTML = acceptanceSummaryCards()
    .map(
      (card) => `
        <article class="metric">
          <span>${card.label}</span>
          <strong>${card.value}</strong>
          <div class="dispatch-hint">${card.hint}</div>
        </article>
      `,
    )
    .join("");

  const items = acceptanceChecklistItems();
  document.getElementById("acceptanceResultCaption").textContent = `${items.filter((item) => item.status === "pass").length} / ${items.length} 项已具备`;
  document.getElementById("acceptanceChecklist").innerHTML = items
    .map(
      (item) => `
        <article class="acceptance-card ${item.status}">
          <header>
            <div>
              <h4>${item.title}</h4>
              <p>${item.detail}</p>
            </div>
            <span class="acceptance-status ${item.status}">${item.status === "pass" ? "已具备" : "待补强"}</span>
          </header>
          <div class="acceptance-meta">
            ${item.meta.map(([label, value]) => `<span>${label}</span><strong>${value}</strong>`).join("")}
          </div>
          <div class="inline-actions">
            <button class="btn" type="button" data-acceptance-action="${item.action}">${item.actionLabel}</button>
          </div>
        </article>
      `,
    )
    .join("");

  document.getElementById("acceptanceActions").innerHTML = acceptanceActions()
    .map(
      (item) => `
        <article class="acceptance-action-card">
          <header>
            <div>
              <h4>${item.title}</h4>
              <p>${item.detail}</p>
            </div>
          </header>
          <div class="inline-actions">
            <button class="btn primary" type="button" data-acceptance-action="${item.action}">${item.label}</button>
          </div>
        </article>
      `,
    )
    .join("");

  acceptanceView.querySelectorAll("[data-acceptance-action]").forEach((button) => {
    button.addEventListener("click", () => runAcceptanceAction(button.dataset.acceptanceAction));
  });
}

function renderActiveView() {
  const orderMode = activeView === "orders";
  const dispatchMode = activeView === "dispatch";
  const archiveMode = activeView === "archive";
  const workerMode = activeView === "workers";
  const acceptanceMode = activeView === "acceptance";
  ordersView.classList.toggle("hidden", !orderMode);
  metricsSection.classList.toggle("hidden", !orderMode);
  opsDashboard.classList.toggle("hidden", !orderMode);
  dispatchView.classList.toggle("hidden", !dispatchMode);
  archiveView.classList.toggle("hidden", !archiveMode);
  workersView.classList.toggle("hidden", !workerMode);
  acceptanceView.classList.toggle("hidden", !acceptanceMode);
  if (orderMode) {
    pageTitle.textContent = "订单管理";
    pageSubtitle.textContent = "统一查看订单、运营提醒、报价、派单和服务推进。";
  } else if (dispatchMode) {
    pageTitle.textContent = "派单看板";
    pageSubtitle.textContent = "集中处理待报价、待派单和当天服务商排班。";
  } else if (archiveMode) {
    pageTitle.textContent = "完成归档";
    pageSubtitle.textContent = "集中处理完工回传、分账建议、结算和导出。";
  } else if (acceptanceMode) {
    pageTitle.textContent = "阶段验收";
    pageSubtitle.textContent = "把第一期是否可内部试运营、可汇报、可重复演示直接摊开看。";
  } else {
    pageTitle.textContent = "服务商管理";
    pageSubtitle.textContent = "查看服务商资料、当天任务顺序和一键推进节点。";
  }
  document.querySelectorAll("[data-view]").forEach((button) => {
    button.classList.toggle("active", button.dataset.view === activeView);
  });
  document.getElementById("newOrderBtn").style.display = orderMode ? "inline-flex" : "none";
  if (dispatchMode) {
    renderDispatchView();
  } else if (archiveMode) {
    renderArchiveView();
  } else if (acceptanceMode) {
    renderAcceptanceView();
  } else if (!orderMode) {
    renderWorkersView();
  }
}

function render() {
  populateTagFilter(opsTagFilter, opsTagFilter.value, true);
  renderStatusBanner();
  renderMetrics();
  renderOpsDashboard();
  renderList();
  renderDetail();
  renderActiveView();
}

function openOrderModal() {
  orderModal.classList.add("open");
  orderModal.setAttribute("aria-hidden", "false");
  createOrderForm.reset();
  if (!document.getElementById("createRequestedDate").value) {
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    const year = tomorrow.getFullYear();
    const month = String(tomorrow.getMonth() + 1).padStart(2, "0");
    const day = String(tomorrow.getDate()).padStart(2, "0");
    document.getElementById("createRequestedDate").value = `${year}-${month}-${day}`;
  }
  document.getElementById("createRequestedStart").value = "09:00";
  document.getElementById("createRequestedEnd").value = "12:00";
  document.getElementById("createUser").focus();
}

function closeOrderModal() {
  orderModal.classList.remove("open");
  orderModal.setAttribute("aria-hidden", "true");
}

function buildRequestedTimeFromControls(payload) {
  const requestedDate = String(payload.requestedDate || "").trim();
  const requestedStart = String(payload.requestedStart || "").trim();
  const requestedEnd = String(payload.requestedEnd || "").trim();
  if (!requestedDate || !requestedStart || !requestedEnd) {
    throw new Error("请先完整选择服务日期和时间段。");
  }
  if (requestedStart >= requestedEnd) {
    throw new Error("结束时间需要晚于开始时间。");
  }
  return `${requestedDate} ${requestedStart}-${requestedEnd}`;
}

function openWorkerModal(workerId) {
  const worker = workers.find((item) => item.id === workerId);
  if (!worker) {
    return;
  }
  workerProfileForm.dataset.workerId = worker.id;
  workerProfileForm.elements.name.value = worker.name || "";
  workerProfileForm.elements.phone.value = worker.phone || "";
  workerProfileForm.elements.area.value = worker.area || "";
  workerProfileForm.elements.approvalStatus.value = worker.approvalStatus || "approved";
  workerProfileForm.elements.serviceNote.value = worker.serviceNote || "";
  workerProfileForm.elements.lat.value = worker.lat ?? "";
  workerProfileForm.elements.lng.value = worker.lng ?? "";
  workerModal.classList.add("open");
  workerModal.setAttribute("aria-hidden", "false");
  document.getElementById("workerName").focus();
}

function closeWorkerModal() {
  workerModal.classList.remove("open");
  workerModal.setAttribute("aria-hidden", "true");
  workerProfileForm.reset();
  delete workerProfileForm.dataset.workerId;
}

function hydrate(payload) {
  orders = payload.orders || [];
  workers = payload.workers || [];
  storeMeta = payload.store || storeMeta;
  if (!orders.find((order) => order.id === selectedId)) {
    selectedId = orders[0]?.id || "";
  }
  render();
}

async function request(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    let message = "请求失败";
    try {
      const payload = await response.json();
      message = payload.detail || message;
    } catch (error) {
      message = response.statusText || message;
    }
    throw new Error(message);
  }
  return response.json();
}

async function bootstrap() {
  const payload = await request("/api/bootstrap");
  hydrate(payload);
}

async function saveQuote() {
  const order = selectedOrder();
  const price = document.getElementById("priceInput").value.trim();
  const priceNote = document.getElementById("priceNoteInput").value.trim();
  if (!price) {
    alert("请先填写最终价格。");
    return;
  }
  const payload = await request(`/api/orders/${order.id}/quote`, {
    method: "POST",
    body: JSON.stringify({ price, priceNote }),
  });
  hydrate(payload);
  const updated = orders.find((item) => item.id === order.id);
  if (!updated || updated.assignedWorkerId) {
    return;
  }
  const recommended = suggestWorkers(updated);
  if (!recommended.length) {
    return;
  }
  const select = document.getElementById("workerSelect");
  if (select) {
    select.value = recommended[0].id;
  }
}

async function saveOrderOps() {
  const order = selectedOrder();
  const priorityLevel = document.getElementById("priorityLevelInput").value;
  const opsTag = document.getElementById("opsTagInput").value.trim();
  const payload = await request(`/api/orders/${order.id}/ops`, {
    method: "POST",
    body: JSON.stringify({ priorityLevel, opsTag }),
  });
  hydrate(payload);
}

async function saveServiceLog() {
  const order = selectedOrder();
  const stage = document.getElementById("serviceLogStageInput").value;
  const note = document.getElementById("serviceLogNoteInput").value.trim();
  const payload = await request(`/api/orders/${order.id}/service-log`, {
    method: "POST",
    body: JSON.stringify({ stage, note }),
  });
  hydrate(payload);
}

async function openExceptionCase() {
  const order = selectedOrder();
  const issueType = document.getElementById("exceptionTypeInput")?.value || "";
  const note = document.getElementById("exceptionNoteInput")?.value.trim() || "";
  const payload = await request(`/api/orders/${order.id}/exception`, {
    method: "POST",
    body: JSON.stringify({ action: "open", issueType, note }),
  });
  hydrate(payload);
}

async function resumeExceptionCase() {
  const order = selectedOrder();
  const nextStatus = document.getElementById("exceptionNextStatusInput")?.value || "in_service";
  const resolution = document.getElementById("exceptionResolutionInput")?.value.trim() || "";
  const payload = await request(`/api/orders/${order.id}/exception`, {
    method: "POST",
    body: JSON.stringify({ action: "resume", nextStatus, resolution }),
  });
  hydrate(payload);
}

async function closeExceptionCase() {
  const order = selectedOrder();
  const resolution = document.getElementById("exceptionResolutionInput")?.value.trim() || "";
  const payload = await request(`/api/orders/${order.id}/exception`, {
    method: "POST",
    body: JSON.stringify({ action: "close", resolution }),
  });
  hydrate(payload);
}

async function approveQualityReview() {
  const order = selectedOrder();
  const note = document.getElementById("qualityReviewNoteInput")?.value.trim() || "";
  const payload = await request(`/api/orders/${order.id}/quality-review`, {
    method: "POST",
    body: JSON.stringify({ action: "approve", note }),
  });
  hydrate(payload);
}

async function reworkQualityReview() {
  const order = selectedOrder();
  const note = document.getElementById("qualityReviewNoteInput")?.value.trim() || "";
  const payload = await request(`/api/orders/${order.id}/quality-review`, {
    method: "POST",
    body: JSON.stringify({ action: "rework", note }),
  });
  hydrate(payload);
}

function applySettlementSuggestionToArchive(orderId) {
  const order = orders.find((item) => item.id === orderId);
  if (!order) return;
  const actualAmount = document.getElementById(`archiveActualAmount-${orderId}`)?.value.trim() || "";
  const suggestion = buildSettlementSuggestion(order, actualAmount);
  document.getElementById(`archivePlatformShare-${orderId}`).value = suggestion.platformShare;
  document.getElementById(`archiveWorkerPayout-${orderId}`).value = suggestion.workerPayout;
}

function applySettlementSuggestionToDetail() {
  const order = selectedOrder();
  if (!order) return;
  const actualAmount = document.getElementById("detailActualAmount")?.value.trim() || "";
  const suggestion = buildSettlementSuggestion(order, actualAmount);
  document.getElementById("detailPlatformShare").value = suggestion.platformShare;
  document.getElementById("detailWorkerPayout").value = suggestion.workerPayout;
}

function prepareArchiveDraft(orderId) {
  const order = orders.find((item) => item.id === orderId);
  if (!order) return;
  const actualAmountInput = document.getElementById(`archiveActualAmount-${orderId}`);
  const completionNoteInput = document.getElementById(`archiveCompletionNote-${orderId}`);
  if (actualAmountInput && !actualAmountInput.value.trim()) {
    actualAmountInput.value = order.actualAmount || order.price || "";
  }
  applySettlementSuggestionToArchive(orderId);
  if (completionNoteInput && !completionNoteInput.value.trim()) {
    completionNoteInput.value = completionNoteTemplate(order);
  }
}

function openArchiveForOrder(orderId, options = {}) {
  const { prepareDraft = false } = options;
  selectedArchiveOrderIds.clear();
  selectedArchiveOrderIds.add(orderId);
  activeView = "archive";
  archiveSettlementFilter.value = "pending";
  archiveWorkerFilter.value = "all";
  archiveDateFilter.value = "";
  archiveMinAmount.value = "";
  archiveMaxAmount.value = "";
  archiveSearchInput.value = orderId;
  render();
  if (prepareDraft) {
    prepareArchiveDraft(orderId);
  }
}

async function addQuickServiceLog(orderId, stage, note) {
  const payload = await request(`/api/orders/${orderId}/service-log`, {
    method: "POST",
    body: JSON.stringify({ stage, note }),
  });
  hydrate(payload);
}

async function workerQuickAdvance(orderId, action) {
  if (action === "accept") {
    const payload = await request(`/api/orders/${orderId}/accept`, { method: "POST" });
    hydrate(payload);
    await addQuickServiceLog(orderId, "pre_visit", "服务商已从工作台确认接单，准备出发。");
    return;
  }
  if (action === "start") {
    const payload = await request(`/api/orders/${orderId}/status`, {
      method: "POST",
      body: JSON.stringify({ status: "in_service" }),
    });
    hydrate(payload);
    await addQuickServiceLog(orderId, "arrival", "服务商已从工作台标记到场并开始作业。");
    return;
  }
  if (action === "complete") {
    const payload = await request(`/api/orders/${orderId}/status`, {
      method: "POST",
      body: JSON.stringify({ status: "pending_quality_review" }),
    });
    hydrate(payload);
    await addQuickServiceLog(orderId, "completion_followup", "服务商已从工作台提交完工，等待平台质量审核。");
    return;
  }
  if (action === "archive") {
    openArchiveForOrder(orderId, { prepareDraft: true });
  }
}

async function assignWorker() {
  const order = selectedOrder();
  const workerId = document.getElementById("workerSelect").value;
  if (!workerId) {
    alert("请选择可接单服务商。");
    return;
  }
  if (!order.price) {
    alert("请先保存报价，再进行派单。");
    return;
  }
  const payload = await request(`/api/orders/${order.id}/assign`, {
    method: "POST",
    body: JSON.stringify({ workerId }),
  });
  hydrate(payload);
}

async function acceptByWorker() {
  const order = selectedOrder();
  if (!order.assignedWorkerId) {
    alert("请先派单，再标记服务商接单。");
    return;
  }
  const payload = await request(`/api/orders/${order.id}/accept`, { method: "POST" });
  hydrate(payload);
}

async function updateOrderStatus(orderId, status) {
  const payload = await request(`/api/orders/${orderId}/status`, {
    method: "POST",
    body: JSON.stringify({ status }),
  });
  hydrate(payload);
}

async function reassignWorker() {
  const order = selectedOrder();
  const workerId = document.getElementById("workerSelect").value;
  if (!workerId) {
    alert("请选择可接单服务商。");
    return;
  }
  if (workerId === order.assignedWorkerId) {
    alert("改派目标不能与当前服务商相同。");
    return;
  }
  const payload = await request(`/api/orders/${order.id}/reassign`, {
    method: "POST",
    body: JSON.stringify({ workerId }),
  });
  hydrate(payload);
}

async function cancelOrder() {
  const order = selectedOrder();
  if (!window.confirm(`确认取消订单 ${order.id}？取消后无法恢复。`)) {
    return;
  }
  const note = window.prompt("取消原因（可选）：");
  const payload = await request(`/api/orders/${order.id}/cancel`, {
    method: "POST",
    body: JSON.stringify({ note: note || "" }),
  });
  hydrate(payload);
}

async function saveInternalNote() {
  const order = selectedOrder();
  const note = document.getElementById("internalNoteInput")?.value ?? "";
  const payload = await request(`/api/orders/${order.id}/internal-note`, {
    method: "POST",
    body: JSON.stringify({ note }),
  });
  hydrate(payload);
}

function toggleEditForm() {
  const form = document.getElementById("editOrderForm");
  if (form) {
    form.style.display = form.style.display === "none" ? "block" : "none";
  }
}

async function saveOrderEdit() {
  const order = selectedOrder();
  const payload = {};
  const fields = ["createUser", "createPhone", "createAddress", "createServiceType", "createRequestedDate", "createRequestedStart", "createRequestedEnd", "createLawnSize", "createCondition", "createNote"];
  const editIds = ["editUser", "editPhone", "editAddress", "editServiceType", "editRequestedDate", "editRequestedStart", "editRequestedEnd", "editLawnSize", "editCondition", "editNote"];
  const attrs = ["user", "phone", "address", "serviceType", null, null, null, "lawnSize", "condition", "note"];

  for (let i = 0; i < fields.length; i++) {
    const el = document.getElementById(editIds[i]);
    if (!el) continue;
    const val = el.value?.trim() ?? "";
    if (attrs[i] && val) payload[attrs[i]] = val;
  }

  // Handle requestedTime from date+time controls
  const dateEl = document.getElementById("editRequestedDate");
  const startEl = document.getElementById("editRequestedStart");
  const endEl = document.getElementById("editRequestedEnd");
  if (dateEl && startEl && endEl) {
    const date = dateEl.value;
    const start = startEl.value;
    const end = endEl.value;
    if (date && start && end) payload.requestedTime = `${date} ${start}-${end}`;
  }

  if (!Object.keys(payload).length) {
    alert("没有修改任何字段。");
    return;
  }

  const result = await request(`/api/orders/${order.id}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
  hydrate(result);
  document.getElementById("editOrderForm").style.display = "none";
}

async function rejectOrder() {
  const order = selectedOrder();
  if (!window.confirm(`确认以服务商身份拒单 ${order.id}？拒单后订单将回到待派单状态。`)) {
    return;
  }
  const payload = await request(`/api/orders/${order.id}/reject`, { method: "POST" });
  hydrate(payload);
}

async function startService() {
  const order = selectedOrder();
  await updateOrderStatus(order.id, "in_service");
}

async function completeService() {
  const order = selectedOrder();
  await updateOrderStatus(order.id, "pending_quality_review");
}

async function saveCompletion(orderId) {
  const actualAmount = document.getElementById(`archiveActualAmount-${orderId}`).value.trim();
  const settlementStatus = document.getElementById(`archiveSettlementStatus-${orderId}`).value;
  const completionNote = document.getElementById(`archiveCompletionNote-${orderId}`).value.trim();
  const platformShare = document.getElementById(`archivePlatformShare-${orderId}`).value.trim();
  const workerPayout = document.getElementById(`archiveWorkerPayout-${orderId}`).value.trim();
  const payload = await request(`/api/orders/${orderId}/completion`, {
    method: "POST",
    body: JSON.stringify({ actualAmount, settlementStatus, completionNote, platformShare, workerPayout }),
  });
  hydrate(payload);
}

async function saveCompletionFromDetail() {
  const order = selectedOrder();
  const actualAmount = document.getElementById("detailActualAmount").value.trim();
  const settlementStatus = document.getElementById("detailSettlementStatus").value;
  const completionNote = document.getElementById("detailCompletionNote").value.trim();
  const platformShare = document.getElementById("detailPlatformShare")?.value.trim() || "";
  const workerPayout = document.getElementById("detailWorkerPayout")?.value.trim() || "";
  const payload = await request(`/api/orders/${order.id}/completion`, {
    method: "POST",
    body: JSON.stringify({ actualAmount, settlementStatus, completionNote, platformShare, workerPayout }),
  });
  hydrate(payload);
}

async function batchSettleArchiveOrders() {
  const items = filteredArchivedOrders().filter((order) => selectedArchiveOrderIds.has(order.id));
  if (!items.length) {
    alert("请先选择需要批量结算的订单。");
    return;
  }
  archiveBatchSettleBtn.disabled = true;
  try {
    for (const order of items) {
      const actualAmountInput = document.getElementById(`archiveActualAmount-${order.id}`);
      const completionNoteInput = document.getElementById(`archiveCompletionNote-${order.id}`);
      const platformShareInput = document.getElementById(`archivePlatformShare-${order.id}`);
      const workerPayoutInput = document.getElementById(`archiveWorkerPayout-${order.id}`);
      const actualAmount = actualAmountInput?.value.trim() || order.actualAmount || order.price || "";
      const completionNote = completionNoteInput?.value.trim() || order.completionNote || "";
      const platformShare = platformShareInput?.value.trim() || order.platformShare || "";
      const workerPayout = workerPayoutInput?.value.trim() || order.workerPayout || "";
      const payload = await request(`/api/orders/${order.id}/completion`, {
        method: "POST",
        body: JSON.stringify({
          actualAmount,
          settlementStatus: "settled",
          completionNote,
          platformShare,
          workerPayout,
        }),
      });
      orders = payload.orders || orders;
      workers = payload.workers || workers;
      storeMeta = payload.store || storeMeta;
    }
    selectedArchiveOrderIds.clear();
    render();
  } finally {
    archiveBatchSettleBtn.disabled = false;
  }
}

function csvEscape(value) {
  const text = String(value ?? "");
  return `"${text.replaceAll('"', '""')}"`;
}

function buildCsvBlob(headers, rows, filename) {
  const content = [headers, ...rows].map((row) => row.map(csvEscape).join(",")).join("\n");
  return { blob: new Blob([`\uFEFF${content}`], { type: "text/csv;charset=utf-8;" }), filename };
}

function downloadCsv(headers, rows, filename) {
  const { blob } = buildCsvBlob(headers, rows, filename);
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function exportOrdersCsv() {
  const items = filteredOrders();
  if (!items.length) {
    alert("当前筛选下没有可导出的订单。");
    return;
  }
  const headers = [
    "订单号", "状态", "优先级", "运营标签",
    "客户", "电话", "地址",
    "服务类型", "预约时间", "草坪面积", "现场情况", "客户备注",
    "报价金额", "价格说明", "服务商", "实收金额",
    "平台分成", "服务商应结", "结算状态",
    "内部备注", "更新时间",
  ];
  const rows = items.map((order) => [
    order.id,
    statusLabels[order.status] || order.status,
    priorityLabel(order.priorityLevel),
    order.opsTag || "",
    order.user,
    order.phone,
    order.address,
    order.serviceType,
    order.requestedTime,
    order.lawnSize,
    order.condition,
    order.note || "",
    order.price || "",
    order.priceNote || "",
    workerName(order.assignedWorkerId),
    order.actualAmount || "",
    order.platformShare || "",
    order.workerPayout || "",
    settlementLabel(order.settlementStatus),
    order.internalNote || "",
    order.updatedAt,
  ]);
  const dateTag = new Date().toISOString().slice(0, 10);
  downloadCsv(headers, rows, `orders-export-${dateTag}.csv`);
}

function exportArchiveCsv() {
  const items = filteredArchivedOrders();
  if (!items.length) {
    alert("当前筛选下没有可导出的归档订单。");
    return;
  }
  const headers = [
    "订单号",
    "客户",
    "电话",
    "地址",
    "服务商",
    "预约时间",
    "完成时间",
    "报价金额",
    "实收金额",
    "平台分成",
    "服务商应结",
    "结算状态",
    "结算时间",
    "完成备注",
  ];
  const rows = items.map((order) => [
    order.id,
    order.user,
    order.phone,
    order.address,
    workerName(order.assignedWorkerId),
    order.requestedTime,
    order.updatedAt,
    order.price,
    order.actualAmount || order.price || "",
    order.platformShare || "",
    order.workerPayout || "",
    settlementLabel(order.settlementStatus),
    order.settledAt || "",
    order.completionNote || "",
  ]);
  const dateTag = new Date().toISOString().slice(0, 10);
  downloadCsv(headers, rows, `archive-export-${dateTag}.csv`);
}

async function resetDemo() {
  const payload = await request("/api/orders/reset-demo", { method: "POST" });
  hydrate(payload);
}

async function addDemoOrder() {
  const payload = await request("/api/orders/demo", { method: "POST" });
  hydrate(payload);
}

async function createOrder(formData) {
  const payload = await request("/api/orders", {
    method: "POST",
    body: JSON.stringify(formData),
  });
  selectedId = payload.order.id;
  hydrate(payload);
}

async function updateWorkerAvailability(workerId, available) {
  const payload = await request(`/api/workers/${workerId}/availability`, {
    method: "POST",
    body: JSON.stringify({ available }),
  });
  hydrate(payload);
}

async function updateWorkerProfile(workerId, formData) {
  const payload = await request(`/api/workers/${workerId}/profile`, {
    method: "POST",
    body: JSON.stringify(formData),
  });
  hydrate(payload);
}

searchInput.addEventListener("input", renderList);
statusFilter.addEventListener("change", renderList);
priorityFilter.addEventListener("change", renderList);
opsTagFilter.addEventListener("change", renderList);
dispatchStatusFilter.addEventListener("change", renderDispatchView);
dispatchAreaFilter.addEventListener("change", renderDispatchView);
dispatchPriorityFilter.addEventListener("change", renderDispatchView);
dispatchOpsTagFilter.addEventListener("change", renderDispatchView);
dispatchSortFilter.addEventListener("change", renderDispatchView);
dispatchDateFilter.addEventListener("change", renderDispatchView);
archiveSearchInput.addEventListener("input", renderArchiveView);
archiveWorkerFilter.addEventListener("change", renderArchiveView);
archiveSettlementFilter.addEventListener("change", renderArchiveView);
archiveDateFilter.addEventListener("change", renderArchiveView);
archiveMinAmount.addEventListener("input", renderArchiveView);
archiveMaxAmount.addEventListener("input", renderArchiveView);
archiveSelectAll.addEventListener("change", () => {
  const items = filteredArchivedOrders();
  if (archiveSelectAll.checked) {
    items.forEach((order) => selectedArchiveOrderIds.add(order.id));
  } else {
    items.forEach((order) => selectedArchiveOrderIds.delete(order.id));
  }
  renderArchiveView();
});
archiveBatchSettleBtn.addEventListener("click", async () => {
  try {
    await batchSettleArchiveOrders();
  } catch (error) {
    alert(error.message);
  }
});
archiveExportBtn.addEventListener("click", exportArchiveCsv);
document.querySelectorAll("[data-view]").forEach((button) => {
  button.addEventListener("click", () => {
    activeView = button.dataset.view;
    renderActiveView();
  });
});
document.getElementById("resetBtn").addEventListener("click", async () => {
  try {
    await resetDemo();
  } catch (error) {
    alert(error.message);
  }
});
document.getElementById("exportOrdersBtn").addEventListener("click", exportOrdersCsv);
document.getElementById("newOrderBtn").addEventListener("click", async () => {
  try {
    openOrderModal();
  } catch (error) {
    alert(error.message);
  }
});
document.getElementById("closeOrderModalBtn").addEventListener("click", closeOrderModal);
document.getElementById("cancelOrderModalBtn").addEventListener("click", closeOrderModal);
orderModal.addEventListener("click", (event) => {
  if (event.target === orderModal) {
    closeOrderModal();
  }
});
document.getElementById("closeWorkerModalBtn").addEventListener("click", closeWorkerModal);
document.getElementById("cancelWorkerModalBtn").addEventListener("click", closeWorkerModal);
workerModal.addEventListener("click", (event) => {
  if (event.target === workerModal) {
    closeWorkerModal();
  }
});
createOrderForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(createOrderForm);
  const payload = Object.fromEntries(form.entries());
  try {
    payload.requestedTime = buildRequestedTimeFromControls(payload);
    delete payload.requestedDate;
    delete payload.requestedStart;
    delete payload.requestedEnd;
    await createOrder(payload);
    closeOrderModal();
  } catch (error) {
    alert(error.message);
  }
});
workerProfileForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const workerId = workerProfileForm.dataset.workerId;
    if (!workerId) {
      return;
    }
    const form = new FormData(workerProfileForm);
    const payload = Object.fromEntries(form.entries());
    if (payload.lat !== undefined) {
      payload.lat = payload.lat === "" ? null : Number(payload.lat);
    }
    if (payload.lng !== undefined) {
      payload.lng = payload.lng === "" ? null : Number(payload.lng);
    }
    try {
      await updateWorkerProfile(workerId, payload);
      closeWorkerModal();
    } catch (error) {
      alert(error.message);
    }
  });

bootstrap().catch((error) => {
  dataMode.className = "status-pill fallback";
  dataMode.textContent = "加载失败";
  dataHint.textContent = error.message;
});

initAutocomplete();
