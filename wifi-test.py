# wifi_test.py -- temporary diagnostic for MatrixPortal M4
# Copy to CIRCUITPY as code.py (back up your real code.py first!), watch the
# serial console, then restore your real code.py.

import os
import time
import board
import busio
from digitalio import DigitalInOut
import adafruit_connection_manager
import adafruit_requests
from adafruit_esp32spi import adafruit_esp32spi

esp32_cs = DigitalInOut(board.ESP_CS)
esp32_ready = DigitalInOut(board.ESP_BUSY)
esp32_reset = DigitalInOut(board.ESP_RESET)
spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)

print("ESP32 status:", esp.status)
fw = esp.firmware_version
print("NINA firmware version:", fw.decode() if isinstance(fw, (bytes, bytearray)) else fw)

print("Connecting to Wi-Fi...")
while not esp.is_connected:
    try:
        esp.connect_AP(
            os.getenv("CIRCUITPY_WIFI_SSID"), os.getenv("CIRCUITPY_WIFI_PASSWORD")
        )
    except OSError as err:
        print("Retrying:", err)
        time.sleep(2)
print("Connected. IP:", esp.ipv4_address)

pool = adafruit_connection_manager.get_radio_socketpool(esp)
ssl_context = adafruit_connection_manager.get_radio_ssl_context(esp)
requests = adafruit_requests.Session(pool, ssl_context)

TESTS = (
    ("HTTP ", "http://wifitest.adafruit.com/testwifi/index.html"),
    ("HTTPS", "https://api.open-meteo.com/v1/forecast?latitude=45.56&longitude=-122.64&current=temperature_2m"),
    ("HTTPS", "https://io.adafruit.com/api/v2/time/seconds"),
)

for label, url in TESTS:
    try:
        r = requests.get(url)
        print(label, "OK", r.status_code, url)
        r.close()
    except Exception as err:  # noqa: BLE001
        print(label, "FAILED", url)
        print("   ", type(err).__name__, err)

print("Done.")