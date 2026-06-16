import socket
import time
import gc

import network
from machine import PWM, Pin
from neopixel import NeoPixel

try:
    from ac_codes import AC_CODES
except ImportError:
    AC_CODES = {}


AP_SSID = "ESP32-AC-Remote"
AP_PASSWORD = "12345678"
AP_USE_PASSWORD = False
AP_CHANNEL = 6
WEB_HOST = "192.168.4.1"

IR_TX_PIN = 25
IR_RX_PIN = 33
IR_FREQ = 38000
IR_DUTY = 512
IR_ACTIVE_LOW = False

LED_OK = 16
LED_ERROR = 12
LED_READY = 13
NEOPIXEL_PIN = 26
NEOPIXEL_COUNT = 3

CAPTURE_TIMEOUT_MS = 15000
FRAME_TIMEOUT_US = 1800000
IDLE_GAP_US = 25000
MAX_PULSES = 1300
MIN_PULSE_US = 80
MAX_PULSE_US = 30000
SEND_REPEATS = 1

COMMANDS = (
    ("off", "Off", "Power off"),
    ("power", "Power", "On / Off"),
    ("cool", "Cool", "Cooling mode"),
    ("dry", "Dry", "Dry mode"),
    ("fan", "Fan", "Fan mode"),
    ("temp_up", "Temp +", "Temperature up"),
    ("temp_down", "Temp -", "Temperature down"),
    ("fan_up", "Fan +", "Fan speed"),
    ("swing", "Swing", "Air swing"),
)

HITACHI_AC344_HDR_MARK = 3300
HITACHI_AC344_HDR_SPACE = 1700
HITACHI_AC344_BIT_MARK = 400
HITACHI_AC344_ONE_SPACE = 1250
HITACHI_AC344_ZERO_SPACE = 500
HITACHI_AC344_MIN_GAP = 100000
HITACHI_AC344_STATE = [
    0x01, 0x10, 0x00, 0x40, 0x00, 0xFF, 0x00, 0xCC, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00,
    0x80, 0x00, 0x03, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
]

HITACHI_BUTTON_POWER = 0x13
HITACHI_BUTTON_TEMP_DOWN = 0x43
HITACHI_BUTTON_TEMP_UP = 0x44
HITACHI_BUTTON_FAN = 0x42
HITACHI_MODE_FAN = 1
HITACHI_MODE_COOL = 3
HITACHI_MODE_DRY = 5
HITACHI_FAN_LOW = 2
HITACHI_FAN_AUTO = 5
HITACHI_POWER_ON = 0xF1
HITACHI_POWER_OFF = 0xE1

HITACHI_COMMANDS = (
    ("off", "Hitachi Off"),
    ("cool25", "Hitachi Cool 25"),
    ("cool26", "Hitachi Cool 26"),
    ("dry", "Hitachi Dry"),
    ("fan", "Hitachi Fan"),
)

HITACHI_AC424_HDR_MARK = 3416
HITACHI_AC424_HDR_SPACE = 1604
HITACHI_AC424_BIT_MARK = 463
HITACHI_AC424_ONE_SPACE = 1208
HITACHI_AC424_ZERO_SPACE = 372
HITACHI_AC424_MIN_GAP = 100000
HITACHI_AC424_STATE = [
    0x01, 0x10, 0x00, 0x40, 0xBF, 0xFF, 0x00, 0xCC, 0x33, 0x92, 0x6D,
    0x13, 0xEC, 0x5C, 0xA3, 0x00, 0xFF, 0x00, 0xFF, 0x00, 0xFF, 0x00,
    0xFF, 0x00, 0xFF, 0x53, 0xAC, 0xF1, 0x0E, 0x00, 0xFF, 0x00, 0xFF,
    0x80, 0x7F, 0x03, 0xFC, 0x01, 0xFE, 0x88, 0x77, 0x00, 0xFF, 0x00,
    0xFF, 0xFF, 0x00, 0xFF, 0x00, 0xFF, 0x00, 0xFF, 0x00,
]

HITACHI424_MODE_FAN = 1
HITACHI424_MODE_COOL = 3
HITACHI424_MODE_DRY = 5
HITACHI424_FAN_LOW = 2
HITACHI424_FAN_AUTO = 5
HITACHI424_POWER_ON = 0xF1
HITACHI424_POWER_OFF = 0xE1

HITACHI424_COMMANDS = (
    ("off", "Hitachi424 Off"),
    ("cool25", "Hitachi424 Cool 25"),
    ("cool26", "Hitachi424 Cool 26"),
    ("dry", "Hitachi424 Dry"),
    ("fan", "Hitachi424 Fan"),
)

# Learned from the user's Hitachi RAS-40HQP / RS13T1 remote.
# This is the already-inverted 43-byte AC344 frame decoded from Learn.
RS13T1_AC344_STATE = [
    0x01, 0x10, 0x00, 0x40, 0xBF, 0xFF, 0x00, 0xCC, 0x33, 0xA9, 0x56,
    0x13, 0xEC, 0x68, 0x97, 0x00, 0xFF, 0x00, 0xFF, 0x00, 0xFF, 0x00,
    0xFF, 0x00, 0xFF, 0x43, 0xBC, 0xF1, 0x0E, 0x01, 0xFE, 0x01, 0xFE,
    0x80, 0x7F, 0x03, 0xFC, 0xE0, 0x1F, 0x00, 0xFF, 0x00, 0xFF,
]

RS13T1_COMMANDS = (
    ("learned_power", "RS13T1 Learned Power"),
    ("off", "RS13T1 Off"),
    ("cool25", "RS13T1 Cool 25"),
    ("cool26", "RS13T1 Cool 26"),
)

LAST_HITACHI344 = {
    "mode": "cool",
    "temp": 26,
    "fan": "auto",
    "power": "on",
}

tx_pwm = PWM(Pin(IR_TX_PIN, Pin.OUT), freq=IR_FREQ, duty=0)
rx_pin = Pin(IR_RX_PIN, Pin.IN, Pin.PULL_UP)
led_ok = Pin(LED_OK, Pin.OUT)
led_error = Pin(LED_ERROR, Pin.OUT)
led_ready = Pin(LED_READY, Pin.OUT)
pixels = NeoPixel(Pin(NEOPIXEL_PIN, Pin.OUT), NEOPIXEL_COUNT)
last_message = "Ready"


def mark_duty():
    return 1023 - IR_DUTY if IR_ACTIVE_LOW else IR_DUTY


def off_duty():
    return 1023 if IR_ACTIVE_LOW else 0


def carrier_off():
    tx_pwm.duty(off_duty())


def rgb_off():
    for index in range(NEOPIXEL_COUNT):
        pixels[index] = (0, 0, 0)
    pixels.write()


def set_status(ok=False, error=False, ready=True):
    rgb_off()
    led_ok.value(1 if ok else 0)
    led_error.value(1 if error else 0)
    led_ready.value(1 if ready else 0)


def flash_ok():
    set_status(ok=True, ready=False)
    time.sleep_ms(120)
    set_status(ready=True)


def flash_error():
    set_status(error=True, ready=False)
    time.sleep_ms(180)
    set_status(ready=True)


def start_ap():
    sta = network.WLAN(network.STA_IF)
    sta.active(False)
    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    if AP_USE_PASSWORD:
        ap.config(
            essid=AP_SSID,
            password=AP_PASSWORD,
            authmode=network.AUTH_WPA_WPA2_PSK,
            channel=AP_CHANNEL,
        )
    else:
        ap.config(
            essid=AP_SSID,
            authmode=network.AUTH_OPEN,
            channel=AP_CHANNEL,
        )
    while not ap.active():
        time.sleep_ms(100)

    print("AP active")
    print("SSID:", AP_SSID)
    if AP_USE_PASSWORD:
        print("Password:", AP_PASSWORD)
    else:
        print("Password: <open>")
    print("Open: http://{}/".format(WEB_HOST))
    print("IR TX: GPIO {}, IR RX: GPIO {}".format(IR_TX_PIN, IR_RX_PIN))
    return ap


def quote_plus(value):
    return str(value).replace(" ", "+")


def unquote_plus(value):
    value = value.replace("+", " ")
    output = ""
    index = 0
    while index < len(value):
        if value[index] == "%" and index + 2 < len(value):
            try:
                output += chr(int(value[index + 1:index + 3], 16))
                index += 3
                continue
            except ValueError:
                pass
        output += value[index]
        index += 1
    return output


def parse_query(path):
    params = {}
    if "?" not in path:
        return params

    query = path.split("?", 1)[1]
    for pair in query.split("&"):
        if not pair:
            continue
        parts = pair.split("=", 1)
        key = unquote_plus(parts[0])
        value = unquote_plus(parts[1]) if len(parts) == 2 else ""
        params[key] = value
    return params


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


def redirect_home(conn, message=None):
    location = "/"
    if message:
        location = "/?msg=" + quote_plus(message)
    response = (
        "HTTP/1.1 303 See Other\r\n"
        "Location: {location}\r\n"
        "Connection: close\r\n"
        "Cache-Control: no-store\r\n"
        "\r\n"
    ).format(location=location)
    send_all(conn, response.encode("utf-8"))


def no_content(conn):
    send_all(
        conn,
        b"HTTP/1.1 204 No Content\r\nConnection: close\r\nCache-Control: no-store\r\n\r\n",
    )


def action_page(title, message):
    gc.collect()
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{title}</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{ font-family: Arial, sans-serif; margin: 0; background: #f3f5f7; color: #1f2937; }}
    main {{ width: min(760px, 100%); margin: 0 auto; padding: 16px; }}
    section {{ padding: 16px; border: 1px solid #d7dde5; border-radius: 8px; background: #fff; }}
    h1 {{ margin: 0 0 8px; font-size: 1.2rem; }}
    p {{ margin: 0; line-height: 1.5; color: #334155; }}
    a {{ display: inline-flex; margin-top: 14px; padding: 10px 12px; border-radius: 8px; background: #1d4ed8; color: #fff; text-decoration: none; font-weight: 700; }}
  </style>
</head>
<body>
  <main>
    <section>
      <h1>{title}</h1>
      <p>{message}</p>
      <a href="/">Back</a>
    </section>
  </main>
</body>
</html>""".format(title=title, message=message)


def send_action_page(conn, title, message):
    send_response(conn, "200 OK", "text/html; charset=utf-8", action_page(title, message))


def pulse_duration(duration):
    duration = int(duration)
    if duration < MIN_PULSE_US:
        return MIN_PULSE_US
    if duration > MAX_PULSE_US:
        return MAX_PULSE_US
    return duration


def iter_pulses(pulses):
    if not pulses:
        return

    first = pulses[0]
    if isinstance(first, tuple) or isinstance(first, list):
        for level, duration in pulses:
            yield int(level), int(duration)
    else:
        level = 0
        for duration in pulses:
            yield level, int(duration)
            level = 1 - level


def compact_pulses(pulses):
    return [pulse_duration(duration) for _, duration in iter_pulses(pulses)]


def set_bits(value, offset, size, data):
    mask = ((1 << size) - 1) << offset
    return (value & ~mask) | ((data << offset) & mask)


def hitachi_base_state():
    return list(HITACHI_AC344_STATE)


def hitachi_invert_byte_pairs(state):
    for index in range(4, len(state), 2):
        state[index] = (~state[index - 1]) & 0xFF


def hitachi_set_temp(state, temp):
    if temp < 16:
        temp = 16
    if temp > 32:
        temp = 32
    state[13] = set_bits(state[13], 2, 6, temp)


def hitachi_set_mode(state, mode):
    state[25] = set_bits(state[25], 0, 4, mode)
    state[27] = HITACHI_POWER_ON


def hitachi_set_fan(state, fan):
    state[25] = set_bits(state[25], 4, 4, fan)
    state[9] = 0x98 if fan <= HITACHI_FAN_LOW else 0x92
    state[29] = 0x01


def hitachi_state(command):
    if command == "off":
        return hitachi344_state(mode="cool", temp=26, fan="auto", power="off")
    if command == "cool25":
        return hitachi344_state(mode="cool", temp=25, fan="auto", power="on")
    if command == "cool26":
        return hitachi344_state(mode="cool", temp=26, fan="auto", power="on")
    if command == "dry":
        return hitachi344_state(mode="dry", temp=26, fan="low", power="on")
    if command == "fan":
        return hitachi344_state(mode="fan", temp=27, fan="low", power="on")
    raise ValueError("Unknown Hitachi command")


def hitachi_pulses(command):
    state = hitachi_state(command)
    pulses = [HITACHI_AC344_HDR_MARK, HITACHI_AC344_HDR_SPACE]
    for byte in state:
        for bit in range(8):
            pulses.append(HITACHI_AC344_BIT_MARK)
            if byte & (1 << bit):
                pulses.append(HITACHI_AC344_ONE_SPACE)
            else:
                pulses.append(HITACHI_AC344_ZERO_SPACE)
    pulses.append(HITACHI_AC344_BIT_MARK)
    pulses.append(HITACHI_AC344_MIN_GAP)
    return pulses


def clamp_int(value, lower, upper, fallback):
    try:
        value = int(value)
    except (TypeError, ValueError):
        return fallback
    if value < lower:
        return lower
    if value > upper:
        return upper
    return value


def hitachi344_state(mode="cool", temp=26, fan="auto", power="on"):
    state = hitachi_base_state()
    state[11] = HITACHI_BUTTON_POWER

    if mode == "dry":
        hitachi_set_mode(state, HITACHI_MODE_DRY)
        if fan == "low":
            hitachi_set_fan(state, HITACHI_FAN_LOW)
        else:
            hitachi_set_fan(state, HITACHI_FAN_AUTO)
    elif mode == "fan":
        hitachi_set_mode(state, HITACHI_MODE_FAN)
        hitachi_set_fan(state, HITACHI_FAN_LOW)
    else:
        hitachi_set_mode(state, HITACHI_MODE_COOL)
        if fan == "low":
            hitachi_set_fan(state, HITACHI_FAN_LOW)
        else:
            hitachi_set_fan(state, HITACHI_FAN_AUTO)

    hitachi_set_temp(state, clamp_int(temp, 16, 32, 26))
    state[27] = HITACHI_POWER_OFF if power == "off" else HITACHI_POWER_ON
    hitachi_invert_byte_pairs(state)
    return state


def hitachi344_pulses(mode="cool", temp=26, fan="auto", power="on"):
    state = hitachi344_state(mode=mode, temp=temp, fan=fan, power=power)
    pulses = [HITACHI_AC344_HDR_MARK, HITACHI_AC344_HDR_SPACE]
    for byte in state:
        for bit in range(8):
            pulses.append(HITACHI_AC344_BIT_MARK)
            if byte & (1 << bit):
                pulses.append(HITACHI_AC344_ONE_SPACE)
            else:
                pulses.append(HITACHI_AC344_ZERO_SPACE)
    pulses.append(HITACHI_AC344_BIT_MARK)
    pulses.append(HITACHI_AC344_MIN_GAP)
    return pulses


def hitachi344_summary():
    return "{mode} {temp}C, fan {fan}, power {power}".format(
        mode=LAST_HITACHI344["mode"],
        temp=LAST_HITACHI344["temp"],
        fan=LAST_HITACHI344["fan"],
        power=LAST_HITACHI344["power"],
    )


def apply_hitachi344_query(params):
    config = dict(LAST_HITACHI344)
    adjusted = False

    mode = params.get("mode", "")
    if mode in ("cool", "dry", "fan"):
        config["mode"] = mode
        adjusted = True

    fan = params.get("fan", "")
    if fan in ("auto", "low"):
        config["fan"] = fan
        adjusted = True

    power = params.get("power", "")
    if power in ("on", "off"):
        config["power"] = power

    if "temp" in params:
        config["temp"] = clamp_int(params.get("temp"), 16, 32, config["temp"])
        adjusted = True

    op = params.get("op", "")
    if op == "temp_up":
        config["temp"] = clamp_int(config["temp"] + 1, 16, 32, config["temp"])
        adjusted = True
    elif op == "temp_down":
        config["temp"] = clamp_int(config["temp"] - 1, 16, 32, config["temp"])
        adjusted = True
    elif op == "fan_toggle":
        config["fan"] = "low" if config["fan"] == "auto" else "auto"
        adjusted = True
    elif op == "cool":
        config["mode"] = "cool"
        config["power"] = "on"
        adjusted = True
    elif op == "dry":
        config["mode"] = "dry"
        config["power"] = "on"
        adjusted = True
    elif op == "fan":
        config["mode"] = "fan"
        config["power"] = "on"
        adjusted = True
    elif op == "off":
        config["power"] = "off"
    elif op == "on":
        config["power"] = "on"

    if adjusted and config.get("power") != "off":
        config["power"] = "on"

    return config


def hitachi424_base_state():
    return list(HITACHI_AC424_STATE)


def hitachi424_set_temp(state, temp):
    if temp < 16:
        temp = 16
    if temp > 32:
        temp = 32
    state[13] = set_bits(state[13], 2, 6, temp)


def hitachi424_set_mode(state, mode):
    state[25] = set_bits(state[25], 0, 4, mode)
    state[27] = HITACHI424_POWER_ON


def hitachi424_set_fan(state, fan):
    state[25] = set_bits(state[25], 4, 4, fan)
    state[9] = 0x98 if fan <= HITACHI424_FAN_LOW else 0x92
    state[29] = 0x01


def hitachi424_state(command):
    state = hitachi424_base_state()
    state[11] = HITACHI_BUTTON_POWER

    if command == "off":
        hitachi424_set_mode(state, HITACHI424_MODE_COOL)
        hitachi424_set_temp(state, 26)
        hitachi424_set_fan(state, HITACHI424_FAN_AUTO)
        state[27] = HITACHI424_POWER_OFF
    elif command == "cool25":
        hitachi424_set_mode(state, HITACHI424_MODE_COOL)
        hitachi424_set_temp(state, 25)
        hitachi424_set_fan(state, HITACHI424_FAN_AUTO)
    elif command == "cool26":
        hitachi424_set_mode(state, HITACHI424_MODE_COOL)
        hitachi424_set_temp(state, 26)
        hitachi424_set_fan(state, HITACHI424_FAN_AUTO)
    elif command == "dry":
        hitachi424_set_mode(state, HITACHI424_MODE_DRY)
        hitachi424_set_temp(state, 26)
        hitachi424_set_fan(state, HITACHI424_FAN_LOW)
    elif command == "fan":
        hitachi424_set_mode(state, HITACHI424_MODE_FAN)
        hitachi424_set_temp(state, 27)
        hitachi424_set_fan(state, HITACHI424_FAN_LOW)
    else:
        raise ValueError("Unknown Hitachi424 command")

    hitachi_invert_byte_pairs(state)
    return state


def hitachi424_pulses(command):
    state = hitachi424_state(command)
    pulses = [HITACHI_AC424_HDR_MARK, HITACHI_AC424_HDR_SPACE]
    for byte in state:
        for bit in range(8):
            pulses.append(HITACHI_AC424_BIT_MARK)
            if byte & (1 << bit):
                pulses.append(HITACHI_AC424_ONE_SPACE)
            else:
                pulses.append(HITACHI_AC424_ZERO_SPACE)
    pulses.append(HITACHI_AC424_BIT_MARK)
    pulses.append(HITACHI_AC424_MIN_GAP)
    return pulses


def analyze_pulses(pulses):
    if not pulses:
        return {
            "count": 0,
            "marks": 0,
            "spaces": 0,
            "duration_ms": 0,
            "first": 0,
            "last": 0,
            "protocol": "unknown",
            "warning": "not learned",
        }

    marks = 0
    spaces = 0
    total_us = 0
    count = 0
    first = 0
    last = 0
    for level, duration in iter_pulses(pulses):
        if count == 0:
            first = int(duration)
        last = int(duration)
        count += 1
        if int(level) == 0:
            marks += 1
        else:
            spaces += 1
        total_us += int(duration)

    protocol = "unknown"
    if 200 <= count <= 230:
        protocol = "Hitachi AC1 / 104-bit candidate"
    elif 510 <= count <= 550:
        protocol = "Hitachi AC264 / 264-bit candidate"
    elif 575 <= count <= 620:
        protocol = "Hitachi AC296 / 296-bit candidate"
    elif 670 <= count <= 715:
        protocol = "Hitachi AC344 / 344-bit candidate"
    elif 830 <= count <= 875:
        protocol = "Hitachi AC424 / 424-bit candidate"

    warning = "looks ok"
    if count < 350:
        warning = "short Hitachi variant or incomplete"
    elif count > 1200:
        warning = "very long; possible noise"
    elif total_us < 90000:
        warning = "duration too short"
    elif total_us > 2000000:
        warning = "duration very long"

    return {
        "count": count,
        "marks": marks,
        "spaces": spaces,
        "duration_ms": total_us // 1000,
        "first": first,
        "last": last,
        "protocol": protocol,
        "warning": warning,
    }


def pulse_total_us(pulses):
    total = 0
    for _, duration in iter_pulses(pulses):
        total += pulse_duration(duration)
    return total


def transmit_raw(pulses, repeats=1, monitor_rx=False, repeat_gap_ms=60):
    if not pulses:
        raise ValueError("No IR pulses")

    start = time.ticks_us()
    base_total_us = pulse_total_us(pulses)
    timeout_limit_us = base_total_us * repeats + max(0, repeats - 1) * (repeat_gap_ms * 1000) + 5000000
    stats = {
        "marks": 0,
        "rx_hits": 0,
        "duration_ms": 0,
        "repeats": repeats,
    }
    carrier_off()
    try:
        for repeat in range(repeats):
            for level, duration in iter_pulses(pulses):
                if time.ticks_diff(time.ticks_us(), start) > timeout_limit_us:
                    raise RuntimeError("IR send timeout")
                usec = pulse_duration(duration)
                if int(level) == 0:
                    stats["marks"] += 1
                    tx_pwm.duty(mark_duty())
                    if monitor_rx and usec > 450:
                        time.sleep_us(250)
                        if rx_pin.value() == 0:
                            stats["rx_hits"] += 1
                        time.sleep_us(usec - 250)
                    else:
                        time.sleep_us(usec)
                else:
                    tx_pwm.duty(off_duty())
                    time.sleep_us(usec)
            carrier_off()
            if repeat + 1 < repeats:
                time.sleep_ms(repeat_gap_ms)
    finally:
        carrier_off()

    stats["duration_ms"] = time.ticks_diff(time.ticks_us(), start) // 1000
    return stats


def send_command(name, monitor_rx=False):
    pulses = AC_CODES.get(name)
    if not pulses:
        raise KeyError(name)
    return transmit_raw(pulses, repeats=SEND_REPEATS, monitor_rx=monitor_rx)


def send_command_blast(name, count=5, gap_ms=120):
    pulses = AC_CODES.get(name)
    if not pulses:
        raise KeyError(name)
    return transmit_raw(pulses, repeats=count, monitor_rx=False, repeat_gap_ms=gap_ms)


def wait_for_ir_start(timeout_ms):
    start = time.ticks_ms()
    while rx_pin.value() == 1:
        if time.ticks_diff(time.ticks_ms(), start) > timeout_ms:
            return False
        time.sleep_ms(1)
    return True


def capture_raw(timeout_ms=CAPTURE_TIMEOUT_MS):
    if not wait_for_ir_start(timeout_ms):
        return []

    pulses = []
    last_level = rx_pin.value()
    last_time = time.ticks_us()
    frame_start = last_time

    overflow = False

    while len(pulses) < MAX_PULSES:
        level = rx_pin.value()
        now = time.ticks_us()
        duration = time.ticks_diff(now, last_time)
        frame_age = time.ticks_diff(now, frame_start)

        if frame_age > FRAME_TIMEOUT_US:
            print("Capture stopped: frame timeout")
            break

        if level != last_level:
            if duration >= MIN_PULSE_US:
                pulses.append((last_level, pulse_duration(duration)))
            last_level = level
            last_time = now
            continue

        if duration > IDLE_GAP_US:
            if last_level == 1:
                break
            print("Capture stopped: signal held low")
            break

    carrier_off()
    if len(pulses) >= MAX_PULSES:
        overflow = True

    if overflow:
        print("Capture failed: too many pulses")
        return []

    return pulses


def save_codes():
    gc.collect()
    with open("ac_codes.py", "w") as file:
        file.write("# Auto-generated by Smart Web AC Remote.\n")
        file.write("# Compact format: each list stores durations in microseconds.\n")
        file.write("# Level is implicit: mark, space, mark, space...\n")
        file.write("AC_CODES = {\n")
        for key in sorted(AC_CODES):
            file.write("    {!r}: [\n".format(key))
            pulses = compact_pulses(AC_CODES[key])
            line = "        "
            for duration in pulses:
                item = "{}".format(int(duration))
                if len(line) + len(item) > 78:
                    file.write(line.rstrip() + "\n")
                    line = "        "
                line += item + ", "
            if line.strip():
                file.write(line.rstrip() + "\n")
            file.write("    ],\n")
        file.write("}\n")


def learn_command(name):
    print("Learning command:", name)
    set_status(ok=True, error=True, ready=False)
    pulses = capture_raw()
    if not pulses:
        flash_error()
        raise RuntimeError("No IR signal captured")

    compact = compact_pulses(pulses)
    info = analyze_pulses(compact)
    AC_CODES[name] = compact
    del pulses
    del compact
    gc.collect()
    save_codes()
    flash_ok()
    print(
        "Saved {count} pulses, {duration_ms} ms for {name}: {warning}".format(
            name=name,
            **info
        )
    )
    return info


def command_cards():
    gc.collect()
    cards = []
    for key, label, hint in COMMANDS:
        pulses = AC_CODES.get(key)
        learned = bool(pulses)
        info = analyze_pulses(pulses)
        cards.append(
            """
            <section class="cmd {state}">
              <div>
                <h2>{label}</h2>
                <p>{hint}</p>
                <span>{learned}</span>
                <code>{diag}</code>
              </div>
              <div class="actions">
                <a class="send" href="/send?cmd={key}">Send</a>
                <a class="learn" href="/learn?cmd={key}">Learn</a>
              </div>
            </section>
            """.format(
                key=key,
                label=label,
                hint=hint,
                state="ready" if learned else "empty",
                learned="Learned" if learned else "Not learned",
                diag=(
                    "{} pulses, {} ms, {}, {}".format(
                        info["count"],
                        info["duration_ms"],
                        info["protocol"],
                        info["warning"],
                    )
                    if learned
                    else "No signal data"
                ),
            )
        )
    return "".join(cards)


def hitachi_cards():
    cards = []
    for key, label in HITACHI_COMMANDS:
        info = analyze_pulses(hitachi_pulses(key))
        cards.append(
            """
            <section class="cmd ready">
              <div>
                <h2>{label}</h2>
                <p>Generated Hitachi AC344 protocol</p>
                <code>{count} pulses, {duration_ms} ms</code>
              </div>
              <div class="actions">
                <a class="send" href="/hitachi?cmd={key}">Send</a>
              </div>
            </section>
            """.format(
                key=key,
                label=label,
                count=info["count"],
                duration_ms=info["duration_ms"],
            )
        )
    return "".join(cards)


def hitachi424_cards():
    cards = []
    for key, label in HITACHI424_COMMANDS:
        info = analyze_pulses(hitachi424_pulses(key))
        cards.append(
            """
            <section class="cmd ready">
              <div>
                <h2>{label}</h2>
                <p>Generated ESPHome Hitachi AC424 protocol</p>
                <code>{count} pulses, {duration_ms} ms</code>
              </div>
              <div class="actions">
                <a class="send" href="/hitachi424?cmd={key}">Send</a>
              </div>
            </section>
            """.format(
                key=key,
                label=label,
                count=info["count"],
                duration_ms=info["duration_ms"],
            )
        )
    return "".join(cards)


def html_page(message="Ready"):
    gc.collect()
    free_mem = gc.mem_free()
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Smart Web AC Remote</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: Arial, sans-serif; background: #f3f5f7; color: #1f2937; }}
    main {{ width: min(760px, 100%); margin: 0 auto; padding: 16px; }}
    .panel {{ background: #fff; border: 1px solid #d7dde5; border-radius: 8px; padding: 16px; margin-bottom: 12px; }}
    .hero {{ display: grid; gap: 10px; }}
    .title {{ margin: 0; font-size: 1.35rem; line-height: 1.2; }}
    .subtitle {{ margin: 0; color: #516072; line-height: 1.5; }}
    .meta {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 4px; }}
    .pill {{ padding: 6px 10px; border: 1px solid #cbd5e1; border-radius: 8px; background: #f8fafc; font-size: 0.88rem; color: #334155; }}
    .status {{ background: #eff6ff; color: #1d4ed8; border-left: 4px solid #2563eb; }}
    .section {{ font-size: 0.82rem; text-transform: uppercase; letter-spacing: 0.05em; color: #64748b; margin: 0 0 10px; }}
    .label {{ margin: 0 0 8px; color: #516072; font-size: 0.9rem; line-height: 1.45; }}
    .grid {{ display: grid; gap: 8px; grid-template-columns: repeat(2, minmax(0, 1fr)); }}
    .grid.single {{ grid-template-columns: 1fr; }}
    a {{ display: inline-flex; align-items: center; justify-content: center; min-height: 44px; padding: 10px 12px; border-radius: 8px; color: #fff; text-decoration: none; font-weight: 700; text-align: center; }}
    .primary {{ min-height: 60px; font-size: 1.05rem; }}
    .send {{ background: #1d4ed8; }}
    .learn {{ background: #475569; }}
    .plain {{ background: #0f766e; }}
    .danger {{ background: #b91c1c; }}
    .muted {{ background: #334155; }}
    details {{ background: #fff; border: 1px solid #d7dde5; border-radius: 8px; padding: 12px 16px; margin-bottom: 12px; }}
    summary {{ cursor: pointer; font-weight: 700; color: #334155; }}
    summary::-webkit-details-marker {{ display: none; }}
    .small-note {{ margin-top: 10px; font-size: 0.88rem; color: #64748b; }}
    @media (max-width: 520px) {{ .grid {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
  <main>
    <section class="panel hero">
      <div>
        <h1 class="title">Smart Web AC Remote</h1>
        <p class="subtitle">ESP32 AP remote for Hitachi 344, learned buttons, and daily AC control.</p>
      </div>
      <div class="meta">
        <div class="pill">Wi-Fi: {ssid}</div>
        <div class="pill">URL: http://{host}</div>
        <div class="pill">IR TX: GPIO {tx}</div>
        <div class="pill">Polarity: {polarity}</div>
        <div class="pill">Learned: {learned_count}</div>
        <div class="pill">344: {hitachi344}</div>
        <div class="pill">Free RAM: {free_mem}</div>
      </div>
    </section>
    <section class="panel status">{message}</section>
    <section class="panel">
      <div class="section">Primary control</div>
      <p class="label">This is the main button you will use most often.</p>
      <div class="grid single">
        <a class="primary send" href="/hitachi?cmd=cool26">Hitachi344 Cool 26</a>
      </div>
      <div class="grid" style="margin-top:8px;">
        <a class="muted" href="/hitachi?cmd=off">Hitachi344 Off</a>
        <a class="plain" href="/hitachi?cmd=cool25">Hitachi344 Cool 25</a>
      </div>
    </section>
    <section class="panel">
      <div class="section">Hitachi 344 Fine Tune</div>
      <p class="label">Adjust the last 344 setting without rebuilding a preset.</p>
      <div class="grid">
        <a class="send" href="/hitachi344?op=mode&mode=cool&power=on">Cool</a>
        <a class="send" href="/hitachi344?op=mode&mode=dry&power=on">Dry</a>
        <a class="send" href="/hitachi344?op=mode&mode=fan&power=on">Fan</a>
        <a class="muted" href="/hitachi344?op=off">Off</a>
        <a class="plain" href="/hitachi344?op=temp_down&power=on">Temp -</a>
        <a class="plain" href="/hitachi344?op=temp_up&power=on">Temp +</a>
        <a class="learn" href="/hitachi344?fan=low&power=on">Fan Low</a>
        <a class="learn" href="/hitachi344?fan=auto&power=on">Fan Auto</a>
      </div>
      <div class="grid" style="margin-top:8px;">
        <a class="send" href="/hitachi344?temp=22&fan=auto&mode=cool&power=on">22C</a>
        <a class="send" href="/hitachi344?temp=24&fan=auto&mode=cool&power=on">24C</a>
        <a class="send" href="/hitachi344?temp=26&fan=auto&mode=cool&power=on">26C</a>
        <a class="send" href="/hitachi344?temp=28&fan=auto&mode=cool&power=on">28C</a>
      </div>
    </section>
    <section class="panel">
      <div class="section">Learned controls</div>
      <p class="label">These are the buttons you have already learned and can resend.</p>
      <div class="grid">
        <a class="learn" href="/learn?cmd=off">Learn Off</a>
        <a class="learn" href="/send?cmd=off">Send Learned Off</a>
        <a class="learn" href="/learn?cmd=power">Learn Power</a>
        <a class="learn" href="/send?cmd=power">Send Learned Power</a>
        <a class="learn" href="/learn?cmd=cool">Learn Cool</a>
        <a class="learn" href="/send?cmd=cool">Send Learned Cool</a>
      </div>
    </section>
    <section class="panel">
      <div class="section">Secondary control</div>
      <p class="label">Use these only when you need the backup profiles.</p>
      <div class="grid">
        <a class="send" href="/hitachi424?cmd=cool26">Hitachi424 Cool 26</a>
        <a class="send" href="/hitachi424?cmd=off">Hitachi424 Off</a>
        <a class="danger" href="/stop">Stop IR Output</a>
        <a class="danger" href="/probe">Probe IR TX</a>
      </div>
    </section>
    <details>
      <summary>Advanced tools</summary>
      <div class="grid" style="margin-top:12px;">
        <a class="muted" href="/polarity?mode=normal">TX Normal</a>
        <a class="muted" href="/polarity?mode=inverted">TX Inverted</a>
        <a class="plain" href="/blast?kind=learned&cmd=power">Blast Learned Power x5</a>
        <a class="plain" href="/blast?kind=hitachi&cmd=cool26">Blast Hitachi344 Cool26 x5</a>
        <a class="plain" href="/blast?kind=hitachi424&cmd=cool26">Blast Hitachi424 Cool26 x5</a>
      </div>
      <div class="small-note">Daily use stays above; these are for setup and diagnostics.</div>
    </details>
  </main>
</body>
</html>""".format(
        ssid=AP_SSID,
        host=WEB_HOST,
        tx=IR_TX_PIN,
        polarity="inverted" if IR_ACTIVE_LOW else "normal",
        learned_count=len(AC_CODES),
        hitachi344=hitachi344_summary(),
        free_mem=free_mem,
        message=message,
    )


def get_command(path):
    params = parse_query(path)
    name = params.get("cmd", "")
    valid = [item[0] for item in COMMANDS]
    if name not in valid:
        raise ValueError("Unknown command")
    return name


def handle_send(conn, path):
    global last_message
    try:
        name = get_command(path)
        stats = send_command(name, monitor_rx=False)
        flash_ok()
        last_message = (
            "Sent {name}: {marks} marks, {duration_ms} ms, repeats {repeats}. "
            "Use Probe IR TX to verify hardware output."
        ).format(name=name, **stats)
    except KeyError:
        flash_error()
        last_message = "Not learned yet. Tap Learn first."
    except Exception as exc:
        flash_error()
        last_message = "Send failed: {}".format(exc)
    send_action_page(conn, "Send Result", last_message)


def handle_hitachi(conn, path):
    global last_message
    try:
        params = parse_query(path)
        name = params.get("cmd", "")
        valid = [item[0] for item in HITACHI_COMMANDS]
        if name not in valid:
            raise ValueError("Unknown Hitachi command")
        pulses = hitachi_pulses(name)
        stats = transmit_raw(pulses, repeats=1, monitor_rx=False)
        flash_ok()
        last_message = "Sent generated Hitachi {}: {} marks, {} ms.".format(
            name,
            stats["marks"],
            stats["duration_ms"],
        )
    except Exception as exc:
        flash_error()
        last_message = "Generated Hitachi send failed: {}".format(exc)
    send_action_page(conn, "Hitachi Result", last_message)


def handle_hitachi424(conn, path):
    global last_message
    try:
        params = parse_query(path)
        name = params.get("cmd", "")
        valid = [item[0] for item in HITACHI424_COMMANDS]
        if name not in valid:
            raise ValueError("Unknown Hitachi424 command")
        pulses = hitachi424_pulses(name)
        stats = transmit_raw(pulses, repeats=1, monitor_rx=False)
        flash_ok()
        last_message = "Sent generated Hitachi424 {}: {} marks, {} ms.".format(
            name,
            stats["marks"],
            stats["duration_ms"],
        )
    except Exception as exc:
        flash_error()
        last_message = "Generated Hitachi424 send failed: {}".format(exc)
    send_action_page(conn, "Hitachi424 Result", last_message)


def handle_hitachi344(conn, path):
    global last_message
    global LAST_HITACHI344
    try:
        params = parse_query(path)
        config = apply_hitachi344_query(params)
        pulses = hitachi344_pulses(
            mode=config["mode"],
            temp=config["temp"],
            fan=config["fan"],
            power=config["power"],
        )
        stats = transmit_raw(pulses, repeats=1, monitor_rx=False)
        LAST_HITACHI344.update(config)
        flash_ok()
        last_message = (
            "Sent Hitachi344 {summary}: {marks} marks, {duration_ms} ms."
        ).format(
            summary=hitachi344_summary(),
            marks=stats["marks"],
            duration_ms=stats["duration_ms"],
        )
    except Exception as exc:
        flash_error()
        last_message = "Hitachi344 send failed: {}".format(exc)
    send_action_page(conn, "Hitachi344 Result", last_message)


def handle_blast(conn, path):
    global last_message
    try:
        params = parse_query(path)
        kind = params.get("kind", "learned")
        name = params.get("cmd", "power")
        if kind == "learned":
            stats = send_command_blast(name, count=5)
            last_message = "Blasted learned {} x5: {} marks, {} ms.".format(
                name, stats["marks"], stats["duration_ms"]
            )
        elif kind == "hitachi424":
            pulses = hitachi424_pulses(name)
            stats = transmit_raw(pulses, repeats=5, monitor_rx=False)
            last_message = "Blasted Hitachi424 {} x5: {} marks, {} ms.".format(
                name, stats["marks"], stats["duration_ms"]
            )
        elif kind == "hitachi":
            pulses = hitachi_pulses(name)
            stats = transmit_raw(pulses, repeats=5, monitor_rx=False)
            last_message = "Blasted Hitachi344 {} x5: {} marks, {} ms.".format(
                name, stats["marks"], stats["duration_ms"]
            )
        else:
            raise ValueError("Unknown blast kind")
        flash_ok()
    except Exception as exc:
        flash_error()
        last_message = "Blast failed: {}".format(exc)
    send_action_page(conn, "Blast Result", last_message)


def handle_learn(conn, path):
    global last_message
    try:
        name = get_command(path)
        info = learn_command(name)
        last_message = "Learned {name}: {count} pulses, {duration_ms} ms, {protocol}, {warning}".format(
            name=name,
            **info
        )
    except Exception as exc:
        flash_error()
        last_message = "Learn failed: {}".format(exc)
    send_action_page(conn, "Learn Result", last_message)


def handle_stop(conn):
    global last_message
    carrier_off()
    set_status(ready=True)
    last_message = "IR output stopped."
    send_action_page(conn, "Stop Result", last_message)


def probe_ir_output():
    carrier_off()
    hits = 0
    samples = 20
    try:
        for _ in range(samples):
            tx_pwm.duty(mark_duty())
            time.sleep_us(700)
            if rx_pin.value() == 0:
                hits += 1
            carrier_off()
            time.sleep_ms(3)
    finally:
        carrier_off()
    return hits, samples


def handle_probe(conn):
    global last_message
    hits, samples = probe_ir_output()
    if hits:
        flash_ok()
        last_message = "Probe OK: RX saw IR {}/{} times.".format(hits, samples)
    else:
        flash_error()
        last_message = (
            "Probe failed: RX saw 0/{} bursts. Aim TX at RX, check VCC/GND/DAT, "
            "or tap TX Inverted and try again."
        ).format(samples)
    send_action_page(conn, "Probe Result", last_message)


def handle_polarity(conn, path):
    global IR_ACTIVE_LOW
    global last_message
    params = parse_query(path)
    mode = params.get("mode", "normal")
    if mode == "inverted":
        IR_ACTIVE_LOW = True
    else:
        IR_ACTIVE_LOW = False
    carrier_off()
    last_message = "TX polarity set to {}.".format(
        "inverted" if IR_ACTIVE_LOW else "normal"
    )
    send_action_page(conn, "Polarity Result", last_message)


def handle_request(conn):
    request = conn.recv(1024)
    if not request:
        return

    request_line = request.decode("utf-8", "ignore").split("\r\n", 1)[0]
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
        message = parse_query(path).get("msg", last_message)
        send_response(conn, "200 OK", "text/html; charset=utf-8", html_page(message))
    elif route == "/send":
        handle_send(conn, path)
    elif route == "/hitachi":
        handle_hitachi(conn, path)
    elif route == "/hitachi344":
        handle_hitachi344(conn, path)
    elif route == "/hitachi424":
        handle_hitachi424(conn, path)
    elif route == "/learn":
        handle_learn(conn, path)
    elif route == "/blast":
        handle_blast(conn, path)
    elif route == "/stop":
        handle_stop(conn)
    elif route == "/probe":
        handle_probe(conn)
    elif route == "/polarity":
        handle_polarity(conn, path)
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
    print("Listening on http://{}/".format(WEB_HOST))

    try:
        while True:
            conn, remote_addr = server.accept()
            print("Client:", remote_addr)
            try:
                handle_request(conn)
            except Exception as exc:
                print("Request error:", exc)
                carrier_off()
                try:
                    send_response(conn, "500 Internal Server Error", body=str(exc))
                except Exception:
                    pass
            finally:
                try:
                    conn.close()
                except Exception:
                    pass
    finally:
        carrier_off()
        tx_pwm.deinit()
        server.close()


def main():
    carrier_off()
    rgb_off()
    set_status(ready=True)
    start_ap()
    serve_forever()


main()
