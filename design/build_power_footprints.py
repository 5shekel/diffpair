"""Create local power footprints through KiCad's native pcbnew API.

Run with KiCad 10's python.exe. Does not modify either project PCB.
Sources: TPS62902 SLVSFM1A p45/46 (RPJ0009A drawing 4224505/A),
Coilcraft XGL4020 document 1529-3 revised 2026-02-19.
"""
from pathlib import Path
import pcbnew

ROOT=Path(__file__).resolve().parents[1]
LIB=ROOT/'kicad/usb3_sfp_hub/libs/power.pretty'
LIB.mkdir(parents=True,exist_ok=True)

def vec(x,y):return pcbnew.VECTOR2I(pcbnew.FromMM(x),pcbnew.FromMM(y))

def line(fp,a,b,layer,width=.1):
    s=pcbnew.PCB_SHAPE(fp); s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(vec(*a)); s.SetEnd(vec(*b)); s.SetLayer(layer)
    s.SetWidth(pcbnew.FromMM(width)); fp.Add(s)

def polygon(fp,points,layer,width=.1):
    for a,b in zip(points,points[1:]+points[:1]):line(fp,a,b,layer,width)

def base(name,description,ref_y,value_y):
    fp=pcbnew.FOOTPRINT(None); fp.SetFPID(pcbnew.LIB_ID('power',name))
    fp.SetAttributes(pcbnew.FP_SMD); fp.SetLibDescription(description)
    fp.SetReference('REF**'); fp.SetValue(name)
    for field,y,layer in [(fp.Reference(),ref_y,pcbnew.F_SilkS),(fp.Value(),value_y,pcbnew.F_Fab)]:
        field.SetPosition(vec(0,y)); field.SetTextSize(vec(.6,.6)); field.SetTextThickness(pcbnew.FromMM(.1)); field.SetLayer(layer)
    return fp

def pad(fp,n,x,y,w,h,radius=0):
    p=pcbnew.PAD(fp); p.SetNumber(str(n)); p.SetAttribute(pcbnew.PAD_ATTRIB_SMD)
    p.SetPosition(vec(x,y)); p.SetSize(vec(w,h))
    p.SetShape(pcbnew.PAD_SHAPE_ROUNDRECT if radius else pcbnew.PAD_SHAPE_RECT)
    if radius:p.SetRoundRectRadiusRatio(radius/min(w,h))
    layers=pcbnew.LSET()
    for layer in [pcbnew.F_Cu,pcbnew.F_Paste,pcbnew.F_Mask]:layers.AddLayer(layer)
    p.SetLayerSet(layers)
    # Preferred NSMD opening; 50um expansion, paste same as copper per source.
    p.SetLocalSolderMaskMargin(pcbnew.FromMM(.05))
    p.SetLocalSolderPasteMargin(0); p.SetLocalSolderPasteMarginRatio(0.0)
    fp.Add(p)

def save(fp):
    for key in ['Source','Assembly note']:
        fp.GetField(key).SetVisible(False)
        fp.GetField(key).SetLayer(pcbnew.F_Fab)
    pcbnew.PCB_IO_MGR.FindPlugin(pcbnew.PCB_IO_MGR.KICAD_SEXP).FootprintSave(str(LIB),fp)
    print(fp.GetFPID().GetLibItemName())

fp=base('TI_RPJ0009A_1.5x2mm','TI RPJ0009A, SLVSFM1A p45/46; nine pads, no separate exposed pad',-1.8,1.8)
# Orientation is the manufacturer's board-layout example; rotated 180 degrees
# from datasheet Figure 5-1. No mirroring: this is the PCB top view.
for args in [(1,-.625,-.25,.65,.2),(2,-.625,.25,.65,.2),(3,-.625,.75,.65,.2),
             (4,.45,.75,1,.2),(5,.625,.25,.65,.2),(6,.45,-.25,1,.2),
             (7,.5,-.925,.25,.55),(8,0,-.925,.25,.55),(9,-.5,-.925,.25,.55)]:
    pad(fp,*args,radius=.04)
polygon(fp,[(-.75,-.35),(-.55,-.55),(-.75,-.75),(-.75,-1),(.75,-1),(.75,1),(-.75,1)],pcbnew.F_Fab)
# Body nominal 1.5 x 2.0mm, notch identifies the pin-1 side near y=-.25.
polygon(fp,[(-1.3,-1.5),(1.3,-1.5),(1.3,1.35),(-1.3,1.35)],pcbnew.F_CrtYd,.05)
line(fp,(-1.12,-.55),(-1.12,-.15),pcbnew.F_SilkS,.12)
line(fp,(-1.12,-.55),(-.92,-.55),pcbnew.F_SilkS,.12)
line(fp,(-.75,1.12),(.75,1.12),pcbnew.F_SilkS,.12)
fp.SetField('Source','https://www.ti.com/lit/ds/symlink/tps62902.pdf; p45/46')
fp.SetField('Assembly note','Pin 9 is FB/VSET, not ground; stencil example based on 0.125mm thickness; confirm fab mask capability')
save(fp)

fp=base('L_Coilcraft_XGL4020','Coilcraft XGL4020, Doc1529-3 2026-02-19; recommended land pattern',-2.65,2.65)
# 2.37mm centre spacing, 0.98 x 3.4mm pads. Pin1 is our winding-start
# convention: orient the package stripe over pad1 and connect SW there for L4.
pad(fp,1,-1.185,0,.98,3.4); pad(fp,2,1.185,0,.98,3.4)
polygon(fp,[(-2,-2),(2,-2),(2,2),(-2,2)],pcbnew.F_Fab)
line(fp,(-1.75,-1.8),(-1.75,1.8),pcbnew.F_Fab,.15)
polygon(fp,[(-2.4,-2.4),(2.4,-2.4),(2.4,2.4),(-2.4,2.4)],pcbnew.F_CrtYd,.05)
polygon(fp,[(-2.27,-2.27),(2.27,-2.27),(2.27,2.27),(-2.27,2.27)],pcbnew.F_SilkS,.12)
line(fp,(-2.05,-1.7),(-2.05,1.7),pcbnew.F_SilkS,.12)
fp.SetField('Source','Coilcraft XGL4020 Doc1529-3, recommended land pattern')
fp.SetField('Assembly note','Stripe identifies short winding start. Orient stripe at pad1; L4 pad1 is SW. Numbering is local convention; part is nonpolar.')
save(fp)
