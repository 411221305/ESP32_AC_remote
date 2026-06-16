from machine import Pin
import time

RECV_PIN = 33

START_TIMEOUT_MS = 5000
FRAME_TIMEOUT_US = 80000
IDLE_GAP_US = 12000
MAX_PULSES = 80
RELEASE_QUIET_MS = 700

KEY_BY_RAW = {
    0xBA45FF00: "1",
    0xB946FF00: "2",
    0xB847FF00: "3",
    0xBB44FF00: "4",
    0xBF40FF00: "5",
    0xBC43FF00: "6",
    0xF807FF00: "7",
    0xEA15FF00: "8",
    0xF609FF00: "9",
    0xE619FF00: "10/0",
    0xE916FF00: "*",
    0xF20DFF00: "#",
    0xE718FF00: "UP",
    0xAD52FF00: "DOWN",
    0xF708FF00: "LEFT",
    0xA55AFF00: "RIGHT",
    0xE31CFF00: "OK",
}

CAPTURE_KEYS = ("*", "#", "UP", "DOWN", "LEFT", "RIGHT", "OK")

ir = Pin(RECV_PIN, Pin.IN, Pin.PULL_UP)


def in_range(value, target, tolerance):
    return target - tolerance <= value <= target + tolerance


def wait_for_start(timeout_ms=START_TIMEOUT_MS):
    start = time.ticks_ms()
    while ir.value() == 1:
        if time.ticks_diff(time.ticks_ms(), start) > timeout_ms:
            return False
    return True


def read_ir(start_timeout_ms=START_TIMEOUT_MS):
    """Read one raw IR frame as (level, duration_us) pulses."""
    if not wait_for_start(start_timeout_ms):
        return []

    pulses = []
    last_level = ir.value()
    last_time = time.ticks_us()
    frame_start = last_time

    while len(pulses) < MAX_PULSES:
        level = ir.value()
        now = time.ticks_us()
        duration = time.ticks_diff(now, last_time)

        if level != last_level:
            pulses.append((last_level, duration))
            last_level = level
            last_time = now
            continue

        if last_level == 1 and duration > IDLE_GAP_US:
            break

        if time.ticks_diff(now, frame_start) > FRAME_TIMEOUT_US:
            break

    return pulses


def bits_to_byte(bits, start):
    value = 0
    for offset in range(8):
        value |= bits[start + offset] << offset
    return value


def decode_nec(pulses):
    """Decode NEC IR pulses. Returns a dict, 'repeat', or None."""
    if len(pulses) < 2:
        return None

    if pulses[0][0] != 0 or pulses[1][0] != 1:
        return None

    leader_low = pulses[0][1]
    leader_high = pulses[1][1]

    if in_range(leader_low, 9000, 1400) and in_range(leader_high, 2250, 650):
        return "repeat"

    if len(pulses) < 4:
        return None

    if not in_range(leader_low, 9000, 1400):
        return None
    if not in_range(leader_high, 4500, 1000):
        return None

    bits = []
    index = 2

    while index + 1 < len(pulses) and len(bits) < 32:
        low_level, low_duration = pulses[index]
        high_level, high_duration = pulses[index + 1]

        if low_level != 0 or high_level != 1:
            return None
        if not in_range(low_duration, 560, 300):
            return None

        if in_range(high_duration, 560, 350):
            bits.append(0)
        elif in_range(high_duration, 1690, 550):
            bits.append(1)
        else:
            return None

        index += 2

    if len(bits) != 32:
        return None

    address = bits_to_byte(bits, 0)
    address_inverse = bits_to_byte(bits, 8)
    command = bits_to_byte(bits, 16)
    command_inverse = bits_to_byte(bits, 24)

    raw = (
        address
        | (address_inverse << 8)
        | (command << 16)
        | (command_inverse << 24)
    )

    return {
        "raw": raw,
        "key": KEY_BY_RAW.get(raw, "?"),
        "address": address,
        "address_inverse": address_inverse,
        "command": command,
        "command_inverse": command_inverse,
        "valid": (address ^ address_inverse) == 0xFF
        and (command ^ command_inverse) == 0xFF,
    }


def show_decode_result(result, pulses):
    if result == "repeat":
        print("NEC repeat")
        return

    if result is None:
        durations = [duration for _, duration in pulses[:10]]
        print("decode failed: pulses={}, first={}".format(len(pulses), durations))
        return

    print(
        "NEC key={} raw=0x{:08X} addr=0x{:02X} cmd=0x{:02X} valid={}".format(
            result["key"],
            result["raw"],
            result["address"],
            result["command"],
            result["valid"],
        )
    )


def wait_for_valid_key():
    while True:
        pulses = read_ir()
        if not pulses:
            continue

        result = decode_nec(pulses)
        if result == "repeat":
            continue
        if result is None:
            durations = [duration for _, duration in pulses[:8]]
            print("decode failed: pulses={}, first={}".format(len(pulses), durations))
            continue
        if not result["valid"]:
            print(
                "invalid NEC raw=0x{:08X} cmd=0x{:02X}".format(
                    result["raw"],
                    result["command"],
                )
            )
            continue

        return result


def wait_until_quiet(quiet_ms=RELEASE_QUIET_MS):
    quiet_start = time.ticks_ms()

    while time.ticks_diff(time.ticks_ms(), quiet_start) < quiet_ms:
        pulses = read_ir(100)
        if pulses:
            quiet_start = time.ticks_ms()


def print_key_table(key_by_raw):
    print("")
    print("KEY_BY_RAW = {")
    for raw, key in key_by_raw.items():
        print('    0x{:08X}: "{}",'.format(raw, key))
    print("}")


def capture_keys():
    print("IR receiver ready on GPIO {}".format(RECV_PIN))
    print("Terminal capture mode")
    print("Press each key once when prompted, then release it.")
    print("")

    captured = {}

    for key in CAPTURE_KEYS:
        print("Release all keys. Waiting for quiet signal...")
        wait_until_quiet()

        while True:
            print("Please press [{}], then release ...".format(key))
            result = wait_for_valid_key()
            raw = result["raw"]

            if raw in captured:
                print(
                    "same as [{}] raw=0x{:08X}; release key and press [{}] again".format(
                        captured[raw],
                        raw,
                        key,
                    )
                )
                wait_until_quiet()
                continue

            if raw in KEY_BY_RAW:
                print(
                    "same as existing key [{}] raw=0x{:08X}; press [{}] again".format(
                        KEY_BY_RAW[raw],
                        raw,
                        key,
                    )
                )
                wait_until_quiet()
                continue

            captured[raw] = key
            KEY_BY_RAW[raw] = key
            break

        print(
            "recorded key={} raw=0x{:08X} addr=0x{:02X} cmd=0x{:02X}".format(
                key,
                raw,
                result["address"],
                result["command"],
            )
        )
        print("")
        wait_until_quiet()

    print("Capture complete.")
    print("New keys:")
    print_key_table(captured)
    print("All keys:")
    print_key_table(KEY_BY_RAW)


def monitor_keys():
    print("IR receiver ready on GPIO {}".format(RECV_PIN))
    print("Press Ctrl+C to stop.")

    while True:
        pulses = read_ir()
        if not pulses:
            continue

        result = decode_nec(pulses)
        show_decode_result(result, pulses)


def confirm_all_keys():
    print("IR receiver ready on GPIO {}".format(RECV_PIN))
    print("Confirm mode: press every button on your remote.")
    print("Each press will be printed with key name and raw code.")
    print("Press Ctrl+C to stop.")
    print("")

    seen = {}

    while True:
        pulses = read_ir()
        if not pulses:
            continue

        result = decode_nec(pulses)
        if result == "repeat" or result is None:
            continue
        if not result["valid"]:
            continue

        raw = result["raw"]
        key_name = KEY_BY_RAW.get(raw, "?")

        if raw not in seen:
            seen[raw] = key_name
            print("new key: {} raw=0x{:08X}".format(key_name, raw))
        else:
            print("again: {} raw=0x{:08X}".format(key_name, raw))


def main():
    confirm_all_keys()


if __name__ == "__main__":
    main()
