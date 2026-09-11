# -*- coding: utf-8 -*-
"""Capture les vraies vues de l'interface Strix Console en PNG via Playwright."""
import os
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(__file__)
SHOTS = os.path.join(HERE, "screenshots")
os.makedirs(SHOTS, exist_ok=True)
BASE = "http://localhost:3000"


def run():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1360, "height": 1000}, device_scale_factor=2)
        page = ctx.new_page()

        # 1) Page de connexion (contexte non authentifié)
        page.goto(f"{BASE}/login", wait_until="networkidle")
        page.wait_for_timeout(800)
        page.screenshot(path=os.path.join(SHOTS, "login.png"))
        print("login.png")

        # Connexion via le formulaire
        page.fill("#email", "admin@strix.local")
        page.fill("#password", "ChangeMe123!")
        page.click("button[type=submit]")
        page.wait_for_url("**/dashboard", timeout=15000)
        page.wait_for_timeout(1500)

        shots = [
            ("/dashboard", "dashboard.png", True),
            ("/assessments", "assessments.png", False),
            ("/assessments/1", "assessment_detail.png", True),
            ("/assessments/1/output", "engine_output.png", True),
            ("/schedules", "schedules.png", False),
            ("/roles", "roles.png", False),
        ]
        for path, name, full in shots:
            page.goto(f"{BASE}{path}", wait_until="networkidle")
            page.wait_for_timeout(1800)
            page.screenshot(path=os.path.join(SHOTS, name), full_page=full)
            print(name)

        browser.close()


if __name__ == "__main__":
    run()
