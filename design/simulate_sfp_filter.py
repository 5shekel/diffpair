"""SPICE passive-filter study. Does not model TPS62902 or the unknown module.

Numerical capacitor impedance/ESR comes from Murata's public characteristic
service at 3.3V, 25C. Tolerance cases are engineering sensitivity cases, not
guaranteed component corners. The source is ideal, and loads are explicit.
"""
from pathlib import Path
import json,csv,math,hashlib
import xml.etree.ElementTree as ET
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from ngspice_shared import NgSpice

ROOT=Path(__file__).resolve().parents[1]
PROJ=ROOT/'kicad/usb3_sfp_hub'
OUT=PROJ/'validation/sfp_filter'; OUT.mkdir(exist_ok=True)
xml=ET.parse(PROJ/'validation/netlist.xml').getroot()
components={c.attrib['ref']:c for c in xml.find('components')}
nets=[{(p.attrib['ref'],p.attrib['pin']) for p in n.findall('node')} for n in xml.find('nets')]
def together(*pins):assert any(set(pins)<=n for n in nets),pins
together(('L1','2'),('C10','1'),('C11','1'),('J1','16'))
together(('C10','2'),('R1','1'))
together(('R1','2'),('C11','2'),('J1','1'))
assert components['R1'].findtext('value').startswith('0.43 /')
assert components['C10'].findtext('value').startswith('22uF / 25V')
rows=list(csv.reader((ROOT/'design/references/murata_cap_characteristics.csv').read_text().splitlines()))
def curve(col):
    values=[]
    for row in rows:
        try:values.append((float(row[col]),float(row[col+1])))
        except (ValueError,IndexError):pass
    return np.array(values)
rdata,zdata=curve(3),curve(6)
frequency=15000.
esr=float(np.interp(frequency,rdata[:,0],rdata[:,1]))
impedance=float(np.interp(frequency,zdata[:,0],zdata[:,1]))
cap=1/(2*math.pi*frequency*math.sqrt(impedance**2-esr**2))
spice=NgSpice(); results=[]; curves=[]
cases=[('nominal_typical',4.7e-6,cap,.043,.43,esr),
       ('sensitivity_low_C_high_L',4.7e-6*1.2,11e-6,.07332446,.43*1.04,.035),
       ('sensitivity_high_C_low_L',4.7e-6*.8,24.2e-6,.025,.43*.99,.005)]
for name,inductance,capacity,dcr,damping,resr in cases:
    common=f'''SFP reference filter {name}
Vfeed feed 0 DC 3.3 AC 1
Rind feed lx {dcr:.12g}
Lfilter lx out {inductance:.12g}
Cbypass out 0 100n
Rcap out cpos {resr:.12g}
Cbulk cpos damp {capacity:.12g}
Rdamp damp 0 {damping:.12g}
'''
    # No-load AC peaking isolates passive filter damping. Ideal feed excludes
    # regulator output impedance. The 8-ohm case is the SFF level-II test load.
    acresults={}
    for load in ['unloaded','8ohm']:
        circuit=common+('Rload out 0 8\n' if load=='8ohm' else 'Rload out 0 1e9\n')+'.end\n'
        (OUT/f'{name}_{load}.cir').write_text(circuit)
        spice.circuit(circuit); spice.command('ac dec 80 100 1000000')
        f=spice.vector('frequency').real; v=spice.vector('v(out)')
        gain=20*np.log10(np.abs(v)); peak=int(np.argmax(gain))
        acresults[load]={'peak_gain_dB':float(gain[peak]),'peak_frequency_Hz':float(f[peak]),
                         'gain_at_100kHz_dB':float(np.interp(1e5,f,gain))}
        if load=='8ohm':curves.append((name,'ac',f,gain))
    # Illustrative stress only: 0 -> 0.6A in 10us, peak <50us, then 0.45A.
    # This meets the amplitude envelope but does not claim the actual module
    # has this waveform or no input capacitance. No regulator model is included.
    trans=common+'''Iload out 0 PWL(0 0 200u 0 210u 0.6 245u 0.6 250u 0.45 1000u 0.45)
.tran 0.1u 1m
.end
'''
    (OUT/f'{name}_load_step.cir').write_text(trans)
    spice.circuit(trans); spice.command('run')
    t=spice.vector('time'); v=spice.vector('v(out)'); vd=spice.vector('v(damp)')
    idx=int(np.argmin(v)); energy=float(np.trapezoid(vd**2/damping,t))
    curves.append((name,'tran',t,v))
    np.savetxt(OUT/f'{name}_load_step.csv',np.column_stack([t,v,vd**2/damping]),delimiter=',',header='time_s,module_voltage_V,damping_power_W',comments='')
    results.append({'case':name,'L_H':inductance,'effective_C_F':capacity,'DCR_ohm':dcr,
        'damping_R_ohm':damping,'capacitor_ESR_ohm':resr,'ac':acresults,
        'illustrative_step':{'minimum_V':float(v[idx]),'time_of_minimum_s':float(t[idx]),
           'below_3_14V':bool(v[idx]<3.14),'damping_peak_W':float(np.max(vd**2/damping)),
           'damping_energy_J_over_1ms':energy}})
fig,axes=plt.subplots(1,2,figsize=(11,4.5),layout='constrained')
for name,kind,x,y in curves:
    if kind=='ac':axes[0].semilogx(x,y,label=name.replace('sensitivity_',''))
    else:axes[1].plot(x*1e6,y,label=name.replace('sensitivity_',''))
axes[0].set(xlabel='Frequency (Hz)',ylabel='Voltage gain (dB)',title='Passive filter • ideal feed • 8 ohm load')
axes[1].axhline(3.14,color='red',ls='--',label='3.14 V connector floor')
axes[1].set(xlabel='Time (µs)',ylabel='Module-side voltage (V)',xlim=(180,450),title='Illustrative 0 → 0.6 A load step')
for ax in axes:ax.grid(alpha=.25);ax.legend(fontsize=7)
fig.savefig(OUT/'filter_response.png',dpi=160);fig.savefig(OUT/'filter_response.svg')
(OUT/'ngspice.log').write_text('\n'.join(spice.log)+'\n')
report={'status':'UNQUALIFIED: illustrative stress exposes a transient gap' if any(c['illustrative_step']['below_3_14V'] for c in results) else 'Passive study only; system unqualified',
    'engine':'KiCad bundled ngspice-46 shared library','engine_sha256':hashlib.sha256(spice.path.read_bytes()).hexdigest(),
    'capacitor_typical_data':{'source':'Murata public characteristic CSV at DC3.3V, 25C','evaluation_frequency_Hz':frequency,
        'ESR_ohm':esr,'effective_C_from_impedance_F':cap,'nominal_resistance_sum_ohm':.043+.43+esr},
    'cases':results,'limitations':['Ideal voltage feed omits regulator dynamics and inter-branch coupling.',
        'Unknown module input capacitance, inrush shaping and actual current waveform are absent.',
        '11uF/24.2uF corners are sensitivity assumptions, not guaranteed effective-C limits.',
        'Constant ESR/effective C approximation is local to 15kHz; high-frequency ESL/core effects are omitted.',
        'The voltage dip is a design gap under this assumed load, not a measured failure of the retained working pair.',
        'Damping pulse energy is reported without a pulse-rating pass; resistor pulse capability remains open.',
        'This is not SFF-8431 D.17 integrated-noise testing or a TPS62902 loop-stability test.'],
    'next_action':'Resolve module current rise/input capacitance; revise the filter if the stress waveform is required. Do not release PCB from these results.'}
(OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'status':report['status'],'capacitor':report['capacitor_typical_data'],'step_minimums_V':{c['case']:c['illustrative_step']['minimum_V'] for c in results}},indent=2))
