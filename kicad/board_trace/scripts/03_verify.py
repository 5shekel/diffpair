import os, json
import pcbnew

PROJ = r"C:\dev\diffpair\kicad\board_trace"
PX = 25.9375; W=1030; H=1601
IMG_W=W/PX; IMG_H=H/PX; CX,CY=148.5,105.0; L=CX-IMG_W/2; T=CY-IMG_H/2
def to_px(xmm,ymm): return (int((xmm-L)*PX), int((ymm-T)*PX))
board = pcbnew.LoadBoard(os.path.join(PROJ,"board_trace.kicad_pcb"))
boxes=[]
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
json.dump(boxes, open(os.path.join(PROJ,"verify_boxes.json"),"w"))
print("wrote", len(boxes), "boxes")
