"""Screen alternate SFP filters: parallel bulk capacitors share one damper.

Exploratory model only. The schematic is not modified. All corners are
sensitivity assumptions; manufacturer data does not guarantee these bounds.
"""
from pathlib import Path
import itertools
import json
import numpy as np
from ngspice_shared import NgSpice

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'kicad/usb3_sfp_hub/validation/sfp_filter_comparison'
OUT.mkdir(exist_ok=True)
spice = NgSpice()
results = []
for lu, dcr25 in [(.47, .0051), (.11, .0017)]:
    for count, rd in itertools.product([1, 2, 4], [.033, .047, .068, .1, .15]):
        name = f'L{lu:g}u_damped{count}x22u_R{rd:g}'
        cases = []
        for corner, lf, cap, esr, resistance, rf in [
            ('low_C_high_L_hot', 1.2, 11e-6, .035, dcr25*(1+.00393*140)+.020, 1.04),
            ('high_C_low_L', .8, 24.2e-6, .005, dcr25, .99),
        ]:
            common = f'''SFP shared damped bulk {name} {corner}
Rind feed lx {resistance:.12g}
Lfilter lx out {lu*1e-6*lf:.12g}
Cbypass out 0 100n
Rcap out cpos {esr/count:.12g}
Cbulk cpos damp {cap*count:.12g}
Rdamp damp 0 {rd*rf:.12g}
'''
            spice.circuit(common + 'Vfeed feed 0 DC 3.3 AC 1\n.end\n')
            spice.command('ac dec 100 100 1000000')
            f = spice.vector('frequency').real
            gain = 20*np.log10(abs(spice.vector('v(out)')))
            metrics = {'corner': corner, 'peak_dB': float(max(gain)),
                       'gain_100kHz_dB': float(np.interp(1e5, f, gain)),
                       'gain_1MHz_dB': float(gain[-1])}
            for rise_us in [1., 10.]:
                rise = rise_us*1e-6
                a=200e-6; b=a+rise; c=b+35e-6; d=c+5e-6; e=800e-6; g=e+rise
                circuit = common + f'''Vfeed feed 0 DC 3.3
Iload out 0 PWL(0 0 {a:.12g} 0 {b:.12g} .6 {c:.12g} .6 {d:.12g} .45 {e:.12g} .45 {g:.12g} 0 1m 0)
.tran 0.05u 1m
.end
'''
                spice.circuit(circuit)
                spice.command('run')
                v = spice.vector('v(out)')
                cases.append({**metrics, 'rise_us': rise_us,
                              'min_V': float(min(v)-.09125), 'max_V': float(max(v)+.09125)})
        result = {'candidate': name, 'L_uH': lu, 'bulk_count_per_branch': count,
                  'damping_ohm': rd, 'min_V': min(x['min_V'] for x in cases),
                  'max_V': max(x['max_V'] for x in cases),
                  'peak_dB': max(x['peak_dB'] for x in cases), 'cases': cases}
        result['passes_screen'] = result['min_V'] >= 3.14 and result['max_V'] <= 3.46 and result['peak_dB'] <= 3
        results.append(result)
        if result['passes_screen']:
            print(json.dumps({k: v for k, v in result.items() if k != 'cases'}), flush=True)
report = {
    'scope': 'Passive candidate screening, no schematic change or hardware qualification',
    'screen': '3.14..3.46V for prescribed 1/10us load/release; <=3dB unloaded AC peak (engineering screen, not SFF requirement)',
    'source_range_V': [3.20875, 3.39125],
    'source_basis': '3.3V +/-1.25% regulator accuracy +/-50mV allocated disturbance',
    'limitations': ['No converter loop, module C/inrush or shared-feed impedance.',
                    'Constant ESR/C approximation; high-frequency attenuation not qualified.',
                    'Two paired sensitivity corners do not establish worst-case bounds.',
                    'Integrated SFF noise and startup/hot-plug remain untested.'],
    'candidates': results,
}
(OUT/'damped_bulk.json').write_text(json.dumps(report, indent=2)+'\n')
