"""Compare passive SFP filter candidates without changing the schematic.

Preserves the same load envelope that exposed the original voltage dip and
adds lower source voltage, load release and faster-rise sensitivity cases.
No TPS62902 loop or actual module model is included.
"""
from pathlib import Path
import json,math
import numpy as np
from ngspice_shared import NgSpice

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'kicad/usb3_sfp_hub/validation/sfp_filter_comparison'
OUT.mkdir(exist_ok=True)
old=json.loads((OUT.parent/'sfp_filter/report.json').read_text())
cap=old['capacitor_typical_data']['effective_C_from_impedance_F']
esr=old['capacitor_typical_data']['ESR_ohm']
spice=NgSpice(); results=[]
# DCRs from Coilcraft Doc1529. No PCB copper is hidden in these values.
for lu,dcr25 in [(4.7,.0473),(1.,.009),(.47,.0051)]:
 for rd in [.43,.22,.1]:
  name=f'L{lu:g}u_R{rd:g}'
  ac={}; trans=[]
  for corner,lf,cf,dcr,rf,rc in [('nominal',1.,cap,dcr25,1.,esr),
     ('low_C_high_L_hot',1.2,11e-6,dcr25*(1+.00393*140)+.020,1.04,.035),
     ('high_C_low_L',.8,24.2e-6,dcr25, .99,.005)]:
   common=f'''SFP passive candidate {name} {corner}
Rind feed lx {dcr:.12g}
Lfilter lx out {lu*1e-6*lf:.12g}
Cbypass out 0 100n
Rcap out cpos {rc:.12g}
Cbulk cpos damp {cf:.12g}
Rdamp damp 0 {rd*rf:.12g}
'''
   if corner=='nominal':
    circuit=common+'Vfeed feed 0 DC 3.3 AC 1\nRload out 0 8\n.end\n'
    spice.circuit(circuit);spice.command('ac dec 60 100 1000000')
    f=spice.vector('frequency').real; v=spice.vector('v(out)'); gain=20*np.log10(abs(v))
    ac={'peak_dB':float(max(gain)),'gain_100kHz_dB':float(np.interp(1e5,f,gain)),'gain_1MHz_dB':float(gain[-1])}
   for rise_us in [1.,10.,100.]:
    rise=rise_us*1e-6
    # Source low corner includes 50mV disturbance allocation; source high
    # corner includes the same positive allowance for load-release overshoot.
    for feed in [3.20875,3.39125]:
     a=200e-6;b=a+rise;c=b+35e-6;d=c+5e-6;e=1.2e-3;g=e+rise
     circuit=common+f'''Vfeed feed 0 DC {feed:.9g}
Iload out 0 PWL(0 0 {a:.12g} 0 {b:.12g} .6 {c:.12g} .6 {d:.12g} .45 {e:.12g} .45 {g:.12g} 0 2m 0)
.tran 0.05u 2m
.end
'''
     spice.circuit(circuit);spice.command('run')
     t=spice.vector('time');v=spice.vector('v(out)')
     trans.append({'corner':corner,'rise_us':rise_us,'source_V':feed,'min_V':float(min(v)),'max_V':float(max(v))})
  relevant=[t for t in trans if t['rise_us']==10]
  results.append({'candidate':name,'inductance_uH':lu,'damping_ohm':rd,'ac_nominal_8ohm':ac,
     'step_10us_min_V':min(t['min_V'] for t in relevant),'step_10us_max_V':max(t['max_V'] for t in relevant),
     'passes_10us_voltage_window':all(t['min_V']>=3.14 and t['max_V']<=3.46 for t in relevant),'transient':trans})
report={'scope':'Passive design comparison; not regulator/module/SFF qualification','source_range_V':[3.20875,3.39125],
 'source_basis':'TPS62902 +/-1.25% plus +/-50mV disturbance allocation; constant ideal feed in each case',
 'load':'0 to .6A, hold 35us, fall to .45A in 5us, then release to zero; rise/release durations 1/10/100us',
 'corners':'Effective C and R sensitivity assumptions, Coilcraft DCR temperature estimate + 20mOhm PCB allocation at hot corner',
 'candidates':results,'limitations':['No real module input capacitance/inrush waveform; no converter loop or shared-feed impedance.',
 'Constant ESR and effective C approximation; 1MHz gain is an indicative trend, not validated high-frequency attenuation.',
 'SFF integrated noise and resistor pulse capability remain untested.']}
(OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps([{k:v for k,v in r.items() if k!='transient'} for r in results],indent=2))
