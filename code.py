# MatrixPortal M4: time + weather icon + temperature / date (64x32 RGB matrix)
# CircuitPython 9.x / 10.x
#
# Files needed on CIRCUITPY:
#   code.py, settings.toml, weather_icons.bmp, fonts/LeagueSpartan-Bold-16.bdf

import time
import board
import displayio
import terminalio
import supervisor
import adafruit_imageload
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text import label
from adafruit_matrixportal.matrixportal import MatrixPortal

# ---------- Configuration ----------
TIMEZONE = "America/Los_Angeles"   # tz database name
LATITUDE = 45.56                   # Portland, OR -- change to your location
LONGITUDE = -122.64
USE_FAHRENHEIT = True
TWELVE_HOUR = True

TIME_SYNC_INTERVAL = 60 * 60       # resync clock hourly
WEATHER_INTERVAL = 10 * 60         # refresh weather every 10 min
RETRY_DELAY = 60                   # wait this long after a failed refresh
MAX_FAILURES = 5                   # reload after this many consecutive failures

# The lower-right area alternates between temperature and date.
# Seconds each is shown; set to 0 to always show the temperature.
ROTATE_SECONDS = 5

# Night dimming: between DIM_START and DIM_END (24h clock) everything is scaled
# down to DIM_LEVEL (0.0 = off, 1.0 = full brightness)
DIM_START = 22
DIM_END = 7
DIM_LEVEL = 0.15

TIME_COLOR = 0xFFFFFF
TEMP_COLOR = 0xFF8800
DATE_COLOR = 0x00AAFF

# Date view style:
#   "short" -> "WED 30"      (fits beside the weather icon, which stays visible)
#   "long"  -> "WED SEP 30"  (full width; the icon is hidden while the date shows)
DATE_STYLE = "short"

# Vertical nudges, in pixels, if text looks 1-2 px too high or low on your panel
TIME_Y = 0
TEMP_Y = 16
DATE_Y = 18
# -----------------------------------

DAYS = ("MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN")
MONTHS = ("JAN", "FEB", "MAR", "APR", "MAY", "JUN",
          "JUL", "AUG", "SEP", "OCT", "NOV", "DEC")

# Icon tiles in weather_icons.bmp (16x16 each, stacked top to bottom)
ICON_SUN, ICON_MOON, ICON_PARTLY_DAY, ICON_PARTLY_NIGHT, ICON_CLOUD, \
    ICON_FOG, ICON_RAIN, ICON_SNOW, ICON_THUNDER = range(9)

unit_name = "fahrenheit" if USE_FAHRENHEIT else "celsius"
unit_letter = "F" if USE_FAHRENHEIT else "C"
WEATHER_URL = (
    "https://api.open-meteo.com/v1/forecast"
    f"?latitude={LATITUDE}&longitude={LONGITUDE}"
    f"&current=temperature_2m,weather_code,is_day&temperature_unit={unit_name}"
)
WEATHER_PATH = (
    ("current", "temperature_2m"),
    ("current", "weather_code"),
    ("current", "is_day"),
)

matrixportal = MatrixPortal(status_neopixel=board.NEOPIXEL, bit_depth=4, debug=False)
splash = matrixportal.graphics.splash

big_font = bitmap_font.load_font("/fonts/LeagueSpartan-Bold-16.bdf")
small_font = terminalio.FONT

# --- Text labels ---
time_label = label.Label(
    big_font, text="--:--", color=TIME_COLOR,
    anchor_point=(0.5, 0.0), anchored_position=(32, TIME_Y),
)
temp_label = label.Label(
    big_font, text="--", color=TEMP_COLOR,
    anchor_point=(0.5, 0.0), anchored_position=(41, TEMP_Y),
)
date_label = label.Label(
    small_font, text="", color=DATE_COLOR,
    anchor_point=(0.5, 0.0),
    anchored_position=(41 if DATE_STYLE == "short" else 32, DATE_Y),
)
date_label.hidden = True

# --- Weather icon (one 16x16 tile shown from the sprite sheet) ---
icon_bitmap, icon_palette = adafruit_imageload.load(
    "/weather_icons.bmp", bitmap=displayio.Bitmap, palette=displayio.Palette
)
base_palette = [icon_palette[i] for i in range(len(icon_palette))]
icon_grid = displayio.TileGrid(
    icon_bitmap, pixel_shader=icon_palette,
    width=1, height=1, tile_width=16, tile_height=16, x=1, y=16,
)
icon_grid.hidden = True   # until the first weather fetch succeeds

for item in (time_label, temp_label, date_label, icon_grid):
    splash.append(item)


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
    time_label.color = scale_color(TIME_COLOR, factor)
    temp_label.color = scale_color(TEMP_COLOR, factor)
    date_label.color = scale_color(DATE_COLOR, factor)
    for i, color in enumerate(base_palette):
        icon_palette[i] = scale_color(color, factor)


def icon_for(code, daytime):
    if code in (0, 1):
        return ICON_SUN if daytime else ICON_MOON
    if code == 2:
        return ICON_PARTLY_DAY if daytime else ICON_PARTLY_NIGHT
    if code == 3:
        return ICON_CLOUD
    if code in (45, 48):
        return ICON_FOG
    if 51 <= code <= 67 or 80 <= code <= 82:    # drizzle, rain, showers
        return ICON_RAIN
    if 71 <= code <= 77 or code in (85, 86):    # snow
        return ICON_SNOW
    if code >= 95:
        return ICON_THUNDER
    return ICON_CLOUD


def sync_time():
    matrixportal.network.get_local_time(location=TIMEZONE)


def fetch_weather():
    result = matrixportal.network.fetch_data(WEATHER_URL, json_path=WEATHER_PATH)
    if not isinstance(result, (list, tuple)) or len(result) < 3:
        raise ValueError("unexpected weather response")
    temp = round(float(result[0]))
    code = int(result[1])
    daytime = bool(int(result[2]))
    # Drop the unit letter for 3-digit temps so the text always fits
    text = f"{temp}°{unit_letter}" if abs(temp) < 100 else f"{temp}°"
    return text, icon_for(code, daytime)


def format_time(now, colon_on):
    hour, minute = now.tm_hour, now.tm_min
    sep = ":" if colon_on else " "
    if TWELVE_HOUR:
        return f"{hour % 12 or 12}{sep}{minute:02d}"
    return f"{hour:02d}{sep}{minute:02d}"


def update_view():
    """Show either temperature or date in the lower area; manage icon visibility."""
    temp_label.hidden = showing_date
    date_label.hidden = not showing_date
    icon_grid.hidden = not have_weather or (showing_date and DATE_STYLE == "long")


failures = 0
next_time_sync = 0        # monotonic timestamps of the next attempt
next_weather = 0
next_rotate = 0
showing_date = False
have_weather = False
night_state = None
last_time_text = None
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
            temp_text, icon_index = fetch_weather()
            temp_label.text = temp_text
            icon_grid[0] = icon_index
            have_weather = True
            update_view()
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

    if DATE_STYLE == "short":
        date_text = f"{DAYS[local.tm_wday]} {local.tm_mday}"
    else:
        date_text = f"{DAYS[local.tm_wday]} {MONTHS[local.tm_mon - 1]} {local.tm_mday}"
    if date_text != last_date_text:
        date_label.text = date_text
        last_date_text = date_text

    if ROTATE_SECONDS and now_mono >= next_rotate:
        showing_date = not showing_date
        update_view()
        next_rotate = now_mono + ROTATE_SECONDS

    time_text = format_time(local, int(now_mono) % 2 == 0)
    if time_text != last_time_text:
        time_label.text = time_text
        last_time_text = time_text

    time.sleep(0.25)