"""Reproducible photo observations, not an inferred electrical netlist."""
from pathlib import Path
import csv
import hashlib
import json
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "design/receiver"
OUT.mkdir(exist_ok=True)
source = ROOT / "photos/recieve_top.png"
im = Image.open(source).convert("RGB")
regions = [
    ("A", [275, 22, 525, 344], "USB-A socket", "high", "Blue insert and Standard-A-shaped shell; contact wiring hidden."),
    ("B", [505, 310, 770, 1158], "SFP cage", "high", "Cage obscures socket contacts and underlying board; no module label visible."),
    ("C", [181, 85, 228, 298], "PCB marking", "high", "Reads 123486S_Y171 after rotating the crop."),
    ("D", [370, 350, 430, 405], "Two marked resistors", "medium", "Both appear marked 331; resistance and connections unmeasured."),
    ("E", [368, 426, 435, 626], "Five-pin IC and passives", "high", "One 1R0-marked resistor, three MLCC candidates, and an unidentified five-pin IC."),
    ("F", [370, 643, 490, 763], "Two magnetic components", "medium", "Two inductor/ferrite candidates, each flanked by MLCC candidates; values unverified."),
    ("G", [303, 778, 456, 1156], "LED area", "high", "Two leaded LEDs and two resistors that appear marked 331; functions and polarity unknown."),
    ("H", [609, 272, 663, 317], "Two MLCC candidates", "medium", "Parts next to parallel trace segments; endpoints hidden by cage."),
]
record = {
    "source": "photos/recieve_top.png",
    "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
    "image_size_px": list(im.size),
    "external_view": {
        "source": "photos/external view.png",
        "sha256": hashlib.sha256((ROOT / "photos/external view.png").read_bytes()).hexdigest(),
        "user_report": "Both units are the same size.",
        "interpretation": "Same enclosure size; absolute dimensions and internal PCB dimensions unmeasured.",
        "visible_labels": ["PC-USB3.0 Port", "DC 5V", "TX", "RX"],
        "limits": "No module model label visible. Do not assign the lower panel's power input to the PC-side PCB solely from the stacked arrangement."
    },
    "coordinate_system": "original image, x right, y down; boxes x0,y0,x1,y1",
    "user_report": "Unbranded PC-side receiver: SFP+ port to USB female, then cable to PC. Receiver and pictured hub came together and work; optical module markings unavailable.",
    "reference_system": {
        "status": "working matched pair, user-reported",
        "evidence": "User: they come togther and work. i dont have the marking",
        "design_use": "Retain existing receiver, cable and module pair as compatibility baseline",
        "negotiated_speed": "not independently measured or captured",
        "new_board_compatibility": "unverified"
    },
    "observations": [dict(id=i, box_px=b, title=t, confidence=c, evidence=e) for i,b,t,c,e in regions],
    "inferences": [
        {"confidence": "medium", "claim": "Receiver and hub may be related designs.",
         "basis": "Shared 123486S PCB marking prefix; similar five-pin IC, 1R0 resistor, two magnetic components and two LEDs.",
         "limit": "Does not establish same IC, schematic, firmware, or module compatibility."},
        {"confidence": "low", "claim": "Five-pin IC and adjacent passives may form SFP power conditioning.",
         "basis": "Placement and similarity to the hub's corresponding area.",
         "limit": "No readable IC marking or confirmed net; regulator type, pinout and voltage unknown."}
    ],
    "trust_summary": {
        "basis": "Visual observations plus user-reported operation of the supplied matched pair; no independent electrical or speed measurements.",
        "electrical_connections_verified": 0,
        "module_identity": "unknown",
        "cable_wiring": "unknown",
        "end_to_end_operation": "existing matched pair works per user; new design untested",
        "hidden_areas": ["underside", "under USB shell", "under SFP cage"]
    }
}
(OUT / "observations.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")

font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 24)
small = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 20)
canvas = Image.new("RGB", (im.width + 490, im.height), "#f7f8fa")
canvas.paste(im, (0, 0))
draw = ImageDraw.Draw(canvas)
for index, (tag, box, title, confidence, evidence) in enumerate(regions):
    draw.rectangle(box, outline="#00e5ff", width=3)
    x, y = box[:2]
    draw.rectangle((x, y, x+30, y+31), fill="#003e50")
    draw.text((x+6, y+2), tag, font=font, fill="white")
    ly = 135 + index * 104
    draw.text((im.width+25, ly), f"{tag}  {title}", font=font, fill="#172534")
    draw.text((im.width+25, ly+35), f"Observation confidence: {confidence}", font=small, fill="#374658")
draw.text((im.width+25, 30), "PC-side receiver", font=font, fill="#172534")
draw.text((im.width+25, 70), "Photo observations / no verified nets", font=small, fill="#374658")
draw.text((im.width+25, 1040), "PCB marking: 123486S_Y171", font=small, fill="#172534")
draw.text((im.width+25, 1080), "Original source image is preserved.", font=small, fill="#374658")
draw.text((im.width+25, 1120), "Hidden components remain unknown.", font=small, fill="#374658")
canvas.save(OUT / "annotated_top.png")
for name, box, size, rotate in [
    ("power_detail", (350,345,490,830), (560,1940), 0),
    ("silk_detail", (175,70,250,310), (960,300), 90),
    ("signal_detail", (365,235,715,500), (1050,795), 0),
]:
    crop = im.crop(box)
    if rotate: crop = crop.rotate(rotate, expand=True)
    crop.resize(size).save(OUT / (name + ".png"))

# Blank observations, never pre-populated pass/fail results. Contact numbers
# require a connector drawing/breakout; do not infer them from photo orientation.
rows = []
def add(group, a, b, purpose):
    rows.append([group, a, b, purpose, "", "", "not measured"])
for pin in [1,2,3,4,5,6,7,8,9]:
    add("cable", f"PC-end contact {pin} if Standard-A", "receiver-end contacts 1..9, record all matches",
        "Identify actual cable mapping, including VBUS and USB2; adapt labels if PC end is Type-C")
for usb in [5,6,8,9]:
    for sfp in [12,13,18,19]:
        add("signal", f"receiver USB contact {usb}", f"receiver SFP contact {sfp}",
            "Check direct path, then trace via intervening parts; DC-open may be a coupling capacitor")
for sfp in [15,16]:
    add("power", f"receiver SFP contact {sfp}", "each side of both magnetic components",
        "Distinguish VccR/VccT branches and common feed")
add("power", "receiver USB VBUS contact 1", "both ends of 1R0 resistor and IC pads",
    "Identify input feed; use physical IC pad locations until pin 1 is known")
add("ground", "receiver USB GND contact 4", "SFP contacts 1,10,11,14,17,20; USB7; shields separately",
    "Record each result separately; do not assume shield and signal ground are identical")
for pin, name in [(2,"TX_FAULT"),(3,"TX_DISABLE"),(6,"MOD_ABS"),(7,"RS0"),(8,"RX_LOS"),(9,"RS1")]:
    add("control", f"receiver SFP {pin} {name}", "resistors, LEDs, ground and supply branches",
        "Resolve straps and status wiring; do not assign a signal from LED placement")
worksheet = OUT / "connection_measurements.csv"
if not worksheet.exists():
    with worksheet.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["group","endpoint_a","endpoint_b","purpose","measured_ohms_or_path","conditions_notes","status"])
        writer.writerows(rows)
    worksheet_status = f"created {len(rows)} unmeasured connection checks"
else:
    worksheet_status = "preserved existing connection worksheet, including any entered measurements"
print(f"Saved {len(regions)} observation regions; {worksheet_status}.")
