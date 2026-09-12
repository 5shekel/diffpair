"""Bounded SFP supply allocation, not a transient or hardware qualification.

TI TPS62902 SLVSFM1A pp.5-6/10-11/18-21; SFF-8431 Table 8.
Values marked allocation must be met by selected parts and measured hardware.
"""
from pathlib import Path
import json
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'kicad/usb3_sfp_hub/validation'
xml = ET.parse(OUT / 'netlist.xml').getroot()
components = {c.attrib['ref']: c for c in xml.find('components')}
expected = {'U7':'TPS62902RPJR', 'R22':'32.4k / 1% / 100ppm',
            'R23':'10k / 1%', 'C54':'10nF / 5% / C0G',
            'C52':'10uF / 10V / X7R', 'C53':'22uF / 10V / X7R',
            'L4':'1uH / XGL4020-102MEC', 'L1':'4.7uH / XGL4020-472MEC',
            'L2':'4.7uH / XGL4020-472MEC'}
for ref,value in expected.items():
    assert components[ref].findtext('value') == value, (ref,value)

v_nom = 3.3
accuracy = .0125  # VSET, full -40..150C junction range, TI p6.
v_min, v_max = v_nom*(1-accuracy), v_nom*(1+accuracy)
# Engineering allocations, not measured DCR or ripple. SFF Table 8 voltage
# window includes ripple/droop/noise below 100kHz at the host connector.
branch_resistance_max = .10  # Ohms, hot DCR + PCB copper.
branch_peak = .6  # A, level-II instantaneous maximum per branch.
disturbance = .050  # V, one-sided allocation for sub-100kHz disturbances.
module_min = v_min-branch_peak*branch_resistance_max-disturbance
module_max = v_max+disturbance
assert module_min >= 3.14 and module_max <= 3.46
# Selected filter inductors: manufacturer DCR max at 25C, copper temperature
# estimate through maximum rated part temperature. This is not a thermal model.
hot_dcr_estimate = .0473*(1+.00393*(165-25))
copper_resistance_allocation = .020  # PCB hot resistance, must be verified after routing.
selected_branch_resistance = hot_dcr_estimate+copper_resistance_allocation
assert selected_branch_resistance <= branch_resistance_max
# All five management pullups asserted, plus regulator PG pullup asserted.
# The former is deliberately conservative: MOD_ABS/status/I2C need not all sink.
pullup_current = v_max/(4700*.99)*5 + v_max/(10000*.99)
total_peak = 2*branch_peak+pullup_current
assert total_peak < 2.0
# Typical switching frequency has no min/max spec. This is an estimate, not
# a guaranteed current-ripple maximum. L minimum below assumes no DC-bias loss.
l_min = 1e-6*.8*.9  # +/-20% initial plus 10% bias loss, at 25C current table.
ripple_typ = v_nom*(1-v_nom/5.2)/(l_min*2.5e6)
inductor_peak_est = total_peak+ripple_typ/2
negative_peak_est = ripple_typ/2
assert negative_peak_est < 1.3  # minimum specified negative current limit.
assert inductor_peak_est < 3.8  # selected 1uH part's 10% drop current at 25C.
assert 3.9*1.2 < 6.3  # 20% margin on switch limit below 20% drop current at 25C.
soft_start_typ_us = 10000/2.5*.8+55  # equation14, not a bound for VSET hardware.
mode_resistor_error = .01+100e-6*125  # 25 to 150C; excludes aging.
assert mode_resistor_error < .04

result = {
    'status':'PASS for stated DC allocations only; illustrative transient stress FAILS, see sfp_filter/report.json',
    'regulator_vset_range_V':[v_min,v_max],
    'allocated_branch_hot_resistance_ohm':branch_resistance_max,
    'allocated_low_frequency_disturbance_V':disturbance,
    'allocated_module_voltage_range_V':[module_min,module_max],
    'remaining_voltage_margin_V':{'low':module_min-3.14,'high':3.46-module_max},
    'filter_inductor_MPN':'XGL4020-472MEC',
    'filter_hot_DCR_estimate_ohm_at_165C':hot_dcr_estimate,
    'allocated_hot_PCB_resistance_ohm':copper_resistance_allocation,
    'selected_branch_resistance_estimate_plus_PCB_allocation_ohm':selected_branch_resistance,
    'selected_inductor_voltage_min_estimate_V':v_min-branch_peak*selected_branch_resistance-disturbance,
    'sfp_table8_peak_A_per_branch':branch_peak,
    'two_branch_peak_plus_pullups_A':total_peak,
    'converter_output_rating_A':2.0,
    'regulator_rating_headroom_A':2-total_peak,
    'ripple_estimate_A_pp_at_typical_frequency':ripple_typ,
    'inductor_peak_estimate_A':inductor_peak_est,
    'inductor_MPN':'XGL4020-102MEC',
    'inductor_Isat_at_25C_A':{'10percent_drop':3.8,'20percent_drop':6.3,'30percent_drop':8.8},
    'inductor_fault_basis':'3.9A maximum high-side current-limit threshold plus approximately 20% margin; delay and saturation curve still require validation',
    'nominal_soft_start_estimate_ms':soft_start_typ_us/1000,
    'mode_resistor_tolerance_plus_temperature_fraction':mode_resistor_error,
    'limitations':[
        'An explicit 0-to-600mA/10us load-step study drops below 3.14V; these DC margins do not override that transient gap.',
        'Resistance and disturbance numbers are requirements, not actual part or board measurements.',
        'Module identity unknown; SFF-8431 power levels are a provisional design envelope.',
        '66mV peak-to-peak SFF noise tolerance uses D.17 test spectrum; the 50mV allocation is not proof of that separate requirement.',
        'PG measures unfiltered supply and is undefined below VIN=1.8V; it is not a module-ready detector.',
        'No efficiency, whole-board input-current, inrush, filter stability, thermal, EMI or hot-plug pass is implied.',
        'Soft-start equation is an initial estimate; VSET and filtered module loads need actual startup measurement.',
        'Current/bias estimates use the manufacturer 25C table; temperature-dependent saturation, AC losses and switching-frequency spread remain unqualified.'
    ]
}
(OUT/'sfp_power_budget.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
