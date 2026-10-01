# MatrixPortal M4 Clock and Weather Display

A CircuitPython project for an Adafruit MatrixPortal M4 and a 64x32 RGB LED matrix. The display shows the local time, current temperature, a weather icon, and the date.

The primary program is `code.py`. It gets time over the network and retrieves current weather from the Open-Meteo API. No Open-Meteo API key is required.

## Hardware and Software

- Adafruit MatrixPortal M4 with its ESP32 Wi-Fi co-processor
- 64x32 RGB LED matrix compatible with the MatrixPortal M4
- CircuitPython 9.x or 10.x (the included boot log shows CircuitPython 10.3.1)
- A 2.4 GHz Wi-Fi network with internet access

## Install

1. Install CircuitPython on the MatrixPortal M4 and connect the board to your computer. Its drive should appear as `CIRCUITPY`.
2. Copy `code.py`, `weather_icons.bmp`, `settings.toml`, and the `fonts/` and `lib/` folders to the root of `CIRCUITPY`.
3. Create `settings.toml` using `settings.toml.example` as a template. Replace `CIRCUITPY_WIFI_SSID` and `CIRCUITPY_WIFI_PASSWORD` with your network name and password. The example also contains Adafruit IO placeholders for other experiments; the active `code.py` does not use them.
4. Save the files and let the board restart. The display will update after it connects and receives its first time and weather responses.

Keep real credentials in `settings.toml`, not in source files. This repository ignores `settings.toml`; use the example file for a safe template.

## Configuration

Edit the configuration block near the top of `code.py`:

- `TIMEZONE`: IANA time-zone name used for network time sync, for example `America/Los_Angeles`.
- `LATITUDE` and `LONGITUDE`: coordinates used for the weather request. The defaults are for Portland, Oregon.
- `USE_FAHRENHEIT`: choose Fahrenheit (`True`) or Celsius (`False`).
- `TWELVE_HOUR`: choose 12-hour or 24-hour time.
- `TIME_SYNC_INTERVAL` and `WEATHER_INTERVAL`: time-sync and weather refresh periods, in seconds.
- `ROTATE_SECONDS`: how long each temperature/date view is shown. Set to `0` to keep the temperature visible.
- `DIM_START`, `DIM_END`, and `DIM_LEVEL`: overnight dimming window and brightness scale. Hours use a 24-hour clock; the default dims from 22:00 through 06:59.
- `TIME_COLOR`, `TEMP_COLOR`, `DATE_COLOR`: display colors in `0xRRGGBB` format.
- `TIME_Y`, `TEMP_Y`, and `DATE_Y`: vertical pixel offsets for positioning text on the matrix.

Weather icons are selected from the 16x16 tiles in `weather_icons.bmp`. The custom time font is `fonts/LeagueSpartan-Bold-16.bdf`.

## Display and Network Behavior

- The time is centered across the top of the matrix; the weather icon is at the lower left.
- The lower-right area alternates between temperature and a two-line day/date view.
- The time colon blinks once per second.
- Time is synchronized hourly and current weather is refreshed every 10 minutes by default.
- Failed network updates are retried after 60 seconds. After five consecutive failed update attempts, the board reloads.
- The display dims during the configured night window.

## Files

- `code.py`: active clock, date, and weather display.
- `weather_icons.bmp` and `fonts/LeagueSpartan-Bold-16.bdf`: display assets required by `code.py`.
- `lib/`: CircuitPython libraries used by the project. Copy this folder to the board's root as shown above.
- `settings.toml.example`: template for local configuration; copy its Wi-Fi entries into your private `settings.toml`.
- `clock_code_upgraded.py`: earlier time/date/temperature layout without the weather icon or rotating date view. Copy it to the board as `code.py` to run it.
- `clock_code_original.py`: earlier time/temperature-only version. Copy it to the board as `code.py` to run it.
- `wifi-test.py`: standalone Wi-Fi and HTTPS diagnostic. To run it, back up the active program, copy this file to the board as `code.py`, and inspect the serial console output; restore the active `code.py` afterward.
- `gifs/led_matrices_sine_tube.gif`: asset kept in the project; it is not used by the active program.

## Troubleshooting

- **No Wi-Fi connection:** Check the SSID/password in `settings.toml`, confirm the network is 2.4 GHz, and inspect the serial console for connection errors.
- **Weather does not appear:** Confirm the board has internet access and that the configured coordinates are valid. The active program prints weather-fetch errors to the serial console and retries.
- **Missing asset or import errors:** Verify `weather_icons.bmp`, `fonts/LeagueSpartan-Bold-16.bdf`, and the complete `lib/` folder are present at the paths shown above.
- **Text alignment or brightness needs adjustment:** Tune the position and night-dimming settings near the top of `code.py`.
