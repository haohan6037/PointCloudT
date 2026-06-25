export class PlanningApi {
  constructor(baseUrl) {
    this.baseUrl = baseUrl.replace(/\/$/, "");
    this.token = localStorage.getItem("planningDemoToken") || "";
  }

  setBaseUrl(baseUrl) {
    this.baseUrl = baseUrl.replace(/\/$/, "");
  }

  async ensureSession(email, password) {
    if (this.token) return this.token;

    const request = await this.post("/auth/email/request-code", { email }, false);
    const code = request.debug_code;
    if (!code) {
      throw new Error("Backend debug auth codes are disabled.");
    }

    const verified = await this.post("/auth/email/verify-code", { email, code }, false);
    const endpoint = verified.next_step === "set_password" ? "/auth/password/set" : "/auth/password/verify";
    const session = await this.post(endpoint, { verify_token: verified.verify_token, password }, false);
    this.token = session.access_token;
    localStorage.setItem("planningDemoToken", this.token);
    return this.token;
  }

  clearSession() {
    this.token = "";
    localStorage.removeItem("planningDemoToken");
  }

  async post(path, body, useAuth = true) {
    return this.request(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }, useAuth);
  }

  async get(path, useAuth = true) {
    return this.request(path, { method: "GET" }, useAuth);
  }

  async request(path, options, useAuth) {
    const headers = { ...(options.headers || {}) };
    if (useAuth) {
      if (!this.token) throw new Error("Missing demo session token.");
      headers.Authorization = `Bearer ${this.token}`;
    }

    const response = await fetch(`${this.baseUrl}${path}`, { ...options, headers });
    const text = await response.text();
    const payload = text ? JSON.parse(text) : {};
    if (!response.ok) {
      throw new Error(payload.detail || response.statusText);
    }
    return payload;
  }
}
