"""OLED 中文字視覺特效展示。

硬體：SSD1306 128x64 I2C OLED（SDA=GPIO21, SCL=GPIO22）。
中文字來源：lib/zh_ndhu_font.py（目前僅內建「國立東華大學」六個字）。

內含 8 種特效，會依序循環播放：
  1. TYPEWRITER 逐字浮現
  2. WAVE       波浪起伏
  3. MARQUEE    跑馬燈捲動
  4. DISSOLVE   像素溶解登場
  5. WIPE       拉幕揭露
  6. BLINK      閃爍反白
  7. BOUNCE     上下彈跳
  8. BREATHE    呼吸亮度
"""

import math
from machine import I2C, Pin
from time import sleep_ms

from lib.oled_i2c import OLED12864_I2C
from lib.zh_ndhu_font import GLYPHS, HEIGHT, WIDTH, draw_char, draw_text, text_width

try:  # MicroPython
    import urandom as _rng
except ImportError:  # CPython（離線測試用）
    import random as _rng


OLED_SDA = 21
OLED_SCL = 22
MESSAGE = "國立東華大學"
DEFAULT_CONTRAST = 0xCF


def init_oled():
    i2c = I2C(0, scl=Pin(OLED_SCL), sda=Pin(OLED_SDA), freq=400000)
    devices = i2c.scan()
    print("I2C scan:", [hex(d) for d in devices])
    if not devices:
        raise RuntimeError("No I2C OLED on SDA={} SCL={}".format(OLED_SDA, OLED_SCL))
    addr = 0x3C if 0x3C in devices else devices[0]
    return OLED12864_I2C(i2c, addr=addr)


def centered_x(oled, text=MESSAGE, spacing=1):
    return (oled.width - text_width(text, spacing)) // 2


def centered_y(oled):
    return (oled.height - HEIGHT) // 2


def text_pixels(text, x, y, spacing=1):
    """回傳整段文字所有亮起的像素座標 (px, py)，供溶解 / 粒子效果使用。"""
    points = []
    cursor = x
    for char in text:
        rows = GLYPHS.get(char)
        if rows is not None:
            for row_index, row in enumerate(rows):
                for col_index, pixel in enumerate(row):
                    if pixel == "1":
                        points.append((cursor + col_index, y + row_index))
        cursor += WIDTH + spacing
    return points


def shuffle(items):
    """Fisher-Yates 洗牌（MicroPython 沒有 random.shuffle 也能用）。"""
    for i in range(len(items) - 1, 0, -1):
        j = _rng.getrandbits(16) % (i + 1)
        items[i], items[j] = items[j], items[i]


def banner(oled, label, delay=700):
    """在特效之間顯示英文標題卡。"""
    oled.contrast(DEFAULT_CONTRAST)
    oled.fill(0)
    tx = max(0, (oled.width - len(label) * 8) // 2)
    oled.text(label, tx, 28)
    oled.show()
    sleep_ms(delay)


# --- 特效們 ------------------------------------------------------------------

def effect_typewriter(oled):
    """逐字浮現，像打字一樣一個字一個字跳出來。"""
    x, y = centered_x(oled), centered_y(oled)
    for count in range(1, len(MESSAGE) + 1):
        oled.fill(0)
        draw_text(oled, MESSAGE[:count], x, y)
        oled.show()
        sleep_ms(320)
    sleep_ms(400)


def effect_wave(oled):
    """每個字上下錯開，做出波浪起伏。"""
    x, baseline = centered_x(oled), centered_y(oled)
    for frame in range(48):
        oled.fill(0)
        cursor = x
        for index, char in enumerate(MESSAGE):
            offset = int(6 * math.sin(frame * 0.5 + index * 0.9))
            draw_char(oled, char, cursor, baseline + offset)
            cursor += WIDTH + 1
        oled.show()
        sleep_ms(40)


def effect_marquee(oled):
    """跑馬燈：文字從右邊滑進來、往左邊滑出去。"""
    y = centered_y(oled)
    width = text_width(MESSAGE)
    pos = oled.width
    while pos > -width:
        oled.fill(0)
        draw_text(oled, MESSAGE, pos, y)
        oled.show()
        pos -= 4
        sleep_ms(25)


def effect_dissolve(oled):
    """像素溶解登場：亮點隨機一批一批冒出來，慢慢拼成文字。"""
    x, y = centered_x(oled), centered_y(oled)
    points = text_pixels(MESSAGE, x, y)
    shuffle(points)
    oled.fill(0)
    oled.show()
    batch = max(1, len(points) // 22)
    for start in range(0, len(points), batch):
        for (px, py) in points[start:start + batch]:
            oled.pixel(px, py, 1)
        oled.show()
        sleep_ms(35)
    sleep_ms(400)


def effect_wipe(oled):
    """拉幕揭露：由左而右一道一道把文字刷出來。"""
    x, y = centered_x(oled), centered_y(oled)
    width = text_width(MESSAGE)
    for reveal in range(0, width + 6, 4):
        oled.fill(0)
        draw_text(oled, MESSAGE, x, y)
        edge = x + reveal
        oled.fill_rect(edge, 0, oled.width - edge, oled.height, 0)
        oled.show()
        sleep_ms(28)
    sleep_ms(400)


def effect_blink(oled):
    """閃爍幾下，再來幾次黑白反白。"""
    x, y = centered_x(oled), centered_y(oled)
    for _ in range(4):
        oled.fill(0)
        draw_text(oled, MESSAGE, x, y)
        oled.show()
        sleep_ms(260)
        oled.fill(0)
        oled.show()
        sleep_ms(180)
    for _ in range(3):
        oled.fill(1)
        draw_text(oled, MESSAGE, x, y, color=0)
        oled.show()
        sleep_ms(220)
        oled.fill(0)
        draw_text(oled, MESSAGE, x, y, color=1)
        oled.show()
        sleep_ms(220)


def effect_bounce(oled):
    """整段文字從上方落下，帶阻尼的彈跳。"""
    x = centered_x(oled)
    floor = centered_y(oled)
    for frame in range(34):
        damp = 1.0 - frame / 34.0
        offset = int(abs(22 * math.cos(frame * 0.55)) * damp)
        oled.fill(0)
        draw_text(oled, MESSAGE, x, floor - offset)
        oled.show()
        sleep_ms(40)
    sleep_ms(300)


def effect_breathe(oled):
    """文字不動，用螢幕亮度做出呼吸般的明暗變化。"""
    x, y = centered_x(oled), centered_y(oled)
    oled.fill(0)
    draw_text(oled, MESSAGE, x, y)
    oled.show()
    for _ in range(2):
        for angle in range(0, 360, 12):
            level = int(140 + 115 * math.sin(math.radians(angle)))
            oled.contrast(max(1, min(255, level)))
            sleep_ms(28)
    oled.contrast(DEFAULT_CONTRAST)


EFFECTS = (
    ("1.TYPEWRITER", effect_typewriter),
    ("2.WAVE", effect_wave),
    ("3.MARQUEE", effect_marquee),
    ("4.DISSOLVE", effect_dissolve),
    ("5.WIPE", effect_wipe),
    ("6.BLINK", effect_blink),
    ("7.BOUNCE", effect_bounce),
    ("8.BREATHE", effect_breathe),
)


def main():
    oled = init_oled()
    print("OLED FX ready. Message:", MESSAGE)
    while True:
        for label, effect in EFFECTS:
            print("Effect:", label)
            banner(oled, label)
            effect(oled)
            sleep_ms(500)


main()
