"""Reload native footprint and check against transcribed TI land/stencil dimensions."""
from pathlib import Path
import json
import pcbnew as k

ROOT=Path(__file__).resolve().parents[1]
lib=ROOT/'kicad/usb3_sfp_hub/libs/protection.pretty'
fp=k.FootprintLoad(str(lib),'TI_DQA0010A_1x2.5mm')
assert fp
copper={p.GetNumber():p for p in fp.Pads() if p.IsOnLayer(k.F_Cu)}
paste=[p for p in fp.Pads() if p.IsOnLayer(k.F_Paste)]
assert set(copper)==set(map(str,range(1,11)))
assert len(paste)==10
records=[]
for n in range(1,11):
    p=copper[str(n)];xy=p.GetPosition();size=p.GetSize()
    actual=[k.ToMM(xy.x),k.ToMM(xy.y),k.ToMM(size.x),k.ToMM(size.y)]
    expected=[-.4175 if n<=5 else .4175,(n-3)*.5 if n<=5 else (8-n)*.5,.565,.4 if n in (3,8) else .2]
    assert all(abs(a-b)<1e-6 for a,b in zip(actual,expected)),(n,actual,expected)
    assert p.IsOnLayer(k.F_Mask) and not p.IsOnLayer(k.B_Cu)
    assert abs(k.ToMM(p.GetLocalSolderMaskMargin())-.05)<1e-6
    pp=[q for q in paste if q.GetPosition()==xy]
    assert len(pp)==1
    assert abs(k.ToMM(pp[0].GetSize().x)-.565)<1e-6
    assert abs(k.ToMM(pp[0].GetSize().y)-(.36 if n in (3,8) else .2))<1e-6
    records.append({'pin':n,'x_mm':actual[0],'y_mm':actual[1],'width_mm':actual[2],'height_mm':actual[3],
                    'paste_height_mm':k.ToMM(pp[0].GetSize().y)})
assert not fp.GetField('Source').IsVisible()
gaps=[]
for i,a in enumerate(records):
    for b in records[i+1:]:
        dx=max(0,abs(a['x_mm']-b['x_mm'])-(a['width_mm']+b['width_mm'])/2)
        dy=max(0,abs(a['y_mm']-b['y_mm'])-(a['height_mm']+b['height_mm'])/2)
        gaps.append((dx*dx+dy*dy)**.5)
minimum_gap=min(gaps)
assert abs(minimum_gap-.2)<1e-6
report={'status':'PASS native pad geometry/layers against manually transcribed TI drawing',
        'source':'TPD4E02B04 SLVSD85B pp24-25, DQA0010A 4220328/A',
        'minimum_copper_gap_mm':minimum_gap,'minimum_mask_web_mm':minimum_gap-.1,'pads':records,
        'limitations':'Not fabrication qualification, placed-board DRC, signal-integrity or ESD testing'}
(ROOT/'kicad/usb3_sfp_hub/validation/esd_footprint.json').write_text(json.dumps(report,indent=2)+'\n')
print(report['status'])
