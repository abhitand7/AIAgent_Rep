#!/usr/bin/env python3
"""
Dallas Temperature Agent
Fetches the current Dallas, TX temperature (Open-Meteo, no API key needed)
and emails it to the recipient.

SETUP
1. Turn on 2-Step Verification for the sending Gmail account, then create an
   App Password: https://myaccount.google.com/apppasswords
2. Set environment variables:
     export GMAIL_USER="your_sending_address@gmail.com"
     export GMAIL_APP_PASSWORD="xxxx xxxx xxxx xxxx"
3. Test once:  python3 dallas_temp_agent.py
4. Schedule every 4 hours (Linux/macOS) with `crontab -e`:
     0 */4 * * * GMAIL_USER="you@gmail.com" GMAIL_APP_PASSWORD="xxxx" /usr/bin/python3 /path/to/dallas_temp_agent.py >> /tmp/dallas_temp.log 2>&1
   Windows: use Task Scheduler with a trigger repeating every 4 hours.
"""
import os
import smtplib
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
    user = os.environ["GMAIL_USER"]
    password = os.environ["GMAIL_APP_PASSWORD"]

    msg = EmailMessage()
    msg["From"] = user
    msg["To"] = RECIPIENT
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as smtp:
        smtp.login(user, password)
        smtp.send_message(msg)


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
