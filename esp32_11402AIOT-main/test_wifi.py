import socket
import time

import network


try:
    from config import WIFI_PASSWORD, WIFI_SSID
except ImportError:
    WIFI_SSID = None
    WIFI_PASSWORD = None


CONNECT_TIMEOUT_SECONDS = 15
DNS_TEST_HOST = "micropython.org"


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
    if not WIFI_SSID:
        print("Missing config.py or WIFI_SSID.")
        print("Copy config.example.py to config.py and set WIFI_SSID/WIFI_PASSWORD.")
        return None

    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    time.sleep(0.5)

    print("Wi-Fi active:", wlan.active())
    print("Target SSID:", WIFI_SSID)

    if wlan.isconnected():
        print("Already connected.")
        return wlan

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
    ip, netmask, gateway, dns = wlan.ifconfig()
    print("IP:", ip)
    print("Netmask:", netmask)
    print("Gateway:", gateway)
    print("DNS:", dns)
    return wlan


def test_dns():
    print("Testing DNS:", DNS_TEST_HOST)
    try:
        result = socket.getaddrinfo(DNS_TEST_HOST, 80)
    except OSError as exc:
        print("DNS test failed:", exc)
        return False

    print("DNS OK:", result[0][-1][0])
    return True


def main():
    wlan = connect_wifi()
    if wlan and wlan.isconnected():
        test_dns()
    print("Wi-Fi test done.")


main()
