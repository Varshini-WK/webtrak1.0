from __future__ import annotations

import asyncio
import logging
import smtplib
from email.mime.text import MIMEText
from typing import Iterable

from app.core.settings import get_settings
from app.core.settings import Settings as AppSettings

logger = logging.getLogger(__name__)


def _split_addresses(raw: str | None) -> list[str]:
    if not raw:
        return []
    # Java-side code sometimes uses semicolon-separated strings for recipients.
    parts: list[str] = []
    for chunk in raw.replace(",", ";").split(";"):
        addr = chunk.strip()
        if addr:
            parts.append(addr)
    return parts


def _dedupe_keep_order(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for x in items:
        if x in seen:
            continue
        seen.add(x)
        out.append(x)
    return out


class EmailService:
    """
    SMTP-backed email delivery with Java-parity behavior:
    - Non-PROD environments redirect both `to` and `cc` to `smtp_sender`
    - HTML and plain text are sent using the right MIME subtype
    """

    def __init__(self, settings: AppSettings | None = None) -> None:
        self.settings = settings or get_settings()

    async def send_simple_email(self, to: str, subject: str, body: str, cc: str | None = None) -> None:
        await asyncio.to_thread(self._send_smtp, to=to, subject=subject, body=body, cc=cc, is_html=False)

    async def send_email(
        self, to: str, subject: str, body: str, cc: str | None = None, is_html: bool = True
    ) -> None:
        await asyncio.to_thread(self._send_smtp, to=to, subject=subject, body=body, cc=cc, is_html=is_html)

    def _send_smtp(self, *, to: str, subject: str, body: str, cc: str | None, is_html: bool) -> None:
        smtp_host = (self.settings.smtp_host or "").strip()
        smtp_sender = (self.settings.smtp_sender or "").strip()

        if not smtp_host or not smtp_sender:
            # Allow tests and local runs without email config.
            logger.info("SMTP is not configured; skipping email send.")
            return

        app_env = (self.settings.app_env or "").strip().lower()

        to_list = _split_addresses(to)
        cc_list = _split_addresses(cc) if cc else []

        # Java-parity safety: redirect all recipients in non-PROD.
        if app_env != "prod":
            to_list = [smtp_sender]
            cc_list = [smtp_sender]

        all_recipients = _dedupe_keep_order([*to_list, *cc_list])
        if not all_recipients:
            return

        mime_subtype = "html" if is_html else "plain"
        msg = MIMEText(body or "", mime_subtype, "utf-8")
        msg["Subject"] = subject
        msg["From"] = smtp_sender
        if to_list:
            msg["To"] = ", ".join(to_list)
        if cc_list:
            msg["Cc"] = ", ".join(cc_list)

        server: smtplib.SMTP | None = None
        try:
            server = smtplib.SMTP(self.settings.smtp_host, int(self.settings.smtp_port))
            if bool(self.settings.smtp_use_tls):
                server.starttls()
            if (self.settings.smtp_username or "").strip():
                server.login(self.settings.smtp_username, self.settings.smtp_password)
            server.sendmail(smtp_sender, all_recipients, msg.as_string())
        finally:
            if server is not None:
                try:
                    server.quit()
                except Exception:  # noqa: BLE001
                    server.close()

