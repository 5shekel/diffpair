# SFP filter continuation — 2026-09-12

The expanded passive study identifies a candidate for further testing, but does
not justify replacing the schematic filter yet. The authoritative schematic and
BOM remain at 98 components, with the original 4.7 uH / 22 uF / 0.43 ohm branches.
Their previously reported load-step failure remains open.

## Results

The first comparison reduced inductance, then explored undamped local bulk.
Several combinations improved load-step voltage while producing large AC peaks.
The next comparison put parallel bulk capacitors behind one shared damping
resistor. A full product of the sensitivity variables then exposed additional
resonance peaks that the initial two paired corners missed.

| Candidate per rail | Minimum voltage | Maximum voltage | Maximum unloaded AC peak | Expanded passive screen |
|---|---:|---:|---:|---|
| 0.47 uH, 4 × 22 uF sharing 0.068 ohm | 3.1508 V | 3.4335 V | 5.96 dB | Fails peak screen |
| 0.11 uH, 2 × 22 uF sharing 0.068 ohm | 3.1607 V | 3.4266 V | 3.83 dB | Fails peak screen |
| 0.11 uH, 2 × 22 uF sharing 0.100 ohm | 3.1524 V | 3.4325 V | 2.36 dB | Passes stated screen only |

Each candidate has 32 independent combinations and two load-edge durations:
64 transient runs and 32 unloaded AC sweeps. The AC result is independently
checked against the algebraic transfer function, with maximum absolute complex
gain error below 1e-7. All candidate netlists and worst-case CSV waveforms are
retained in `kicad/usb3_sfp_hub/validation/sfp_filter_comparison/corners/`.

The candidate topology is feed → series inductor → module rail, with 100 nF
directly to ground. Two parallel 22 uF capacitors connect from the module rail
to a common damping node, followed by one 0.100 ohm resistor to ground. The
resistor is not in the DC module-current path. This would add two capacitors
across the complete two-rail design. No candidate has been written into KiCad.

The 0.11 uH inductance corresponds to Coilcraft XGL4020-111MEC in the retained
Doc1529 table. The bulk model uses the existing Murata capacitor family, with
effective capacitance sensitivity values rather than nominal capacitance.
The new damping resistor has no selected MPN or qualified pulse rating.

## Scope and tradeoff

The prescribed load rises from zero to 600 mA in 1 or 10 us, holds for 35 us,
falls to 450 mA in 5 us, then releases to zero. Ideal feed limits are 3.20875 and
3.39125 V: regulator accuracy of +/-1.25% plus the existing +/-50 mV allocation.
The screen uses 3.14–3.46 V and a 3 dB AC-peak ceiling. The latter is an
engineering screen, **not an SFF requirement**.

The grid covers L +/-20%, effective capacitance 11/24.2 uF per capacitor, ESR
5/35 milliohm per capacitor, damping resistance -1/+4%, and series resistance
from effectively zero to estimated hot DCR plus 20 milliohm PCB allocation.
Zero resistance avoids treating a manufacturer's maximum DCR as a minimum.
These are sensitivity assumptions, not guaranteed component bounds over
temperature, bias, aging or assembly. Bypass capacitance remains ideal.

The passing candidate's 100 kHz voltage gain ranges from -1.95 to +1.78 dB
across these corners. It therefore gives little attenuation there and can
amplify supply noise. A passing load-step result cannot establish the SFF
weighted integrated noise requirement. Constant C/ESR also limits the model's
high-frequency accuracy; no mounting ESL, actual module load/input C, shared
feed impedance, or converter control loop is represented.

## Converter model and next decision

TI's TPS62902 datasheet section 8.3.2 discusses distributed load capacitance and
its series resistance; section 8.2.2.3 gives recommended LC combinations.
That supports checking the complete network rather than assuming extra bulk
is harmless. The current C52/C53 selections and startup behavior remain open.

The primary [TI product page](https://www.ti.com/product/TPS62902) provides
PSpice and SIMPLIS models. The PSpice archive was retrieved from
`https://www.ti.com/lit/zip/SLVMDO7` into
`design/references/tps62902_models/`. Its library declares `ENCRYPTED_LIB` and
`CDNENCSTART_ADV2`, model Final 1.00 dated 30SEP2021, for PSpice 17.4-2019 S019.
It cannot be loaded as a supported ngspice model. PSpice/SIMPLIS executables
were not found in PATH or the checked standard installation locations; this
was not an exhaustive filesystem search. No converter simulation was run.
The library notes also exclude temperature-dependent characteristics.

Before selecting the candidate, check converter startup, simultaneous rail
steps, load release and the weighted noise spectrum using a supported model
and then hardware. Preserve the original failure and these candidate results.
Do not keep tuning passive values solely to the assumed waveform. Independent
clock/protection work can continue while the physical optical-interface and
converter tests remain unresolved.

## Reproduction

Run from the repository root using system Python and the installed KiCad
ngspice DLL:

```powershell
python design/compare_sfp_filters.py
python design/compare_sfp_local_bulk.py
python design/compare_sfp_damped_bulk.py
python design/qualify_sfp_filter_candidates.py
```

The final command writes the 192-case expanded study, circuit-algebra checks,
JSON, CSV, and [plot](../kicad/usb3_sfp_hub/validation/sfp_filter_comparison/corners/comparison.png).
No PCB, schematic, or BOM is changed by these commands.
