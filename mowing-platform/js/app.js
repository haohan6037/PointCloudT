// Entry point / 入口 — event binding and bootstrap
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
document.getElementById("openCustomerPortalBtn").addEventListener("click", () => {
  window.location.assign("/customer");
});
document.getElementById("openProviderPortalBtn").addEventListener("click", () => {
  window.location.assign("/provider");
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

// bootstrap() 已移至 admin-prototype.html 的 onAuthorized 回调中
// 确保登录成功后才拉取数据

initAutocomplete();
