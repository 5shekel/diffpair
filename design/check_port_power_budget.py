"""Evaluate stated DC corners, not USB compliance or startup simulation."""
from pathlib import Path
import hashlib
import json
import math
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT/'kicad/usb3_sfp_hub'
components={c.attrib['ref']:c for c in ET.parse(PROJECT/'validation/netlist.xml').getroot().find('components')}
for ref in ['R10','R11','R12','R13']:assert components[ref].findtext('value')=='23.2k / 1%'
for ref in ['R18','R19','R20','R21']:assert components[ref].findtext('value')=='1k / 1%'
for ref in ['C40','C43','C46','C49']:assert components[ref].findtext('value')=='220uF / 10V / 20%'
assert components['R15'].findtext('value')=='10k / 1%'
assert components['J7'].findtext('value')=='5.0-5.2V at board / input TBD'
# TPS255x SLVS841F Table 2 and page 7; SN74LVC1G04 SCES214AF p.6.
limit_min,limit_nom,limit_max=1.0237,1.1097,1.2075
switch_rmax=.135
load=.9
vmin,vmax=5.0,5.2
bleed_rmin,bleed_rmax=990,1010
bleed_imax=vmax/bleed_rmin
path_i=load+bleed_imax
drop=path_i*switch_rmax
off_enable_v=(10e-6+4*.5e-6)*10100
cap_max=220e-6*1.2+100e-9*1.2
discharge=bleed_rmax*cap_max*math.log(vmax/.8)
assert path_i<limit_min
assert off_enable_v<.66  # Minimum enable switching threshold, VCC=0 case only.
assert vmin-drop>4.75   # Project connector-voltage floor, before trace/contact loss.
assert vmax<=5.25       # Supplied VL813 operating maximum.
sources={name:{'sha256':hashlib.sha256((PROJECT/'datasheets'/name).read_bytes()).hexdigest()} for name in ['TPS2552.pdf','SN74LVC1G04.pdf']}
result={
    'status':'PASS for stated DC corners only; no startup/thermal/USB compliance claim',
    'sources':sources,
    'current_limit_A':{'min':limit_min,'nominal':limit_nom,'max':limit_max,'source':'TPS255x Table 2: 23.2k 1%'},
    'external_load_A_per_port':load,
    'max_bleeder_A_per_port':bleed_imax,
    'minimum_current_limit_headroom_A':limit_min-path_i,
    'maximum_switch_drop_V_at_design_load':drop,
    'minimum_output_V_before_trace_and_contact_loss':vmin-drop,
    'remaining_trace_contact_drop_budget_V_to_4_75V_floor':vmin-drop-4.75,
    'maximum_switch_conduction_W_at_design_load':path_i**2*switch_rmax,
    'four_port_normal_A_including_bleeders':4*path_i,
    'four_port_simultaneous_current_limit_upper_A':4*limit_max,
    'input_requirement':'5.0-5.2V measured at board under load; add hub and SFP demand to port current; adapter/connector not selected',
    'enable_voltage_upper_V_with_logic_VCC_zero':off_enable_v,
    'minimum_switch_enable_threshold_V':.66,
    'ideal_unloaded_discharge_to_0_8V_s_at_max_RC':discharge,
    'bleeder_W_at_5_2V_and_min_R':vmax**2/bleed_rmin,
    'limitations':['VCC between 0 and logic minimum is not covered by Ioff; test ramps/brownout',
                   'Discharge assumes disabled switch, no external back-drive and capacitor tolerance as stated',
                   'Current limit is a DC threshold, not a peak-short-circuit clamp',
                   'Thermal shutdown, PCB copper, cable/source transients and simultaneous hot-plug unqualified',
                   'Firmware must use ganged power and report aggregated overcurrent correctly']}
(PROJECT/'validation/port_power_budget.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
