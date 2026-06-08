const statusLabels = {
  pending_review: "待平台确认",
  quoted: "已报价",
  assigned: "已派单",
  accepted_by_worker: "割草工已接单",
  cancelled: "已取消",
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
const workersView = document.getElementById("workersView");
const ordersView = document.getElementById("ordersView");
const metricsSection = document.getElementById("metricsSection");
const pageTitle = document.getElementById("pageTitle");
const pageSubtitle = document.getElementById("pageSubtitle");

function money(value) {
  return value ? `$${Number(value).toLocaleString("en-NZ")}` : "未报价";
}

function workerName(id) {
  const worker = workers.find((item) => item.id === id);
  return worker ? worker.name : "未派单";
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
    count("assigned") + count("accepted_by_worker");
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
        <span>割草工状态</span><strong>${order.assignedWorkerId ? "已分配" : "待分配"}</strong>
      </div>
      <div class="form-grid" style="margin-top: 12px;">
        <div class="field">
          <label for="workerSelect">选择割草工</label>
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
        <button class="btn" type="button" id="acceptBtn">标记割草工已接单</button>
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
}

function renderWorkersView() {
  workersView.innerHTML = workers
    .map(
      (worker) => `
        <article class="worker-card">
          <div class="worker-head">
            <div>
              <h3>${worker.name}</h3>
              <p>${worker.id}</p>
            </div>
            <span class="worker-badge ${worker.available ? "available" : "unavailable"}">
              ${worker.available ? "可接单" : "暂停接单"}
            </span>
          </div>
          <div class="worker-meta">
            <div><span>服务区域</span><br /><strong>${worker.area}</strong></div>
            <div><span>当前状态</span><br /><strong>${worker.available ? "平台可派单" : "暂不参与派单"}</strong></div>
          </div>
          <div class="worker-actions">
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
}

function renderActiveView() {
  const orderMode = activeView === "orders";
  ordersView.classList.toggle("hidden", !orderMode);
  metricsSection.classList.toggle("hidden", !orderMode);
  workersView.classList.toggle("hidden", orderMode);
  pageTitle.textContent = orderMode ? "订单管理" : "割草工管理";
  pageSubtitle.textContent = orderMode
    ? "阶段 1：平台先能接住业务，再逐步开放用户端和割草工端。"
    : "阶段 1：先把可接单人员、服务区域和平台派单边界管理清楚。";
  document.querySelectorAll("[data-view]").forEach((button) => {
    button.classList.toggle("active", button.dataset.view === activeView);
  });
  document.getElementById("newOrderBtn").style.display = orderMode ? "inline-flex" : "none";
  if (!orderMode) {
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
  document.getElementById("createUser").focus();
}

function closeOrderModal() {
  orderModal.classList.remove("open");
  orderModal.setAttribute("aria-hidden", "true");
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
    alert("请选择可接单割草工。");
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
    alert("请先派单，再标记割草工接单。");
    return;
  }
  const payload = await request(`/api/orders/${order.id}/accept`, { method: "POST" });
  hydrate(payload);
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

searchInput.addEventListener("input", renderList);
statusFilter.addEventListener("change", renderList);
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
createOrderForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(createOrderForm);
  const payload = Object.fromEntries(form.entries());
  try {
    await createOrder(payload);
    closeOrderModal();
  } catch (error) {
    alert(error.message);
  }
});

bootstrap().catch((error) => {
  dataMode.className = "status-pill fallback";
  dataMode.textContent = "加载失败";
  dataHint.textContent = error.message;
});
