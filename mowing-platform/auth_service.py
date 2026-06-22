"""Verification code service / 邮箱验证码服务.

In dev mode (no SMTP configured), codes are printed to console.
In production, set SMTP_HOST / SMTP_PORT / SMTP_USER / SMTP_PASS to send real emails.
"""

from __future__ import annotations

import base64
import os
import random
import smtplib
import time
from email.mime.text import MIMEText
from typing import Any

# ── In-memory code storage / 内存验证码存储 ────────────────────────────
# code -> {"email": str, "expires_at": float}
_pending_codes: dict[str, dict[str, Any]] = {}

CODE_LENGTH = 6  # verification code length / 验证码长度
CODE_TTL = 600    # 10 minutes / 10分钟有效期


def strict_clerk_auth_enabled() -> bool:
    """Whether protected APIs must require verified Clerk JWTs."""
    return os.getenv("CLERK_AUTH_STRICT", "").strip().lower() in {"1", "true", "yes", "on"}


def extract_bearer_token(authorization: str = "") -> str:
    """Extract Bearer token from Authorization header."""
    value = authorization.strip()
    if not value.lower().startswith("bearer "):
        return ""
    return value.split(" ", 1)[1].strip()


def _split_env_list(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def derive_clerk_issuer_from_publishable_key(publishable_key: str) -> str:
    """Return Clerk issuer URL encoded in a publishable key, if available."""
    value = publishable_key.strip()
    if value.startswith("pk_test_"):
        encoded = value.removeprefix("pk_test_")
    elif value.startswith("pk_live_"):
        encoded = value.removeprefix("pk_live_")
    else:
        return ""

    padding = "=" * (-len(encoded) % 4)
    try:
        host = base64.urlsafe_b64decode(f"{encoded}{padding}").decode("utf-8").strip().rstrip("$")
    except Exception:
        return ""
    if not host:
        return ""
    return host if host.startswith(("http://", "https://")) else f"https://{host}"


def clerk_issuer_from_env() -> str:
    explicit = os.getenv("CLERK_ISSUER", "").strip()
    if explicit:
        return explicit

    for env_name in ("Clerk_Public_Key", "CLERK_PUBLISHABLE_KEY", "NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY"):
        issuer = derive_clerk_issuer_from_publishable_key(os.getenv(env_name, ""))
        if issuer:
            return issuer
    return ""


def verify_clerk_session_token(authorization: str = "") -> dict[str, Any] | None:
    """Verify Clerk session JWT when configured.

    Non-strict dev mode returns None when no token/key is present so legacy
    email/header flows keep working locally. Strict mode raises PermissionError.
    """
    token = extract_bearer_token(authorization)
    if not token:
        if strict_clerk_auth_enabled():
            raise PermissionError("Missing Clerk session token")
        return None

    jwt_key = os.getenv("CLERK_JWT_KEY", "").strip().replace("\\n", "\n")
    if not jwt_key:
        if strict_clerk_auth_enabled():
            raise PermissionError("CLERK_JWT_KEY is required when CLERK_AUTH_STRICT=1")
        return None

    try:
        import jwt
    except Exception as exc:  # pragma: no cover - depends on optional runtime dep
        raise PermissionError("PyJWT is required for Clerk token verification") from exc

    decode_options: dict[str, Any] = {"algorithms": ["RS256"], "options": {"verify_aud": False}}
    issuer = clerk_issuer_from_env()
    if issuer:
        decode_options["issuer"] = issuer
    audience = _split_env_list(os.getenv("CLERK_AUDIENCE", ""))
    if audience:
        decode_options["audience"] = audience[0] if len(audience) == 1 else audience
        decode_options["options"] = {"verify_aud": True}

    try:
        claims = jwt.decode(token, jwt_key, **decode_options)
    except Exception as exc:
        raise PermissionError("Clerk session token is not valid") from exc

    allowed_parties = _split_env_list(os.getenv("CLERK_AUTHORIZED_PARTIES", ""))
    azp = claims.get("azp")
    if allowed_parties and azp and azp not in allowed_parties:
        raise PermissionError("Clerk session token authorized party is not allowed")
    return claims


def _generate_code() -> str:
    """Generate a random numeric code / 生成随机数字验证码."""
    return "".join(str(random.randint(0, 9)) for _ in range(CODE_LENGTH))


def _cleanup_expired() -> None:
    """Remove expired codes / 清理过期验证码."""
    now = time.time()
    expired = [c for c, v in _pending_codes.items() if v["expires_at"] < now]
    for c in expired:
        del _pending_codes[c]


def send_verification_code(email: str) -> bool:
    """Send a verification code to the given email / 发送验证码到邮箱.

    Returns True if sent (or printed in dev mode), False on failure.
    """
    _cleanup_expired()
    code = _generate_code()
    _pending_codes[code] = {"email": email, "expires_at": time.time() + CODE_TTL}

    subject = "GardenOS 登录验证码 / Verification Code"
    body = f"您的验证码是 / Your code is: {code}\n\n有效期 10 分钟 / Expires in 10 minutes."

    smtp_host = os.getenv("SMTP_HOST")
    if smtp_host:
        # Production: send via SMTP / 生产环境走 SMTP
        try:
            msg = MIMEText(body, "plain", "utf-8")
            msg["Subject"] = subject
            msg["From"] = os.getenv("SMTP_USER", "")
            msg["To"] = email
            with smtplib.SMTP(
                smtp_host,
                int(os.getenv("SMTP_PORT", "587")),
                timeout=10,
            ) as server:
                server.starttls()
                server.login(
                    os.getenv("SMTP_USER", ""),
                    os.getenv("SMTP_PASS", ""),
                )
                server.send_message(msg)
        except Exception:
            return False
    else:
        # Dev mode: print to console / 开发模式打印到控制台
        print(f"\n{'='*50}")
        print(f"📧 验证码发送至 {email}")
        print(f"🔑 验证码: {code}")
        print("⏰ 有效期: 10 分钟")
        print(f"{'='*50}\n")

    return True


def verify_code(email: str, code: str) -> bool:
    """Verify a code for the given email / 验证邮箱验证码."""
    _cleanup_expired()
    entry = _pending_codes.get(code)
    if not entry:
        return False
    if entry["email"] != email:
        return False
    # Remove after successful verification / 验证成功后删除
    del _pending_codes[code]
    return True
