from playwright.sync_api import sync_playwright
import requests
import os
import time
import random
from datetime import datetime
import pytz

# 🎯 Config from Railway env vars
from playwright.sync_api import sync_playwright
import requests
import os
import time
import random
from datetime import datetime, timedelta
import pytz

# 🎯 Format:
# MOVIE_TARGETS=Athiradi:20260516,Drishyam 3:20260522

raw_targets = os.getenv(
    "MOVIE_TARGETS",
    "Athiradi:20260516,Drishyam 3:20260522"
)

TARGETS = {}

for item in raw_targets.split(","):
    if ":" in item:
        movie, datecode = item.split(":", 1)
        TARGETS[movie.strip()] = datecode.strip()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

CHECK_INTERVAL_MIN = 5
CHECK_INTERVAL_MAX = 15

START_HOUR = 8
END_HOUR = 23

IST = pytz.timezone("Asia/Kolkata")

last_status = {}


def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": msg}
    try:
        r = requests.post(url, data=payload, timeout=10)
        if r.status_code != 200:
            print("⚠️ Telegram API error:", r.text)
    except Exception as e:
        print("⚠️ Failed to send Telegram:", e)


def check_movies():
    global last_status

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )

        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/119.0.0.0 Safari/537.36"
            )
        )

        page = context.new_page()

        try:
            for movie, datecode in TARGETS.items():

                url = (
                    "https://in.bookmyshow.com/"
                    "cinemas/kochi/"
                    "vanitha-cineplex-rgb-laser-4k-3d-atmos-edappally/"
                    f"buytickets/VMHE/{datecode}"
                )

                print(f"\n🌐 Checking '{movie}' on {datecode}")

                try:
                    page.goto(
                        url,
                        wait_until="networkidle",
                        timeout=60000
                    )

                    page.wait_for_selector(
                        "div[role='gridcell']",
                        timeout=30000
                    )

                    movies = [
                        m.strip()
                        for m in page.locator(
                            "div[role='gridcell'] a"
                        ).all_text_contents()
                        if m.strip()
                    ]

                    print("🎬 Found movies:", movies)

                    found = any(
                        movie.lower() in m.lower()
                        for m in movies
                    )

                    key = (movie, datecode)

                    if found and last_status.get(key) != "available":

                        msg = (
                            f"🎟 Tickets Open!\n\n"
                            f"🎬 Movie: {movie}\n"
                            f"📅 Date: {datecode}\n"
                            f"📍 Theatre: Vanitha Cineplex"
                        )

                        print(msg)

                        send_telegram(msg)

                        last_status[key] = "available"

                    elif not found:
                        print(f"❌ {movie} not available yet")
                        last_status[key] = "not_available"

                except Exception as e:
                    print(f"⚠️ Error checking {movie}: {e}")

        finally:
            browser.close()


def run_loop():
    while True:
        now = datetime.now(IST)
        if START_HOUR <= now.hour < END_HOUR:
            print(f"⏰ Active hours ({START_HOUR}-{END_HOUR} IST). Running check...")
            check_movies()
            delay = random.randint(CHECK_INTERVAL_MIN * 60, CHECK_INTERVAL_MAX * 60)
            print(f"⏳ Waiting {delay // 60} minutes before next check...\n")
            time.sleep(delay)
        else:
            tomorrow = now.replace(hour=START_HOUR, minute=0, second=0, microsecond=0)
            if now.hour >= END_HOUR:
                tomorrow = tomorrow + timedelta(days=1)

            sleep_time = (tomorrow - now).total_seconds()
            hrs = int(sleep_time // 3600)
            mins = int((sleep_time % 3600) // 60)

            print(f"🌙 Outside active hours ({now.hour} IST). Sleeping for {hrs}h {mins}m...\n")
            time.sleep(sleep_time)


if __name__ == "__main__":
    run_loop()
