#!/usr/bin/env python3
"""
Dallas Temperature Agent (with Claude Sonnet weekly outlook)

1. Fetches current Dallas, TX conditions + last 7 days + 7-day model forecast (Open-Meteo).
2. Asks Claude Sonnet to write a next-week temperature prediction from that data.
3. Emails everything via the Resend API.

Required environment variables (GitHub Actions secrets):
  RESEND_API_KEY     from https://resend.com/api-keys
  ANTHROPIC_API_KEY  from https://console.anthropic.com/
"""
import json
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

RECIPIENT = "abhishek.a.tandon@capgemini.com
SENDER = "Dallas Weather <onboarding@resend.dev>"  # Resend's built-in test sender
CLAUDE_MODEL = "claude-sonnet-5-5"
LAT, LON = 32.7767, -96.7970  # Dallas, TX
TZ = ZoneInfo("America/Chicago")

WEATHER_URL = (
    "https://api.open-meteo.com/v1/forecast"
    f"?latitude={LAT}&longitude={LON}"
    "&current=temperature_2m,apparent_temperature,relative_humidity_2m,wind_speed_10m"
    "&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max"
    "&past_days=7&forecast_days=7"
    "&temperature_unit=fahrenheit&wind_speed_unit=mph&timezone=America%2FChicago"
)


def fetch_weather() -> dict:
    resp = requests.get(WEATHER_URL, timeout=20)
    resp.raise_for_status()
    return resp.json()


def split_daily(daily: dict):
    """Return (past_rows, future_rows); each row is a dict for one day."""
    today = datetime.now(TZ).strftime("%Y-%m-%d")
    past, future = [], []
    for i, day in enumerate(daily["time"]):
        row = {
            "date": day,
            "high_f": daily["temperature_2m_max"][i],
            "low_f": daily["temperature_2m_min"][i],
            "rain_chance_pct": daily["precipitation_probability_max"][i],
        }
        (past if day < today else future).append(row)
    return past, future


def ask_claude(current: dict, past: list, future: list) -> str:
    api_key = os.environ["ANTHROPIC_API_KEY"].strip()
    data = {"current": current, "last_7_days": past, "model_forecast_next_7_days": future}
    prompt = (
        "You are a weather analyst. Using ONLY the data below for Dallas, TX "
        "(current conditions, the past 7 days, and a numerical model forecast for the "
        "next 7 days), write a concise next-week temperature outlook for a regular person.\n\n"
        "Include:\n"
        "1. A day-by-day prediction (day name, expected high/low in °F).\n"
        "2. The overall trend vs. the past week (warming, cooling, steady).\n"
        "3. Any notable risks (rain, big temperature swings).\n"
        "4. One line on confidence (later days are less certain).\n\n"
        "Plain text only, no markdown, under 220 words. Do not invent data.\n\n"
        f"DATA:\n{json.dumps(data)}"
    )
    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": CLAUDE_MODEL,
            "max_tokens": 700,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=60,
    )
    if resp.status_code >= 300:
        raise RuntimeError(f"Anthropic API {resp.status_code}: {resp.text}")
    blocks = resp.json()["content"]
    return "".join(b.get("text", "") for b in blocks if b.get("type") == "text").strip()


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
        raw = fetch_weather()
        cur = raw["current"]
        past, future = split_daily(raw["daily"])
        now = datetime.now(TZ).strftime("%a %b %d, %I:%M %p %Z")
        temp = cur["temperature_2m"]

        try:
            outlook = ask_claude(cur, past, future)
        except Exception as exc:  # still send the raw data if the LLM fails
            print(f"Warning: Claude step failed: {exc}", file=sys.stderr)
            outlook = "(AI outlook unavailable this run.)"

        table = "\n".join(
            f"  {d['date']}: high {d['high_f']:.0f}°F / low {d['low_f']:.0f}°F, "
            f"rain {d['rain_chance_pct']}%"
            for d in future
        )
        body = (
            f"Dallas, TX weather as of {now}\n\n"
            f"Now: {temp:.1f}°F (feels like {cur['apparent_temperature']:.1f}°F), "
            f"humidity {cur['relative_humidity_2m']}%, wind {cur['wind_speed_10m']} mph\n\n"
            f"--- AI next-week outlook (Claude Sonnet) ---\n{outlook}\n\n"
            f"--- Model forecast data ---\n{table}\n\n"
            "Predictions are AI-generated from forecast data and may be wrong."
        )
        subject = f"Dallas: {temp:.0f}°F now + next-week outlook ({now})"
        send_email(subject, body)
        print(f"[{now}] Sent: {subject}")
        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
