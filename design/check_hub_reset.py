"""Check reset DC allocations; does not simulate hardware or assert sequencing pass."""
from pathlib import Path
import hashlib
import json
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'kicad/usb3_sfp_hub/validation'
tree=ET.parse(OUT/'netlist.xml').getroot()
components={c.attrib['ref']:c for c in tree.find('components')}
for ref,value in [('U12','TPS3808G33DBVR'),('R9','12.1k / 1%'),('R24','10k / 1%')]:
    assert components[ref].findtext('value')==value
threshold=3.07
fall_min,fall_max=threshold*.985,threshold*1.015
# Conservative upper threshold using the maximum hysteresis fraction and
# upper falling threshold. Full-temperature bounds, not typical 0.5% accuracy.
release_upper=fall_max*1.025
pullup_max=12100*1.01
pullup_min=12100*.99
hub_leakage=10e-6
supervisor_leakage=300e-9
high_min=3.0-pullup_max*(hub_leakage+supervisor_leakage)
sink_max=3.6/pullup_min+hub_leakage
assert fall_min>3.0
assert release_upper<3.3
assert high_min>2.0
assert sink_max<1e-3
assert .4<.8  # U12 VOL at 1mA and VDD>=1.8 versus VL813 VIL maximum.
files=['VL813.pdf','kicad/usb3_sfp_hub/datasheets/TPS3808.pdf']
result={
    'status':'PASS static voltage/current allocations only; sequencing/timing/hardware unqualified',
    'source_class':'Manual primary datasheet transcription, not canonical extraction cache',
    'sources':{'VL813':'supplied rev1.00 pp11-12','TPS3808':'SBVS050N August 2026 pp3-7'},
    'source_hashes':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in files},
    'falling_threshold_range_V':[fall_min,fall_max],
    'conservative_release_threshold_upper_V':release_upper,
    'required_steady_HUB_3V3_minimum_V':3.20,
    'VL813_3V3_operating_range_V':[3.0,3.6],
    'RESET_high_min_V_at_3V3_rail_3V':high_min,
    'VL813_VIH_min_V':2.0,
    'RESET_sink_current_upper_A':sink_max,
    'U12_VOL_max_V_at_1mA_VDD_ge_1V8':.4,
    'VL813_VIL_max_V':.8,
    'CT_open_delay_ms_under_datasheet_test_conditions':[12,20,28],
    'limitations':[
        'Only the 3.3V rail is monitored; core 1.2V and local 5V validity are not established by RESET.',
        'HUB_3V3 must rise above the release threshold; 3.20V minimum steady output is a design constraint, not a measured LDO guarantee.',
        'Supplied VL813 document gives reset polarity/logic levels but no minimum reset delay or complete power-sequencing requirement.',
        'Reset-output load differs from TI timing-table default 100k/50pF; actual output edge/load/startup must be measured.',
        'Fast brownout response, low-VDD behavior, clock readiness and regulator operation during reset remain unqualified.',
        'J9 exposes an open-drain reset request; no optical recovery policy or controller has been implemented.',
    ]}
(OUT/'hub_reset_checks.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
