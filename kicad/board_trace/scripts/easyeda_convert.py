import json, os

SRC = r"C:\Users\user\AppData\Local\Temp\opencode\dp\C7501881_easyeda.json"
OUTDIR = r"C:\dev\diffpair\kicad\board_trace\libs\lcsc.pretty"
os.makedirs(OUTDIR, exist_ok=True)
NAME = "HC-USB3.0-L175-2X1-P"
MM = 0.254   # EasyEDA PCB unit = mil-ish (10 mil) per calibration

res = json.load(open(SRC))["result"]
pd = res["packageDetail"]
obj = pd["dataStr"]
shape = obj["shape"]; head = obj["head"]

pads = []
for s in shape:
    f = s.split("~")
    if f[0] != "PAD": continue
    st = f[1]
    cx, cy, w, h = float(f[2]), float(f[3]), float(f[4]), float(f[5])
    layer = f[6]
    num = f[8]
    hole = float(f[9]) if len(f) > 9 and f[9] not in ("", "0") else 0.0
    pads.append(dict(shape=st, cx=cx, cy=cy, w=w, h=h, layer=layer, num=num, hole=hole))

# origin = centroid of pad cluster
ox = sum(p["cx"] for p in pads)/len(pads)
oy = sum(p["cy"] for p in pads)/len(pads)
xs = [ (p["cx"]-ox)*MM for p in pads ]; ys = [ -(p["cy"]-oy)*MM for p in pads ]
minx, maxx, miny, maxy = min(xs)-0.5, max(xs)+0.5, min(ys)-0.5, max(ys)+0.5

lines = []
lines.append('(footprint "%s"' % NAME)
lines.append('  (version 20240108)')
lines.append('  (generator "easyeda-convert")')
lines.append('  (layer "F.Cu")')
lines.append('  (attr through_hole)')
lines.append('  (fp_rect (start %.3f %.3f) (end %.3f %.3f) (stroke (width 0.1) (type default)) (fill none) (layer "F.Fab"))' % (minx, miny, maxx, maxy))
lines.append('  (fp_rect (start %.3f %.3f) (end %.3f %.3f) (stroke (width 0.05) (type default)) (fill none) (layer "F.CrtYd"))' % (minx-0.25, miny-0.25, maxx+0.25, maxy+0.25))
for p in pads:
    x = (p["cx"]-ox)*MM; y = -(p["cy"]-oy)*MM
    dx, dy = p["w"]*MM, p["h"]*MM
    thru = (p["layer"] == "11") and p["hole"] > 0
    pshape = "circle" if abs(dx-dy) < 0.02 else "oval"
    num = p["num"] or ""
    if thru:
        drill = 2*p["hole"]*MM
        lines.append('  (pad "%s" thru_hole %s (at %.3f %.3f) (size %.3f %.3f) (drill %.3f) (layers "*.Cu" "*.Mask"))'
                     % (num, pshape, x, y, dx, dy, drill))
    else:
        lines.append('  (pad "%s" smd %s (at %.3f %.3f) (size %.3f %.3f) (layers "F.Cu" "F.Paste" "F.Mask"))'
                     % (num, pshape, x, y, dx, dy))
lines.append(')')
fp = "\n".join(lines)
open(os.path.join(OUTDIR, NAME + ".kicad_mod"), "w", encoding="utf-8", newline="\n").write(fp)
print("pads:", len(pads), " origin=(%.3f,%.3f)" % (ox, oy))
print("footprint extent mm: x %.2f..%.2f  y %.2f..%.2f" % (minx, maxx, miny, maxy))
print("drills:", sorted(set(round(2*p['hole']*MM,2) for p in pads if p['hole']>0)))
print("wrote", os.path.join(OUTDIR, NAME + ".kicad_mod"))
