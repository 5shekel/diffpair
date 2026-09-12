"""Validate the saved board independently of the placement writer (KiCad Python)."""
from pathlib import Path
import json
import math
import base64
import io
import re
import hashlib
from PIL import Image
import pcbnew

PROJ=Path(__file__).resolve().parents[1]
board=pcbnew.LoadBoard(str(PROJ/"board_trace.kicad_pcb"))
plan=json.loads((PROJ/"placement_plan.json").read_text())
refs=[f.GetReference() for f in board.GetFootprints()]
assert len(refs)==len(set(refs))==len(plan["parts"])
assert set(refs)=={p["ref"] for p in plan["parts"]}
assert not set(refs).intersection(plan["retired_refs"])
assert not board.GetTracks() and board.GetNetCount()==1
back=[f for f in board.GetFootprints() if f.GetLayer()==pcbnew.B_Cu]
assert [f.GetReference() for f in back]==["U1"]
assert all(p.IsOnLayer(pcbnew.B_Cu) and not p.IsOnLayer(pcbnew.F_Cu) for p in back[0].Pads())
edges=[d for d in board.GetDrawings() if d.GetLayer()==pcbnew.Edge_Cuts]
ends={}
for edge in edges:
    for p in [edge.GetStart(),edge.GetEnd()]:
        key=(p.x,p.y); ends[key]=ends.get(key,0)+1
assert len(edges)==4 and len(ends)==4 and set(ends.values())=={2}
fits=json.loads((PROJ/"review"/"connector_fit.json").read_text())
metrics={}
scale=plan["px_per_mm"]
left=148.5-1030/scale/2; top=105-1601/scale/2
for ref,fit in fits.items():
    fp=next(f for f in board.GetFootprints() if f.GetReference()==ref)
    actual=[((pcbnew.ToMM(p.GetPosition().x)-left)*scale,
             (pcbnew.ToMM(p.GetPosition().y)-top)*scale) for p in fp.Pads()]
    assert len(actual)==22
    # Nearest observed joint must form a one-to-one assignment for this fit.
    matched=[]; errors=[]
    for x,y in actual:
        distances=[math.hypot(x-a,y-b) for a,b in fit["observed_px"]]
        index=min(range(len(distances)),key=distances.__getitem__)
        matched.append(index); errors.append(distances[index]/scale)
    assert len(set(matched))==22
    rms=math.sqrt(sum(e*e for e in errors)/len(errors))
    assert rms<.1 and max(errors)<.25
    metrics[ref]=dict(rms_mm=rms,max_mm=max(errors),unique_matched_joints=22)
result=dict(footprints=len(refs),back_smd_refs=[f.GetReference() for f in back],
            back_smd_pads=back[0].GetPadCount(),tracks=0,named_nets=0,
            outline_closed=True,outline_dimensionally_verified=False,
            connector_saved_pad_fit=metrics,
            limitation="Structural/placement checks only; no electrical or manufacturing signoff")
# Read-only check of native saved image payloads, including scale and orientation.
raw=(PROJ/"board_trace.kicad_pcb").read_text(encoding="utf-8")
pattern=r'\(image\s+\(at ([^)]+)\)\s+\(layer "([^"]+)"\)\s+\(scale ([^)]+)\)\s+\(data(.*?)\)\s+\(uuid'
image_checks=[]
for at,layer,image_scale,payload in re.findall(pattern,raw,re.S):
    filename={"Dwgs.User":"board_top.png","Cmts.User":"board_bottom.png"}[layer]
    encoded="".join(payload.replace('"','').split())
    im=Image.open(io.BytesIO(base64.b64decode(encoded))).convert("RGB")
    source=Image.open(PROJ/"images"/filename).convert("RGB")
    assert im.size==source.size and im.tobytes()==source.tobytes()
    assert [float(n) for n in at.split()]==[148.5,105]
    assert abs(float(image_scale)-300/(25.4*scale))<1e-6
    image_checks.append(dict(layer=layer,pixels_unchanged=True,size=im.size,
                             center_mm=[148.5,105],scale=float(image_scale),
                             sha256=hashlib.sha256(im.tobytes()).hexdigest()))
assert len(image_checks)==2
result["reference_images"]=image_checks
(PROJ/"review"/"saved_checks.json").write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps(result,indent=2))
