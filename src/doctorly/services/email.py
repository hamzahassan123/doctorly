from __future__ import annotations

from datetime import UTC, datetime
from email.message import EmailMessage
from zoneinfo import ZoneInfo

import aiosmtplib

from doctorly.core.config import get_settings


def _format_ics(
    *,
    summary: str,
    start: datetime,
    end: datetime,
    location: str,
    description: str,
    uid: str,
) -> str:
    start_utc = start.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")
    end_utc = end.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")
    now = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return "\n".join(
        [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//Doctorly//Appointment//EN",
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{now}",
            f"DTSTART:{start_utc}",
            f"DTEND:{end_utc}",
            f"SUMMARY:{summary}",
            f"LOCATION:{location}",
            f"DESCRIPTION:{description}",
            "END:VEVENT",
            "END:VCALENDAR",
        ]
    )


async def send_booking_confirmation_email(
    *,
    recipient: str,
    summary: str,
    start: datetime,
    end: datetime,
    location: str,
    description: str,
    uid: str,
) -> bool:
    settings = get_settings()
    if not settings.smtp_host or not settings.smtp_username or not settings.smtp_password:
        return False

    message = EmailMessage()
    message["From"] = settings.email_from
    message["To"] = recipient
    message["Subject"] = summary
    message.set_content(
        "Your appointment has been confirmed. Please see the attached calendar invite."
    )
    message.add_attachment(
        _format_ics(
            summary=summary,
            start=start,
            end=end,
            location=location,
            description=description,
            uid=uid,
        ).encode("utf-8"),
        maintype="text",
        subtype="calendar",
        charset="utf-8",
        filename="appointment.ics",
    )

    await aiosmtplib.send(
        message,
        sender=settings.email_from,
        recipients=[recipient],
        hostname=settings.smtp_host,
        port=settings.smtp_port,
        username=settings.smtp_username,
        password=settings.smtp_password,
        use_tls=settings.smtp_use_tls,
        start_tls=settings.smtp_use_tls,
    )
    return True
