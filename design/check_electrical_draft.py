"""Check independently exported KiCad XML connectivity against the design intent."""
from pathlib import Path
import xml.etree.ElementTree as ET
import json

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"kicad"/"usb3_sfp_hub"/"validation"
xml=ET.parse(OUT/"netlist.xml").getroot()
nets={n.attrib["name"]:{(p.attrib["ref"],p.attrib["pin"]) for p in n.findall("node")} for n in xml.find("nets")}
nodes={node:name for name,group in nets.items() for node in group}
def group(ref,pin):return nets[nodes[(ref,str(pin))]]
def together(*pins):
    expected={(r,str(p)) for r,p in pins}
    assert expected<=group(*pins[0]),(pins,group(*pins[0]))
def isolated(ref,pin):
    assert group(ref,pin)=={(ref,str(pin))}
    assert nodes[(ref,str(pin))].startswith("unconnected-"),nodes[(ref,str(pin))]

# This list is independently transcribed from supplied VL813.pdf page 10.
for pin in [28,29,64,65,72,73,9,10,16,17]:isolated("U1",pin)
for ref in ["J2","J3","J4","J5"]:
    isolated(ref,2); isolated(ref,3)
for pin in [21,42,55,56,57]:isolated("U1",pin)
together(("U1",20),("U1",77),("J1",1),("J1",20))
assert nodes[("U1","20")]=="GND"
for pin in [19,38]:assert nodes[("U1",str(pin))]=="HUB_5V"
assert nodes[("U1","18")]=="HUB_3V3"
together(("U1",18),("U1",2))
assert nodes[("U1","37")]=="HUB_1V2"
assert len(group("U1",40))==1,"Unresolved pin 40 must not be silently wired"

port_pins=[(59,60,62,63),(66,67,69,70),(3,4,6,7),(11,12,14,15)]
for port,(txp,txn,rxp,rxn) in enumerate(port_pins,1):
    connector=f"J{port+1}"
    esd=f"U{port+7}"
    for cap,hubpin,connectorpin in [(f"C{2*port-1}",txp,9),(f"C{2*port}",txn,8)]:
        assert group("U1",hubpin)=={("U1",str(hubpin)),(cap,"1")}
        esd_pins=("1","10") if connectorpin==9 else ("2","9")
        assert group(cap,2)=={(cap,"2"),(connector,str(connectorpin)),*((esd,n) for n in esd_pins)}
        assert nodes[(cap,"1")]!=nodes[(cap,"2")]
    assert group("U1",rxp)=={("U1",str(rxp)),(connector,"6"),(esd,"4"),(esd,"7")}
    assert group("U1",rxn)=={("U1",str(rxn)),(connector,"5"),(esd,"5"),(esd,"6")}
    together((esd,3),(esd,8),("U1",77))
    for n in range(1,11):assert nodes[(esd,str(n))] not in ("HUB_5V",f"PORT{port}_5V_SWITCHED")
    together((connector,4),(connector,7),("U1",77))

# SFP+ pin functions are from SFF-8431 Table 3, not the numeric imported symbol.
for pin,name in [(18,"TD_P"),(19,"TD_N"),(13,"RD_P"),(12,"RD_N"),(7,"RS0"),(9,"RS1")]:
    assert nodes[("J1",str(pin))]=="SFP_"+name
for pin in [23,22,26,25]:
    assert len(group("U1",pin))==1,"Unqualified optical circuit must not be silently treated as wired"

components={c.attrib["ref"]:c for c in xml.find("components")}
assert len(components)==105
for ref in ["U8","U9","U10","U11"]:
    assert components[ref].findtext("value")=="TPD4E02B04DQAR"
    assert components[ref].findtext("footprint")=="protection:TI_DQA0010A_1x2.5mm"
    props={p.attrib['name']:p.attrib['value'] for p in components[ref].findall('property')}
    assert props['MPN']=="TPD4E02B04DQAR"
# Independently checked against SFF-8431 Figure 56: bulk damping is in a
# shunt capacitor branch, never in the DC module current path.
for branch,pin in [(0,16),(1,15)]:
    inductor=f"L{branch+1}"
    cin,bulk,cout=(f"C{n+branch*3}" for n in [9,10,11])
    damp=f"R{branch+1}"
    together(("J1",pin),(inductor,2),(bulk,1),(cout,1))
    together((inductor,1),(cin,1))
    assert nodes[(inductor,"1")]=="SFP_3V3_FEED"
    assert nodes[(inductor,"1")]!=nodes[(inductor,"2")]
    assert group(bulk,2)=={(bulk,"2"),(damp,"1")}
    together((damp,2),(cin,2),(cout,2),("U1",77))
    assert components[inductor].findtext("value").startswith("4.7uH")
    assert components[bulk].findtext("value").startswith("22uF")
    assert components[damp].findtext("value")=="0.43 / 1% / 0.25W"
    for ref,mpn,fp in [(bulk,'GRM32ER71E226KE15L','Capacitor_SMD:C_1210_3225Metric'),(damp,'ERJ8RQFR43V','Resistor_SMD:R_1206_3216Metric')]:
        props={p.attrib['name']:p.attrib['value'] for p in components[ref].findall('property')}
        assert props['MPN']==mpn
        assert components[ref].findtext('footprint')==fp
    for cap in [cin,cout]:assert components[cap].findtext("value").startswith("100nF")
assert nodes[("J1","15")]!=nodes[("J1","16")]
for ref,pin,rail_pin in [("R3",2,16),("R4",8,15),("R5",6,16),("R6",4,16),("R7",5,16)]:
    together((ref,1),("J1",rail_pin))
    together((ref,2),("J1",pin))
    assert nodes[(ref,"1")]!=nodes[(ref,"2")]
    assert components[ref].findtext("value")=="4.7k / 1%"
for header_pin,sfp_pin in [(2,16),(3,4),(4,5),(5,6),(6,8),(7,2),(8,3),(9,7),(10,9)]:
    together(("J6",header_pin),("J1",sfp_pin))
together(("J6",1),("U1",77))
for sfp_pin,header_pin in [(3,8),(7,9),(9,10)]:
    assert group("J1",sfp_pin)=={("J1",str(sfp_pin)),("J6",str(header_pin))},"Control must not be silently strapped"
# Hub support topology: datasheet pin functions + independently read published
# VL813 reference. These checks do not qualify its analog values or pin 40 policy.
together(("J7",1),("U1",19),("U1",38),("C15",1),("C16",1))
together(("J7",2),("U1",77))
assert group("L3",1)=={("L3","1"),("U1","39")}
together(("L3",2),("U1",37),("C18",1),("C19",1))
assert nodes[("L3","1")]!=nodes[("L3","2")]
together(("U1",18),("C17",1))
assert components["L3"].findtext("value").startswith("10uH")
for ref in ["C15","C16","C17","C18","C19"]:
    assert components[ref].findtext("value").startswith("4.7uF")
    together((ref,2),("U1",77))
for index,pin in enumerate([2,8,27,36,41,49,71,5,13,24,30,48,58,61,68,74]):
    ref=f"C{20+index}"
    together((ref,1),("U1",pin)); together((ref,2),("U1",77))
    assert components[ref].findtext("value").startswith("100nF")
    props={p.attrib["name"]:p.attrib["value"] for p in components[ref].findall("property")}
    assert props["Placement target"]==f"U1.{pin}"
for hubpin,ypin,cap in [(75,1,"C36"),(76,2,"C37")]:
    assert group("U1",hubpin)=={("U1",str(hubpin)),("Y1",str(ypin)),(cap,"1")}
    together((cap,2),("U1",77))
    assert components[cap].findtext("value").startswith("22pF")
assert components["Y1"].findtext("value").startswith("25MHz")
assert group("U1",1)=={("U1","1"),("R8","1")}
together(("R8",2),("U1",77))
assert components["R8"].findtext("value")=="BIAS_R_TBD"
together(("R9",1),("U1",18))
assert group("U1",54)=={("U1","54"),("R9","2"),("U12","1")}
together(("U12",6),("U12",5),("U1",18),("C38",1),("R24",1))
together(("U12",2),("U1",77),("J9",2))
assert group("U12",3)=={("U12","3"),("R24","2"),("J9","1")}
isolated("U12",4)
together(("C38",2),("U1",77))
assert components["U12"].findtext("value")=="TPS3808G33DBVR"
assert components["U12"].findtext("footprint")=="Package_TO_SOT_SMD:SOT-23-6"
assert components["R9"].findtext("value")=="12.1k / 1%"
assert components["R24"].findtext("value")=="10k / 1%"
assert components["C38"].findtext("value").startswith("100nF")
assert "HUB_3V3"!=nodes[("L1","1")],"SFP must not be silently powered by an unbudgeted hub LDO"
# TPS2553 DBV pinout: 1 IN, 2 GND, 3 EN, 4 FAULT, 5 ILIM, 6 OUT.
# Check all branch OUT nets are distinct; only open-drain FAULT outputs combine.
port_outputs=[]
for port in range(1,5):
    sw=f"U{port+1}"; rlim=f"R{port+9}"
    cin,bulk,cout=(f"C{n+3*(port-1)}" for n in [39,40,41])
    together((sw,1),(cin,1),("J7",1))
    together((sw,2),(cin,2),(bulk,2),(cout,2),(rlim,2),("U1",77))
    together((sw,3),("U6",4),("R15",1))
    together((sw,4),("U1",45),("R16",2))
    assert group(sw,5)=={(sw,"5"),(rlim,"1")}
    bleed=f"R{port+17}"
    assert group(sw,6)=={(sw,"6"),(bulk,"1"),(cout,"1"),(bleed,"1"),(f"J{port+1}","1")}
    together((bleed,2),("U1",77))
    assert components[bleed].findtext("value")=="1k / 1%"
    port_outputs.append(nodes[(sw,"6")])
    assert components[sw].findtext("value")=="TPS2553DBVR"
    assert components[sw].findtext("footprint")=="Package_TO_SOT_SMD:SOT-23-6"
    assert components[rlim].findtext("value")=="23.2k / 1%"
    assert components[bulk].findtext("value")=="220uF / 10V / 20%"
    props={p.attrib["name"]:p.attrib["value"] for p in components[sw].findall("property")}
    assert props["MPN"]=="TPS2553DBVR" and props["Manufacturer"]=="Texas Instruments"
assert len(set(port_outputs))==4
assert group("U6",2)=={("U6","2"),("U1","43"),("R14","2")}
together(("U6",5),("R14",1),("R16",1),("R17",1),("C51",1),("U1",18))
together(("U6",3),("R15",2),("C51",2),("U1",77))
isolated("U6",1)
assert group("U1",44)=={("U1","44"),("R17","2")}
for ref in ["R14","R15","R16","R17"]:assert components[ref].findtext("value")=="10k / 1%"
assert components["U6"].findtext("value")=="SN74LVC1G04DBVR"
assert components["U6"].findtext("footprint")=="Package_TO_SOT_SMD:SOT-23-5"
# TPS62902 RPJ: TI SLVSFM1A p3. Pin 9 is VSET, not an exposed ground pad.
together(("U7",6),("U7",5),("C52",1),("C55",1),("J7",1))
together(("U7",4),("C52",2),("C53",2),("C54",2),("C55",2),("R22",2),("J8",3),("U1",77))
assert group("U7",2)=={("U7","2"),("L4","1")}
together(("U7",3),("L4",2),("C53",1),("L1",1),("L2",1),("R23",1),("J8",1))
assert group("U7",1)=={("U7","1"),("R23","2"),("J8","2")}
assert group("U7",7)=={("U7","7"),("R22","1")}
assert group("U7",8)=={("U7","8"),("C54","1")}
isolated("U7",9)  # Table 7-2 option 16, provided MODE selects VSET operation.
assert components["R22"].findtext("value")=="32.4k / 1% / 100ppm"
assert components["U7"].findtext("value")=="TPS62902RPJR"
assert components["U7"].findtext("footprint")=="power:TI_RPJ0009A_1.5x2mm"
for ref,mpn in [('L1','XGL4020-472MEC'),('L2','XGL4020-472MEC'),('L4','XGL4020-102MEC')]:
    props={p.attrib['name']:p.attrib['value'] for p in components[ref].findall('property')}
    assert props['MPN']==mpn and props['Manufacturer']=='Coilcraft'
    assert components[ref].findtext('footprint')=='power:L_Coilcraft_XGL4020'
assert components["L4"].findtext("value").startswith("1uH")
assert components["C54"].findtext("value")=="10nF / 5% / C0G"
assert nodes[("U7","3")]!=nodes[("U1","18")]
hub=components["U1"]
native_pins=[p.attrib["num"] for u in hub.findall("./units/unit") for p in u.findall("./pins/pin")]
assert len(native_pins)==len(set(native_pins))==77
assert set(native_pins)=={str(n) for n in range(1,78)}
result={"status":"PASS for implemented draft connectivity only","native_components":len(components),
        "usb3_signal_esd_arrays":4,"protected_signal_lines":16,
        "esd_scope":"TPD4E02B04 shunts on TX connector side and RX; NC routing pads share nets but require PCB copper bridges; SI/ESD untested",
        "unique_hub_pins":77,"downstream_superspeed_ports":4,"series_tx_capacitors":8,
        "hub_usb2_pins_isolated":10,"connector_usb2_contacts_isolated":8,
        "pin20_ground":True,"pin21_and_pin57_nc":True,
        "unused_debug_pins_nc":[55,56],"hub_supply_pin_bypass_capacitors":16,
        "hub_buck_inductor":"10uH candidate; ratings and loop behavior unqualified",
        "hub_crystal":"25MHz with candidate 22pF loads; part/drive/startup unqualified",
        "hub_reset":"TPS3808G33DBVR monitors 3.3V; CT open, J9 manual request; core rail/timing/recovery unqualified",
        "pin40_and_bias":"UNRESOLVED",
        "port_power_switches":4,"port_enable":"ganged via inverter; active-high TPS2553",
        "port_faults":"four open drains to HOC1; unused HOC2 pulled high",
        "port_current_limit_mA":{"min":1023.7,"nominal":1109.7,"max":1207.5,"basis":"TI Table 2, 23.2k 1%"},
        "sfp_regulator":"TPS62902RPJR; VSET open=3.3V; MODE 32.4k=forced PWM 2.5MHz with discharge",
        "sfp_regulator_qualification":"Pin mapping and local RPJ/inductor land patterns checked; capacitor parts, stability, startup and thermal qualification pending",
        "sfp_supply_branches":2,"bulk_damping_topology":"series resistor in shunt capacitor branch",
        "sfp_status_pullups":3,"sfp_i2c_pullups":2,"management_access_pins":10,
        "sfp_filter_parts_and_transient_behavior":"Selected L/bulk C/damping R; behavior NOT QUALIFIED; see filter simulation report",
        "optical_bridge":"OPEN / UNIMPLEMENTED","electrical_operation":"UNVERIFIED",
        "remaining":["power component selection and qualification","pin 40 disposition","crystal qualification and reference bias","reset qualification and VBUS detection",
                     "port power qualification, VBUS/input protection and signal ESD testing","SFP filter part selection and qualification","SFP management controller","optical physical layer","firmware","PCB layout","hardware tests"]}
(OUT/"connectivity_checks.json").write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps(result,indent=2))
