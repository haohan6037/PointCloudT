const statusLabels = {
  pending_review: "待平台确认",
  quoted: "已报价",
  assigned: "已派单",
  accepted_by_worker: "服务商已接单",
  in_service: "服务中",
  completed: "已完成",
  cancelled: "已取消",
};

const workerApprovalLabels = {
  approved: "已审核",
  probation: "观察中",
  pending_info: "资料待补充",
};

let orders = [];
let workers = [];
let selectedId = "";
let storeMeta = { mode: "fallback", databaseEnabled: false, error: null };
let activeView = "orders";

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
const metricsSection = document.getElementById("metricsSection");
const pageTitle = document.getElementById("pageTitle");
const pageSubtitle = document.getElementById("pageSubtitle");
const dispatchStatusFilter = document.getElementById("dispatchStatusFilter");
const dispatchAreaFilter = document.getElementById("dispatchAreaFilter");
const dispatchDateFilter = document.getElementById("dispatchDateFilter");
const archiveSearchInput = document.getElementById("archiveSearchInput");
const archiveWorkerFilter = document.getElementById("archiveWorkerFilter");
const archiveDateFilter = document.getElementById("archiveDateFilter");

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
  if (order.status === "completed") return "已完成待归档";
  return statusLabels[order.status] || "待处理";
}

function suggestWorkers(order) {
  const area = orderArea(order);
  const assigned = order.assignedWorkerId;
  const candidates = workers.filter((worker) => worker.available || worker.id === assigned);
  const matched = candidates.filter((worker) => worker.area === area);
  return (matched.length ? matched : candidates).slice(0, 3);
}

function filteredDispatchOrders() {
  const selectedStatus = dispatchStatusFilter.value;
  const selectedArea = dispatchAreaFilter.value;
  const selectedDate = dispatchDateFilter.value;
  return orders
    .filter((order) => !["cancelled", "completed"].includes(order.status))
    .filter((order) => {
      if (selectedStatus === "needs_quote") return order.status === "pending_review";
      if (selectedStatus === "needs_assign") return order.status === "quoted";
      if (selectedStatus === "assigned") {
        return order.status === "assigned" || order.status === "accepted_by_worker";
      }
      if (selectedStatus === "in_service") return order.status === "in_service";
      return true;
    })
    .filter((order) => selectedArea === "all" || orderArea(order) === selectedArea)
    .filter((order) => !selectedDate || orderDate(order) === selectedDate)
    .sort((a, b) => `${orderDate(a)} ${a.requestedTime}`.localeCompare(`${orderDate(b)} ${b.requestedTime}`));
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
            <span>当前报价</span><strong>${money(order.price)}</strong>
            <span>已派服务商</span><strong>${workerName(order.assignedWorkerId)}</strong>
          </div>
          <div>
            <div class="suggestion-row">
              ${candidates
                .map((worker) => `<span class="suggestion-chip">${worker.name} · ${worker.area}</span>`)
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
                    (worker) => `
                      <option value="${worker.id}" ${worker.id === order.assignedWorkerId ? "selected" : ""}>
                        ${worker.name} · ${worker.area}
                      </option>
                    `,
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
            ${order.status === "in_service" ? `<button class="btn primary" type="button" data-dispatch-status="${order.id}" data-next-status="completed">标记已完成</button>` : ""}
          </div>
          <div class="dispatch-hint">
            ${disabledAssign ? "还没有报价，先在订单详情保存价格后再派单。" : "派单后可以继续推进到“已接单”、“服务中”和“已完成”。"}
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
  const date = archiveDateFilter.value;
  return orders
    .filter((order) => order.status === "completed")
    .filter((order) => workerId === "all" || order.assignedWorkerId === workerId)
    .filter((order) => !date || orderDate(order) === date)
    .filter((order) => {
      const source = `${order.id} ${order.user} ${order.address}`.toLowerCase();
      return !keyword || source.includes(keyword);
    })
    .sort((a, b) => `${orderDate(b)} ${b.updatedAt}`.localeCompare(`${orderDate(a)} ${a.updatedAt}`));
}

function renderArchiveSummary(items) {
  const totalRevenue = items.reduce((sum, order) => sum + (Number(order.price) || 0), 0);
  const uniqueWorkers = new Set(items.map((order) => order.assignedWorkerId).filter(Boolean)).size;
  const averageTicket = items.length ? totalRevenue / items.length : 0;
  const summary = [
    { label: "已完成订单", value: items.length },
    { label: "已完成金额", value: money(totalRevenue).replace(".00", "") },
    { label: "参与服务商", value: uniqueWorkers },
    { label: "平均客单", value: money(averageTicket).replace(".00", "") },
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
  if (!items.length) {
    target.innerHTML = `<div class="empty">当前筛选下还没有已完成订单</div>`;
    return;
  }
  target.innerHTML = items
    .map((order) => `
      <article class="archive-card">
        <header>
          <div>
            <h4>${order.id} · ${order.user}</h4>
            <p>${order.address}</p>
          </div>
          <span class="badge completed">已完成</span>
        </header>
        <div class="archive-grid">
          <span>完成时间</span><strong>${order.updatedAt}</strong>
          <span>服务商</span><strong>${workerName(order.assignedWorkerId)}</strong>
          <span>成交金额</span><strong>${money(order.price)}</strong>
          <span>预约时间</span><strong>${order.requestedTime}</strong>
        </div>
      </article>
    `)
    .join("");
}

function renderArchiveRanking(items) {
  const target = document.getElementById("archiveRankingList");
  document.getElementById("archiveRankingCaption").textContent = archiveDateFilter.value || "全部完成日期";
  const ranking = workers
    .map((worker) => {
      const workerOrders = items.filter((order) => order.assignedWorkerId === worker.id);
      const total = workerOrders.reduce((sum, order) => sum + (Number(order.price) || 0), 0);
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

function money(value) {
  return value ? `$${Number(value).toLocaleString("en-NZ")}` : "未报价";
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
  return orders.filter((order) => {
    const matchesStatus = status === "all" || order.status === status;
    const source = `${order.id} ${order.user} ${order.address}`.toLowerCase();
    return matchesStatus && (!keyword || source.includes(keyword));
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
            <button class="order-row ${order.id === selectedId ? "active" : ""}" type="button" data-id="${order.id}">
              <span class="order-main">
                <span class="order-title">
                  <strong>${order.id}</strong>
                  <span class="badge ${order.status}">${statusLabels[order.status]}</span>
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
        </div>
      </div>
    </section>

    <section class="detail-section">
      <h4>草坪照片占位</h4>
      <div class="photo-strip">
        ${order.photos.map((photo) => `<div class="photo">${photo}</div>`).join("")}
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
      </div>
      <div class="form-grid" style="margin-top: 12px;">
        <div class="field">
          <label for="workerSelect">选择服务商</label>
          <select class="select" id="workerSelect">
            <option value="">未派单</option>
            ${workers
              .filter((worker) => worker.available || worker.id === order.assignedWorkerId)
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
        <button class="btn" type="button" id="acceptBtn">标记服务商已接单</button>
        ${order.status === "accepted_by_worker" ? '<button class="btn" type="button" id="startServiceBtn">标记服务中</button>' : ""}
        ${order.status === "in_service" ? '<button class="btn primary" type="button" id="completeServiceBtn">标记已完成</button>' : ""}
      </div>
    </section>

    <section class="detail-section">
      <h4>处理记录</h4>
      <ul class="activity">
        ${order.activity.map((item) => `<li>${item}</li>`).join("")}
      </ul>
    </section>
  `;

  document.getElementById("saveQuoteBtn").addEventListener("click", saveQuote);
  document.getElementById("assignBtn").addEventListener("click", assignWorker);
  document.getElementById("acceptBtn").addEventListener("click", acceptByWorker);
  document.getElementById("startServiceBtn")?.addEventListener("click", startService);
  document.getElementById("completeServiceBtn")?.addEventListener("click", completeService);
}

function renderWorkersView() {
  workersView.innerHTML = workers
    .map(
      (worker) => `
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
      `,
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
}

function renderActiveView() {
  const orderMode = activeView === "orders";
  const dispatchMode = activeView === "dispatch";
  const archiveMode = activeView === "archive";
  const workerMode = activeView === "workers";
  ordersView.classList.toggle("hidden", !orderMode);
  metricsSection.classList.toggle("hidden", !orderMode);
  dispatchView.classList.toggle("hidden", !dispatchMode);
  archiveView.classList.toggle("hidden", !archiveMode);
  workersView.classList.toggle("hidden", !workerMode);
  if (orderMode) {
    pageTitle.textContent = "订单管理";
    pageSubtitle.textContent = "阶段 1：平台先能接住业务，再逐步开放用户端和服务商端。";
  } else if (dispatchMode) {
    pageTitle.textContent = "派单看板";
    pageSubtitle.textContent = "先把待报价、待派单和服务商日程放在一个视图里，方便当天排活。";
  } else if (archiveMode) {
    pageTitle.textContent = "完成归档";
    pageSubtitle.textContent = "把已完成订单沉到一个单独视图里，方便对账、回看和统计服务商产出。";
  } else {
    pageTitle.textContent = "服务商管理";
    pageSubtitle.textContent = "阶段 1：先把服务商资料、服务区域和平台派单边界管理清楚。";
  }
  document.querySelectorAll("[data-view]").forEach((button) => {
    button.classList.toggle("active", button.dataset.view === activeView);
  });
  document.getElementById("newOrderBtn").style.display = orderMode ? "inline-flex" : "none";
  if (dispatchMode) {
    renderDispatchView();
  } else if (archiveMode) {
    renderArchiveView();
  } else if (!orderMode) {
    renderWorkersView();
  }
}

function render() {
  renderStatusBanner();
  renderMetrics();
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

async function startService() {
  const order = selectedOrder();
  await updateOrderStatus(order.id, "in_service");
}

async function completeService() {
  const order = selectedOrder();
  await updateOrderStatus(order.id, "completed");
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
dispatchStatusFilter.addEventListener("change", renderDispatchView);
dispatchAreaFilter.addEventListener("change", renderDispatchView);
dispatchDateFilter.addEventListener("change", renderDispatchView);
archiveSearchInput.addEventListener("input", renderArchiveView);
archiveWorkerFilter.addEventListener("change", renderArchiveView);
archiveDateFilter.addEventListener("change", renderArchiveView);
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
