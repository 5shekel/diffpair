"""Render actual KiCad pad geometry over the unmodified tracing photos."""
from pathlib import Path
import json
import math
from PIL import Image, ImageDraw, ImageFont

PROJ=Path(__file__).resolve().parents[1]
geometry=json.loads((PROJ/"review"/"pad_geometry.json").read_text())
plan=json.loads((PROJ/"placement_plan.json").read_text())
font=ImageFont.truetype("C:/Windows/Fonts/consola.ttf",15)

def rotated_box(center,size,angle):
    x,y=center; w,h=size; a=math.radians(angle)
    return [(x+dx*math.cos(a)+dy*math.sin(a),y-dx*math.sin(a)+dy*math.cos(a))
            for dx,dy in [(-w/2,-h/2),(w/2,-h/2),(w/2,h/2),(-w/2,h/2),(-w/2,-h/2)]]

for side,name in [("F","top"),("B","bottom")]:
    im=Image.open(PROJ/"images"/f"board_{name}.png").convert("RGB")
    d=ImageDraw.Draw(im)
    outline=[tuple(p) for p in plan["outline"]["vertices_px"]]
    d.line(outline+[outline[0]],fill="#ff57ed",width=3)
    for fp in geometry:
        for p in fp["pads"]:
            if side not in p["sides"]: continue
            color="#ffcf40" if any(p["drill"]) else "#42f5ff"
            d.line(rotated_box(p["center"],p["size"],p["angle"]),fill=color,width=1)
            x,y=p["center"]
            d.line((x-3,y,x+3,y),fill=color); d.line((x,y-3,x,y+3),fill=color)
        if fp["side"]==side or any(any(p["drill"]) for p in fp["pads"]):
            x,y=fp["center"]
            label=fp["ref"]
            # Keep clustered passive labels readable by alternating their sides.
            n=int(''.join(c for c in label if c.isdigit()))
            pos=(x-12,y-35 if n%2 else y+25)
            d.text(pos,label,font=font,fill="white",stroke_width=2,stroke_fill="black")
    im.save(PROJ/"review"/f"overlay_{name}.png")
print("Saved top/bottom overlays from reloaded KiCad pads")
