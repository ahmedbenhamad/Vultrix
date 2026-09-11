"""Outbound alerts: POST to a configured webhook when a significant finding lands.

Slack-formats the payload when the URL is a Slack incoming webhook; otherwise
sends a generic JSON body. Fire-and-forget from a daemon thread so it never
blocks or breaks the scan runner. Bypasses any proxy (internal tooling).
"""

import threading

import httpx

from app.core.config import settings

_SEV_RANK = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
_SEV_EMOJI = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵", "info": "⚪"}


def _meets_threshold(severity: str) -> bool:
    floor = _SEV_RANK.get(settings.ALERT_MIN_SEVERITY.lower(), 3)
    return _SEV_RANK.get(severity.lower(), 0) >= floor


def _payload(assessment_name: str, target: str, title: str, severity: str, cve: str | None) -> dict:
    emoji = _SEV_EMOJI.get(severity.lower(), "⚪")
    text = (
        f"{emoji} *{severity.upper()}* finding on *{assessment_name}* ({target})\n"
        f"{title}" + (f"  `{cve}`" if cve else "")
    )
    if "hooks.slack.com" in settings.ALERT_WEBHOOK_URL:
        return {"text": text}
    return {
        "event": "finding.discovered",
        "assessment": assessment_name,
        "target": target,
        "severity": severity,
        "title": title,
        "cve": cve,
        "text": text,
    }


def _send(body: dict) -> None:
    try:
        with httpx.Client(timeout=10, trust_env=False) as client:
            client.post(settings.ALERT_WEBHOOK_URL, json=body)
    except httpx.HTTPError:
        pass  # alerting must never break a scan


def notify_finding(assessment_name: str, target: str, title: str, severity: str, cve: str | None) -> None:
    if not settings.ALERT_WEBHOOK_URL or not _meets_threshold(severity):
        return
    body = _payload(assessment_name, target, title, severity, cve)
    threading.Thread(target=_send, args=(body,), daemon=True).start()
