"""Kontrola ceny zajazdu VOI Baia di Tindari na Fischer.cz.

Nacita stranku cez Playwright (ceny su renderovane JavaScriptom),
najde aktualnu cenu, porovna s ulozenou najnizsou cenou v price.json
a pri zlacneni posle push notifikaciu cez ntfy.
"""

import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = "https://www.fischer.cz/italie/sicilie/voi-baia-di-tindari-resort"
STATE_FILE = Path("price.json")
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "").strip()
NTFY_SERVER = os.environ.get("NTFY_SERVER", "https://ntfy.sh").rstrip("/")


def notify(title, message, priority="default", tags="airplane"):
    if not NTFY_TOPIC:
        print("NTFY_TOPIC nie je nastaveny - notifikacia sa neposiela.")
        return
    req = urllib.request.Request(
        f"{NTFY_SERVER}/{NTFY_TOPIC}",
        data=message.encode("utf-8"),
        headers={
            "Title": title,
            "Priority": priority,
            "Tags": tags,
            "Click": URL,
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        print(f"ntfy: {resp.status}")


def get_page_text():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
            ),
            locale="cs-CZ",
        )
        page.goto(URL, wait_until="domcontentloaded", timeout=90000)
        text = ""
        for _ in range(30):
            page.wait_for_timeout(2000)
            text = page.inner_text("body")
            if "Kč" in text and re.search(r"Celkem", text):
                break
        browser.close()
    return text


def parse_price(text):
    """Vrati (cena_v_kc, popis_terminu)."""
    m = re.search(r"Celkem(?:\s+za\s+všechny)?\s*\n?\s*([\d\s\u00a0]{4,12})Kč", text)
    if m:
        price = int(re.sub(r"\D", "", m.group(1)))
        term = ""
        t = re.search(
            r"(\d{1,2}\.\s?\d{1,2}\.\s?\d{2})\s*\(\w+\)\s*-\s*(\d{1,2}\.\s?\d{1,2}\.\s?\d{2})",
            text,
        )
        if t:
            term = f"{t.group(1)} - {t.group(2)}"
        return price, term or "najblizsi termin"
    prices = [
        int(re.sub(r"\D", "", p))
        for p in re.findall(r"Od\s*([\d\s\u00a0]{4,12})Kč", text)
    ]
    prices = [p for p in prices if p > 5000]
    if prices:
        return min(prices), "najlacnejsi termin zo zoznamu (fallback)"
    return None, None


def main():
    text = get_page_text()
    price, term = parse_price(text)
    if price is None:
        print("Cenu sa nepodarilo najst na stranke!")
        notify(
            "Fischer watch: chyba",
            "Nepodarilo sa nacitat cenu zo stranky. Skontroluj workflow log.",
            priority="low",
            tags="warning",
        )
        return 1

    now = time.strftime("%Y-%m-%d %H:%M")
    print(f"{now} | {term} | {price} Kc")

    if STATE_FILE.exists():
        state = json.loads(STATE_FILE.read_text())
        first_run = False
    else:
        state = {"lowest": price, "baseline": price, "history": []}
        first_run = True

    lowest = state["lowest"]
    state["history"].append({"time": now, "price": price, "term": term})
    state["history"] = state["history"][-500:]

    if first_run:
        msg = f"Sledujem VOI Baia di Tindari. Aktualna cena: {price} Kc ({term})"
        notify("Fischer watch je aktivny", msg, tags="white_check_mark")
    elif price < lowest:
        diff = lowest - price
        msg = (
            f"Nova cena: {price} Kc (predtym {lowest} Kc, -{diff} Kc)\n"
            f"Termin: {term}\nKlikni pre otvorenie ponuky."
        )
        notify(
            "CENA KLESLA - Fischer Tindari",
            msg,
            priority="urgent",
            tags="rotating_light,chart_with_downwards_trend",
        )
        state["lowest"] = price
    else:
        print(f"Bez zlacnenia (najnizsia doteraz: {lowest} Kc).")

    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
