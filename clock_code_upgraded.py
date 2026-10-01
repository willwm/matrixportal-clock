# MatrixPortal M4: time + date + temperature display (64x32 RGB matrix)
# CircuitPython 9.x / 10.x

import time
import board
import terminalio
import supervisor
from adafruit_matrixportal.matrixportal import MatrixPortal

# ---------- Configuration ----------
TIMEZONE = "America/Los_Angeles"   # tz database name
LATITUDE = 45.56                   # Portland, OR -- change to your location
LONGITUDE = -122.64
USE_FAHRENHEIT = True
TWELVE_HOUR = True

TIME_SYNC_INTERVAL = 60 * 60       # resync clock hourly
WEATHER_INTERVAL = 10 * 60         # refresh temperature every 10 min
RETRY_DELAY = 60                   # wait this long after a failed refresh
MAX_FAILURES = 5                   # reload after this many consecutive failures

# Night dimming: between DIM_START and DIM_END (24h clock) colors are scaled
# down to DIM_LEVEL (0.0 = off, 1.0 = full brightness)
DIM_START = 22
DIM_END = 7
DIM_LEVEL = 0.15

TIME_COLOR = 0xFFFFFF
DATE_COLOR = 0x00AAFF
TEMP_COLOR = 0xFF8800
# -----------------------------------

DAYS = ("MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN")
MONTHS = ("JAN", "FEB", "MAR", "APR", "MAY", "JUN",
          "JUL", "AUG", "SEP", "OCT", "NOV", "DEC")

unit = "fahrenheit" if USE_FAHRENHEIT else "celsius"
WEATHER_URL = (
    "https://api.open-meteo.com/v1/forecast"
    f"?latitude={LATITUDE}&longitude={LONGITUDE}"
    f"&current=temperature_2m&temperature_unit={unit}"
)
TEMP_PATH = (("current", "temperature_2m"),)

matrixportal = MatrixPortal(status_neopixel=board.NEOPIXEL, debug=False)

# Layout (64x32): time on top (scale 2), date in the middle, temperature below
TIME_FIELD = matrixportal.add_text(
    text_font=terminalio.FONT,
    text_position=(32, 8),
    text_anchor_point=(0.5, 0.5),
    text_color=TIME_COLOR,
    text_scale=2,
    text="--:--",
)
DATE_FIELD = matrixportal.add_text(
    text_font=terminalio.FONT,
    text_position=(32, 20),
    text_anchor_point=(0.5, 0.5),
    text_color=DATE_COLOR,
    text="",
)
TEMP_FIELD = matrixportal.add_text(
    text_font=terminalio.FONT,
    text_position=(32, 28),
    text_anchor_point=(0.5, 0.5),
    text_color=TEMP_COLOR,
    text="--",
)


def scale_color(color, factor):
    r = int(((color >> 16) & 0xFF) * factor)
    g = int(((color >> 8) & 0xFF) * factor)
    b = int((color & 0xFF) * factor)
    return (r << 16) | (g << 8) | b


def is_night(hour):
    if DIM_START > DIM_END:                # window crosses midnight
        return hour >= DIM_START or hour < DIM_END
    return DIM_START <= hour < DIM_END


def apply_brightness(night):
    factor = DIM_LEVEL if night else 1.0
    matrixportal.set_text_color(scale_color(TIME_COLOR, factor), TIME_FIELD)
    matrixportal.set_text_color(scale_color(DATE_COLOR, factor), DATE_FIELD)
    matrixportal.set_text_color(scale_color(TEMP_COLOR, factor), TEMP_FIELD)


def sync_time():
    matrixportal.network.get_local_time(location=TIMEZONE)


def fetch_temperature():
    result = matrixportal.network.fetch_data(WEATHER_URL, json_path=TEMP_PATH)
    if isinstance(result, (list, tuple)):
        result = result[0]
    suffix = "F" if USE_FAHRENHEIT else "C"
    return f"{round(float(result))}{suffix}"


def format_time(now, colon_on):
    hour, minute = now.tm_hour, now.tm_min
    if TWELVE_HOUR:
        hour = hour % 12 or 12
        return f"{hour}:{minute:02d}" if colon_on else f"{hour} {minute:02d}"
    return f"{hour:02d}:{minute:02d}" if colon_on else f"{hour:02d} {minute:02d}"


def format_date(now):
    return f"{DAYS[now.tm_wday]} {MONTHS[now.tm_mon - 1]} {now.tm_mday}"


failures = 0
next_time_sync = 0        # monotonic timestamps of the next attempt
next_weather = 0
night_state = None
last_date_text = None

while True:
    now_mono = time.monotonic()

    # --- Refresh network data (each task fails independently) ---
    if now_mono >= next_time_sync:
        try:
            sync_time()
            next_time_sync = now_mono + TIME_SYNC_INTERVAL
            failures = 0
        except (RuntimeError, ValueError, OSError) as err:
            print("Time sync failed:", err)
            failures += 1
            next_time_sync = now_mono + RETRY_DELAY

    if now_mono >= next_weather:
        try:
            matrixportal.set_text(fetch_temperature(), TEMP_FIELD)
            next_weather = now_mono + WEATHER_INTERVAL
            failures = 0
        except (RuntimeError, ValueError, OSError) as err:
            print("Weather fetch failed:", err)
            failures += 1
            next_weather = now_mono + RETRY_DELAY

    if failures >= MAX_FAILURES:
        supervisor.reload()

    # --- Update display ---
    local = time.localtime()

    night = is_night(local.tm_hour)
    if night != night_state:
        apply_brightness(night)
        night_state = night

    date_text = format_date(local)
    if date_text != last_date_text:
        matrixportal.set_text(date_text, DATE_FIELD)
        last_date_text = date_text

    # Blink the colon each second
    matrixportal.set_text(format_time(local, int(now_mono) % 2 == 0), TIME_FIELD)
    time.sleep(0.5)