"""TI DQA0010A native land pattern, TPD4E02B04 PDF pp24-25.

Run with KiCad Python. No PCB is changed. Copper and paste differ on pads 3/8.
"""
from pathlib import Path
import pcbnew as k

ROOT=Path(__file__).resolve().parents[1]
LIB=ROOT/'kicad/usb3_sfp_hub/libs/protection.pretty'
LIB.mkdir(parents=True,exist_ok=True)
NAME='TI_DQA0010A_1x2.5mm'
v=lambda x,y:k.VECTOR2I(k.FromMM(x),k.FromMM(y))
fp=k.FOOTPRINT(None)
fp.SetFPID(k.LIB_ID('protection',NAME))
fp.SetAttributes(k.FP_SMD)
fp.SetLibDescription('TI DQA0010A land/stencil pattern 4220328/A 12/2015; TPD4E02B04 SLVSD85B pp24-25; top view')
fp.SetReference('REF**');fp.SetValue(NAME)
for field,y,layer in [(fp.Reference(),-1.9,k.F_SilkS),(fp.Value(),1.9,k.F_Fab)]:
    field.SetPosition(v(0,y));field.SetTextSize(v(.6,.6));field.SetTextThickness(k.FromMM(.1));field.SetLayer(layer)

def pad(number,x,y,height,layers):
    p=k.PAD(fp);p.SetNumber(str(number));p.SetAttribute(k.PAD_ATTRIB_SMD)
    p.SetPosition(v(x,y));p.SetSize(v(.565,height));p.SetShape(k.PAD_SHAPE_ROUNDRECT)
    p.SetRoundRectRadiusRatio(.05/min(.565,height))
    ls=k.LSET()
    for layer in layers:ls.AddLayer(layer)
    p.SetLayerSet(ls);p.SetLocalSolderMaskMargin(k.FromMM(.05))
    p.SetLocalSolderPasteMargin(0);p.SetLocalSolderPasteMarginRatio(0.0)
    fp.Add(p)

for n in range(1,11):
    x=-.4175 if n<=5 else .4175
    y=(n-3)*.5 if n<=5 else (8-n)*.5
    ground=n in (3,8)
    pad(n,x,y,.4 if ground else .2,[k.F_Cu,k.F_Mask] if ground else [k.F_Cu,k.F_Mask,k.F_Paste])
    if ground:pad('',x,y,.36,[k.F_Paste])

def line(a,b,layer,width=.1):
    s=k.PCB_SHAPE(fp);s.SetShape(k.SHAPE_T_SEGMENT);s.SetStart(v(*a));s.SetEnd(v(*b))
    s.SetLayer(layer);s.SetWidth(k.FromMM(width));fp.Add(s)

for points,layer,width in [
    ([(-.5,-1.05),(-.3,-1.25),(.5,-1.25),(.5,1.25),(-.5,1.25),(-.5,-1.05)],k.F_Fab,.1),
    ([(-.95,-1.6),(.95,-1.6),(.95,1.6),(-.95,1.6),(-.95,-1.6)],k.F_CrtYd,.05),
    ([(-.8,-1.35),(-.8,-1.2)],k.F_SilkS,.12),
    ([(-.8,-1.35),(-.5,-1.35)],k.F_SilkS,.12),
]:
    for a,b in zip(points,points[1:]):line(a,b,layer,width)
fp.SetField('Source','https://www.ti.com/lit/ds/symlink/tpd4e02b04.pdf; pp24-25')
fp.SetField('Assembly note','TI 0.1mm stencil example; paste pads 3/8 .565x.36mm; NSMD +.05mm; no separate EP. Check fab capabilities.')
for field in ['Source','Assembly note']:
    fp.GetField(field).SetVisible(False);fp.GetField(field).SetLayer(k.F_Fab)
k.PCB_IO_MGR.FindPlugin(k.PCB_IO_MGR.KICAD_SEXP).FootprintSave(str(LIB),fp)
print(LIB/(NAME+'.kicad_mod'))
