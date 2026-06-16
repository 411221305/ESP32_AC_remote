try:
    from config import WIFI_PASSWORD, WIFI_SSID
except ImportError:
    WIFI_SSID = None
    WIFI_PASSWORD = None


def connect_wifi(timeout_seconds=10):
    if not WIFI_SSID:
        print("config.py not found or WIFI_SSID is empty; skipping Wi-Fi.")
        return None

    import network
    import time

    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if not wlan.isconnected():
        print("Connecting to Wi-Fi...")
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)

        timeout = timeout_seconds
        while not wlan.isconnected() and timeout > 0:
            time.sleep(1)
            timeout -= 1

    if wlan.isconnected():
        print("Wi-Fi connected")
        print("IP:", wlan.ifconfig()[0])
    else:
        print("Wi-Fi connection failed")

    return wlan


# Uncomment this after config.py is ready and you want Wi-Fi at boot.
# connect_wifi()
