"""Generate the electrical draft, retaining unresolved interfaces as separate nets.

This writes new KiCad schematic/symbol files; it never modifies the traced PCB.
Pin names derive from the supplied VL813.pdf, page 8; types/dispositions use
pages 9-11. SFP contacts derive from SFF-8431 Table 3 (PDF page 23).
"""
from pathlib import Path
import json
import re
import uuid
import hashlib
import shutil

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"kicad"/"usb3_sfp_hub"
(OUT/"libs").mkdir(parents=True,exist_ok=True)
(OUT/"validation").mkdir(exist_ok=True)
NAME="usb3_sfp_hub"
project=OUT/(NAME+".kicad_pro")
if not project.exists():
    project.write_text(json.dumps({"meta":{"filename":project.name,"version":1}},indent=2)+"\n")
q=lambda value:json.dumps(str(value),ensure_ascii=False)
uid=lambda key:str(uuid.uuid5(uuid.NAMESPACE_URL,"diffpair/electrical-draft/"+key))
sheet=uid("sheet")
text=(ROOT/"design"/"VL813_local_text.txt").read_text(encoding="utf-8")
table=text.split("PAGE 8\n")[1].split("PAGE 9\n")[0]
names={}
for a,b,c,d in re.findall(r"^\s*(\d+) (\S+) (\d+) (\S+)\s*$",table,re.M):
    names[int(a)]=b; names[int(c)]=d
assert set(names)==set(range(1,77))
names[77]="GND_EP"
usb2={9,10,16,17,28,29,64,65,72,73}
power={2,5,8,13,18,19,20,24,27,30,36,37,38,39,40,41,48,49,58,61,68,71,74,77}
groups=[[23,22,26,25],[59,60,62,63],[66,67,69,70],[3,4,6,7],[11,12,14,15],
        sorted(usb2),sorted(power)]
groups.append(sorted(set(names)-set(sum(groups,[]))))
assert len(sum(groups,[]))==77 and len(set(sum(groups,[])))==77
titles=["UPSTREAM USB3","DOWNSTREAM 1","DOWNSTREAM 2","DOWNSTREAM 3","DOWNSTREAM 4",
        "USB2 - NOT CONNECTED","POWER / REGULATORS","CONTROL / CLOCK"]
def hub_type(n):
    name=names[n]
    if n in usb2:return "bidirectional"
    if name.startswith("SSTX"):return "output"
    if name.startswith("SSRX"):return "input"
    if n in (18,39):return "power_out"
    if n in power and n not in (37,40):return "power_in"
    if n in (31,44,45,47,54,55,57,75):return "input"
    if n==56:return "bidirectional"
    if n in (32,33,34,35,42,43,46,50,51,52,53,76):return "output"
    return "passive"  # Analog reference/feedback and undocumented SMBus types.

hub_nets={}
for n,name in names.items():
    net=name.replace("+","_P").replace("-","_N").replace("#","_N")
    if n in (20,77):net="GND"
    elif n in (19,38):net="HUB_5V"
    elif n in (2,8,18,27,36,41,49,71):net="HUB_3V3"
    elif n in (5,13,24,30,37,48,58,61,68,74):net="HUB_1V2"
    elif n==40:net="DC12FB40_PENDING"
    elif n==39:net="REG12_LX"
    elif n==31:net="VBUSDET_PENDING"
    elif n==47:net="EXTPWRON_PENDING"
    elif n==1:net="SSREXT_PENDING"
    if n in usb2 or n in (21,42,55,56,57):net=None
    hub_nets[n]=net

# Symbol pin placement records: (number, name, type, x, y, direction).
def split_pins(numbers,lookup,type_fn,width=16.51):
    half=(len(numbers)+1)//2
    pins=[]
    for index,n in enumerate(numbers):
        right=index>=half; row=index-half if right else index
        pins.append((str(n),lookup[n],type_fn(n),width if right else -width,
                     ((half-1)/2-row)*2.54,180 if right else 0))
    return pins

definitions={}; footprints={}; placement={}; library=[]; instances=[]; drawings=[]
def symbol(name,units,heading,footprint=""):
    content=[f'(symbol {q(name)} (pin_names (offset 0.5)) (in_bom yes) (on_board yes)',
             f'(property "Reference" "U" (at 0 0 0) (effects (font (size 1.27 1.27))))',
             f'(property "Value" {q(heading)} (at 0 -2.54 0) (effects (font (size 1.27 1.27))))',
             f'(property "Footprint" {q(footprint)} (at 0 0 0) (effects (font (size 1 1)) hide))']
    for unit,(title,pins) in enumerate(units,1):
        xs=[p[3] for p in pins]; ys=[p[4] for p in pins]
        x0=min(xs)+2.54; x1=max(xs)-2.54
        if x0>=x1:x0,x1=-10.16,10.16
        high=max(ys)+3.81; low=min(ys)-2.54
        content.append(f'(symbol {q(name+"_"+str(unit)+"_1")}')
        if name in ("C_SERIES", "C_BULK", "C_POLAR"):
            for pts in [[(-2.54,0),(-.635,0)],[(.635,0),(2.54,0)],[(-.635,-1.905),(-.635,1.905)],[(.635,-1.905),(.635,1.905)]]:
                xy=" ".join(f"(xy {x} {y})" for x,y in pts)
                content.append(f'(polyline (pts {xy}) (stroke (width 0.254) (type default)) (fill (type none)))')
            if name=="C_POLAR":
                content.append('(text "+" (at -2.032 2.54 0) (effects (font (size 1 1))))')
        elif name in ("R", "L", "XTAL"):
            if name=="R":
                content.append('(rectangle (start -2.54 -1.016) (end 2.54 1.016) (stroke (width 0.254) (type default)) (fill (type none)))')
            elif name=="L":
                for start in [-2.54,-1.27,0,1.27]:
                    content.append(f'(arc (start {start} 0) (mid {start+.635} 0.635) (end {start+1.27} 0) (stroke (width 0.254) (type default)) (fill (type none)))')
            else:
                content.append('(rectangle (start -1.27 -2.032) (end 1.27 2.032) (stroke (width 0.254) (type default)) (fill (type none)))')
                for x in [-2.54,2.54]:
                    content.append(f'(polyline (pts (xy {x} -2.54) (xy {x} 2.54)) (stroke (width 0.254) (type default)) (fill (type none)))')
        else:
            content.append(f'(rectangle (start {x0} {high}) (end {x1} {low}) (stroke (width 0.254) (type default)) (fill (type background)))')
            content.append(f'(text {q(title)} (at 0 {high-1.27} 0) (effects (font (size 1 1))))')
        for n,label,kind,x,y,a in pins:
            content.append(f'(pin {kind} line (at {x} {y} {a}) (length 2.54) (name {q(label)} (effects (font (size 1 1)))) (number {q(n)} (effects (font (size 0.9 0.9)))))')
        content.append(')')
    content.append(')')
    definitions[name]=units
    footprints[name]=footprint
    library.append("\n".join(content))

symbol("VL813_A1",[(t,split_pins(g,names,hub_type,24.13 if i>=6 else 16.51)) for i,(t,g) in enumerate(zip(titles,groups))],"VL813(A1)","lcsc:C69418_QFN-76_L9_0-W9_0-P0_40-EP6_4-TL")
sfp_names={1:"VeeT",2:"TX_FAULT",3:"TX_DISABLE",4:"SDA",5:"SCL",6:"MOD_ABS",7:"RS0",8:"RX_LOS",9:"RS1",10:"VeeR",11:"VeeR",12:"RD_N",13:"RD_P",14:"VeeR",15:"VccR",16:"VccT",17:"VeeT",18:"TD_P",19:"TD_N",20:"VeeT"}
symbol("SFP_PLUS",[("SFP+ SOCKET",split_pins(list(sfp_names),sfp_names,lambda n:"passive",17.78))],"SFP+ (module TBD)")
usb_names={1:"VBUS",2:"D_N_NC",3:"D_P_NC",4:"GND",5:"SSRX_N",6:"SSRX_P",7:"DRAIN",8:"SSTX_N",9:"SSTX_P","SH":"SHIELD"}
symbol("USB3_A_SS_ONLY",[("USB3-A / NO USB2",split_pins(list(usb_names),usb_names,lambda n:"passive",17.78))],"USB3-A")
symbol("C_SERIES",[("",[("1","~","passive",-5.08,0,0),("2","~","passive",5.08,0,180)])],"100nF", "Capacitor_SMD:C_0402_1005Metric")
passive_pins=[("1","~","passive",-5.08,0,0),("2","~","passive",5.08,0,180)]
symbol("C_BULK",[("",passive_pins)],"22uF")
symbol("C_POLAR",[("",passive_pins)],"220uF")
symbol("R",[("",passive_pins)],"R", "Resistor_SMD:R_0603_1608Metric")
symbol("L",[("",passive_pins)],"4.7uH")
symbol("XTAL",[("",passive_pins)],"25MHz")
symbol("DC_INPUT",[("LOCAL 5V INPUT",split_pins([1,2],{1:"+5V",2:"GND"},lambda n:"passive",15.24))],"5V regulated input")
switch_pins={1:"IN",2:"GND",3:"EN",4:"FAULT_N",5:"ILIM",6:"OUT"}
switch_types={1:"power_in",2:"power_in",3:"input",4:"open_collector",5:"passive",6:"power_out"}
symbol("TPS2553_DBV",[("PORT CURRENT LIMIT",split_pins(list(switch_pins),switch_pins,lambda n:switch_types[n],20.32))],"TPS2553DBVR","Package_TO_SOT_SMD:SOT-23-6")
inv_pins={1:"NC",2:"A",3:"GND",4:"Y",5:"VCC"}
inv_types={1:"passive",2:"input",3:"power_in",4:"output",5:"power_in"}
symbol("LVC1G04_DBV",[("INVERTER / Ioff",split_pins(list(inv_pins),inv_pins,lambda n:inv_types[n],20.32))],"SN74LVC1G04DBVR","Package_TO_SOT_SMD:SOT-23-5")
reg_pins={1:"PG",2:"SW",3:"VOS",4:"GND",5:"EN",6:"VIN",7:"MODE_SCONF",8:"SS_TR",9:"FB_VSET"}
reg_types={1:"open_collector",2:"power_out",3:"input",4:"power_in",5:"input",6:"power_in",7:"input",8:"passive",9:"passive"}
symbol("TPS62902_RPJ",[("SFP 3.3V BUCK",split_pins(list(reg_pins),reg_pins,lambda n:reg_types[n],22.86))],"TPS62902RPJR","power:TI_RPJ0009A_1.5x2mm")
symbol("SUPPLY_TEST",[("SUPPLY TEST ACCESS",split_pins([1,2,3],{1:"3V3",2:"PG",3:"GND"},lambda n:"passive",20.32))],"SFP supply test")
esd_pins={1:"IO1",2:"IO2",3:"GND",4:"IO3",5:"IO4",6:"NC_ROUTE",7:"NC_ROUTE",8:"GND",9:"NC_ROUTE",10:"NC_ROUTE"}
symbol("TPD4E02B04_DQA",[("USB3 SIGNAL ESD",split_pins(list(esd_pins),esd_pins,lambda n:"passive",22.86))],"TPD4E02B04DQAR","protection:TI_DQA0010A_1x2.5mm")
reset_pins={1:"RESET_N",2:"GND",3:"MR_N",4:"CT",5:"SENSE",6:"VDD"}
reset_types={1:"open_collector",2:"power_in",3:"input",4:"passive",5:"input",6:"power_in"}
symbol("TPS3808_DBV",[("3.3V RESET SUPERVISOR",split_pins(list(reset_pins),reset_pins,lambda n:reset_types[n],22.86))],"TPS3808G33DBVR","Package_TO_SOT_SMD:SOT-23-6")
symbol("RESET_ACCESS",[("RESET REQUEST",split_pins([1,2],{1:"MR_N",2:"GND"},lambda n:"passive",15.24))],"Reset access","Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical")
management={1:"GND",2:"VccT_REF",3:"SDA",4:"SCL",5:"MOD_ABS",6:"RX_LOS",7:"TX_FAULT",8:"TX_DISABLE",9:"RS0",10:"RS1"}
symbol("SFP_MGMT",[("SFP MANAGEMENT ACCESS",split_pins(list(management),management,lambda n:"passive",20.32))],"SFP management / 3.3V only")

def wire(a,b,key):
    drawings.append(f'(wire (pts (xy {a[0]} {a[1]}) (xy {b[0]} {b[1]})) (stroke (width 0) (type default)) (uuid {q(uid(key))}))')
def label(net,pos,key,angle=0):
    justify="right" if angle==180 else "left"
    # Shared power and SFP nets cross the new support sheet. Local hub nets stay local.
    if net=="GND" or net.startswith(("SFP_","HUB_")) or net.endswith("_5V_SWITCHED") or re.fullmatch(r"SSRX[1-4]_[PN]|PORT[1-4]_TX_[PN]",net) or net in ("SSXI","SSXO","SSREXT_PENDING","RESET_N","REG12_LX","USBHPE1_N","USBHOC1_N","USBHOC2_N"):
        drawings.append(f'(global_label {q(net)} (shape bidirectional) (at {pos[0]} {pos[1]} {angle}) (effects (font (size 1 1)) (justify {justify})) (uuid {q(uid(key))}))')
    else:
        drawings.append(f'(label {q(net)} (at {pos[0]} {pos[1]} 0) (effects (font (size 1 1)) (justify {justify} bottom)) (uuid {q(uid(key))}))')
def add(name,ref,unit,x,y,connections,value=None,properties=None,footprint=None):
    title,pins=definitions[name][unit-1]
    v=value or ("VL813(A1)" if name=="VL813_A1" else name)
    ref_offset=3.81 if name in ("XTAL","C_POLAR") else 2.54 if name in ("C_SERIES","C_BULK","R","L") else 7.62
    value_offset=3.81 if name=="XTAL" else 2.54 if name in ("C_SERIES","C_BULK","C_POLAR","R","L") else 5.08
    item=[f'(symbol (lib_id {q("draft:"+name)}) (at {x} {y} 0) (unit {unit}) (in_bom yes) (on_board yes) (dnp no) (uuid {q(uid(ref+":"+str(unit)))})',
          f'(property "Reference" {q(ref)} (at {x} {y-max(p[4] for p in pins)-ref_offset} 0) (effects (font (size 1.27 1.27))))',
          f'(property "Value" {q(v)} (at {x} {y-min(p[4] for p in pins)+value_offset} 0) (effects (font (size 1 1))))']
    item.append(f'(property "Footprint" {q(footprints[name] if footprint is None else footprint)} (at {x} {y} 0) (effects (font (size 1 1)) hide))')
    for key,val in (properties or {}).items():
        item.append(f'(property {q(key)} {q(val)} (at {x} {y} 0) (effects (font (size 1 1)) hide))')
    for n,_,_,dx,dy,angle in pins:
        item.append(f'(pin {q(n)} (uuid {q(uid(ref+":"+n))}))')
        pos=(round(x+dx,4),round(y-dy,4)); net=connections.get(int(n) if n.isdigit() else n)
        placement[(ref,n)]=dict(net=net,at=pos,unit=unit)
        if net is None:
            drawings.append(f'(no_connect (at {pos[0]} {pos[1]}) (uuid {q(uid("nc:"+ref+":"+n))}))')
        else:
            end=(round(pos[0]+(5.08 if angle==180 else -5.08),4),pos[1])
            wire(pos,end,"wire:"+ref+":"+n)
            label(net,end,"label:"+ref+":"+n,0 if angle==180 else 180)
    item.append(f'(instances (project {q(NAME)} (path {q("/"+sheet)} (reference {q(ref)}) (unit {unit})))) )')
    instances.append("\n".join(item))

positions=[(170.18,50.8),(254,48.26),(254,91.44),(254,134.62),(254,177.8),
           (294.64,243.84),(60.96,215.9),(167.64,147.32)]
for unit,((x,y),numbers) in enumerate(zip(positions,groups),1):
    add("VL813_A1","U1",unit,x,y,{n:hub_nets[n] for n in numbers},properties={"MPN":"VL813(A1)","Manufacturer":"VIA Labs","Datasheet":"../../VL813.pdf","BOM Comments":"EOL reference baseline; footprint and operating circuit qualification pending"})
ground_sfp={1,10,11,14,17,20}
sfp_nets={n:("GND" if n in ground_sfp else "SFP_"+sfp_names[n]) for n in sfp_names}
add("SFP_PLUS","J1",1,63.5,50.8,sfp_nets,value="SFP+ / MODULE TBD")
for port,y in enumerate([48.26,91.44,134.62,177.8],1):
    connections={1:f"PORT{port}_5V_SWITCHED",2:None,3:None,4:"GND",7:"GND","SH":"CHASSIS_PENDING",
                 5:f"SSRX{port}_N",6:f"SSRX{port}_P",8:f"PORT{port}_TX_N",9:f"PORT{port}_TX_P"}
    add("USB3_A_SS_ONLY",f"J{port+1}",1,365.76,y,connections,value=f"USB3-A PORT {port}")
    for i,pol in enumerate(["P","N"]):
        add("C_SERIES",f"C{port*2-1+i}",1,297.18,y-5.08+i*10.16,
            {1:f"SSTX{port}_{pol}",2:f"PORT{port}_TX_{pol}"},value="100nF / 0402")

def note(message,x,y,key,size=1.5):
    drawings.append(f'(text {q(message)} (at {x} {y} 0) (effects (font (size {size} {size})) (justify left top)) (uuid {q(uid(key))}))')
note("USB3-ONLY HUB OVER SFP+ — ELECTRICAL DRAFT",15.24,12.7,"title",2.2)
note("Optical interface NOT YET CONNECTED: resolve Rx.Detect, LFPS, idle and disconnect behavior.\nSFP_TD/RD and SSTX0/SSRX0 are intentionally separate nets until that circuit is qualified.",15.24,81.28,"optical-gap")
note("No USB2 data routing: all ten hub D+/D- pins and all USB-A D+/D- contacts are NC.\nNC does not remove the hub's need for the specified power rails and configuration.",15.24,101.6,"usb2-note")
note("PENDING: power/clock/port qualification, pin 40 disposition, SSREXT value, reset/VBUS policy,\nVBUS/input protection, signal ESD layout/testing, SFP controller/filter, firmware and module qualification.",15.24,266.7,"pending",1.3)
note("Pin 20 = GND; pin 21 = float; pin 57 = NC (normal mode).\nSource: supplied VL813.pdf pp.8–11; SFP contacts: SFF-8431 Table 3.\nPin names / critical dispositions checked; operation NOT verified.",15.24,127,"source",1.3)

root_sheet=sheet
child_sheet=uid("sfp-support-sheet")
drawings.append(f'''(sheet (at 337.82 226.06) (size 63.5 22.86) (fields_autoplaced)
 (stroke (width 0.1524) (type solid)) (fill (color 0 0 0 0)) (uuid {q(child_sheet)})
 (property "Sheetname" "SFP power and management" (at 337.82 225.298 0) (effects (font (size 1.27 1.27)) (justify left bottom)))
 (property "Sheetfile" "sfp_support.kicad_sch" (at 337.82 249.682 0) (effects (font (size 1.27 1.27)) (justify left top)))
 (instances (project {q(NAME)} (path {q('/'+root_sheet)} (page "2")))))''')
power_sheet=uid("hub-support-sheet")
drawings.append(f'''(sheet (at 337.82 200.66) (size 63.5 17.78) (fields_autoplaced)
 (stroke (width 0.1524) (type solid)) (fill (color 0 0 0 0)) (uuid {q(power_sheet)})
 (property "Sheetname" "Hub power and clock" (at 337.82 199.898 0) (effects (font (size 1.27 1.27)) (justify left bottom)))
 (property "Sheetfile" "hub_support.kicad_sch" (at 337.82 219.202 0) (effects (font (size 1.27 1.27)) (justify left top)))
 (instances (project {q(NAME)} (path {q('/'+root_sheet)} (page "3")))))''')
port_sheet=uid("port-power-sheet")
drawings.append(f'''(sheet (at 20.32 154.94) (size 91.44 22.86) (fields_autoplaced)
 (stroke (width 0.1524) (type solid)) (fill (color 0 0 0 0)) (uuid {q(port_sheet)})
 (property "Sheetname" "Downstream port power" (at 20.32 154.178 0) (effects (font (size 1.27 1.27)) (justify left bottom)))
 (property "Sheetfile" "port_power.kicad_sch" (at 20.32 178.562 0) (effects (font (size 1.27 1.27)) (justify left top)))
 (instances (project {q(NAME)} (path {q('/'+root_sheet)} (page "4")))))''')
supply_sheet=uid("sfp-supply-sheet")
drawings.append(f'''(sheet (at 152.4 228.6) (size 86.36 17.78) (fields_autoplaced)
 (stroke (width 0.1524) (type solid)) (fill (color 0 0 0 0)) (uuid {q(supply_sheet)})
 (property "Sheetname" "SFP regulated supply" (at 152.4 227.838 0) (effects (font (size 1.27 1.27)) (justify left bottom)))
 (property "Sheetfile" "sfp_supply.kicad_sch" (at 152.4 247.142 0) (effects (font (size 1.27 1.27)) (justify left top)))
 (instances (project {q(NAME)} (path {q('/'+root_sheet)} (page "5")))))''')
esd_sheet=uid("usb3-esd-sheet")
drawings.append(f'''(sheet (at 205.74 203.2) (size 76.2 15.24) (fields_autoplaced)
 (stroke (width 0.1524) (type solid)) (fill (color 0 0 0 0)) (uuid {q(esd_sheet)})
 (property "Sheetname" "USB3 signal protection" (at 205.74 202.438 0) (effects (font (size 1.27 1.27)) (justify left bottom)))
 (property "Sheetfile" "usb3_esd.kicad_sch" (at 205.74 219.202 0) (effects (font (size 1.27 1.27)) (justify left top)))
 (instances (project {q(NAME)} (path {q('/'+root_sheet)} (page "6")))))''')
root_instances,root_drawings=instances,drawings
instances,drawings=[],[]
sheet=root_sheet+"/"+child_sheet  # KiCad instance path includes the parent root UUID.

# SFF-8431 D.17/Figure 56: damping belongs in the bulk capacitor's shunt branch.
# Do not copy the test source's 0.1-ohm impedance into the production supply path.
for branch,y,rail in [(0,43.18,"SFP_VccT"),(1,96.52,"SFP_VccR")]:
    bulk_node=f"SFP_DAMP_{'T' if branch==0 else 'R'}"
    add("L",f"L{branch+1}",1,66.04,y,{1:"SFP_3V3_FEED",2:rail},"4.7uH / XGL4020-472MEC",
        {"MPN":"XGL4020-472MEC","Manufacturer":"Coilcraft","Datasheet":"https://www.coilcraft.com/getmedia/76c9c081-4945-4c85-9129-9356e1ad6734/xgl4020.pdf","BOM Comments":"47.3mOhm max DCR at 25C; 1.9/3.0/4.1A Isat at 10/20/30% drop at 25C; thermal/AC and filter validation pending"},footprint="power:L_Coilcraft_XGL4020")
    add("C_SERIES",f"C{9+branch*3}",1,167.64,y,{1:"SFP_3V3_FEED",2:"GND"},"100nF / 0402")
    add("C_BULK",f"C{10+branch*3}",1,269.24,y,{1:rail,2:bulk_node},"22uF / 25V / X7R / 10%",
        {"MPN":"GRM32ER71E226KE15L","Manufacturer":"Murata","Datasheet":"https://pim.murata.com/asset/pim4/ceramicCapacitorSMD/GRM32ER71E226KE15-04CA-EN_PDF_CERAMICCAPACITORSMD","BOM Comments":"1210; manufacturer 3.3V/25C frequency data gives about 15.2uF and 20.5mOhm at 15kHz. Typical data, not guaranteed corner. Hot-plug/filter qualification pending."},footprint="Capacitor_SMD:C_1210_3225Metric")
    add("R",f"R{branch+1}",1,368.3,y,{1:bulk_node,2:"GND"},"0.43 / 1% / 0.25W",
        {"MPN":"ERJ8RQFR43V","Manufacturer":"Panasonic","Datasheet":"https://industrial.panasonic.com/cdbs/www-data/pdf/RDN0000/AOA0000C313.pdf","BOM Comments":"1206 damping candidate; nominal total R about 0.494Ohm at 15kHz. Pulse capability and board filter response require qualification."},footprint="Resistor_SMD:R_1206_3216Metric")
    add("C_SERIES",f"C{11+branch*3}",1,167.64,y+20.32,{1:rail,2:"GND"},"100nF / 0402")
for ref,net,rail,x,y in [
    ("R3","SFP_TX_FAULT","SFP_VccT",66.04,157.48),
    ("R4","SFP_RX_LOS","SFP_VccR",66.04,180.34),
    ("R5","SFP_MOD_ABS","SFP_VccT",66.04,203.2),
    ("R6","SFP_SDA","SFP_VccT",190.5,157.48),
    ("R7","SFP_SCL","SFP_VccT",190.5,180.34),
]:
    add("R",ref,1,x,y,{1:rail,2:net},"4.7k / 1%")
mgmt_nets={1:"GND",2:"SFP_VccT",**{n:"SFP_"+management[n] for n in range(3,11)}}
add("SFP_MGMT","J6",1,335.28,172.72,mgmt_nets,"3.3V management access / footprint TBD")
note("SFP POWER FILTERS AND MANAGEMENT — DRAFT",15.24,12.7,"support-title",2.2)
note("TX supply branch",15.24,25.4,"tx-filter")
note("RX supply branch",15.24,78.74,"rx-filter")
note("SFF-8431 D.17 / Figure 56: target R_damp + inductor DCR + 22uF ESR = 0.5 ohm.\nR1/R2 = 0.43 ohm candidate; nominal total about 0.494 ohm at 15kHz. Transient qualification pending.",205.74,60.96,"damping",1.15)
note("100nF input/output bypass; bulk capacitor connects to GND THROUGH damping resistor. Separate TX/RX inductors.\nOPEN ISSUE: ideal-feed SPICE stress (0 to 600mA in 10us, no module C) dips to 3.03V nominal. Not qualified for that load.",15.24,124.46,"filter-notes",1.2)
note("Status pullups: 4.7k (sections 2.4.1 / 2.4.4 / 2.4.6).\nSDA/SCL: 4.7k initial, 100kHz and bus C <= 100pF; verify rise time.\nPullups use module-side supplies; external controller must not back-power them.",15.24,226.06,"pullups",1.2)
note("J6 provides access, NOT link control. Pin 2 is a voltage reference, not a 5V input.\nTX_DISABLE relies on the module pullup: transmitter stays disabled until driven low.\nRS0/RS1 policy and recovery controller remain pending; no permanent enable strap.",15.24,250.19,"control-gap",1.2)
child_instances,child_drawings=instances,drawings
instances,drawings=[],[]
sheet=root_sheet+"/"+power_sheet
add("DC_INPUT","J7",1,60.96,38.1,{1:"HUB_5V",2:"GND"},"5.0-5.2V at board / input TBD")
add("L","L3",1,256.54,38.1,{1:"REG12_LX",2:"HUB_1V2"},"10uH / current rating TBD")
for ref,net,x,y,target in [
    ("C15","HUB_5V",60.96,60.96,"U1.19 input"),
    ("C16","HUB_5V",162.56,60.96,"U1.38 input"),
    ("C17","HUB_3V3",365.76,38.1,"U1.18 LDO output"),
    ("C18","HUB_1V2",256.54,60.96,"L3 output / U1.37"),
    ("C19","HUB_1V2",365.76,60.96,"L3 output / U1.37"),
]:
    add("C_BULK",ref,1,x,y,{1:net,2:"GND"},"4.7uF / effective C TBD",{"Placement target":target})
for index,pin in enumerate([2,8,27,36,41,49,71,5,13,24,30,48,58,61,68,74]):
    rail="HUB_3V3" if index<7 else "HUB_1V2"
    add("C_SERIES",f"C{20+index}",1,55.88+(index%4)*96.52,106.68+(index//4)*17.78,
        {1:rail,2:"GND"},"100nF / 0402",{"Placement target":f"U1.{pin}","Basis":"Engineering starting value; place at assigned supply pin"})
add("XTAL","Y1",1,60.96,210.82,{1:"SSXI",2:"SSXO"},"25MHz / CL and package TBD")
add("C_SERIES","C36",1,60.96,233.68,{1:"SSXI",2:"GND"},"22pF / candidate C0G")
add("C_SERIES","C37",1,162.56,233.68,{1:"SSXO",2:"GND"},"22pF / candidate C0G")
add("R","R8",1,162.56,210.82,{1:"SSREXT_PENDING",2:"GND"},"BIAS_R_TBD")
add("R","R9",1,266.7,210.82,{1:"HUB_3V3",2:"RESET_N"},"12.1k / 1%",{"BOM Comments":"TPS3808 open-drain RESET pullup; leakage/low-level DC bounds checked; reset timing qualification pending"})
add("C_SERIES","C38",1,368.3,210.82,{1:"HUB_3V3",2:"GND"},"100nF / 0402",{"Placement target":"U12.6 to U12.2","BOM Comments":"Repurposed from former 1uF RESET RC capacitor; no capacitor directly on RESET_N"})
add("TPS3808_DBV","U12",1,327.66,233.68,{1:"RESET_N",2:"GND",3:"HUB_RESET_REQUEST_N",4:None,5:"HUB_3V3",6:"HUB_3V3"},"TPS3808G33DBVR",
    {"MPN":"TPS3808G33DBVR","Manufacturer":"Texas Instruments","Datasheet":"https://www.ti.com/lit/ds/symlink/tps3808.pdf","BOM Comments":"3.07V nominal falling threshold; CT open gives 12-28ms delay under specified test conditions. Monitors 3.3V only; core rail and optical recovery qualification pending."})
add("RESET_ACCESS","J9",1,266.7,185.42,{1:"HUB_RESET_REQUEST_N",2:"GND"},"Short 1-2 to request reset / MPN TBD")
add("R","R24",1,368.3,185.42,{1:"HUB_3V3",2:"HUB_RESET_REQUEST_N"},"10k / 1%",{"BOM Comments":"External MR pullup, in parallel with internal pullup; external control must be open-drain to GND"})
note("VL813 POWER, DECOUPLING AND CLOCK — CANDIDATE CIRCUIT",15.24,12.7,"hub-support-title",2.0)
note("U1.18 feeds HUB_3V3; U1.39 drives L3; U1.37 senses HUB_1V2.\nU1.40 remains unresolved (datasheet lists DC12FB; published project leaves it open).",15.24,78.74,"regulator-policy",1.25)
note("Supply-pin bypass allocation is stored on each C20-C35 as Placement target. Values and layout require qualification.",15.24,93.98,"decoupling-targets",1.25)
note("Clock and bias",15.24,185.42,"clock-heading",1.6)
note("Clock: 25MHz / 22pF candidates; crystal CL, ESR, drive and parasitics remain unqualified. SSREXT value remains TBD.\nU12 monitors HUB_3V3, CT open: 12-28ms delay. J9 requests reset; C38 now bypasses U12, replacing the old reset RC.\nRequire HUB_3V3 >= 3.20V steady for worst-case reset release; verify LDO tolerance under load.\nDoes not monitor HUB_1V2 or implement optical recovery. Core-rail sequencing, clock startup and reset timing require tests.",15.24,254,"clock-limitations",1.2)
note("J7 feeds hub, four switched ports and SFP regulator. Connector rating, input protection and total budget remain pending.",15.24,172.72,"power-scope",1.25)
power_instances,power_drawings=instances,drawings
instances,drawings=[],[]
sheet=root_sheet+"/"+port_sheet
for port,y in enumerate([40.64,81.28,121.92,162.56],1):
    switch=f"U{port+1}"
    output=f"PORT{port}_5V_SWITCHED"
    limit=f"PORT{port}_ILIM"
    add("TPS2553_DBV",switch,1,76.2,y,{1:"HUB_5V",2:"GND",3:"PORTS_EN",4:"USBHOC1_N",5:limit,6:output},"TPS2553DBVR",
        {"MPN":"TPS2553DBVR","Manufacturer":"Texas Instruments","Datasheet":"https://www.ti.com/lit/ds/symlink/tps2552.pdf","BOM Comments":"Active-high constant-current version; DBV pin 4 FAULT, pin 5 ILIM. Stock not verified."})
    add("R",f"R{port+9}",1,180.34,y,{1:limit,2:"GND"},"23.2k / 1%",{"BOM Comments":"TPS255x Table 2: 1023.7/1109.7/1207.5mA min/nom/max"})
    add("C_SERIES",f"C{39+3*(port-1)}",1,269.24,y,{1:"HUB_5V",2:"GND"},"100nF / 0402",{"Placement target":f"{switch}.1"})
    add("C_POLAR",f"C{40+3*(port-1)}",1,368.3,y,{1:output,2:"GND"},"220uF / 10V / 20%",{"BOM Comments":"Polarized low-ESR output bulk; MPN/package/ripple qualification pending; pin 1 positive"})
    add("C_SERIES",f"C{41+3*(port-1)}",1,269.24,y+17.78,{1:output,2:"GND"},"100nF / 0402",{"Placement target":f"J{port+1}.1"})
    add("R",f"R{17+port}",1,368.3,y+17.78,{1:output,2:"GND"},"1k / 1%",{"BOM Comments":"Passive output discharge; 27mW maximum at 5.2V; verify selected capacitor and back-drive behavior"})
add("LVC1G04_DBV","U6",1,76.2,228.6,{1:None,2:"USBHPE1_N",3:"GND",4:"PORTS_EN",5:"HUB_3V3"},"SN74LVC1G04DBVR",
    {"MPN":"SN74LVC1G04DBVR","Manufacturer":"Texas Instruments","Datasheet":"https://www.ti.com/lit/ds/symlink/sn74lvc1g04.pdf","BOM Comments":"Inverts hub active-low gang enable; Ioff plus R15 holds EN low at VCC=0; ramp behavior requires test"})
for ref,x,y,n1,n2 in [("R14",180.34,215.9,"HUB_3V3","USBHPE1_N"),("R15",180.34,241.3,"PORTS_EN","GND"),("R16",279.4,215.9,"HUB_3V3","USBHOC1_N"),("R17",375.92,215.9,"HUB_3V3","USBHOC2_N")]:
    add("R",ref,1,x,y,{1:n1,2:n2},"10k / 1%")
add("C_SERIES","C51",1,76.2,254,{1:"HUB_3V3",2:"GND"},"100nF / 0402",{"Placement target":"U6.5"})
note("FOUR CURRENT-LIMITED PORTS — GANGED ENABLE AND FAULT",15.24,12.7,"ports-title",2.0)
note("23.2k / 1%: 1.024-1.208A current-limit range (TI Table 2); design load 0.9A per port.\nFault outputs combine at USBHOC1_N; OUT rails remain independent. R18-R21 discharge output bulk.",15.24,185.42,"ports-policy",1.3)
note("U6 inverts USBHPE1_N. R14 defaults request OFF; R15 holds EN low with U6 unpowered (VCC=0).\nHOC2 is pulled inactive; unused charging-enable pin 42 is NC. Verify normal/gang firmware behavior.\nRequire 5.0-5.2V at board under load. Input surge/budget, capacitor selection, ramps and thermal tests pending.",15.24,266.7,"ports-pending",1.2)
port_instances,port_drawings=instances,drawings
instances,drawings=[],[]
sheet=root_sheet+"/"+supply_sheet
add("TPS62902_RPJ","U7",1,93.98,58.42,
    {1:"SFP_FEED_PG",2:"SFP_BUCK_SW",3:"SFP_3V3_FEED",4:"GND",5:"HUB_5V",6:"HUB_5V",7:"SFP_BUCK_MODE",8:"SFP_BUCK_SS",9:None},"TPS62902RPJR",
    {"MPN":"TPS62902RPJR","Manufacturer":"Texas Instruments","Datasheet":"https://www.ti.com/lit/ds/symlink/tps62902.pdf","BOM Comments":"RPJ nine-pad VQFN, no separate EP. Native local footprint from TI land pattern. VSET open=3.3V with 32.4k MODE; stock not verified."})
add("L","L4",1,241.3,43.18,{1:"SFP_BUCK_SW",2:"SFP_3V3_FEED"},"1uH / XGL4020-102MEC",
    {"MPN":"XGL4020-102MEC","Manufacturer":"Coilcraft","Datasheet":"https://www.coilcraft.com/getmedia/76c9c081-4945-4c85-9129-9356e1ad6734/xgl4020.pdf","BOM Comments":"TI Table 8-4 listed part; 9mOhm max DCR; 3.8/6.3/8.8A Isat at 10/20/30% drop at 25C; stripe faces pad1 SW; thermal/AC/fault peaks pending"},footprint="power:L_Coilcraft_XGL4020")
add("C_BULK","C52",1,93.98,111.76,{1:"HUB_5V",2:"GND"},"10uF / 10V / X7R",{"Placement target":"U7.6 to U7.4; effective capacitance qualification pending"})
add("C_BULK","C53",1,241.3,73.66,{1:"SFP_3V3_FEED",2:"GND"},"22uF / 10V / X7R",{"Placement target":"L4 output to U7.4; U7.3 Kelvin sense here","BOM Comments":"Effective 11-26.4uF target from TI Table 8-3; part and filtered-load stability pending"})
add("C_SERIES","C54",1,93.98,144.78,{1:"SFP_BUCK_SS",2:"GND"},"10nF / 5% / C0G",{"BOM Comments":"Candidate soft start, about 3.26ms from TI equation 14; startup through SFP filters requires measurement"})
add("C_SERIES","C55",1,93.98,177.8,{1:"HUB_5V",2:"GND"},"100nF / 0402",{"Placement target":"U7.6 to U7.4; minimize input switching loop"})
add("R","R22",1,241.3,111.76,{1:"SFP_BUCK_MODE",2:"GND"},"32.4k / 1% / 100ppm",
    {"BOM Comments":"TI Table 7-1 option 10: VSET, 2.5MHz, forced PWM, discharge enabled; total tolerance within +/-4%, pin C <=30pF"})
add("R","R23",1,241.3,144.78,{1:"SFP_3V3_FEED",2:"SFP_FEED_PG"},"10k / 1%")
add("SUPPLY_TEST","J8",1,350.52,73.66,{1:"SFP_3V3_FEED",2:"SFP_FEED_PG",3:"GND"},"Supply test access / footprint TBD")
note("SFP REGULATED SUPPLY — 3.3V / 2A CONVERTER",15.24,12.7,"supply-title",2.0)
note("U7 is independent of the hub 3.3V LDO. Both SFP filters share its output.\nMODE 32.4k selects forced PWM / 2.5MHz / VSET / discharge. Pin 9 deliberately OPEN selects 3.3V.\nEN follows local 5V. This sheet does not implement commanded module power cycling.",15.24,205.74,"supply-config",1.3)
note("PG is test access only: it senses the regulator output BEFORE L1/L2. It does not prove module voltage or link readiness.\nPG is undefined below VIN=1.8V; no reset or TX-enable logic is driven from it.\nNominal 10nF soft start is about 3.26ms. Module inrush, filter resonance, rail skew and brownout remain test items.",15.24,231.14,"supply-pg",1.3)
note("Source: TI TPS62902 SLVSFM1A pp.3,5-6,10-12,18-21,45-46; Coilcraft XGL4020 Doc1529. Capacitor selection pending.\nNative RPJ/XGL4020 footprints checked. DC allocation: <=0.10 ohm per filter branch; 50mV low-frequency disturbances.\nThese are design constraints, not measured performance. Module electrical and optical compatibility remains unqualified.",15.24,256.54,"supply-limits",1.2)
supply_instances,supply_drawings=instances,drawings
instances,drawings=[],[]
sheet=root_sheet+"/"+esd_sheet
for port,x,y in [(1,99.06,63.5),(2,299.72,63.5),(3,99.06,137.16),(4,299.72,137.16)]:
    txp,txn=f"PORT{port}_TX_P",f"PORT{port}_TX_N"
    rxp,rxn=f"SSRX{port}_P",f"SSRX{port}_N"
    add("TPD4E02B04_DQA",f"U{port+7}",1,x,y,
        {1:txp,2:txn,3:"GND",4:rxp,5:rxn,6:rxn,7:rxp,8:"GND",9:txn,10:txp},"TPD4E02B04DQAR",
        {"MPN":"TPD4E02B04DQAR","Manufacturer":"Texas Instruments","Datasheet":"https://www.ti.com/lit/ds/symlink/tpd4e02b04.pdf",
         "Placement target":f"J{port+1} SuperSpeed contacts; TX connector side of AC capacitors; short ground returns at pins 3/8",
         "BOM Comments":"Bidirectional +/-3.6V signal-only TVS; 0.25pF typical, 0.33pF max at 0V/1MHz/25C. NC pads used for PCB flow-through, not internally connected. SI/ESD tests pending."})
    note(f"PORT {port} — J{port+1}",x-45.72,y-27.94,f"esd-port-{port}",1.5)
note("FOUR USB3 PORTS — SIGNAL-LINE ESD PROTECTION",15.24,12.7,"esd-title",2.0)
note("One four-channel bidirectional TVS per port. Pins 1/2 protect TX; pins 4/5 protect RX. Both GND pins connect.\nTX protection is on the connector side of C1-C8. No connection to VBUS, D+ or D-. No supply pin is required.",15.24,185.42,"esd-topology",1.3)
note("Pads 10/9/7/6 have no internal signal path. Route copper across pad pairs 1-10, 2-9, 4-7, 5-6.\nIdentical net labels do NOT provide an internal bridge. Place the array at the connector, with continuous pair routing\nand short ground returns. Avoid stubs and keep incoming ESD paths away from protected traces.",15.24,210.82,"esd-layout",1.3)
note("TI TPD4E02B04 SLVSD85B pp.3-5,15,24-25. Bidirectional +/-3.6V; not suitable for 5V VBUS protection.\n0.25pF typical / 0.33pF max per line at 0V, 1MHz, 25C. PCB/connector parasitics add to this.\nComponent ESD ratings do not establish board immunity. USB eye/return-loss and system ESD tests remain required.",15.24,246.38,"esd-limits",1.2)
esd_instances,esd_drawings=instances,drawings
instances,drawings=root_instances,root_drawings
sheet=root_sheet

lib_text='(kicad_symbol_lib (version 20231120) (generator "kicad_symbol_editor")\n'+"\n".join(library)+'\n)\n'
(OUT/"libs"/"draft.kicad_sym").write_text(lib_text,encoding="utf-8")
embedded=[]
for name,raw in zip(definitions,library):
    embedded.append(raw.replace('(symbol '+q(name),'(symbol '+q("draft:"+name),1))
sch=f'(kicad_sch (version 20250114) (generator "eeschema") (uuid {q(sheet)}) (paper "A3")\n'
sch+='(lib_symbols\n'+"\n".join(embedded)+')\n'+"\n".join(instances+drawings)
sch+='\n(sheet_instances (path "/" (page "1")))\n(embedded_fonts no))\n'
(OUT/(NAME+".kicad_sch")).write_text(sch,encoding="utf-8")
child=f'(kicad_sch (version 20250114) (generator "eeschema") (uuid {q(child_sheet)}) (paper "A3")\n'
child+='(lib_symbols\n'+"\n".join(embedded)+')\n'+"\n".join(child_instances+child_drawings)
child+='\n(embedded_fonts no))\n'
(OUT/"sfp_support.kicad_sch").write_text(child,encoding="utf-8")
support=f'(kicad_sch (version 20250114) (generator "eeschema") (uuid {q(power_sheet)}) (paper "A3")\n'
support+='(lib_symbols\n'+"\n".join(embedded)+')\n'+"\n".join(power_instances+power_drawings)
support+='\n(embedded_fonts no))\n'
(OUT/"hub_support.kicad_sch").write_text(support,encoding="utf-8")
portfile=f'(kicad_sch (version 20250114) (generator "eeschema") (uuid {q(port_sheet)}) (paper "A3")\n'
portfile+='(lib_symbols\n'+"\n".join(embedded)+')\n'+"\n".join(port_instances+port_drawings)
portfile+='\n(embedded_fonts no))\n'
(OUT/"port_power.kicad_sch").write_text(portfile,encoding="utf-8")
supplyfile=f'(kicad_sch (version 20250114) (generator "eeschema") (uuid {q(supply_sheet)}) (paper "A3")\n'
supplyfile+='(lib_symbols\n'+"\n".join(embedded)+')\n'+"\n".join(supply_instances+supply_drawings)
supplyfile+='\n(embedded_fonts no))\n'
(OUT/"sfp_supply.kicad_sch").write_text(supplyfile,encoding="utf-8")
esdfile=f'(kicad_sch (version 20250114) (generator "eeschema") (uuid {q(esd_sheet)}) (paper "A3")\n'
esdfile+='(lib_symbols\n'+"\n".join(embedded)+')\n'+"\n".join(esd_instances+esd_drawings)
esdfile+='\n(embedded_fonts no))\n'
(OUT/"usb3_esd.kicad_sch").write_text(esdfile,encoding="utf-8")
(OUT/"sym-lib-table").write_text('(sym_lib_table (version 7) (lib (name "draft")(type "KiCad")(uri "${KIPRJMOD}/libs/draft.kicad_sym")(options "")(descr "Evidence-backed electrical draft symbols")))\n')
fplib=OUT/"libs"/"lcsc.pretty"
fplib.mkdir(exist_ok=True)
fpname="C69418_QFN-76_L9_0-W9_0-P0_40-EP6_4-TL.kicad_mod"
shutil.copy2(ROOT/"kicad"/"board_trace"/"libs"/"lcsc.pretty"/fpname,fplib/fpname)
(OUT/"fp-lib-table").write_text('(fp_lib_table (version 7) (lib (name "lcsc")(type "KiCad")(uri "${KIPRJMOD}/libs/lcsc.pretty")(options "")(descr "VL813 candidate footprint, qualification pending")) (lib (name "power")(type "KiCad")(uri "${KIPRJMOD}/libs/power.pretty")(options "")(descr "Manufacturer land patterns generated through pcbnew")))\n')
contract=dict(source="VL813.pdf revision 1.00 (2015-07-22), pages 8-11",sha256=hashlib.sha256((ROOT/"VL813.pdf").read_bytes()).hexdigest(),
              pins=[dict(number=n,name=names[n],electrical_type=hub_type(n),net=hub_nets[n],
                         pin_name_source_page=8 if n!=77 else 10,
                         function_source_page=9 if names[n].startswith(("SSTX","SSRX")) or n in (2,5,8,13,24,61,68,71) else 10 if n in usb2 or n in power or n in (1,21,75,76) else 11,
                         note="EPAD represented as footprint pad 77" if n==77 else "") for n in sorted(names)],
              no_usb2_pin_numbers=sorted(usb2),unconnected_normal_mode_pins=[21,57],unused_debug_pins=[55,56],unused_charging_enable_pin=42,
              electrical_type_policy="Schematic ERC types are engineering interpretations; feedback/reference pins remain passive. SMCLK/SMDAT are documented as debug-only nonstandard SMBus on page 11 and unused here.",
              provisional=True,open_subsystems=["optical PHY interface","power","clock/bias","reset/VBUS","SFP management","port protection","firmware"])
(ROOT/"design"/"vl813_pin_contract.json").write_text(json.dumps(contract,indent=2)+"\n")
fp_table=OUT/"fp-lib-table"
fp_table.write_text(fp_table.read_text().rstrip()[:-1]+' (lib (name "protection")(type "KiCad")(uri "${KIPRJMOD}/libs/protection.pretty")(options "")(descr "TI signal-protection land patterns generated through pcbnew")))\n')
print(f"Wrote {OUT/(NAME+'.kicad_sch')}: 6 sheets, 105 components, 77 hub pins, 4 SuperSpeed ports; optical signal interface remains open")
