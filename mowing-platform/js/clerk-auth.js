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

  function routeForRole(role) {
    if (role === "admin") return "/";
    if (role === "provider") return "/provider";
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
    return data.user;
  }

  async function mountSignIn(targetId) {
    const target = document.getElementById(targetId);
    if (!target) return;
    target.innerHTML = "";
    window.Clerk.mountSignIn(target, {
      signInFallbackRedirectUrl: window.location.pathname,
      signUpFallbackRedirectUrl: window.location.pathname,
      signInForceRedirectUrl: window.location.pathname,
      signUpForceRedirectUrl: window.location.pathname,
      appearance: {
        elements: {
          card: { boxShadow: "none", border: "0", backgroundColor: "transparent", padding: "0" },
        },
      },
    });
  }

  async function guardPage(options) {
    const requiredRole = options.requiredRole;
    const allowedRoles = Array.isArray(options.allowedRoles) ? options.allowedRoles : null;
    const loginStatusEl = options.loginStatusId ? document.getElementById(options.loginStatusId) : null;

    function setStatus(message) {
      if (loginStatusEl) loginStatusEl.innerHTML = message || "";
    }

    async function render() {
      if (!window.Clerk?.isSignedIn) {
        if (typeof options.onUnauthorized === "function") {
          options.onUnauthorized();
        }
        setStatus("");
        if (options.mountTargetId) {
          await mountSignIn(options.mountTargetId);
        }
        return;
      }

      const sessionUser = await syncCurrentUser();
      const nextPath = routeForRole(sessionUser.role);
      const roleAllowed = allowedRoles
        ? allowedRoles.includes(sessionUser.role)
        : !requiredRole || sessionUser.role === requiredRole;
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
    await ensureLoaded();
    window.Clerk.addListener(() => {
      render().catch((error) => setStatus(`❌ ${error.message}`));
    });
    await render().catch((error) => setStatus(`❌ ${error.message}`));
  }

  async function signOut() {
    if (!window.Clerk) return;
    await window.Clerk.signOut();
  }

  window.GardenOSAuth = {
    ensureLoaded,
    getPrimaryEmail,
    routeForRole,
    guardPage,
    signOut,
  };
})();
