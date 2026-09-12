"""Apply placement_plan.json with KiCad 10 pcbnew; no board text editing.

The committed board supplies its two native embedded reference images. Refuse
to rebuild a board that has acquired routing, nets, or unrecognized references.
"""
from pathlib import Path
from datetime import datetime
import json
import os
import shutil
import pcbnew

PROJ = Path(__file__).resolve().parents[1]
KI = Path(os.environ.get("KICAD10_FOOTPRINT_DIR", r"C:\Program Files\KiCad\10.0\share\kicad\footprints"))
PCB = PROJ / "board_trace.kicad_pcb"
plan = json.loads((PROJ / "placement_plan.json").read_text(encoding="utf-8"))
PX=plan["px_per_mm"]
W,H=plan["image_size_px"]
CX,CY=plan["image_center_mm"]
LEFT,TOP=CX-W/PX/2,CY-H/PX/2

def vector(x,y):
    return pcbnew.VECTOR2I(pcbnew.FromMM(float(x)),pcbnew.FromMM(float(y)))

def point(x,y):
    return vector(LEFT+x/PX,TOP+y/PX)

def local_library(name):
    return PROJ / "libs" / f"{name}.pretty"

def make_jack():
    """Provisional tab numbering; do not interpret as electrical pin functions."""
    lib=local_library("trace")
    lib.mkdir(parents=True,exist_ok=True)
    fp=pcbnew.FOOTPRINT(None)
    fp.SetFPID(pcbnew.LIB_ID("trace","BarrelJack_PhotoTrace"))
    fp.SetAttributes(pcbnew.FP_THROUGH_HOLE)
    for n,x,y,w,h in [(1,-2,0,92,38),(2,130,64,38,92),(3,-2,160,92,38)]:
        p=pcbnew.PAD(fp)
        p.SetNumber(str(n)); p.SetAttribute(pcbnew.PAD_ATTRIB_PTH)
        p.SetShape(pcbnew.PAD_SHAPE_OVAL)
        p.SetPosition(vector(x/PX,y/PX)); p.SetSize(vector(w/PX,h/PX))
        p.SetDrillShape(pcbnew.PAD_DRILL_SHAPE_OBLONG)
        p.SetDrillSize(vector(2.5 if w>h else .8,.8 if w>h else 2.5))
        layers=pcbnew.LSET.AllCuMask()
        layers.AddLayer(pcbnew.F_Mask); layers.AddLayer(pcbnew.B_Mask)
        p.SetLayerSet(layers)
        fp.Add(p)
    shape=pcbnew.PCB_SHAPE(fp)
    shape.SetShape(pcbnew.SHAPE_T_RECT); shape.SetLayer(pcbnew.F_Fab)
    shape.SetStart(vector(-136/PX,-35/PX)); shape.SetEnd(vector(113/PX,333/PX))
    shape.SetWidth(pcbnew.FromMM(.1)); fp.Add(shape)
    fp.SetField("Trace limitations","Photo proxy; slot sizes, pin functions and body dimensions unverified")
    pcbnew.PCB_IO_MGR.FindPlugin(pcbnew.PCB_IO_MGR.KICAD_SEXP).FootprintSave(str(lib),fp)

board=pcbnew.LoadBoard(str(PCB))
known={p["ref"] for p in plan["parts"]} | set(plan["retired_refs"])
unknown={f.GetReference() for f in board.GetFootprints()}-known
if len(board.GetTracks()) or board.GetNetCount()>1 or unknown:
    raise SystemExit(f"Refusing placement rebuild: routing/nets/new references exist: {sorted(unknown)}")
if sum(d.GetClass()=="PCB_REFERENCE_IMAGE" for d in board.GetDrawings())!=2:
    raise SystemExit("Expected two native reference images in the committed board seed")

make_jack()
loaded=[]
for p in plan["parts"]:
    lib=local_library(p["library"]) if p["library"] in ("lcsc","trace") else KI/f'{p["library"]}.pretty'
    fp=pcbnew.FootprintLoad(str(lib),p["fp"])
    if fp is None:
        raise RuntimeError(f"Cannot load {p['ref']} from {lib}/{p['fp']}")
    fp.SetFPID(pcbnew.LIB_ID(p["library"],p["fp"]))
    loaded.append((p,fp))

backup=PROJ/"review"/"backups"/datetime.now().strftime("%Y%m%d_%H%M%S_%f")
backup.mkdir(parents=True)
shutil.copy2(PCB,backup/PCB.name)
removed_footprints=list(board.GetFootprints())  # Keep SWIG wrappers alive until save.
for fp in removed_footprints:
    board.Remove(fp)
original_drawings=list(board.GetDrawings())
for drawing in original_drawings:
    if drawing.GetLayer()==pcbnew.Edge_Cuts:
        board.Remove(drawing)
vertices=plan["outline"]["vertices_px"]
for a,b in zip(vertices,vertices[1:]+vertices[:1]):
    line=pcbnew.PCB_SHAPE(board)
    line.SetShape(pcbnew.SHAPE_T_SEGMENT); line.SetLayer(pcbnew.Edge_Cuts)
    line.SetStart(point(*a)); line.SetEnd(point(*b)); line.SetWidth(pcbnew.FromMM(.05))
    board.Add(line)

placed=[]
for p,fp in loaded:
    fp.SetReference(p["ref"]); fp.SetValue(p["value"])
    fp.SetPosition(point(p["px"],p["py"])); board.Add(fp)
    if p["side"]=="B":
        fp.Flip(fp.GetPosition(),pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
    fp.SetOrientationDegrees(float(p["rot"]))
    fp.SetField("Trace confidence",p["confidence"])
    fp.SetField("Trace evidence",p["evidence"])
    fp.SetField("Trace source",f"images/board_{'top' if p['side']=='F' else 'bottom'}.png; x={p['px']:.2f}, y={p['py']:.2f} px")
    for field in fp.GetFields():
        field.SetVisible(False)
    fp.Reference().SetVisible(True)
    fp.Reference().SetTextSize(vector(.55,.55))
    fp.Reference().SetTextThickness(pcbnew.FromMM(.1))
    fp.Reference().SetPosition(fp.GetPosition()+vector(0,-1.5))
    placed.append(dict(p,x=round(pcbnew.ToMM(fp.GetPosition().x),6),y=round(pcbnew.ToMM(fp.GetPosition().y),6)))

temporary=PROJ/"board_trace.next.kicad_pcb"
pcbnew.SaveBoard(str(temporary),board)
check=pcbnew.LoadBoard(str(temporary))
assert len(check.GetFootprints())==len(loaded)
assert sum(d.GetClass()=="PCB_REFERENCE_IMAGE" for d in check.GetDrawings())==2
assert {f.GetReference() for f in check.GetFootprints() if f.GetLayer()==pcbnew.B_Cu}=={"U1"}
for f in check.GetFootprints():
    if f.GetReference()=="U1":
        assert all(p.IsOnLayer(pcbnew.B_Cu) and not p.IsOnLayer(pcbnew.F_Cu) for p in f.Pads())
os.replace(temporary,PCB)
(PROJ/"placement.json").write_text(json.dumps(placed,indent=2)+"\n",encoding="utf-8")
print(f"Saved {len(loaded)} footprints, 2 unchanged reference images, 4 photo-traced outline segments.")
print(f"Backup: {backup}")
