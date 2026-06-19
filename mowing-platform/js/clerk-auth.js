(function () {
  const PUBLISHABLE_KEY =
    window.__GARDENOS_CLERK_PUBLISHABLE_KEY__ ||
    window.localStorage.getItem("GARDENOS_CLERK_PUBLISHABLE_KEY") ||
    "";
  let loaded = false;
  let pending = null;

  function getClerkDomain(publishableKey) {
    return atob(publishableKey.split("_")[2]).slice(0, -1);
  }

  function loadScript(src, attrs) {
    return new Promise((resolve, reject) => {
      const script = document.createElement("script");
      script.src = src;
      script.async = true;
      script.crossOrigin = "anonymous";
      Object.entries(attrs || {}).forEach(([key, value]) => script.setAttribute(key, value));
      script.onload = resolve;
      script.onerror = () => reject(new Error(`Failed to load script: ${src}`));
      document.head.appendChild(script);
    });
  }

  async function ensureLoaded() {
    if (loaded) return;
    if (pending) return pending;
    pending = (async () => {
      if (!PUBLISHABLE_KEY) {
        throw new Error("Clerk Publishable Key 未配置");
      }
      const clerkDomain = getClerkDomain(PUBLISHABLE_KEY);
      await loadScript(`https://${clerkDomain}/npm/@clerk/ui@1/dist/ui.browser.js`);
      await loadScript(
        `https://${clerkDomain}/npm/@clerk/clerk-js@6/dist/clerk.browser.js`,
        { "data-clerk-publishable-key": PUBLISHABLE_KEY },
      );
      await window.Clerk.load({
        ui: { ClerkUI: window.__internal_ClerkUICtor },
      });
      loaded = true;
    })();
    return pending;
  }

  function getPrimaryEmail(user) {
    return (
      user?.primaryEmailAddress?.emailAddress ||
      user?.emailAddresses?.[0]?.emailAddress ||
      ""
    );
  }

  function getDisplayName(user) {
    return (
      [user?.firstName, user?.lastName].filter(Boolean).join(" ").trim() ||
      user?.username ||
      getPrimaryEmail(user)
    );
  }

  function normalizeRole(role) {
    if (role === "provider") return "server";
    return role || "customer";
  }

  function routeForRole(role) {
    const normalizedRole = normalizeRole(role);
    if (normalizedRole === "admin") return "/";
    if (normalizedRole === "server") return "/provider";
    return "/customer";
  }

  async function syncCurrentUser() {
    const user = window.Clerk?.user;
    const email = getPrimaryEmail(user);
    if (!email) {
      throw new Error("当前 Clerk 账号没有可用邮箱");
    }
    const resp = await fetch("/api/session/sync", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email,
        clerkUserId: user?.id || "",
        displayName: getDisplayName(user),
      }),
    });
    const data = await resp.json();
    if (!resp.ok) {
      throw new Error(data.detail || "同步登录状态失败");
    }
    return { ...data.user, role: normalizeRole(data.user?.role) };
  }

  async function mountSignIn(targetId) {
    const target = document.getElementById(targetId);
    if (!target) return;
    target.innerHTML = "";
    window.Clerk.mountSignIn(target, {
      signInFallbackRedirectUrl: window.location.pathname,
      signUpFallbackRedirectUrl: window.location.pathname,
      appearance: {
        elements: {
          card: { boxShadow: "none", border: "0", backgroundColor: "transparent", padding: "0" },
        },
      },
    });
  }

  async function mountSignUp(targetId) {
    const target = document.getElementById(targetId);
    if (!target) return;
    target.innerHTML = "";
    window.Clerk.mountSignUp(target, {
      signInFallbackRedirectUrl: window.location.pathname,
      signUpFallbackRedirectUrl: window.location.pathname,
      appearance: {
        elements: {
          card: { boxShadow: "none", border: "0", backgroundColor: "transparent", padding: "0" },
        },
      },
    });
  }

  function _showKeySetup(statusEl, mountTargetId) {
    if (!statusEl) return;
    const targetEl = mountTargetId ? document.getElementById(mountTargetId) : null;
    const container = targetEl || statusEl;
    container.innerHTML = `
      <div style="padding:8px 0;color:var(--portal-ink, #2D3A31);">
        <p style="margin-bottom:8px;font-weight:600;">⚙️ 配置 Clerk 密钥</p>
        <p style="font-size:13px;color:var(--portal-muted, #6E7568);margin-bottom:12px;">
          请从 <a href="https://dashboard.clerk.com" target="_blank" style="color:var(--portal-sage-dark, #6B7A65);">Clerk Dashboard</a>
          复制 Publishable Key，粘贴到下方后保存。
        </p>
        <input id="__gardenos_key_input"
               type="text"
               placeholder="pk_live_... 或 pk_test_..."
               style="width:100%;padding:10px 12px;border:1px solid var(--portal-line, #E6E2DA);border-radius:8px;font-size:14px;margin-bottom:10px;" />
        <button id="__gardenos_key_save"
                style="padding:8px 20px;background:var(--portal-sage, #8C9A84);color:#fff;border:none;border-radius:8px;cursor:pointer;font-size:14px;font-weight:600;">
          保存密钥并刷新
        </button>
        <span id="__gardenos_key_msg" style="margin-left:10px;font-size:13px;"></span>
      </div>`;
    document.getElementById("__gardenos_key_save").addEventListener("click", () => {
      const input = document.getElementById("__gardenos_key_input");
      const msg = document.getElementById("__gardenos_key_msg");
      const key = input.value.trim();
      if (!key) { msg.innerHTML = "❌ 请输入密钥"; return; }
      if (!key.startsWith("pk_")) { msg.innerHTML = "❌ 密钥格式不正确，应以 pk_ 开头"; return; }
      window.localStorage.setItem("GARDENOS_CLERK_PUBLISHABLE_KEY", key);
      msg.innerHTML = "✅ 已保存，刷新页面...";
      setTimeout(() => window.location.reload(), 600);
    });
  }

  async function guardPage(options) {
    const requiredRole = options.requiredRole;
    const allowedRoles = Array.isArray(options.allowedRoles) ? options.allowedRoles : null;
    const loginStatusEl = options.loginStatusId ? document.getElementById(options.loginStatusId) : null;
    const authMode = options.mode === "signUp" ? "signUp" : "signIn";

    function setStatus(message) {
      if (loginStatusEl) loginStatusEl.innerHTML = message || "";
    }

    async function render() {
      if (!window.Clerk?.isSignedIn) {
        // ── Don't disrupt an active multi-step sign-in flow ──────────────
        // When the user has entered their email and Clerk transitions to the
        // password step (or any subsequent factor), isSignedIn is still false.
        // The Clerk listener fires, and without this guard we would call
        // onUnauthorized() → mountSignIn() which does target.innerHTML = ""
        // and remounts from scratch, resetting back to the identifier screen.
        const signIn = window.Clerk?.client?.signIn;
        const hasActiveSignIn =
          signIn &&
          signIn.status &&
          signIn.status !== "needs_identifier" &&
          signIn.status !== "abandoned";

        if (hasActiveSignIn) {
          setStatus("");
          return;
        }

        if (typeof options.onUnauthorized === "function") {
          options.onUnauthorized();
        }
        setStatus("");
        if (options.mountTargetId) {
          if (authMode === "signUp") {
            await mountSignUp(options.mountTargetId);
          } else {
            await mountSignIn(options.mountTargetId);
          }
        }
        return;
      }

      const sessionUser = await syncCurrentUser();
      const nextPath = routeForRole(sessionUser.role);
      const isAdmin = sessionUser.role === "admin";
      const normalizedAllowedRoles = allowedRoles ? allowedRoles.map(normalizeRole) : null;
      const normalizedRequiredRole = normalizeRole(requiredRole);
      const roleAllowed = allowedRoles
        ? isAdmin || normalizedAllowedRoles.includes(sessionUser.role)
        : isAdmin || !requiredRole || sessionUser.role === normalizedRequiredRole;
      if (!roleAllowed) {
        if (window.location.pathname !== nextPath) {
          window.location.assign(nextPath);
        }
        return;
      }

      setStatus("");
      if (typeof options.onAuthorized === "function") {
        await options.onAuthorized({
          clerkUser: window.Clerk.user,
          sessionUser,
        });
      }
    }

    setStatus("⏳ 正在加载登录组件...");
    const loadingTimeout = setTimeout(() => {
      if (loginStatusEl && loginStatusEl.innerHTML.includes("正在加载登录组件")) {
        setStatus("❌ 登录加载超时，请刷新页面重试。如持续出现，请打开浏览器控制台（F12）查看错误详情。");
      }
    }, 10_000);
    try {
      await ensureLoaded();
    } catch (error) {
      clearTimeout(loadingTimeout);
      if (error.message && error.message.includes("Publishable Key")) {
        _showKeySetup(loginStatusEl, options.mountTargetId);
      } else {
        setStatus(`❌ 登录组件加载失败：${error.message}`);
      }
      return;
    }
    window.Clerk.addListener(() => {
      render().catch((error) => { clearTimeout(loadingTimeout); setStatus(`❌ ${error.message}`); });
    });
    await render().then(
      () => clearTimeout(loadingTimeout),
      (error) => { clearTimeout(loadingTimeout); setStatus(`❌ ${error.message}`); },
    );
  }

  async function signOut() {
    if (!window.Clerk) return;
    await window.Clerk.signOut();
  }

  window.GardenOSAuth = {
    ensureLoaded,
    getPrimaryEmail,
    normalizeRole,
    routeForRole,
    guardPage,
    signOut,
    mountSignIn,
    mountSignUp,
  };
})();
