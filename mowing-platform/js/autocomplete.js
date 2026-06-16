// Address autocomplete widget / 地址自动补全组件
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
