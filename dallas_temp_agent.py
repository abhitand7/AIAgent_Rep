#!/usr/bin/env python3
"""
Dallas Temperature Agent
Fetches the current Dallas, TX temperature (Open-Meteo, no API key needed)
and emails it to the recipient via Gmail SMTP.

Required environment variables (GitHub Actions secrets):
  GMAIL_USER          sending Gmail address
  GMAIL_APP_PASSWORD  16-character Google App Password
"""
import os
import smtplib
import ssl
import sys
from datetime import datetime
from email.message import EmailMessage
from zoneinfo import ZoneInfo

import requests

RECIPIENT = "sunriseky21@gmail.com"
LAT, LON = 32.7767, -96.7970  # Dallas, TX
TZ = ZoneInfo("America/Chicago")

API_URL = (
    "https://api.open-meteo.com/v1/forecast"
    f"?latitude={LAT}&longitude={LON}"
    "&current=temperature_2m,apparent_temperature,relative_humidity_2m,wind_speed_10m"
    "&temperature_unit=fahrenheit&wind_speed_unit=mph&timezone=America%2FChicago"
)


def fetch_weather() -> dict:
    resp = requests.get(API_URL, timeout=20)
    resp.raise_for_status()
    return resp.json()["current"]


def send_email(subject: str, body: str) -> None:
    user = os.environ["GMAIL_USER"].strip()
    # App passwords are shown with spaces; remove any whitespace/newlines.
    password = "".join(os.environ["GMAIL_APP_PASSWORD"].split())

    if "@" not in user:
        raise ValueError("GMAIL_USER secret must be a full email address")
    if len(password) != 16:
        raise ValueError(
            f"GMAIL_APP_PASSWORD should be 16 characters (got {len(password)}). "
            "Create a Google App Password, not your normal password."
        )

    msg = EmailMessage()
    msg["From"] = user
    msg["To"] = RECIPIENT
    msg["Subject"] = subject
    msg.set_content(body)

    ctx = ssl.create_default_context()
    errors = []

    # Attempt 1: port 587 with STARTTLS
    try:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as smtp:
            smtp.ehlo()
            smtp.starttls(context=ctx)
            smtp.ehlo()
            smtp.login(user, password)
            smtp.send_message(msg)
        return
    except Exception as exc:
        errors.append(f"587/STARTTLS: {type(exc).__name__}: {exc}")

    # Attempt 2: port 465 with SSL
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ctx, timeout=30) as smtp:
            smtp.login(user, password)
            smtp.send_message(msg)
        return
    except Exception as exc:
        errors.append(f"465/SSL: {type(exc).__name__}: {exc}")

    raise RuntimeError("Could not send email. " + " | ".join(errors))


def main() -> int:
    try:
        w = fetch_weather()
        now = datetime.now(TZ).strftime("%a %b %d, %I:%M %p %Z")
        temp = w["temperature_2m"]
        subject = f"Dallas temperature: {temp:.0f}°F ({now})"
        body = (
            f"Dallas, TX weather as of {now}\n\n"
            f"Temperature:  {temp:.1f}°F\n"
            f"Feels like:   {w['apparent_temperature']:.1f}°F\n"
            f"Humidity:     {w['relative_humidity_2m']}%\n"
            f"Wind:         {w['wind_speed_10m']} mph\n"
        )
        send_email(subject, body)
        print(f"[{now}] Sent: {subject}")
        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
