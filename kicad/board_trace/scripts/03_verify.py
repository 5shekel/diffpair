import os, json
from pathlib import Path
import pcbnew

PROJ = str(Path(__file__).resolve().parents[1])
PX = 25.9375; W=1030; H=1601
IMG_W=W/PX; IMG_H=H/PX; CX,CY=148.5,105.0; L=CX-IMG_W/2; T=CY-IMG_H/2
def to_px(xmm,ymm): return (int((xmm-L)*PX), int((ymm-T)*PX))
board = pcbnew.LoadBoard(os.path.join(PROJ,"board_trace.kicad_pcb"))
boxes=[]; geometry=[]
for fp in board.GetFootprints():
    xs=[]; ys=[]
    for pad in fp.Pads():
        bb=pad.GetBoundingBox(); xs+=[bb.GetLeft(),bb.GetRight()]; ys+=[bb.GetTop(),bb.GetBottom()]
    if not xs:
        bb=fp.GetBoundingBox(); xs=[bb.GetLeft(),bb.GetRight()]; ys=[bb.GetTop(),bb.GetBottom()]
    x0,y0 = to_px(pcbnew.ToMM(min(xs)), pcbnew.ToMM(min(ys)))
    x1,y1 = to_px(pcbnew.ToMM(max(xs)), pcbnew.ToMM(max(ys)))
    boxes.append(dict(ref=fp.GetReference(), layer=("F" if fp.GetLayer()==pcbnew.F_Cu else "B"),
                      box=[x0,y0,x1,y1],
                      w=round(pcbnew.ToMM(max(xs)-min(xs)),2), h=round(pcbnew.ToMM(max(ys)-min(ys)),2)))
    pads=[]
    for pad in fp.Pads():
        pads.append(dict(number=pad.GetNumber(),center=to_px(pcbnew.ToMM(pad.GetPosition().x),pcbnew.ToMM(pad.GetPosition().y)),
                         size=[pcbnew.ToMM(pad.GetSize().x)*PX,pcbnew.ToMM(pad.GetSize().y)*PX],
                         drill=[pcbnew.ToMM(pad.GetDrillSize().x)*PX,pcbnew.ToMM(pad.GetDrillSize().y)*PX],
                         angle=pad.GetOrientationDegrees(),
                         sides=[side for side,layer in [("F",pcbnew.F_Cu),("B",pcbnew.B_Cu)] if pad.IsOnLayer(layer)]))
    geometry.append(dict(ref=fp.GetReference(),side="F" if fp.GetLayer()==pcbnew.F_Cu else "B",
                         center=to_px(pcbnew.ToMM(fp.GetPosition().x),pcbnew.ToMM(fp.GetPosition().y)),pads=pads))
json.dump(boxes, open(os.path.join(PROJ,"verify_boxes.json"),"w"))
json.dump(geometry, open(os.path.join(PROJ,"review","pad_geometry.json"),"w"),indent=2)
print("wrote", len(boxes), "boxes")
