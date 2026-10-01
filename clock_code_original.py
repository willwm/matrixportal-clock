# MatrixPortal M4: time + temperature display (64x32 RGB matrix)
# Requires CircuitPython 9.x or 10.x and the libraries listed in README.txt


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
MAX_FAILURES = 5                   # reboot after this many consecutive failures

TIME_COLOR = 0xFFFFFF
TEMP_COLOR = 0xFF8800
# -----------------------------------

unit = "fahrenheit" if USE_FAHRENHEIT else "celsius"
WEATHER_URL = (
    "https://api.open-meteo.com/v1/forecast"
    f"?latitude={LATITUDE}&longitude={LONGITUDE}"
    f"&current=temperature_2m&temperature_unit={unit}"
)
TEMP_PATH = (("current", "temperature_2m"),)

matrixportal = MatrixPortal(status_neopixel=board.NEOPIXEL, debug=False)

# Text field 0: time (scale 2), field 1: temperature
TIME_FIELD = matrixportal.add_text(
    text_font=terminalio.FONT,
    text_position=(32, 10),
    text_anchor_point=(0.5, 0.5),
    text_color=TIME_COLOR,
    text_scale=2,
    text="--:--",
)
TEMP_FIELD = matrixportal.add_text(
    text_font=terminalio.FONT,
    text_position=(32, 26),
    text_anchor_point=(0.5, 0.5),
    text_color=TEMP_COLOR,
    text="--",
)


def sync_time():
    matrixportal.network.get_local_time(location=TIMEZONE)


def fetch_temperature():
    result = matrixportal.network.fetch_data(WEATHER_URL, json_path=TEMP_PATH)
    if isinstance(result, (list, tuple)):
        result = result[0]
    suffix = "F" if USE_FAHRENHEIT else "C"
    return f"{round(float(result))}{suffix}"


def format_time(colon_on):
    now = time.localtime()
    hour, minute = now.tm_hour, now.tm_min
    if TWELVE_HOUR:
        hour = hour % 12 or 12
        text = f"{hour}:{minute:02d}" if colon_on else f"{hour} {minute:02d}"
    else:
        text = f"{hour:02d}:{minute:02d}" if colon_on else f"{hour:02d} {minute:02d}"
    return text


failures = 0
last_time_sync = None
last_weather = None

while True:
    now = time.monotonic()

    try:
        if last_time_sync is None or now - last_time_sync > TIME_SYNC_INTERVAL:
            sync_time()
            last_time_sync = now

        if last_weather is None or now - last_weather > WEATHER_INTERVAL:
            matrixportal.set_text(fetch_temperature(), TEMP_FIELD)
            last_weather = now

        failures = 0
    except (RuntimeError, ValueError, OSError) as err:
        failures += 1
        print("Update failed:", err)
        if failures >= MAX_FAILURES:
            supervisor.reload()
        time.sleep(5)
        continue

    # Blink the colon each second
    matrixportal.set_text(format_time(int(now) % 2 == 0), TIME_FIELD)
    time.sleep(0.5)
