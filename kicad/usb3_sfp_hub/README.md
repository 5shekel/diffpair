# USB3-only SFP+ hub electrical draft

Open `usb3_sfp_hub.kicad_pro` in KiCad 10. The schematic contains one VL813 split
into eight functional units, four downstream USB-A connectors, eight 100 nF TX
coupling capacitors, and an SFP+ socket with named signals. A second sheet adds
SFP power-filter branches, five management pullups and a ten-pin access connector
(105 physical components across six sheets total). A third sheet adds hub supply
passives, decoupling, clock and reset circuitry; a fourth implements downstream
power switches and overcurrent aggregation. A fifth supplies the SFP filters from
an independent 3.3 V buck converter. The interfaces that
still require circuitry are visibly marked on the sheet.

This is a new electrical draft; references differ from the photo-trace project.
It has no PCB yet. Do not use it as a manufacturing design.

## Implemented and checked

- VL813's 76 numbered contacts plus exposed pad are represented exactly once.
- Pin 20 connects to ground; pin 21 floats; TESTEN pin 57 is NC for normal mode.
  These dispositions come from the supplied `VL813.pdf`, pages 10–11.
- All ten hub USB2 D+/D- pins and all eight connector D+/D- contacts are NC.
- Each downstream TX pair crosses two separate series coupling capacitors.
  Each RX pair connects directly to the respective connector's receive contacts.
- SFP pin functions use SFF-8431 Table 3. In particular, pin 7 is RS0 and pin 9 is
  RS1; neither is silently grounded by a generic numeric connector symbol.
- The native netlist passes `design/check_electrical_draft.py`. This is a check of
  implemented draft nets only, not evidence of hub enumeration or optical operation.

Native ERC currently has **27 findings: 7 errors and 20 warnings**. They identify
undriven supplies/inputs and isolated labels for circuits not yet implemented.
No exclusions or fake power flags were added to hide those omissions.

## SFP regulated supply

[`sfp_supply.kicad_sch`](sfp_supply.kicad_sch), [preview](validation/sfp_supply.png),
adds TPS62902RPJR, a 1 uH candidate inductor, input/output bypass, a 10 nF
soft-start capacitor and power-good test access. Its nine-pad RPJ pinout was
checked against the manufacturer's drawing; its local footprint now follows the
manufacturer's p.45/46 land/stencil examples, including the longer VIN/GND pads.
32.4 kOhm on MODE selects VSET, forced PWM at 2.5 MHz and output discharge;
leaving VSET open selects 3.3 V. EN follows the board's 5 V supply.
[TI TPS62902 datasheet](https://www.ti.com/lit/ds/symlink/tps62902.pdf), pp. 3, 10–12.

The full-temperature VSET regulation range is ±1.25%. The draft allocates at most
0.10 ohm hot resistance per filter branch and 50 mV for low-frequency disturbances.
At the SFF-8431 level-II instantaneous limit of 600 mA per branch, this leaves
8.75 mV above the connector's 3.14 V floor. These are **requirements on the
unfinished circuit**, not measured performance. The separate SFF noise test,
filter resonance, startup rail skew and module hot-plug still need qualification.
[TI electrical limits](https://www.ti.com/lit/ds/symlink/tps62902.pdf), pp. 5–6;
[SFF-8431 Table 8 and D.17](https://members.snia.org/document/dl/25891).

PG senses the regulator output before the SFP filters; it is available at J8 and
does not drive hub reset or optical enable. It cannot establish module readiness.
The candidate 10 nF soft start gives an initial estimate of 3.26 ms. Actual VSET
startup and filtered-load behavior remain unmeasured. Capacitor part selection,
total input budget, stability and thermal work remain open.
[`sfp_power_budget.json`](validation/sfp_power_budget.json) records the calculations
and their limits; [`sfp_supply_evidence.json`](../../design/sfp_supply_evidence.json)
records source provenance. PDFs are in `datasheets/`.

L1/L2 now use Coilcraft XGL4020-472MEC and L4 uses XGL4020-102MEC, with a local
footprint based on the recommended 0.98 × 3.4 mm lands and 2.37 mm centre spacing.
The filter inductor's maximum 25 °C DCR is 47.3 mOhm. Applying the manufacturer's
copper-temperature equation to a 165 °C part-temperature bound gives about
73.3 mOhm; adding a 20 mOhm hot-copper allocation fits the 100 mOhm branch budget.
This is a resistance estimate, not a thermal pass. Saturation figures are specified
at 25 °C; AC losses and hot saturation still need qualification.
[Coilcraft XGL4020](https://www.coilcraft.com/getmedia/76c9c081-4945-4c85-9129-9356e1ad6734/xgl4020.pdf),
[temperature equation](https://www.coilcraft.com/en-us/resources/application-notes/current-and-temperature-ratings/).

[`power_footprints.json`](validation/power_footprints.json) checks the saved pads,
numbering, copper/mask/paste layers and clearances against the drawings.
[Copper preview](validation/power_footprints.png) uses those reloaded coordinates.
The RPJ orientation follows the board-layout drawing, rotated 180 degrees relative
to the datasheet's pinout figure. The inductor stripe faces local pad 1, which is
SW for L4. Assembly yield and the eventual PCB layout are not validated by this
footprint check.

## Downstream port power

[`port_power.kicad_sch`](port_power.kicad_sch), [preview](validation/port_power.png),
implements four TPS2553DBVR switches with independent OUT rails, 23.2 kOhm/1%
current-setting resistors, input/output bypass, polarized 220 uF bulk capacitors,
and 1 kOhm discharge resistors. The datasheet table gives a 1.024–1.208 A limit
range at this setting. The design load is 900 mA per port plus the bleeder load.
[TI TPS255x datasheet](https://www.ti.com/lit/ds/symlink/tps2552.pdf), pp. 5, 7, 20.

An SN74LVC1G04DBVR inverts the VL813's active-low gang enable into the switches'
active-high enable. Input pullup R14 and output pulldown R15 establish the intended
off states at valid logic power and at VCC=0. Intermediate supply ramps require
testing. The inverter has partial-power-down support.
[TI inverter datasheet](https://www.ti.com/lit/ds/symlink/sn74lvc1g04.pdf), pp. 3–6.

The switches' four open-drain faults share HOC1. HOC2 is pulled inactive and
charging-enable output U1.42 is NC. This requires normal ganged hub operation;
firmware configuration and fault recovery must be tested with the actual hub.

`python design/check_port_power_budget.py` writes
[`validation/port_power_budget.json`](validation/port_power_budget.json).
For the stated DC corners, it calculates approximately 122 mV switch drop at
900 mA plus bleeder current, leaving 128 mV for traces/contacts above the chosen
4.75 V port floor when the board input is 5.0 V. J7 therefore now specifies
**5.0–5.2 V at the board under load**. A generic 5 V +/-5% adapter has not been
qualified. The port load alone is about 3.62 A; simultaneous current limiting can
reach 4.83 A, before adding hub/SFP demand. Supply, cable, jack rating and input
protection remain unselected.

The ideal unloaded discharge estimate is about 0.50 s to 0.8 V at maximum stated
RC. It assumes no external back-drive and does not replace a discharge or hot-plug
test. The calculations do not validate transient peaks, rail ramps, thermal
behavior, capacitor ESR/ripple, firmware, or USB compliance.

MPN, Manufacturer and Datasheet fields are stored on the selected IC symbols.
[`bom/bom.csv`](bom/bom.csv) is an **incomplete tracking BOM**, not an order file.
TI lists TPS2553DBVR as active, but its direct store showed unavailable stock;
distributor stock remains unchecked. The majority of passives/connectors are
still generic. Local PDFs are in [`datasheets/`](datasheets/); `TPS2552.pdf` is the
shared family datasheet covering the selected TPS2553 as well.

## Hub support sheet

[`hub_support.kicad_sch`](hub_support.kicad_sch), [preview](validation/hub_support.png),
adds a candidate circuit based on the supplied VL813 pin descriptions and the
schematic published by [GoodYuHuang](https://oshwhub.com/goodyuhuang/ji-yu-VL813de-USB3.0-HUBshe-ji).
This is an author's working USB hub design, not a VIA application note or a
measured reconstruction of the optical reference board. Provenance and decisions
are in [`design/hub_support_evidence.json`](../../design/hub_support_evidence.json).

- J7 provides the local regulated 5 V input. U1 pin 18 feeds the 3.3 V hub rail.
  U1 pin 39 drives a candidate 10 uH inductor; its output feeds the 1.2 V rail and
  pin 37. Supply inputs/output have 4.7 uF candidate capacitors, with two in parallel
  at the buck output. Part ratings, effective capacitance, ESR and regulator
  stability must be qualified. No SFP load is assigned to the hub's internal LDO.
- C20–C35 add 100 nF bypass capacitors for the sixteen 3.3 V/1.2 V supply pins.
  Each has a `Placement target` property naming its intended U1 pin; PCB placement
  and return paths remain to be implemented. A shared net does not prove proximity.
- Y1 bridges SSXI/SSXO at 25 MHz, with candidate 22 pF C0G load capacitors.
  The crystal itself, package pinout, load/stray capacitance, ESR and drive remain
  unselected. R9/C38 provide a 10 kOhm/1 uF reset RC starting point; reset timing,
  slow supply ramps, brownout and optical recovery remain unverified.
- **Pin 40 is deliberately unresolved.** The supplied datasheet lists pins 37
  and 40 as DC12FB. The published schematic connects pin 37 to the buck output
  but leaves pin 40 behind an unpopulated link described as reserved for VL812.
  The previous draft's automatic 37/40 tie has been removed. Resolve this against
  the actual reference hardware or a manufacturer application circuit before power-on.
- **R8 remains `BIAS_R_TBD`.** The published example uses 1 kOhm plus 5.1 kOhm,
  but the supplied datasheet gives no resistance. This is not enough to establish
  the intended manufacturer value. The existing board's nearby resistor marking
  and connectivity have not been conclusively identified.
- SMCLK/SMDAT pins 55/56 are NC because debug access is unused. Their descriptions
  are on supplied datasheet page 11: debug-only, nonstandard SMBus. The earlier pin
  contract's statement that their functions were undocumented has been corrected.

The three remaining power ERC errors concern the external 5 V feed, ground and
the 1.2 V rail after the passive inductor. No power flags were added in this draft.
The other four errors concern unfinished VBUS/presence and upstream
receive inputs. Passing the connected-net checks does not qualify analog operation.

## SFP support sheet

[`sfp_support.kicad_sch`](sfp_support.kicad_sch) is a child sheet of the main
schematic. See its [rendered preview](validation/sfp_support.png). Global SFP and
ground labels connect both sheets; other hub nets remain local.

- L1/L2 provide separate 4.7 uH branches from `SFP_3V3_FEED_PENDING` to VccT/VccR.
  Each branch has input/output 100 nF bypass and a 22 uF bulk capacitor in series
  with a damping resistor to ground. C10/C13 now use GRM32ER71E226KE15L and R1/R2
  use ERJ8RQFR43V (0.43 ohm, 1%, 0.25 W, 1206). Nominal resistor plus inductor DCR
  plus capacitor ESR is about 0.494 ohm at 15 kHz. This follows
  SFF-8431 D.17/Figure 56; the figure's test-source resistance is not a fitted part.
- R3/R4/R5 are 4.7 kOhm pullups for TX_FAULT, RX_LOS and MOD_ABS. R6/R7 are
  4.7 kOhm SDA/SCL pullups, initially assuming 100 kHz and at most 100 pF bus
  capacitance. Verify actual bus capacitance and rise time before increasing speed.
  Pullups use module-side supplies; controller I/O must avoid back-powering them.
- J6 exposes ground, VccT reference, SDA, SCL, MOD_ABS, RX_LOS, TX_FAULT,
  TX_DISABLE, RS0 and RS1 in pin order. It provides management access, not an
  implemented recovery controller. Its footprint is still unassigned. TX_DISABLE
  relies on the module's pullup and must be actively pulled low to enable TX;
  TX_DISABLE and rate-select pins are not permanently strapped.

Source: SFF-8431 sections 2.4.1–2.4.6, Table 21 and D.17/Figure 56, visually checked
against the retained PDF (Figure 56 is PDF page 114).
[SNIA reference](https://members.snia.org/document/dl/25891).

This is a reference-derived candidate circuit, not a measured reconstruction of
the working pair. Inductor current/saturation/DCR, effective capacitance and ESR,
damping resistance, supply accuracy/current, hot-plug response, noise and layout
remain to be qualified. The feed regulator is now on `sfp_supply.kicad_sch`.
The native XML checker verifies the damping branch topology and cross-sheet
pin mapping, not analog performance.

**The first passive-filter simulation exposes a transient gap.**
[`sfp_filter/report.json`](validation/sfp_filter/report.json) and
[response plot](validation/sfp_filter/filter_response.png) use KiCad's bundled
ngspice-46 DLL, an ideal 3.3 V source and an explicit load waveform: rise from
0 to 600 mA in 10 us, remain at peak for 35 us, then reduce to 450 mA.
The nominal model dips to **3.028 V**; two sensitivity cases reach 2.962/3.089 V.
All fall below 3.14 V. The module's unknown input capacitance and inrush shaping
are absent, so this is a failure under the assumed stress, not evidence that the
retained working pair fails. Resolve the real module load or redesign this filter
before treating it as qualified. DC allocation checks do not override this result.

Murata's current data gives about **15.2 uF effective capacitance and 20.6 mOhm ESR
at 15 kHz, 3.3 V and 25 C** for the nominal 22 uF part. The simulation uses a local
series-R/C approximation from that data. Constant ESR, sensitivity capacitances,
ideal input and omitted module/regulator dynamics limit the result. It does not
establish integrated SFF noise compliance or regulator loop stability.
[Murata product and data](https://pim.murata.com/en-us/pim/details/?partNum=GRM32ER71E226KE15%23),
[Panasonic resistor specifications](https://industrial.panasonic.com/ww/products/pt/current-sensing-chip-resistors/models/ERJ8RQFR43V).

Source responses, requests and numerical curves are retained under
`design/references/murata_*`; valid Murata PDFs and the 0 V/25 C SPICE model are in
`datasheets/`. The supplied capacitor model is not used as a 3.3 V model.
The Panasonic PDF download timed out; the selection uses the primary product
table and the PDF retrieved through web browsing. Local PDF and pulse capability
remain sourcing/qualification gaps. See `design/sfp_filter_evidence.json`.

## Optical interface decision still open

The user has now supplied a top photo of the existing unbranded PC-side adapter.
Its PCB marking is `123486S_Y171`, with a USB-A socket and SFP cage. The shared
marking prefix and similar power-area layout suggest a relationship to the hub,
but establish no signal nets. The cable mapping and optical module identities are
still unknown. The user confirms the receiver and hub were supplied together and
work; module markings are unavailable. Use that matched receiver/cable/module set
as the reference for the new board, with negotiated speed and recovery still to
be measured. See [receiver evidence and connection worksheet](../../design/receiver/README.md).

The SFP electrical specification describes data-agnostic modules, but support for
lower signaling rates is optional. A socket or a 10 Gb/s label therefore does not
establish USB link compatibility. Consult the exact module data and qualify the
link. SFF-8431 is archived and points to SFF-8418/8419 for its successors.
[SNIA SFF-8431 archive](https://members.snia.org/document/dl/25891).

The open interface must address USB receiver detection, LFPS, electrical idle,
5 Gb/s payload signaling, and fiber/module disconnect recovery. A patent disclosure
describes a direct optical approach with receiver-load emulation and coordinated
reset/transmitter control. This is useful architectural evidence, not validation
of this circuit, this photographed board, or an arbitrary SFP+ module.
[Technical disclosure CN107276675B](https://patents.google.com/patent/CN107276675B/en).

For that reason, `SSTX0_P/N` and `SSRX0_P/N` remain **separate** from
`SFP_TD_P/N` and `SFP_RD_P/N`. They are not connected through a fictitious bridge.

## Other pending circuits

- Hub power-component selection, input protection, rail budget, regulator stability,
  decoupling layout and pin 40 disposition. Do not infer supply function from
  `VCC12I`'s name; pin 20 remains grounded.
- Crystal selection/load/startup qualification and SSREXT value.
- Reset qualification, VBUSDET and EXTPWRON policy for a locally powered optical link.
- Port-power component/firmware/thermal/transient qualification and ESD/protection.
- SFP filter/regulator component selection and qualification, rate-selection
  policy and management/recovery controller. Filter topology and pullups now exist.
- Firmware/configuration and startup requirements; no flash image is available.
- Final footprints and PCB implementation. The VL813 footprint is a candidate
  carried forward from the reference project; connector footprints are unassigned.

The retained VL813 baseline is a legacy part: VIA lists it under EOL products.
That matters for a subsequent component selection decision; this draft does not
claim new-production availability. [VIA VL813](https://www.via-labs.com/product_show.php?id=81).

## Reproduce

The hub reset RC has been replaced by **U12 TPS3808G33DBVR**, monitoring
HUB_3V3. CT is open for the datasheet's fixed delay (12–28 ms under its test
conditions). R9 is now a 12.1 kOhm RESET pullup; C38 is now a 100 nF supply
bypass. J9 provides a manual/open-drain reset request, with R24 pullup.
`design/check_hub_reset.py` checks static thresholds and logic/current margins.
The design requires **HUB_3V3 >= 3.20 V steady** to guarantee release across the
chosen supervisor threshold/hysteresis bounds; this LDO condition still needs
qualification. It does not monitor 1.2 V or implement optical recovery. See
`validation/hub_reset_checks.json`. No dynamic reset or hardware pass is claimed.

The sixth sheet, [USB3 signal protection](usb3_esd.kicad_sch), adds U8–U11,
one TPD4E02B04DQAR per USB-A port. TX protection connects on the connector side
of C1–C8; RX protection shares the connector/hub nets. The 16 signal lines get
bidirectional TVS shunts, with all USB2 contacts still isolated. Pads 6/7/9/10
are internally NC and used for copper routing across the footprint, not an
internal signal bridge. Both ground pins connect to GND. VBUS/input protection
remains pending. See [selection and layout evidence](../../design/usb3_esd_evidence.json).

`design/build_esd_footprint.py` creates the local DQA footprint through pcbnew;
`design/check_esd_footprint.py` reloads its copper/mask/paste geometry. Run both
with KiCad Python. `design/plot_esd_footprint.py` renders the checked geometry.
The native XML checker checks all four arrays and the intended pair mapping.
No board ESD immunity or signal-integrity pass is implied; no nonlinear ESD
simulation has been run. The electrical draft still has 7 ERC errors and 20 warnings.

The later [filter comparison](../../design/sfp_filter_comparison.md) includes
an expanded 192-case passive study and a candidate that passes its stated
voltage/peaking screen. It has not been selected in this schematic because
noise attenuation and converter interaction remain unqualified. The original
4.7 uH filter's load-step failure remains open.

From the repository root, with system Python and KiCad's CLI:

```powershell
& 'C:\Program Files\KiCad\10.0\bin\python.exe' design\build_power_footprints.py
& 'C:\Program Files\KiCad\10.0\bin\python.exe' design\check_power_footprints.py
python design\plot_power_footprints.py
python design\build_electrical_draft.py
& 'C:\Program Files\KiCad\10.0\bin\kicad-cli.exe' sch export netlist kicad\usb3_sfp_hub\usb3_sfp_hub.kicad_sch --format kicadxml --output kicad\usb3_sfp_hub\validation\netlist.xml
python design\check_electrical_draft.py
python design\check_port_power_budget.py
python design\check_sfp_power_budget.py
python design\simulate_sfp_filter.py
& 'C:\Program Files\KiCad\10.0\bin\kicad-cli.exe' sch erc kicad\usb3_sfp_hub\usb3_sfp_hub.kicad_sch --format json --output kicad\usb3_sfp_hub\validation\erc.json
& 'C:\Program Files\KiCad\10.0\bin\kicad-cli.exe' sch export svg kicad\usb3_sfp_hub\usb3_sfp_hub.kicad_sch --output kicad\usb3_sfp_hub\validation\
```

The generator currently rebuilds this draft schematic. Make persistent edits in
the generator, or retire it before editing the schematic interactively. Its input
text extraction is `design/VL813_local_text.txt` from the supplied PDF.

The [full goal and completion criteria](../../design/GOAL.md) remain active.
