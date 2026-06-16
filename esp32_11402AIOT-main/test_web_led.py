import socket
import time

import network
from machine import Pin
from neopixel import NeoPixel


AP_SSID = "AIOT-LED"
AP_PASSWORD = "aiot12345"
AP_CHANNEL = 6
NEOPIXEL_PIN = 26
NEOPIXEL_COUNT = 3

LED_NAMES = {
    "red": "紅燈",
    "yellow": "黃燈",
    "green": "綠燈",
}

pins = {
    "red": Pin(16, Pin.OUT),
    "yellow": Pin(12, Pin.OUT),
    "green": Pin(13, Pin.OUT),
}
state = {
    "red": 0,
    "yellow": 0,
    "green": 0,
}


def sync_leds():
    for name, pin in pins.items():
        pin.value(state[name])


def turn_off_rgb():
    pixels = NeoPixel(Pin(NEOPIXEL_PIN), NEOPIXEL_COUNT)
    for index in range(NEOPIXEL_COUNT):
        pixels[index] = (0, 0, 0)
    pixels.write()
    print("RGB LED off")


def start_ap():
    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    ap.config(
        essid=AP_SSID,
        password=AP_PASSWORD,
        authmode=network.AUTH_WPA_WPA2_PSK,
        channel=AP_CHANNEL,
    )

    while not ap.active():
        time.sleep(0.1)

    print("AP active")
    print("SSID:", AP_SSID)
    print("Password:", AP_PASSWORD)
    print("ifconfig:", ap.ifconfig())
    print("Open: http://192.168.4.1")
    return ap


def html_page():
    rows = []
    for led in ("red", "yellow", "green"):
        is_on = state[led] == 1
        status = "亮亮 ✨" if is_on else "呼呼 💤"
        rows.append(
            """
            <section class="led-card {led} {card_state}">
                <div class="led-info">
                    <span class="lamp">
                        <span class="shine"></span>
                        <span class="face">
                            <span class="eye left"></span>
                            <span class="eye right"></span>
                            <span class="cheek left"></span>
                            <span class="cheek right"></span>
                            <span class="smile"></span>
                        </span>
                        <span class="ray ray-a">✦</span>
                        <span class="ray ray-b">✧</span>
                        <span class="ray ray-c">✦</span>
                    </span>
                    <div class="led-text">
                        <h2>{name}</h2>
                        <p>{hint}</p>
                    </div>
                </div>
                <div class="control-panel">
                    <span class="badge {status_class}">{status}</span>
                    <div class="actions">
                        <a class="button on {on_selected}" href="/set?led={led}&state=on">開燈 💡</a>
                        <a class="button off {off_selected}" href="/set?led={led}&state=off">關燈 🌙</a>
                    </div>
                </div>
            </section>
            """.format(
                led=led,
                name=LED_NAMES[led],
                hint={"red": "勇氣紅 · GPIO 16", "yellow": "陽光黃 · GPIO 12", "green": "森林綠 · GPIO 13"}[led],
                status=status,
                status_class="badge-on" if is_on else "badge-off",
                card_state="is-on" if is_on else "is-off",
                on_selected="selected" if is_on else "",
                off_selected="selected" if not is_on else "",
            )
        )

    page = """<!doctype html>
<html lang="zh-Hant">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>ESP32 LED Control</title>
    <style>
        * {
            box-sizing: border-box;
        }
        @keyframes floaty {
            0%, 100% { transform: translateY(0) rotate(-3deg); }
            50% { transform: translateY(-8px) rotate(3deg); }
        }
        @keyframes blink {
            0%, 90%, 100% { transform: scaleY(1); }
            95% { transform: scaleY(0.12); }
        }
        @keyframes popin {
            0% { opacity: 0; transform: scale(0.86) translateY(14px); }
            100% { opacity: 1; transform: scale(1) translateY(0); }
        }
        @keyframes glow {
            0%, 100% { box-shadow: inset 0 -8px 14px rgba(38, 50, 79, 0.16), 0 0 0 0 var(--glow); }
            50% { box-shadow: inset 0 -8px 14px rgba(38, 50, 79, 0.16), 0 0 22px 7px var(--glow); }
        }
        @keyframes sparkle {
            0%, 100% { opacity: 0; transform: scale(0.3) rotate(-20deg); }
            50% { opacity: 1; transform: scale(1.1) rotate(20deg); }
        }
        body {
            margin: 0;
            min-height: 100vh;
            font-family: "Segoe UI Rounded", "Comic Sans MS", "Noto Sans TC", "Microsoft JhengHei", sans-serif;
            background:
                radial-gradient(circle at 18% 18%, rgba(255, 255, 255, 0.75), transparent 22%),
                radial-gradient(circle at 82% 30%, rgba(255, 255, 255, 0.55), transparent 18%),
                radial-gradient(circle at 50% 90%, rgba(255, 255, 255, 0.5), transparent 20%),
                linear-gradient(135deg, #ffe3f1 0%, #ece4ff 46%, #d8f3ff 100%);
            background-attachment: fixed;
            color: #5b4a6b;
        }
        main {
            width: min(720px, 100%);
            margin: 0 auto;
            padding: 22px 16px 36px;
        }
        .topbar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 16px;
            margin-bottom: 20px;
            padding: 20px;
            border: 4px solid #ffffff;
            border-radius: 30px;
            background: linear-gradient(160deg, #ffffff 0%, #fff3fa 100%);
            box-shadow: 0 14px 30px rgba(196, 137, 200, 0.28);
        }
        .title-block {
            min-width: 0;
            flex: 1 1 auto;
        }
        .mascot {
            position: relative;
            flex: 0 0 auto;
            width: 74px;
            height: 74px;
            border: 4px solid #ffffff;
            border-radius: 26px;
            background: linear-gradient(160deg, #c4b5fd, #a78bfa);
            box-shadow: inset 0 -8px 0 rgba(0, 0, 0, 0.08), 0 8px 16px rgba(124, 58, 237, 0.3);
            animation: floaty 3.2s ease-in-out infinite;
        }
        .mascot .m-eye {
            position: absolute;
            top: 26px;
            width: 11px;
            height: 12px;
            border-radius: 50%;
            background: #ffffff;
            animation: blink 4.2s infinite;
        }
        .mascot .m-eye.left { left: 18px; }
        .mascot .m-eye.right { right: 18px; }
        .mascot .m-cheek {
            position: absolute;
            top: 38px;
            width: 10px;
            height: 7px;
            border-radius: 50%;
            background: rgba(255, 138, 176, 0.85);
        }
        .mascot .m-cheek.left { left: 13px; }
        .mascot .m-cheek.right { right: 13px; }
        .mascot .mouth {
            position: absolute;
            left: 27px;
            bottom: 16px;
            width: 20px;
            height: 11px;
            border-bottom: 4px solid #ffffff;
            border-radius: 0 0 18px 18px;
        }
        .mascot .antenna {
            position: absolute;
            top: -20px;
            left: 33px;
            width: 8px;
            height: 20px;
            border-radius: 8px 8px 0 0;
            background: #7c3aed;
        }
        .mascot .antenna::before {
            content: "";
            position: absolute;
            top: -9px;
            left: -4px;
            width: 16px;
            height: 16px;
            border-radius: 50%;
            background: #ffd43b;
            box-shadow: 0 0 10px rgba(255, 212, 59, 0.8);
        }
        h1 {
            margin: 0 0 8px;
            font-size: 2.05rem;
            line-height: 1.2;
            color: #ff5f9e;
            text-shadow: 0 2px 0 rgba(255, 255, 255, 0.8);
        }
        .subtitle {
            margin: 0;
            color: #8a7aa0;
            font-size: 0.98rem;
            line-height: 1.5;
        }
        .network {
            flex: 0 0 auto;
            min-width: 140px;
            padding: 12px 14px;
            border-radius: 22px;
            background: linear-gradient(160deg, #7dd3fc, #60a5fa);
            color: #ffffff;
            text-align: right;
            box-shadow: 0 8px 16px rgba(96, 165, 250, 0.4);
        }
        .network span {
            display: block;
            color: #eff6ff;
            font-size: 0.78rem;
        }
        .network strong {
            display: block;
            margin-top: 4px;
            font-size: 1.05rem;
            letter-spacing: 0.5px;
        }
        .stack {
            display: grid;
            gap: 16px;
        }
        .led-card {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 16px;
            min-height: 116px;
            padding: 18px 20px;
            border: 4px solid #ffffff;
            border-radius: 28px;
            background: linear-gradient(160deg, #ffffff 0%, #fdf6ff 100%);
            box-shadow: 0 12px 24px rgba(168, 150, 200, 0.26);
            transition: transform 0.18s ease, box-shadow 0.18s ease;
            animation: popin 0.5s ease both;
        }
        .led-card:nth-child(2) { animation-delay: 0.08s; }
        .led-card:nth-child(3) { animation-delay: 0.16s; }
        .led-card:hover {
            transform: translateY(-5px) rotate(-0.5deg);
            box-shadow: 0 18px 30px rgba(168, 150, 200, 0.34);
        }
        .led-info {
            display: flex;
            align-items: center;
            gap: 16px;
            min-width: 0;
        }
        .lamp {
            position: relative;
            width: 58px;
            height: 58px;
            border-radius: 50%;
            border: 6px solid #ffffff;
            background: #c7d0de;
            box-shadow: inset 0 -8px 14px rgba(38, 50, 79, 0.16), 0 6px 0 rgba(38, 50, 79, 0.1);
        }
        .shine {
            position: absolute;
            top: 9px;
            left: 12px;
            width: 16px;
            height: 16px;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.82);
        }
        .face {
            position: absolute;
            inset: 0;
        }
        .eye {
            position: absolute;
            top: 24px;
            width: 7px;
            height: 9px;
            border-radius: 50%;
            background: rgba(38, 50, 79, 0.74);
            animation: blink 4.5s infinite;
        }
        .eye.left { left: 19px; }
        .eye.right { right: 19px; }
        .cheek {
            position: absolute;
            top: 31px;
            width: 9px;
            height: 6px;
            border-radius: 50%;
            background: rgba(255, 120, 160, 0.45);
        }
        .cheek.left { left: 12px; }
        .cheek.right { right: 12px; }
        .smile {
            position: absolute;
            left: 21px;
            bottom: 13px;
            width: 14px;
            height: 8px;
            border-bottom: 3px solid rgba(38, 50, 79, 0.74);
            border-radius: 0 0 14px 14px;
        }
        .ray {
            position: absolute;
            display: none;
            font-size: 0.85rem;
            line-height: 1;
            color: #ffffff;
            text-shadow: 0 0 6px rgba(255, 255, 255, 0.9);
        }
        .ray-a { top: -10px; right: 2px; }
        .ray-b { right: -12px; bottom: 16px; }
        .ray-c { left: -2px; bottom: -8px; }
        .is-on .ray {
            display: block;
            animation: sparkle 1.5s ease-in-out infinite;
        }
        .is-on .ray-b { animation-delay: 0.5s; }
        .is-on .ray-c { animation-delay: 1s; }
        .red { --glow: rgba(255, 95, 126, 0.55); }
        .yellow { --glow: rgba(245, 158, 11, 0.5); }
        .green { --glow: rgba(52, 211, 153, 0.5); }
        .red .lamp { background: radial-gradient(circle at 32% 30%, #ff8aa6, #ff4f70); }
        .yellow .lamp { background: radial-gradient(circle at 32% 30%, #ffe27a, #ffd43b); }
        .green .lamp { background: radial-gradient(circle at 32% 30%, #7eecc0, #34d399); }
        .is-on .lamp {
            animation: glow 1.8s ease-in-out infinite;
        }
        .is-off .lamp {
            background: #cdd5e2;
            opacity: 0.5;
            filter: grayscale(0.6);
        }
        .is-off .cheek { opacity: 0; }
        .red.is-on { border-color: #ffc2d0; }
        .yellow.is-on { border-color: #ffe9a3; }
        .green.is-on { border-color: #b6f3d6; }
        .led-text { min-width: 0; }
        h2 {
            margin: 0 0 5px;
            font-size: 1.4rem;
            line-height: 1.15;
            color: #4a3a5e;
        }
        p {
            margin: 0;
            color: #9a8cb0;
            font-size: 0.92rem;
        }
        .control-panel {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .badge {
            min-width: 70px;
            padding: 8px 12px;
            border-radius: 999px;
            font-size: 0.92rem;
            font-weight: bold;
            text-align: center;
            border: 2px solid #ffffff;
        }
        .badge-on {
            background: linear-gradient(160deg, #bbf7d0, #86efac);
            color: #15803d;
            box-shadow: 0 4px 10px rgba(134, 239, 172, 0.55);
        }
        .badge-off {
            background: linear-gradient(160deg, #e9e3ff, #d6ccff);
            color: #6d51c7;
        }
        .actions {
            display: flex;
            gap: 8px;
            padding: 6px;
            border-radius: 999px;
            background: #f3eefc;
        }
        .button {
            display: inline-block;
            min-width: 86px;
            padding: 14px 18px;
            border-radius: 999px;
            color: #8a7aa0;
            background: transparent;
            font-size: 1.08rem;
            font-weight: bold;
            text-align: center;
            text-decoration: none;
            transition: transform 0.12s ease;
        }
        .button:active { transform: scale(0.94); }
        .button.selected {
            color: #ffffff;
            box-shadow: 0 5px 12px rgba(0, 0, 0, 0.16);
        }
        .on.selected {
            background: linear-gradient(160deg, #4ade80, #22c55e);
        }
        .off.selected {
            background: linear-gradient(160deg, #a5b4fc, #818cf8);
        }
        .footer {
            margin-top: 22px;
            text-align: center;
            color: #b09cc4;
            font-size: 0.92rem;
        }
        @media (max-width: 520px) {
            main {
                padding: 14px 12px 28px;
            }
            .topbar {
                flex-direction: column;
                align-items: stretch;
                text-align: center;
                padding: 18px;
            }
            .mascot {
                align-self: center;
            }
            h1 {
                font-size: 1.7rem;
            }
            .network {
                width: 100%;
                text-align: center;
            }
            .led-card {
                align-items: stretch;
                flex-direction: column;
                min-height: 0;
                padding: 18px;
            }
            .control-panel {
                align-items: stretch;
                flex-direction: column;
            }
            .actions {
                display: grid;
                grid-template-columns: 1fr 1fr;
            }
            .button {
                width: 100%;
                min-width: 0;
                padding: 18px 12px;
            }
        }
    </style>
</head>
<body>
    <main>
        <section class="topbar">
            <div class="mascot">
                <span class="antenna"></span>
                <span class="m-eye left"></span>
                <span class="m-eye right"></span>
                <span class="m-cheek left"></span>
                <span class="m-cheek right"></span>
                <span class="mouth"></span>
            </div>
            <div class="title-block">
                <h1>小小 LED 任務台 ✨</h1>
                <p class="subtitle">按一下「開燈」讓燈寶寶亮起來，按「關燈」讓它休息一下 💕</p>
            </div>
            <div class="network">
                <span>打開網址 🌈</span>
                <strong>192.168.4.1</strong>
            </div>
        </section>
        <section class="stack">
            __ROWS__
        </section>
        <footer class="footer">用心點亮每一盞燈 💛</footer>
    </main>
</body>
</html>
"""
    return page.replace("__ROWS__", "".join(rows))


def send_all(conn, data):
    while data:
        sent = conn.send(data)
        if sent is None:
            return
        data = data[sent:]


def send_response(conn, status, content_type="text/plain; charset=utf-8", body=""):
    if isinstance(body, str):
        body = body.encode("utf-8")

    headers = (
        "HTTP/1.1 {status}\r\n"
        "Content-Type: {content_type}\r\n"
        "Content-Length: {length}\r\n"
        "Connection: close\r\n"
        "Cache-Control: no-store\r\n"
        "\r\n"
    ).format(status=status, content_type=content_type, length=len(body))

    send_all(conn, headers.encode("utf-8"))
    if body:
        send_all(conn, body)


def redirect_home(conn):
    response = (
        "HTTP/1.1 303 See Other\r\n"
        "Location: /\r\n"
        "Connection: close\r\n"
        "Cache-Control: no-store\r\n"
        "\r\n"
    )
    send_all(conn, response.encode("utf-8"))


def no_content(conn):
    response = (
        "HTTP/1.1 204 No Content\r\n"
        "Connection: close\r\n"
        "Cache-Control: no-store\r\n"
        "\r\n"
    )
    send_all(conn, response.encode("utf-8"))


def parse_query(path):
    params = {}
    if "?" not in path:
        return params

    query = path.split("?", 1)[1]
    for pair in query.split("&"):
        if not pair:
            continue
        key_value = pair.split("=", 1)
        if len(key_value) == 2:
            params[key_value[0]] = key_value[1]
    return params


def handle_set(conn, path):
    params = parse_query(path)
    led = params.get("led")
    value = params.get("state")

    if led not in pins or value not in ("on", "off"):
        send_response(conn, "400 Bad Request", body="Invalid led or state")
        return

    state[led] = 1 if value == "on" else 0
    pins[led].value(state[led])
    print(LED_NAMES[led], "=", value.upper())
    redirect_home(conn)


def handle_request(conn):
    request = conn.recv(1024)
    if not request:
        return

    request_line = request.decode().split("\r\n", 1)[0]
    parts = request_line.split()
    if len(parts) < 2:
        send_response(conn, "400 Bad Request", body="Bad request")
        return

    method = parts[0]
    path = parts[1]
    route = path.split("?", 1)[0]
    print(method, path)

    if method != "GET":
        send_response(conn, "405 Method Not Allowed", body="Only GET is supported")
    elif route == "/":
        send_response(conn, "200 OK", "text/html; charset=utf-8", html_page())
    elif route == "/set":
        handle_set(conn, path)
    elif route == "/favicon.ico":
        no_content(conn)
    else:
        send_response(conn, "404 Not Found", body="Not found")


def serve_forever():
    addr = socket.getaddrinfo("0.0.0.0", 80)[0][-1]
    server = socket.socket()
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(addr)
    server.listen(4)
    print("Listening on http://192.168.4.1")

    try:
        while True:
            conn, remote_addr = server.accept()
            print("Client:", remote_addr)
            try:
                handle_request(conn)
            except Exception as exc:
                print("Request error:", exc)
                try:
                    send_response(conn, "500 Internal Server Error", body="Server error")
                except Exception:
                    pass
            finally:
                conn.close()
    finally:
        server.close()


def main():
    turn_off_rgb()
    sync_leds()
    start_ap()
    serve_forever()


main()
