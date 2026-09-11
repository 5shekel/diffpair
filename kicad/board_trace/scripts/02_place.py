import os, base64, uuid, json
import pcbnew

PROJ = r"C:\dev\diffpair\kicad\board_trace"
IMGDIR = os.path.join(PROJ, "images")
LCSC = r"C:\dev\diffpair\kicad\usb3_over_optical_hub\usb3_over_optical_hub\libs\lcsc\footprints.pretty"
KI = r"C:\Program Files\KiCad\10.0\share\kicad\footprints"
det = json.load(open(os.path.join(PROJ,"detect.json")))
W = H = None
PX = 25.9375
W, H = 1030, 1601
IMG_W = W/PX; IMG_H = H/PX
CX, CY = 148.5, 105.0; LEFT = CX-IMG_W/2; TOP = CY-IMG_H/2
def mm(px,py): return (LEFT+px/PX, TOP+py/PX)

# ---- component plan ----------------------------------------------------------------
plan = []   # (ref, libpath, fpname, px, py, rot, layer)
# top passives
for i,(px,py,w,h) in enumerate(sorted(det["top"], key=lambda c:(c[1],c[0])), start=1):
    plan.append(("C%d"%i, os.path.join(KI,"Capacitor_SMD.pretty"), "C_0603_1608Metric",
                 px, py, 90 if h>w*1.2 else 0, "F"))
# bottom passives (hardcoded from the bottom photo — detection is via-prone)
bottom_pass = [(188,1320,0), (320,1360,90), (190,1465,0)]
for k,(px,py,rot) in enumerate(bottom_pass, start=1):
    plan.append(("C%d"%(len(det["top"])+k), os.path.join(KI,"Capacitor_SMD.pretty"), "C_0603_1608Metric",
                 px, py, rot, "B"))
# non-passives (positions read from the photos)
plan += [
    ("J1", os.path.join(PROJ,"libs","lcsc.pretty"), "HC-USB3.0-L175-2X1-P", 240, 320, 0, "F"),
    ("J2", os.path.join(PROJ,"libs","lcsc.pretty"), "HC-USB3.0-L175-2X1-P", 785, 320, 0, "F"),
    ("J3", LCSC, "C42418480_CONN-SMD_20P-P0_80_SFP20P", 780, 658, 0, "F"),
    ("Y1", os.path.join(KI,"Crystal.pretty"), "Crystal_SMD_3225-4Pin_3.2x2.5mm", 352, 613, 0, "F"),
    ("L1", os.path.join(KI,"Inductor_SMD.pretty"), "L_Sunlord_SWPA5040S", 118, 948, 0, "F"),
    ("C50", os.path.join(KI,"Capacitor_Tantalum_SMD.pretty"), "CP_EIA-7343-30_AVX-N", 180, 1069, 0, "F"),
    ("C51", os.path.join(KI,"Capacitor_SMD.pretty"), "CP_Elec_6.3x5.4", 144, 1194, 0, "F"),
    ("C52", os.path.join(KI,"Capacitor_SMD.pretty"), "CP_Elec_10x10.5", 196, 1300, 0, "F"),
    ("U1", LCSC, "C69418_QFN-76_L9_0-W9_0-P0_40-EP6_4-TL", 280, 790, 0, "B"),
]

pcb = os.path.join(PROJ,"board_trace.kicad_pcb")
board = pcbnew.NewBoard(pcb)
r = pcbnew.PCB_SHAPE(board); r.SetShape(pcbnew.SHAPE_T_RECT)
r.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(LEFT),pcbnew.FromMM(TOP)))
r.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(LEFT+IMG_W),pcbnew.FromMM(TOP+IMG_H)))
r.SetLayer(pcbnew.Edge_Cuts); r.SetWidth(pcbnew.FromMM(0.05)); board.Add(r)

placed=[]; errors=[]
for ref, lib, name, px, py, rot, side in plan:
    fp = pcbnew.FootprintLoad(lib, name)
    if fp is None:
        errors.append((ref,name)); continue
    x,y = mm(px,py)
    fp.SetReference(ref)
    fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x),pcbnew.FromMM(y)))
    board.Add(fp)
    if side == "B":
        fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
    fp.SetOrientationDegrees(float(rot))
    placed.append(dict(ref=ref, fp=name, x=round(x,3), y=round(y,3), rot=rot, side=side))
pcbnew.SaveBoard(pcb, board)

# ---- inject reference images (correct scale, gimp orientation) --------------------
SCALE = IMG_W/(W/300.0*25.4)
def blk(png,layer):
    d=base64.b64encode(open(png,"rb").read()).decode("ascii")
    ch="\n".join('      "%s"'%d[i:i+76] for i in range(0,len(d),76))
    return ('  (image (at %.6f %.6f)\n    (layer "%s")\n    (scale %g)\n    (data\n%s\n    )\n    (uuid "%s")\n  )\n'
            %(CX,CY,layer,SCALE,ch,uuid.uuid4()))
raw=open(pcb,encoding="utf-8").read(); i=raw.rstrip().rfind(")")
open(pcb,"w",encoding="utf-8",newline="\n").write(raw[:i]+blk(os.path.join(IMGDIR,"board_top.png"),"Dwgs.User")+blk(os.path.join(IMGDIR,"board_bottom.png"),"Cmts.User")+raw[i:])

b2=pcbnew.LoadBoard(pcb)
bcount=sum(1 for f in b2.GetFootprints() if f.GetLayer()==pcbnew.B_Cu)
print("footprints:", len(b2.GetFootprints()), " on B.Cu:", bcount)
if errors: print("LOAD ERRORS:", errors)
json.dump(placed, open(os.path.join(PROJ,"placement.json"),"w"), indent=1)
print("done")
