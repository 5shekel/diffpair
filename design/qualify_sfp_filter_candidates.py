"""Expanded passive corner screen; this is not module/regulator qualification.

Run after compare_sfp_damped_bulk.py. Keeps all tested candidate netlists and
worst-case waveforms, cross-checks AC against circuit algebra, and reports the
noise-filtering tradeoff. Does not change authoritative schematic or BOM.
"""
from pathlib import Path
import hashlib
import itertools
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from ngspice_shared import NgSpice

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'kicad/usb3_sfp_hub/validation/sfp_filter_comparison/corners'
OUT.mkdir(parents=True, exist_ok=True)
spice = NgSpice()
results = []
fig, axes = plt.subplots(2, 1, figsize=(10, 8), layout='constrained')
for name, lu, count, rd, dcr in [
    ('L047_4C_R068', .47, 4, .068, .0051),
    ('L011_2C_R068', .11, 2, .068, .0017),
    ('L011_2C_R100', .11, 2, .1, .0017),
]:
    directory = OUT/name
    directory.mkdir(exist_ok=True)
    cases = []
    worst_min = (float('inf'), None)
    worst_peak = (-float('inf'), None)
    for index, (lf, cf, esr, rf, hot) in enumerate(itertools.product(
        [.8, 1.2], [11e-6, 24.2e-6], [.005, .035], [.99, 1.04], [False, True]
    )):
        # Datasheet DCR max is not a minimum; zero series resistance is the
        # conservative cold bound for resonance. Hot includes 20mOhm copper.
        dc = dcr*(1+.00393*140)+.020 if hot else 0.
        L = lu*1e-6*lf
        C = cf*count
        R = rd*rf + esr/count
        common = f'''SFP candidate {name}, corner {index}
Rind feed lx {max(dc, 1e-9):.12g}
Lfilter lx out {L:.12g}
Cbypass out 0 100n
Rcap out cpos {esr/count:.12g}
Cbulk cpos damp {C:.12g}
Rdamp damp 0 {rd*rf:.12g}
'''
        ac_circuit = common+'Vfeed feed 0 DC 3.3 AC 1\n.end\n'
        (directory/f'{index:02d}_ac.cir').write_text(ac_circuit)
        spice.circuit(ac_circuit)
        spice.command('ac dec 150 100 1000000')
        f = spice.vector('frequency').real
        voltage = spice.vector('v(out)')
        s = 2j*np.pi*f
        admittance = s*100e-9 + 1/(R+1/(s*C))
        analytical = 1/(1+(max(dc, 1e-9)+s*L)*admittance)
        error = float(max(abs(voltage-analytical)))
        assert error < 1e-7, error
        gain = 20*np.log10(abs(voltage))
        peak = float(max(gain))
        if peak > worst_peak[0]:
            worst_peak = (peak, np.column_stack([f, gain]))
        ac_metrics = {'unloaded_peak_dB': peak, 'peak_frequency_Hz': float(f[np.argmax(gain)]),
                      'gain_100kHz_dB': float(np.interp(1e5, f, gain)),
                      'gain_1MHz_dB': float(gain[-1]), 'AC_algebra_max_abs_error': error}
        for rise_us in [1., 10.]:
            rise = rise_us*1e-6
            a=200e-6; b=a+rise; c=b+35e-6; d=c+5e-6; e=800e-6; g=e+rise
            circuit=common+f'''Vfeed feed 0 DC 3.3
Iload out 0 PWL(0 0 {a:.12g} 0 {b:.12g} .6 {c:.12g} .6 {d:.12g} .45 {e:.12g} .45 {g:.12g} 0 1m 0)
.tran 0.05u 1m
.end
'''
            (directory/f'{index:02d}_{rise_us:g}us.cir').write_text(circuit)
            spice.circuit(circuit)
            spice.command('run')
            t = spice.vector('time')
            v = spice.vector('v(out)')
            minimum = float(min(v)-.09125)
            maximum = float(max(v)+.09125)
            if minimum < worst_min[0]:
                worst_min = (minimum, np.column_stack([t, v-.09125, v+.09125]))
            cases.append({'index': index, 'rise_us': rise_us, 'L_H': L,
                          'effective_bulk_C_F': C, 'parallel_cap_ESR_ohm': esr/count,
                          'damping_ohm': rd*rf, 'series_DCR_and_copper_ohm': dc,
                          'min_V': minimum, 'max_V': maximum, **ac_metrics})
    result = {'candidate': name, 'inductance_uH': lu, 'bulk_count_per_branch': count,
              'nominal_damping_ohm': rd, 'transient_case_count': len(cases),
              'min_V': min(x['min_V'] for x in cases), 'max_V': max(x['max_V'] for x in cases),
              'max_unloaded_peak_dB': max(x['unloaded_peak_dB'] for x in cases),
              'gain_100kHz_range_dB': [min(x['gain_100kHz_dB'] for x in cases), max(x['gain_100kHz_dB'] for x in cases)],
              'cases': cases}
    result['passes_expanded_passive_screen'] = result['min_V'] >= 3.14 and result['max_V'] <= 3.46 and result['max_unloaded_peak_dB'] <= 3
    results.append(result)
    np.savetxt(directory/'worst_minimum_waveform.csv', worst_min[1], delimiter=',',
               header='time_s,rail_at_low_source_V,rail_at_high_source_V', comments='')
    np.savetxt(directory/'worst_peak_ac.csv', worst_peak[1], delimiter=',',
               header='frequency_Hz,voltage_gain_dB', comments='')
    axes[0].plot((worst_min[1][:,0]-200e-6)*1e6, worst_min[1][:,1], label=name)
    axes[1].semilogx(worst_peak[1][:,0], worst_peak[1][:,1], label=name)
    print(json.dumps({k:v for k,v in result.items() if k != 'cases'}), flush=True)

axes[0].axhline(3.14, color='firebrick', linestyle='--', label='3.14 V target')
axes[0].set(xlim=(-5,100), xlabel='Time from load-step start (us)', ylabel='Rail voltage (V)',
            title='Worst minimum among 64 sensitivity runs per candidate; ideal low feed 3.20875 V')
axes[1].axhline(3, color='firebrick', linestyle='--', label='3 dB engineering screen')
axes[1].set(xlabel='Frequency (Hz)', ylabel='Unloaded voltage gain (dB)',
            title='Worst resonance among tested corners; constant C/ESR approximation')
for ax in axes:
    ax.grid(True, alpha=.25)
    ax.legend(fontsize=8)
fig.savefig(OUT/'comparison.png', dpi=160)
fig.savefig(OUT/'comparison.svg')
source_files = ['design/qualify_sfp_filter_candidates.py', 'design/ngspice_shared.py',
                'design/references/murata_cap_characteristics.csv']
report = {'scope': 'Expanded passive sensitivity screen only; authoritative 4.7uH schematic unchanged',
          'source_range_V': [3.20875,3.39125],
          'load': '0 to 600mA in 1/10us, hold 35us, fall to 450mA in 5us, release to zero in 1/10us',
          'criteria': '3.14..3.46V plus <=3dB unloaded peak; 3dB is an engineering screen, not SFF requirement',
          'assumptions': 'Full product of L +/-20%, effective C 11/24.2uF per part, ESR 5/35mOhm per part, damper -.01/+.04 fractional, and series R zero/hot estimate +20mOhm copper',
          'limitations': ['Sensitivity values are not guaranteed temperature/DC-bias/aging bounds.',
                         'No regulator loop/output impedance, shared supply, module C/inrush or mounting ESL.',
                         'No SFF weighted RMS noise test; 1MHz gain is only indicative with this model.',
                         'Additional bulk changes converter loading and startup; validate before schematic selection.',
                         '0.068/0.100-ohm resistor parts and pulse ratings have not been selected.'],
          'source_hashes': {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in source_files},
          'candidates': results}
(OUT/'report.json').write_text(json.dumps(report, indent=2)+'\n')
(OUT/'ngspice.log').write_text('\n'.join(spice.log)+'\n')
