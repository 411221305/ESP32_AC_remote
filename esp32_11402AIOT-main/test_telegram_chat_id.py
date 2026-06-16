import time

import network


try:
    import requests
except ImportError:
    import urequests as requests

try:
    from config import TELEGRAM_BOT_TOKEN, WIFI_PASSWORD, WIFI_SSID
except ImportError:
    WIFI_SSID = None
    WIFI_PASSWORD = None
    TELEGRAM_BOT_TOKEN = None


CONNECT_TIMEOUT_SECONDS = 20


def is_missing(value):
    return value is None or value == "" or value.startswith("請") or value.startswith("your-")


def connect_wifi():
    if is_missing(WIFI_SSID):
        print("Missing WIFI_SSID in config.py.")
        return None

    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    time.sleep(0.5)

    if not wlan.isconnected():
        print("Connecting to Wi-Fi:", WIFI_SSID)
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)

    start = time.time()
    while not wlan.isconnected() and time.time() - start < CONNECT_TIMEOUT_SECONDS:
        print("Waiting for Wi-Fi...")
        time.sleep(1)

    if wlan.isconnected():
        print("Wi-Fi connected. IP:", wlan.ifconfig()[0])
    else:
        print("Wi-Fi connection failed.")

    return wlan


def get_updates():
    if is_missing(TELEGRAM_BOT_TOKEN):
        print("Missing TELEGRAM_BOT_TOKEN in config.py.")
        return

    url = "https://api.telegram.org/bot{}/getUpdates".format(TELEGRAM_BOT_TOKEN)
    print("Reading Telegram updates...")

    response = None
    try:
        response = requests.get(url)
        print("HTTP status:", response.status_code)
        data = response.json()
    except Exception as exc:
        print("getUpdates failed:", exc)
        return
    finally:
        if response:
            response.close()

    if not data.get("ok"):
        print("Telegram error:", data)
        return

    updates = data.get("result", [])
    if not updates:
        print("No updates found.")
        print("Open your bot in Telegram, press Start, send hello, then run this again.")
        return

    print("Available chat id(s):")
    for update in updates:
        message = update.get("message") or update.get("channel_post") or {}
        chat = message.get("chat", {})
        chat_id = chat.get("id")
        chat_type = chat.get("type", "")
        title = chat.get("title") or chat.get("username") or chat.get("first_name") or ""
        text = message.get("text", "")
        print("  CHAT_ID={} type={} name={} text={}".format(chat_id, chat_type, title, text))


def main():
    wlan = connect_wifi()
    if wlan and wlan.isconnected():
        get_updates()


main()
