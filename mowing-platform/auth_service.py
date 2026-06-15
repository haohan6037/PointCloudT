"""Verification code service / 邮箱验证码服务.

In dev mode (no SMTP configured), codes are printed to console.
In production, set SMTP_HOST / SMTP_PORT / SMTP_USER / SMTP_PASS to send real emails.
"""

from __future__ import annotations

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
        print(f"⏰ 有效期: 10 分钟")
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
