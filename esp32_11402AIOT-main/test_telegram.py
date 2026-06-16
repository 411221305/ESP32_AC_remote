import time

import network


try:
    import requests
except ImportError:
    import urequests as requests

try:
    from config import (
        TELEGRAM_BOT_TOKEN,
        TELEGRAM_CHAT_ID,
        WIFI_PASSWORD,
        WIFI_SSID,
    )
except ImportError:
    WIFI_SSID = None
    WIFI_PASSWORD = None
    TELEGRAM_BOT_TOKEN = None
    TELEGRAM_CHAT_ID = None


CONNECT_TIMEOUT_SECONDS = 20
TEST_MESSAGE = "ESP32 Telegram test OK"


def is_missing(value):
    return (
        value is None
        or value == ""
        or value.startswith("請")
        or value.startswith("your-")
    )


def quote_plus(text):
    safe = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_.~"
    encoded = []

    for byte in str(text).encode("utf-8"):
        char = chr(byte)
        if char in safe:
            encoded.append(char)
        elif char == " ":
            encoded.append("+")
        else:
            encoded.append("%{:02X}".format(byte))

    return "".join(encoded)


def status_name(status):
    names = {
        network.STAT_IDLE: "IDLE",
        network.STAT_CONNECTING: "CONNECTING",
        network.STAT_WRONG_PASSWORD: "WRONG_PASSWORD",
        network.STAT_NO_AP_FOUND: "NO_AP_FOUND",
        network.STAT_CONNECT_FAIL: "CONNECT_FAIL",
        network.STAT_GOT_IP: "GOT_IP",
    }
    return names.get(status, str(status))


def connect_wifi():
    if is_missing(WIFI_SSID):
        print("Missing WIFI_SSID in config.py.")
        return None

    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    time.sleep(0.5)

    print("Wi-Fi active:", wlan.active())
    print("Target SSID:", WIFI_SSID)

    if not wlan.isconnected():
        print("Connecting...")
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)

    start = time.time()
    last_status = None
    while not wlan.isconnected() and time.time() - start < CONNECT_TIMEOUT_SECONDS:
        status = wlan.status()
        if status != last_status:
            print("Status:", status_name(status))
            last_status = status
        time.sleep(1)

    if not wlan.isconnected():
        print("Wi-Fi connection failed.")
        print("Final status:", status_name(wlan.status()))
        return wlan

    print("Wi-Fi connected.")
    print("IP:", wlan.ifconfig()[0])
    return wlan


def send_telegram_message(text):
    if is_missing(TELEGRAM_BOT_TOKEN):
        print("Missing TELEGRAM_BOT_TOKEN in config.py.")
        return False

    if is_missing(TELEGRAM_CHAT_ID):
        print("Missing TELEGRAM_CHAT_ID in config.py.")
        return False

    url = (
        "https://api.telegram.org/bot{}/sendMessage?chat_id={}&text={}".format(
            TELEGRAM_BOT_TOKEN,
            quote_plus(TELEGRAM_CHAT_ID),
            quote_plus(text),
        )
    )

    print("Sending Telegram message...")
    response = None
    try:
        response = requests.get(url)
        print("HTTP status:", response.status_code)
        print("Response:", response.text)
        return response.status_code == 200 and '"ok":true' in response.text
    except Exception as exc:
        print("Telegram send failed:", exc)
        return False
    finally:
        if response:
            response.close()


def main():
    wlan = connect_wifi()
    if not wlan or not wlan.isconnected():
        print("Telegram test skipped because Wi-Fi is not connected.")
        return

    if send_telegram_message(TEST_MESSAGE):
        print("Telegram test done.")
    else:
        print("Telegram test failed.")


main()
