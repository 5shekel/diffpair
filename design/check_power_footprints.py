"""Reload saved footprints with pcbnew and check against manufacturer drawings.

Run using KiCad 10 python. Audit covers land geometry and layer/mask settings;
it does not establish assembly yield or validate the still-unrouted hub PCB.
"""
from pathlib import Path
import json,math,hashlib
import pcbnew

ROOT=Path(__file__).resolve().parents[1]
PROJ=ROOT/'kicad/usb3_sfp_hub'
LIB=PROJ/'libs/power.pretty'
report={'scope':'Saved land-pattern geometry only; no PCB or assembly qualification','footprints':{}}
for name in ['TI_RPJ0009A_1.5x2mm','L_Coilcraft_XGL4020']:
    fp=pcbnew.FootprintLoad(str(LIB),name)
    assert fp is not None
    for field in ['Source','Assembly note']:assert not fp.GetField(field).IsVisible()
    pads={}
    for p in fp.Pads():
        key=p.GetNumber(); assert key not in pads
        assert p.GetAttribute()==pcbnew.PAD_ATTRIB_SMD
        assert set(p.GetLayerSet().Seq())=={pcbnew.F_Cu,pcbnew.F_Paste,pcbnew.F_Mask}
        assert p.GetDrillSize().x==0 and p.GetDrillSize().y==0
        assert p.GetLocalSolderMaskMargin()==pcbnew.FromMM(.05)
        assert p.GetLocalSolderPasteMargin()==0 and p.GetLocalSolderPasteMarginRatio()==0
        pads[key]={'x':pcbnew.ToMM(p.GetPosition().x),'y':pcbnew.ToMM(p.GetPosition().y),
                   'w':pcbnew.ToMM(p.GetSize().x),'h':pcbnew.ToMM(p.GetSize().y)}
    close=lambda a,b:math.isclose(a,b,abs_tol=1e-6)
    if name.startswith('TI'):
        assert set(pads)==set(map(str,range(1,10)))  # no extra thermal pad
        for n in [1,2,3]:
            p=pads[str(n)]; assert close(p['x'],-.625) and close(p['w'],.65) and close(p['h'],.2)
        assert [pads[str(n)]['y'] for n in [1,2,3]]==[-.25,.25,.75]
        for n in [4,6]:
            p=pads[str(n)]; assert close(p['x'],.45) and close(p['w'],1) and close(p['h'],.2)
        assert pads['4']['y']==.75 and pads['6']['y']==-.25
        assert pads['5']=={'x':.625,'y':.25,'w':.65,'h':.2}
        for n in [7,8,9]:
            p=pads[str(n)]; assert close(p['y'],-.925) and close(p['w'],.25) and close(p['h'],.55)
        assert [pads[str(n)]['x'] for n in [7,8,9]]==[.5,0,-.5]
        source='TPS62902.pdf'; source_pages=[3,45,46]
    else:
        assert set(pads)=={'1','2'}
        assert close(pads['2']['x']-pads['1']['x'],2.37)
        for p in pads.values():assert close(p['y'],0) and close(p['w'],.98) and close(p['h'],3.4)
        assert pads['1']['x']<0<pads['2']['x']
        source='XGL4020.pdf'; source_pages=[3]
    # Conservative rectangle bounding boxes; rounded corners only add clearance.
    gaps=[]; values=list(pads.values())
    for i,a in enumerate(values):
        for b in values[i+1:]:
            dx=max(0,abs(a['x']-b['x'])-(a['w']+b['w'])/2)
            dy=max(0,abs(a['y']-b['y'])-(a['h']+b['h'])/2)
            gaps.append(math.hypot(dx,dy))
    minimum=min(gaps); assert minimum>=.249999
    report['footprints'][name]={'pads':pads,'pad_count':len(pads),'minimum_copper_gap_mm':minimum,
        'conservative_minimum_mask_web_mm':minimum-.1,'source':source,'source_pages':source_pages,
        'source_sha256':hashlib.sha256((PROJ/'datasheets'/source).read_bytes()).hexdigest(),
        'footprint_sha256':hashlib.sha256((LIB/(name+'.kicad_mod')).read_bytes()).hexdigest(),
        'status':'PASS geometry against stated manufacturer land pattern',
        'orientation':'PCB top view; RPJ follows p45, 180-degree rotation of p3 pinout figure; XGL pad1 is local winding-start convention'}
(PROJ/'validation/power_footprints.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:{'pads':v['pad_count'],'min_copper_gap_mm':v['minimum_copper_gap_mm'],'status':v['status']} for k,v in report['footprints'].items()},indent=2))
