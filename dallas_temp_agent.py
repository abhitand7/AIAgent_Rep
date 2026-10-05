#!/usr/bin/env python3
"""
Dallas Temperature Agent
Fetches the current Dallas, TX temperature (Open-Meteo, no key needed)
and emails it using the Resend API (works from GitHub Actions, unlike Gmail SMTP).

Required environment variable (GitHub Actions secret):
  RESEND_API_KEY   API key from https://resend.com/api-keys
"""
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

RECIPIENT = "abhishek.a.tandon@capgemini.com"
SENDER = "Dallas Weather <onboarding@resend.dev>"  # Resend's built-in test sender
LAT, LON = 32.7767, -96.7970  # Dallas, TX
TZ = ZoneInfo("America/Chicago")

WEATHER_URL = (
    "https://api.open-meteo.com/v1/forecast"
    f"?latitude={LAT}&longitude={LON}"
    "&current=temperature_2m,apparent_temperature,relative_humidity_2m,wind_speed_10m"
    "&temperature_unit=fahrenheit&wind_speed_unit=mph&timezone=America%2FChicago"
)


def fetch_weather() -> dict:
    resp = requests.get(WEATHER_URL, timeout=20)
    resp.raise_for_status()
    return resp.json()["current"]


def send_email(subject: str, text: str) -> None:
    api_key = os.environ["RESEND_API_KEY"].strip()
    resp = requests.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {api_key}"},
        json={"from": SENDER, "to": [RECIPIENT], "subject": subject, "text": text},
        timeout=30,
    )
    if resp.status_code >= 300:
        raise RuntimeError(f"Resend API {resp.status_code}: {resp.text}")


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
