from __future__ import annotations

"""
Property of Data-Blitz Inc.
Author: Paul Harvener

Catalog generator for creating deterministic mock DigiKey-style product data.
"""

import json
import random
from pathlib import Path

TARGET_COUNT = 5000
RNG = random.Random(42)

VENDORS = [
    "Raspberry Pi",
    "Adafruit Industries",
    "SparkFun Electronics",
    "Seeed Studio",
    "DFRobot",
    "Pimoroni Ltd",
    "STMicroelectronics",
    "Texas Instruments",
    "Microchip Technology",
    "NXP USA Inc.",
    "Infineon Technologies",
    "Vishay Dale",
    "Murata Electronics",
    "Panasonic Electronic Components",
    "TE Connectivity",
    "Molex",
    "Samtec Inc.",
    "Amphenol ICC",
    "onsemi",
    "Analog Devices Inc.",
    "Silicon Labs",
    "Nordic Semiconductor",
    "Espressif Systems",
    "ROHM Semiconductor",
    "Littelfuse Inc.",
]

CATEGORIES = [
    {
        "name": "Single Board Computers (SBC)",
        "tokens": ["single board computer", "linux", "arm", "embedded"],
        "use_cases": ["edge ai", "iot gateway", "industrial control", "education"],
        "price": (35.0, 210.0),
        "stock": (40, 2800),
        "series": ["Raspberry Pi 5", "Raspberry Pi 4", "Compute Module 4", "Raspberry Pi Zero 2 W"],
    },
    {
        "name": "Raspberry Pi Accessories",
        "tokens": ["raspberry pi", "accessory", "kit"],
        "use_cases": ["prototyping", "education", "lab setup"],
        "price": (4.0, 89.0),
        "stock": (80, 12000),
        "series": ["Official Case", "GPIO Ribbon", "Heatsink Kit", "Display Adapter", "PoE+ HAT"],
    },
    {
        "name": "Raspberry Pi HATs and Add-On Boards",
        "tokens": ["raspberry pi", "hat", "expansion"],
        "use_cases": ["motor control", "data acquisition", "automation", "sensor expansion"],
        "price": (9.0, 149.0),
        "stock": (30, 6500),
        "series": ["Motor Driver HAT", "RTC HAT", "Relay HAT", "DAC HAT", "AI Accelerator HAT"],
    },
    {
        "name": "Power Supplies - External/Internal (Off-Board)",
        "tokens": ["power supply", "ac-dc", "usb-c"],
        "use_cases": ["sbc power", "embedded system", "bench setup"],
        "price": (6.0, 68.0),
        "stock": (120, 24000),
        "series": ["USB-C PSU", "Desktop Adapter", "DIN Rail PSU", "Wall Adapter"],
    },
    {
        "name": "Cable Assemblies",
        "tokens": ["cable", "assembly", "wire"],
        "use_cases": ["debug", "power", "signal", "camera link"],
        "price": (1.5, 36.0),
        "stock": (140, 42000),
        "series": ["USB-C Cable", "Micro-HDMI Cable", "CSI Ribbon", "Jumper Wire Set"],
    },
    {
        "name": "Memory Cards, Modules",
        "tokens": ["memory", "storage", "flash"],
        "use_cases": ["boot media", "data logging", "edge compute"],
        "price": (5.0, 74.0),
        "stock": (75, 12000),
        "series": ["microSD Card", "eMMC Module", "Industrial microSD"],
    },
    {
        "name": "Sensors, Transducers",
        "tokens": ["sensor", "transducer", "measurement"],
        "use_cases": ["environmental", "motion", "position", "safety"],
        "price": (1.2, 98.0),
        "stock": (55, 26000),
        "series": ["Accelerometer", "IMU", "Temperature Sensor", "Pressure Sensor", "ToF Sensor"],
    },
    {
        "name": "RF Transceiver Modules",
        "tokens": ["rf", "wireless", "ble", "wifi"],
        "use_cases": ["iot", "telemetry", "remote control"],
        "price": (2.5, 68.0),
        "stock": (35, 9200),
        "series": ["ESP32 Module", "BLE Module", "LoRa Module", "Wi-Fi 6 Module"],
    },
    {
        "name": "Embedded Processors & Controllers",
        "tokens": ["microcontroller", "mcu", "processor"],
        "use_cases": ["iot node", "motor drive", "low power control"],
        "price": (0.8, 36.0),
        "stock": (180, 60000),
        "series": ["STM32", "PIC32", "LPC", "AVR", "nRF52"],
    },
    {
        "name": "Linear Amplifiers",
        "tokens": ["op amp", "amplifier", "analog"],
        "use_cases": ["sensor conditioning", "filtering", "front end"],
        "price": (0.2, 14.0),
        "stock": (260, 95000),
        "series": ["Low Noise Op Amp", "Rail-to-Rail Op Amp", "Instrumentation Amp"],
    },
    {
        "name": "Resistors",
        "tokens": ["resistor", "thick film", "precision"],
        "use_cases": ["current limiting", "divider", "bias network"],
        "price": (0.005, 0.65),
        "stock": (10000, 900000),
        "series": ["0603 Resistor", "0402 Resistor", "Current Sense Resistor", "Precision Resistor"],
    },
    {
        "name": "Capacitors",
        "tokens": ["capacitor", "mlcc", "electrolytic"],
        "use_cases": ["decoupling", "bulk storage", "filtering"],
        "price": (0.01, 1.85),
        "stock": (5000, 800000),
        "series": ["MLCC 0603", "MLCC 0402", "Aluminum Electrolytic", "Tantalum Capacitor"],
    },
    {
        "name": "Connectors, Interconnects",
        "tokens": ["connector", "header", "socket"],
        "use_cases": ["board interconnect", "wire harness", "power entry"],
        "price": (0.08, 12.0),
        "stock": (320, 240000),
        "series": ["Pin Header", "USB Connector", "FFC Connector", "Terminal Block"],
    },
    {
        "name": "Clock/Timing",
        "tokens": ["clock", "oscillator", "timing"],
        "use_cases": ["mcu clock", "network timing", "reference"],
        "price": (0.18, 8.5),
        "stock": (300, 120000),
        "series": ["MEMS Oscillator", "Crystal", "TCXO", "RTC Module"],
    },
    {
        "name": "Data Acquisition",
        "tokens": ["adc", "dac", "converter"],
        "use_cases": ["instrumentation", "control loop", "monitoring"],
        "price": (1.2, 36.0),
        "stock": (60, 8000),
        "series": ["12-Bit ADC", "16-Bit ADC", "Precision DAC", "Sigma-Delta ADC"],
    },
    {
        "name": "PMIC - Voltage Regulators",
        "tokens": ["regulator", "buck", "ldo"],
        "use_cases": ["power rail", "battery system", "sbc design"],
        "price": (0.25, 15.0),
        "stock": (250, 55000),
        "series": ["Buck Converter", "Boost Converter", "Low Noise LDO", "Dual Rail PMIC"],
    },
    {
        "name": "Development Boards, Kits, Programmers",
        "tokens": ["development", "evaluation", "kit"],
        "use_cases": ["proof of concept", "firmware bring-up", "training"],
        "price": (9.0, 220.0),
        "stock": (20, 4200),
        "series": ["Dev Kit", "Eval Board", "Programmer", "Debug Probe"],
    },
    {
        "name": "Displays - LCD, OLED, Graphic",
        "tokens": ["display", "lcd", "oled"],
        "use_cases": ["hmi", "status panel", "embedded ui"],
        "price": (4.2, 95.0),
        "stock": (45, 7400),
        "series": ["OLED Module", "TFT LCD", "Touch Display", "ePaper Display"],
    },
    {
        "name": "Fans, Thermal Management",
        "tokens": ["thermal", "fan", "heatsink"],
        "use_cases": ["cpu cooling", "enclosure airflow", "passive cooling"],
        "price": (1.1, 48.0),
        "stock": (40, 16000),
        "series": ["Heatsink", "Cooling Fan", "Thermal Pad", "Heat Pipe"],
    },
    {
        "name": "Switches",
        "tokens": ["switch", "pushbutton", "toggle"],
        "use_cases": ["user input", "safety interlock", "panel control"],
        "price": (0.18, 8.8),
        "stock": (350, 170000),
        "series": ["Tactile Switch", "Toggle Switch", "Slide Switch", "Rotary Encoder"],
    },
]

RASPBERRY_PRODUCTS = [
    ("Raspberry Pi 5 Model B 8GB", "single board computer with quad-core CPU and dual 4K output", "RPI5-8GB"),
    ("Raspberry Pi 5 Model B 4GB", "single board computer optimized for edge AI and multimedia", "RPI5-4GB"),
    ("Raspberry Pi 4 Model B 8GB", "general-purpose SBC for industrial and maker applications", "RPI4-8GB"),
    ("Raspberry Pi Zero 2 W", "compact wireless single board computer", "RPIZ2W"),
    ("Raspberry Pi Compute Module 4", "industrial compute module for embedded carrier designs", "CM4"),
    ("Raspberry Pi Camera Module 3", "12MP camera module for machine vision and streaming", "CAM3"),
    ("Raspberry Pi 7-inch Touch Display", "official capacitive touch display for HMI projects", "RPI-7DSP"),
    ("Raspberry Pi Official USB-C 27W PSU", "high current power supply for Raspberry Pi 5", "RPI-PSU-27W"),
    ("Raspberry Pi Official Case for Pi 5", "snap-fit protective enclosure with fan support", "RPI5-CASE"),
    ("Raspberry Pi PoE+ HAT", "power-over-ethernet add-on for remote edge nodes", "RPI-POE-PLUS"),
    ("Raspberry Pi NVMe Base HAT", "PCIe storage expansion board for high-speed logging", "RPI-NVME-HAT"),
    ("Raspberry Pi GPIO Breakout HAT", "prototyping accessory for safe GPIO access", "RPI-GPIO-HAT"),
]

ADJECTIVES = [
    "High Efficiency",
    "Low Noise",
    "Industrial",
    "Automotive Grade",
    "Precision",
    "Compact",
    "Wide Input",
    "Ultra Low Power",
    "High Speed",
    "Enhanced",
    "Reliable",
    "Rugged",
    "Advanced",
    "Performance",
]

PACKAGE_HINTS = ["SMD", "THT", "Module", "Board", "Kit", "Cable", "Assembly"]


# Args:
#   low: float
#     Lower bound for random price generation.
#   high: float
#     Upper bound for random price generation.
# Returns:
#   float
#     Rounded unit price.
def money(low: float, high: float) -> float:
    return round(RNG.uniform(low, high), 2)


# Args:
#   low: int
#     Minimum stock quantity.
#   high: int
#     Maximum stock quantity.
# Returns:
#   int
#     Random stock quantity.
def stock(low: int, high: int) -> int:
    return RNG.randint(low, high)


# Args:
#   vendor: str
#     Manufacturer name.
#   cat_index: int
#     Category index used for deterministic grouping.
#   item_index: int
#     Per-item sequence number.
# Returns:
#   str
#     Synthetic manufacturer part number.
def make_part_number(vendor: str, cat_index: int, item_index: int) -> str:
    prefix = "".join(ch for ch in vendor.upper() if ch.isalnum())[:4] or "PART"
    return f"{prefix}-{cat_index:02d}{item_index:04d}-{RNG.randint(10,99)}"


# Args:
#   vendor: str
#     Manufacturer name for this product.
#   category: dict
#     Category metadata block containing ranges/tags/series.
#   cat_index: int
#     Category sequence number.
#   item_index: int
#     Product sequence number.
# Returns:
#   dict
#     Fully-formed catalog document for one synthetic product.
# Notes:
#   Produces deterministic pseudo-random values via RNG seed.
def make_product(vendor: str, category: dict, cat_index: int, item_index: int) -> dict:
    series = RNG.choice(category["series"])
    adjective = RNG.choice(ADJECTIVES)
    package = RNG.choice(PACKAGE_HINTS)
    token_hint = ", ".join(RNG.sample(category["tokens"], k=min(2, len(category["tokens"]))))

    part_number = make_part_number(vendor, cat_index, item_index)
    name = f"{adjective} {series} {package}"
    description = (
        f"{name} from {vendor} for {RNG.choice(category['use_cases'])}. "
        f"Optimized for {token_hint} applications and long lifecycle deployments."
    )

    product_slug = part_number.lower().replace("/", "-")
    vendor_slug = vendor.lower().replace(" ", "-").replace(".", "")

    return {
        "id": f"mock-{cat_index:02d}-{item_index:04d}",
        "manufacturer": vendor,
        "manufacturer_part_number": part_number,
        "name": name,
        "description": description,
        "category": category["name"],
        "unit_price": money(*category["price"]),
        "quantity_available": stock(*category["stock"]),
        "tags": list({*category["tokens"], series.lower(), package.lower()}),
        "use_cases": RNG.sample(category["use_cases"], k=min(2, len(category["use_cases"]))),
        "key_specs": {
            "series": series,
            "package": package,
            "temperature": f"{-40 + RNG.randint(0, 20)}C to {85 + RNG.randint(0, 40)}C",
            "revision": f"R{RNG.randint(1,5)}.{RNG.randint(0,9)}",
        },
        "product_url": f"https://www.digikey.com/en/products/detail/{vendor_slug}/{product_slug}/",
        "datasheet_url": f"https://datasheets.example.com/{product_slug}.pdf",
    }


# Args:
#   None
# Returns:
#   list[dict]
#     Curated Raspberry Pi board and accessory records.
def raspberry_pi_overrides() -> list[dict]:
    docs = []
    for idx, (name, description, suffix) in enumerate(RASPBERRY_PRODUCTS, start=1):
        part = f"RPI-{suffix}-{RNG.randint(10,99)}"
        docs.append(
            {
                "id": f"rpi-featured-{idx:03d}",
                "manufacturer": "Raspberry Pi",
                "manufacturer_part_number": part,
                "name": name,
                "description": description,
                "category": "Single Board Computers (SBC)" if "Pi" in name or "Compute" in name else "Raspberry Pi Accessories",
                "unit_price": round(RNG.uniform(9.0, 165.0), 2),
                "quantity_available": RNG.randint(50, 9000),
                "tags": ["raspberry pi", "accessory", "iot", "embedded"],
                "use_cases": ["maker", "education", "edge ai"],
                "key_specs": {
                    "interface": RNG.choice(["USB-C", "CSI", "HDMI", "GPIO", "PCIe"]),
                    "generation": RNG.choice(["Pi 4", "Pi 5", "CM4", "Zero"]),
                    "status": "Active",
                },
                "product_url": f"https://www.digikey.com/en/products/detail/raspberry-pi/{part.lower()}/",
                "datasheet_url": f"https://datasheets.example.com/raspberry-pi/{part.lower()}.pdf",
            }
        )
    return docs


# Args:
#   None
# Returns:
#   list[dict]
#     Complete catalog list sized to TARGET_COUNT.
# Notes:
#   Blends curated Raspberry Pi entries with generated category coverage.
def build_catalog() -> list[dict]:
    docs: list[dict] = raspberry_pi_overrides()

    item_index = 1
    while len(docs) < TARGET_COUNT:
        for cat_index, category in enumerate(CATEGORIES, start=1):
            vendor = RNG.choice(VENDORS)
            if category["name"].startswith("Raspberry Pi") or category["name"].startswith("Single Board"):
                if RNG.random() < 0.55:
                    vendor = "Raspberry Pi"
            docs.append(make_product(vendor, category, cat_index, item_index))
            item_index += 1
            if len(docs) >= TARGET_COUNT:
                break

    return docs[:TARGET_COUNT]


# Args:
#   None
# Returns:
#   None
# Notes:
#   Writes JSON output to data/catalog.json for Elasticsearch seeding.
def main() -> None:
    target_path = Path(__file__).resolve().parent.parent / "data" / "catalog.json"
    catalog = build_catalog()
    target_path.write_text(json.dumps(catalog, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(catalog)} products to {target_path}")


if __name__ == "__main__":
    main()
