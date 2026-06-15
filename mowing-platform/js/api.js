// API and action functions / API 请求和操作函数
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

