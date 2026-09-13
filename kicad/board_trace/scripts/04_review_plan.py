"""Compile the manually reviewed photo inventory; system Python + numpy.

Coordinates are observations in the unchanged 1030 x 1601 aligned photo frame.
References retained where an old detection represented a real component.
This is placement evidence, not an electrical netlist or a manufacturing BOM.
"""
from pathlib import Path
import json
import numpy as np

PROJ = Path(__file__).resolve().parents[1]
PX = 25.9375
parts = []

def add(ref, lib, fp, x, y, rot=0, side="F", value="UNKNOWN", evidence="Photo body and terminations; package inferred", confidence="inferred"):
    parts.append(dict(ref=ref, library=lib, fp=fp, px=x, py=y, rot=rot,
                      side=side, value=value, evidence=evidence, confidence=confidence))

# Old refs kept for real MLCC bodies; duplicate pad detections are retired.
caps = [("C1",355,474,90),("C2",283,474,90),("C3",497,474,90),
        ("C4",417,474,90),("C5",448,474,90),("C6",242,655,90),
        ("C7",395,729,90),("C8",349,729,90),("C9",159,743,90),
        ("C10",93,755,0),("C13",162,815,90),("C14",320,855,90),
        ("C15",436,892,0),("C17",470,955,0),("C20",215,974,90),
        ("C21",247,974,90),("C22",470,987,0),("C26",443,1355,0),
        ("C28",514,1355,0)]
new_caps = [(516,57,90),(558,57,90),(253,474,90),(324,474,90),
            (530,474,90),(729,449,0),(815,449,0),(284,610,90),
            (430,610,90),(222,851,90),(274,853,90),(355,855,90),
            (175,974,90),(365,1120,0),(440,1120,0),(514,1120,0),
            (372,1294,0)]
new_refs = list(range(35,50)) + [53,54]
caps += [(f"C{i}",x,y,r) for i,(x,y,r) in zip(new_refs,new_caps)]
for ref,x,y,r in caps:
    add(ref,"Capacitor_SMD","C_0603_1608Metric",x,y,r)

# Record printed codes verbatim. Electrical values are deliberately not decoded
# without checking code conventions (particularly the ambiguous crystal resistor).
resistors = [(92,681,0,"472"),(92,717,0,"472"),(92,794,0,"473"),
             (92,828,0,"472"),(465,610,90,"68?"),(282,974,90,"472"),
             (520,932,90,"331"),(520,1010,90,"331"),
             (391,1070,0,"1R0"),(391,1417,0,"331"),(391,1491,0,"331")]
for i,(x,y,r,code) in enumerate(resistors,1):
    add(f"R{i}","Resistor_SMD","R_1206_3216Metric" if i==9 else "R_0603_1608Metric",
        x,y,r,value=f"MARK:{code}",evidence=f"Black chip with printed code {code}; resistance not independently measured")

# Measured connector holes, all 18 signals + four shell mounts for each connector.
# Pad identities inherit the old footprint; fit does not establish signal pinout.
local = np.array([[-3.5,-2.144],[-1,-2.144],[1,-2.144],[3.5,-2.144],
                  [4,-.644],[2,-.644],[0,-.644],[-2,-.644],[-4,-.644],
                  [-3.5,1.056],[-1,1.056],[1,1.056],[3.5,1.056],
                  [4,2.556],[2,2.556],[0,2.556],[-2,2.556],[-4,2.556],
                  [-6.57,-4.144],[-6.57,1.536],[6.57,-4.144],[6.57,1.536]])*PX
observations = {
    "J1": [[178,263],[243,264],[295,264],[362,264],
           [374,303],[322,303],[269,303],[217,303],[164,303],
           [177,348],[242,348],[295,349],[361,349],
           [374,388],[322,387],[269,386],[217,387],[164,387],
           [94,209],[94,360],[440,213],[440,360]],
    "J2": [[691,267],[757,270],[810,271],[873,271],
           [887,308],[835,308],[784,307],[733,307],[680,306],
           [691,350],[757,351],[810,351],[873,353],
           [887,392],[835,391],[784,390],[733,390],[680,389],
           [611,214],[611,362],[950,219],[950,365]]}
fits={}
for ref,points in observations.items():
    target=np.array(points,dtype=float)
    a=local-local.mean(0); b=target-target.mean(0)
    u,_,vt=np.linalg.svd(a.T@b)
    rot=u@vt
    assert np.linalg.det(rot)>0, "Fit must not mirror the user's images"
    origin=target.mean(0)-local.mean(0)@rot
    residual=np.linalg.norm(local@rot+origin-target,axis=1)
    angle=float(np.degrees(np.arctan2(rot[0,1],rot[0,0])))
    fits[ref]=dict(observed_px=points, local_mm=(local/PX).tolist(),
                   origin_px=origin.tolist(), rotation_kicad_deg=-angle,
                   rms_px=float(np.sqrt(np.mean(residual**2))),max_px=float(max(residual)),
                   note="Rigid fit at retained scale; photo distortion and manual picking remain")
    add(ref,"lcsc","HC-USB3.0-L175-2X1-P",*origin,rot=-angle,
        value="USB3 stacked Type-A (candidate)",confidence="photo-measured",
        evidence="Rigid fit to all 22 bottom-photo joints; footprint candidate retained, pin numbering unverified")

add("J3","lcsc","C42418480_CONN-SMD_20P-P0_80_SFP20P",773.5,652,
    value="SFP20 (candidate)",evidence="Centered on locating pegs at (650,652) and (897,652); contact-row fit and pinout remain uncertain")
add("Y1","Crystal","Crystal_SMD_3225-4Pin_3.2x2.5mm",356,611,
    value="25MHz",evidence="25.000 MHz printed on can; four-pad package and pin assignment inferred")
add("U1","lcsc","C69418_QFN-76_L9_0-W9_0-P0_40-EP6_4-TL",274,782,side="B",
    value="VL813 (candidate)",evidence="Back-photo package center; prior part identification retained, pin-1 orientation unverified")
add("U2","Package_TO_SOT_SMD","SOT-23-5",371,1210,270,
    evidence="Three top leads and two bottom leads; device identity and pinout unknown")
for ref,x,y,size,value in [("L1",114,942,"4030","10uH"),
                            ("L2",488,1188,"3015","UNKNOWN"),
                            ("L3",488,1288,"3015","UNKNOWN")]:
    add(ref,"Inductor_SMD",f"L_Sunlord_SWPA{size}S",x,y,90,value=value,
        evidence="Shielded inductor body; footprint is a size proxy, height unknown" + ("; adjacent silk reads 10uH" if ref=="L1" else ""))
add("D1","Diode_SMD","D_SMB",168,1074,180,value="UNKNOWN (MARK:KE)",
    evidence="Former C50; molded two-terminal body and end band suggest a diode. SMB size, diode type and polarity are provisional")
add("C51","Capacitor_THT","CP_Radial_D5.0mm_P2.50mm",166,1186,270,
    evidence="Two back-photo joints at (166,1186)/(166,1253); radial electrolytic, diameter approximate and polarity unknown. Downsized from a D8.0mm to a D5.0mm can because the real J4 jack body is longer than the photo proxy and would encroach on an 8mm can (same 2.50mm lead pitch, so the leads stay in the same holes)")
add("J4","lcsc","C319099_DC-005-2.5A-2.0",188.06,1487.02,value="DC-005-2.5A-2.0 (XKB, LCSC C319099)",
    evidence="Former C52. Real panel-mount DC power jack placed on the two photo-measured collinear holes (old pad1/old pad3); barrel faces the board edge. Land/pin numbers from vendor datasheet 'PCB HOLES (TOP VIEW)' and EasyEDA package; datasheet schedules pin1=tip, pin2=break, pin3=outer. Electrical use unverified",confidence="vendor-fit")
add("CAGE1","lcsc","C5441174_CAGE-SFP-1X1-TH",773.55,963.28,value="SFP+ 1x1 cage (CND-tek 201N1Y02001)",
    evidence="Real SFP+ cage fitted to J3 locating holes, centred on J3 X +12.0mm toward the module end; added after the photo-placement pass",confidence="vendor-fit")
for ref,x,y in [("D2",450,1425),("D3",450,1498)]:
    add(ref,"LED_THT","LED_D5.0mm",x,y,value="LED (bent leads)",
        evidence="Visible LED and two through-hole joints, nominal 2.54mm pitch; polarity unknown, stock body does not model bent leads")

result=dict(schema_version=1,px_per_mm=PX,image_size_px=[1030,1601],image_center_mm=[148.5,105],
            orientation="Top unchanged; pre-aligned bottom unchanged",
            outline=dict(status="approximate photo trace, NOT dimensionally verified",
                         vertices_px=[[8,17],[1032,8],[1040,1626],[-16,1622]],
                         evidence="Full photos/board_top.jpg board corners, offset (-247,-183) into aligned crop. Cropped image omits bottom/side edges; camera perspective retained."),
            retired_refs={"C11":"Second termination of C10", "C12":"Second termination of C9",
                          "C16":"Second termination of C15", "C18":"Second termination of C17",
                          "C19":"Unpopulated two-pad site", "C23":"Second termination of C22",
                          "C24":"Unpopulated two-pad site", "C25":"Silkscreen/cage-region false detection",
                          "C27":"Second termination of C26", "C29":"Second termination of C28",
                          "C30":"D3 solder joint", "C31":"D3 lead/silk false detection",
                          "C32":"J4 solder tab", "C33":"J4 solder tab", "C34":"J4 solder tab",
                          "C50":"Replaced by provisional D1", "C52":"Replaced by J4 barrel jack"},
            parts=parts)
(PROJ/"placement_plan.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
(PROJ/"review"/"connector_fit.json").write_text(json.dumps(fits,indent=2)+"\n",encoding="utf-8")
print(f"Reviewed inventory: {len(parts)} footprints")
for ref,f in fits.items():
    print(f"{ref}: origin {f['origin_px']}, angle {f['rotation_kicad_deg']:.3f}, RMS {f['rms_px']/PX:.3f} mm, max {f['max_px']/PX:.3f} mm")
