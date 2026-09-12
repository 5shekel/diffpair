"""Evaluate extra local bulk to address the same 1/10us SFP step stresses.

All capacitances are effective values, not nominal markings. No circuit is
automatically selected or marked qualified by this exploratory script.
"""
from pathlib import Path
import json
import numpy as np
from ngspice_shared import NgSpice
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'kicad/usb3_sfp_hub/validation/sfp_filter_comparison'
spice=NgSpice(); results=[]
for lu,dcr25 in [(1.,.009),(.47,.0051),(.11,.0017)]:
 for count in [1,2,4]:
  for rd in [.43,.1]:
   name=f'L{lu:g}u_direct{count}x22u_R{rd:g}'
   cases=[]; ac={}
   for corner,lf,cb,cd,rc,dc in [
      ('low_C_high_L_hot',1.2,11e-6,count*11e-6,.035,dcr25*(1+.00393*140)+.020),
      ('high_C_low_L',.8,24.2e-6,count*24.2e-6,.005,dcr25)]:
    common=f'''SFP local bulk {name} {corner}
Rind feed lx {dc:.12g}
Lfilter lx out {lu*1e-6*lf:.12g}
Cbypass out 0 100n
Rlocal out clocal {rc/count:.12g}
Clocal clocal 0 {cd:.12g}
Rcap out cpos {rc:.12g}
Cbulk cpos damp {cb:.12g}
Rdamp damp 0 {rd*(1.04 if corner.endswith('hot') else .99):.12g}
'''
    circuit=common+'Vfeed feed 0 DC 3.3 AC 1\nRload out 0 8\n.end\n'
    spice.circuit(circuit);spice.command('ac dec 50 100 1000000')
    f=spice.vector('frequency').real;v=spice.vector('v(out)');gain=20*np.log10(abs(v))
    ac[corner]={'peak_dB':float(max(gain)),'gain_100kHz_dB':float(np.interp(1e5,f,gain)),'gain_1MHz_dB':float(gain[-1])}
    for rise_us in [1.,10.]:
     rise=rise_us*1e-6
     # Linear passive circuit: source is a DC offset, so one solve covers
     # both source offsets exactly (the load is a prescribed current source).
     a=200e-6;b=a+rise;c=b+35e-6;d=c+5e-6;e=800e-6;g=e+rise
     circuit=common+f'''Vfeed feed 0 DC 3.3
Iload out 0 PWL(0 0 {a:.12g} 0 {b:.12g} .6 {c:.12g} .6 {d:.12g} .45 {e:.12g} .45 {g:.12g} 0 1m 0)
.tran 0.1u 1m
.end
'''
     spice.circuit(circuit);spice.command('run');v=spice.vector('v(out)')
     cases.append({'corner':corner,'rise_us':rise_us,'minimum_at_low_source_V':float(min(v)-.09125),'maximum_at_high_source_V':float(max(v)+.09125)})
   c={'candidate':name,'L_uH':lu,'additional_22uF_count_per_branch':count,'damping_ohm':rd,
      'min_V':min(t['minimum_at_low_source_V'] for t in cases),'max_V':max(t['maximum_at_high_source_V'] for t in cases),
      'max_passband_peak_dB':max(x['peak_dB'] for x in ac.values()),'ac':ac,'cases':cases}
   c['passes_test_window']=c['min_V']>=3.14 and c['max_V']<=3.46
   results.append(c)
   print(json.dumps({k:v for k,v in c.items() if k not in ['ac','cases']}),flush=True)
(OUT/'local_bulk.json').write_text(json.dumps({'scope':'Ideal-source passive sensitivity exploration; no module/regulator qualification','effective_capacitance_assumption_uF_per_22uF_part':[11,24.2],'candidates':results},indent=2)+'\n')
