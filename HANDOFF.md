# HANDOFF — USB3-only hub over SFP+ and photo tracing

> **Historical document — superseded 2026-09-13.** The active objective and
> completion criteria now live in [`design/GOAL.md`](design/GOAL.md), with
> [`design/STATUS.md`](design/STATUS.md) as the current-state snapshot. This file
> is retained for session history only; do not use it as the source of truth.

## Active goal continuation — electrical design

**Latest continuation — board_trace real-part fit (2026-09-13):** on the photo
placement model, the provisional barrel-jack proxy was replaced by the real XKB
**DC-005-2.5A-2.0** (LCSC C319099) as J4, and the adjacent bulk capacitor C51 was
downsized from a D8.0 to a D5.0 mm radial can so it clears the longer jack body.
`placement_plan.json` now lists 62 parts (the CND-tek C5441174 SFP cage had never
been added back to the plan); `06_check_saved.py` passes again, and native DRC is
283 violations (128 errors, 155 warnings), 0 unconnected, no tracks or named nets.
This is better than the 322-violation pre-jack board, mainly because the smaller
C51 silkscreen removes 37 silk warnings. This is placement evidence only and makes
no hub electrical change; hub J7 remains `input TBD`.

**Latest continuation — hub reset supervisor:** current hub draft is now
**105 physical components on six sheets**. U12 TPS3808G33DBVR replaces the
former reset RC with a 3.3V supervisor: DBV pins 1 RESET_N, 2 GND, 3 MR_N,
4 CT intentionally NC, 5 SENSE and 6 VDD to HUB_3V3. R9 changes to 12.1k/1%;
C38 changes from 1uF on RESET to 100nF across U12 supply. J9 pins 1/2 provide
MR/GND manual or external open-drain reset request; R24 is its 10k pullup.
TPS3808.pdf is current TI SBVS050N (August 2026), with source pin page rendered.

`design/check_hub_reset.py` passes static allocations: falling threshold
3.024–3.116V; conservative maximum release threshold 3.194V. Require steady
HUB_3V3 >=3.20V and verify LDO tolerance under load. RESET high worst DC level
2.874V exceeds VL813 VIH=2.0V; sink-current bound 0.311mA is within U12's 1mA
VOL test. CT-open delay is 12–28ms under TI test conditions, not a measured board
timing guarantee. Core 1.2V validity, power sequencing, fast brownouts, clock
readiness and optical recovery remain unqualified. Supplied VL813 document
does not give minimum reset delay/complete sequencing requirements.

Native connectivity passes including 18 USB2 isolated contacts. ERC remains
7 errors /20 warnings; no PCB changed. Six previews, analyzer, and 35-line
tracking BOM refreshed. Classification: progress; full board goal incomplete.

**Latest continuation — optical evidence and USB3 capture:** the user reiterated
USB3 only and confirmed the working pair is disconnected from this PC. They also
asked for status of both boards; `design/STATUS.md` gives the exact inventory:
no receiver schematic/PCB, partial 102-component/six-sheet hub schematic, and
a separate 61-footprint photo model with no named nets/tracks. Neither is ready
to fabricate. Keep the full goal intact; reusing the working receiver remains
the current compatibility baseline, not a completed receiver redesign.

`design/optical_reference_audit.md` records the newly inspected patent drawings:
the Rx.Detect figure is a block, not a component circuit. Its dual-controller
and USB2-management architecture is not established for the user hardware and
the USB2 channel must not be imported. The receiver underside is still absent.

A native Windows read-only capture tool is now in `design/receiver/`:
`build_usb3_capture.cmd`, `usb3_capture.cpp`, `capture_usb3.ps1`. It builds with
the installed VS2019/Windows SDK and classifies actual EX_V2 operating-speed
flags separately from capabilities. Self-tests pass. The saved capture
`captures/20260912T090809182Z.json` queried 3 hubs / 32 ports without errors and
saw zero active USB3 links. The pair was disconnected: this is NOT evidence of
kit failure or success. No schematic/PCB changes occurred in this continuation.
Classification: progress — source audit and a tested measurement tool completed;
actual optical-interface and end-to-end hardware evidence are still missing.

**Latest continuation — USB3 signal ESD (2026-09-12):** the authoritative draft
now has **102 physical components on six sheets**. `usb3_esd.kicad_sch` adds
U8–U11 TPD4E02B04DQAR, one four-channel bidirectional array per downstream port.
TX shunts are on the connector side of C1–C8; RX shunts share connector/hub nets.
Both ground pins connect. Internally-NC pads 10/9/7/6 share the respective
signal nets for physical copper routing across pairs 1-10/2-9/4-7/5-6; they do
not provide an internal signal path. All 18 USB2 contacts remain isolated.

Primary TI datasheet and rendered pin/land-pattern pages are in project
`datasheets/`. `design/build_esd_footprint.py` creates native local DQA0010A
copper/mask/paste (ground pad paste is smaller); `check_esd_footprint.py` reloads
and checks geometry, and `plot_esd_footprint.py` renders it. The standard KiCad
USON footprint was inspected but not selected because its dimensions differ
from the TI example. TPD4E05U06 PDF is an evaluated alternative, not a BOM part.
Native connectivity and footprint checks pass stated scope; ERC remains
7 errors / 20 warnings. All six SVG/PNG previews, analyzer and 33-line tracking
BOM are refreshed. `design/usb3_esd_evidence.json` records the source and limits.
No PCB was changed. VBUS/input protection, board SI/ESD testing and the original
optical/power/clock/firmware gaps remain open. Full objective is incomplete.

**Latest continuation — passive filter comparison (2026-09-12):** see
`design/sfp_filter_comparison.md`. Three finalists received 64 transient and
32 unloaded AC runs each, covering independent sensitivity combinations.
0.11 uH with two parallel 22 uF bulk capacitors sharing one 0.100 ohm damping
resistor passes the stated passive screen: 3.1524–3.4325 V, maximum 2.36 dB AC
peak. The 0.068 ohm finalists fail the expanded peak screen. The 3 dB ceiling
is an engineering screen, not an SFF requirement. The passing candidate has
little 100 kHz attenuation, so it has NOT been promoted into the schematic.
Original filter failure remains open; design stays at 98 physical components.
Reproduction: `design/qualify_sfp_filter_candidates.py`; results/netlists/plot:
`kicad/usb3_sfp_hub/validation/sfp_filter_comparison/corners/`.

TI's PSpice converter model was downloaded into
`design/references/tps62902_models/`; it is encrypted and cannot run as a
supported ngspice model. No PSpice/SIMPLIS executable was located in the checked
locations. Converter stability, shared-rail transients, startup and weighted
noise remain untested. Do not equate the candidate passive pass with hardware
qualification or keep tuning to one assumed waveform. Continue independent
clock/protection work while these tests and the optical-interface evidence
remain unresolved. No schematic, BOM or PCB was edited in this continuation.

The full goal is **a board offering a USB3 hub (no USB2) over SFP+**. It is not
complete. Read `design/GOAL.md` for completion criteria and current evidence.

A new project, `kicad/usb3_sfp_hub/`, now contains a connected downstream electrical
draft: VL813, four USB-A ports, eight TX coupling capacitors, and an SFP socket.
Native XML checks prove the implemented signal mapping and deliberate isolation
of all ten hub USB2 pins plus eight connector USB2 contacts. The schematic also
correctly grounds VL813 pin 20 and leaves pins 21/57 NC. See its README and
`validation/connectivity_checks.json` for scope and reproduction commands.

**2026-09-12 electrical update:** a second sheet, `sfp_support.kicad_sch`, adds
separate 4.7 uH VccT/VccR filter branches, input/output bypass, damped 22 uF bulk
capacitors, five management pullups and a ten-pin management access connector.
That update added 30 physical components. The damping resistors await selection
against inductor DCR and capacitor ESR; the feed regulator and control logic are
unimplemented. Source: SFF-8431 D.17/Figure 56, low-speed sections and Table 21.
This is a reference-derived candidate, not a photo-confirmed circuit. The updated
native XML checker passes topology and cross-sheet mapping checks, including all
18 isolated USB2 contacts. Both SVG/PNG previews were regenerated.

**Later 2026-09-12 hub support update:** the third sheet `hub_support.kicad_sch`
brings the design to **59 physical components**. It connects U1.18 to HUB_3V3,
U1.39 through a candidate 10 uH inductor to HUB_1V2/U1.37, regulator capacitors,
16 per-pin bypass capacitors, a 25 MHz crystal/22 pF candidate load network and
10 kOhm/1 uF reset RC. J7 is the local 5 V input; protection and total budget remain
pending. Values/topology use the supplied pin descriptions and GoodYuHuang's
published USB hub schematic, NOT a manufacturer application note. See the project
README and `design/hub_support_evidence.json` for source hashes and limitations.

U1.40 is now an isolated pending net: the datasheet and published application differ
on its use, so the old automatic U1.37/40 tie was removed. R8 bias resistance remains
TBD. Debug-only pins 55/56 are now NC; their functions were found on datasheet page
11 and the pin contract was corrected. The native netlist checks pass across all
three sheets, with USB2 isolation preserved. All three previews were regenerated
and visually inspected. No PCB was edited in either electrical-support update.

**Latest 2026-09-12 port-power update:** `port_power.kicad_sch` adds four
TPS2553DBVR switches, independent output rails, shared open-drain fault reporting
to HOC1, and SN74LVC1G04DBVR to invert the hub's gang enable. HOC2 is pulled high;
unused charging-enable pin 42 is NC. Each output has polarized 220 uF bulk,
bypass and a 1 kOhm discharge path. 23.2 kOhm/1% ILIM settings give the datasheet
range 1.024–1.208 A. The design now has **89 components on four sheets**.
The native net checks and `design/check_port_power_budget.py` pass their stated
scope. J7 now requires 5.0–5.2 V at the board under load to retain port-voltage
margin; connector/adapter total capacity and input protection remain unresolved.
Datasheets are in `kicad/usb3_sfp_hub/datasheets/`. Selected IC properties feed
`bom/bom.csv`, an incomplete tracking BOM (no ordering/stock qualification).
DC checks do not establish transient, firmware, thermal or hardware operation.

**2026-09-12 SFP supply update:** `sfp_supply.kicad_sch` adds TPS62902RPJR,
1 uH candidate L4, 10/22 uF supply capacitors, 10 nF soft-start, 32.4 kOhm MODE
selection and PG test access. The draft now contains **98 components on five
sheets**. SFP_3V3_FEED connects both filters to an independent 3.3 V regulator;
the hub LDO remains separate. VSET pin 9 is intentionally open for 3.3 V, not GND.
MODE selects forced PWM/2.5 MHz/discharge. EN follows local 5 V; PG drives no
control logic. See `design/sfp_supply_evidence.json` and the project README.
`design/check_sfp_power_budget.py` checks stated allocations, not actual hardware:
0.10 ohm maximum hot branch resistance plus 50 mV low-frequency disturbance leaves
8.75 mV low-side margin at 600 mA per branch. Regulator footprint, L/C parts,
filter damping/stability, thermal and startup qualification remain open. Native
connectivity and both budget checks pass their limited scope; ERC remains 7 errors
and 20 warnings. All five previews and the incomplete tracking BOM were refreshed.
The TPS62162 PDF is an evaluated alternative, not a selected BOM part.

**2026-09-12 power footprint/inductor update:** U7 now has a native local RPJ
footprint transcribed from TI's land pattern (nine pads, longer pads 4/6, no extra
EP). L1/L2 use Coilcraft XGL4020-472MEC, L4 uses XGL4020-102MEC, all with a native
local XGL4020 footprint. `design/build_power_footprints.py` generates only these
library parts; it changes no PCB. `design/check_power_footprints.py` reloads and
checks pad geometry/layers/mask settings, and `design/plot_power_footprints.py`
renders their saved copper. Run the first two with KiCad's Python. The electrical
generator assigns the local `power` library and selected MPNs, and the tracking
BOM is refreshed. Component count stays 98. Estimated filter hot DCR plus a
20 mOhm copper allocation is 93.3 mOhm, inside the 100 mOhm branch requirement.
Native footprint/connectivity and DC allocation checks pass their stated scope;
capacitor choice, damping, filter/regulator dynamic behavior and hot saturation
remain unqualified. See `design/sfp_supply_evidence.json` for source hashes.

**2026-09-12 filter selection/simulation update:** C10/C13 now use Murata
GRM32ER71E226KE15L (22 uF/25 V/X7R/1210), R1/R2 use Panasonic ERJ8RQFR43V
(0.43 ohm/1%/0.25 W/1206). Murata moved its site: old PDF endpoints fail; current
public product/characteristics API responses and valid PDFs are retained. The
frequency data at 3.3 V/25 C gives approximately 15.2 uF and 20.6 mOhm at 15 kHz.
Nominal damping sum is 0.494 ohm. Panasonic local PDF downloads timed out; primary
product table and web-fetched PDF support the part selection, pulse rating open.

**New analog gap:** `design/simulate_sfp_filter.py` uses KiCad's existing ngspice-46
DLL through `design/ngspice_shared.py`. Native analyzer was run first; the explicit
testbench checks its topology against native XML. With an ideal 3.3 V feed, no
module input capacitance and a 0-to-600mA/10us rise, nominal output dips to 3.028 V
(sensitivity cases 2.962/3.089 V), below 3.14 V. This is a stated stress-model
failure, not a hardware test of the user pair. See validation/sfp_filter/report.json,
plot and saved netlists/data. Do not treat earlier passing DC budgets as a transient
pass. Resolve module inrush/input C or revise the filter. Capacitors C52/C53 and
converter closed-loop behavior remain unfinished. Component count remains 98.

**Still incomplete:** optical physical interface, power/decoupling, clock/bias,
reset/VBUS, protection, SFP management, firmware, PCB, and hardware verification.
The SFP TD/RD nets are deliberately separate from hub upstream TX/RX pending
Rx.Detect/LFPS/idle/recovery qualification. Native draft ERC: 27 findings (7 errors,
20 warnings), not a pass. Power/clock/filter parts and dynamic behavior remain unqualified.

**Receiver update:** the user supplied `photos/recieve_top.png` and described an
unbranded SFP+-to-USB-female PC-side adapter. Photo marking `123486S_Y171` shares
the hub's `123486S` prefix; similar power-area components suggest related designs,
but no electrical connection or IC identity is established. See
`design/receiver/README.md`, annotated photo, observation JSON and blank connection
worksheet. `design/inspect_receiver.py` reproduces those artifacts. The user now
confirms the receiver and pictured hub came together and work; module markings
are unavailable. Retain the existing receiver, cable and modules as the working
reference pair (user-reported). Module models and actual cable wiring remain unknown;
negotiated speed and recovery have not been independently measured. The USB-A
socket means the cable mapping must be included before assigning host TX/RX.
Do not infer hidden circuitry is absent or promote this photo into a netlist.

**Mechanical update:** `photos/external view.png` shows the two enclosed units;
the user states they are the same size. Treat enclosure size as equal, with absolute
dimensions and internal PCB sizes still unmeasured. Visible panel labels include
`PC-USB3.0 Port`, `DC 5V`, and `TX`/`RX`. Do not infer which PCB owns the lower
visible panel solely from the stacked photo, or rescale the trace PCB from it.

The original sibling hub schematic was checked and contains only two unconnected
symbols. `default.json` adds ground annotations only, not a reusable signal netlist.
The photo-trace work below remains useful reference evidence and was preserved.

`design/build_electrical_draft.py` creates the new schematic and typed library;
`design/check_electrical_draft.py` independently checks KiCad's exported netlist.
No traced PCB files were modified during this electrical-design continuation.

Updated 2026-09-12 after filter selection and passive SPICE stress analysis. Earlier handoff is in git history.

## Current deliverable

`kicad/board_trace/board_trace.kicad_pcb` now contains **61 footprints**, two
unchanged embedded photo references, and a closed, approximate photo-traced outline.
This is an **unrouted reverse-engineering placement model**, not a working circuit.
There are no named nets or tracks; `board_trace.kicad_sch` is still an empty stub.

The board was already tracked when this continuation began (the old handoff's
"untracked" statement was stale). Current edits are uncommitted. A pre-existing
change to the sibling project's `.kicad_prl` was left alone.

KiCad PCB Editor was open on this board during the work. Reopen the saved file to
load these disk changes; the existing editor view may still show the earlier board.

## What changed

- J1/J2 fitted to **all 22 visible joints each** on the bottom photo, with no
  mirroring or scale change. J1 moved about 1.11 mm right; J2 needed a small nudge.
  Independent checks on reloaded pad coordinates: RMS **0.0749/0.0715 mm**,
  maximum **0.2158/0.1607 mm** respectively. These measure photo-fit error,
  not physical manufacturing accuracy or electrical pinout correctness.
- Replaced individual-pad/silkscreen detections with manually reviewed component
  centers. Existing valid references were retained; `placement_plan.json` records
  every retired reference and why it was retired.
- C52 was a **barrel power jack**, now J4. C32–C34 were that jack's solder tabs,
  not bottom-side passives. J4 uses a local provisional photo footprint.
- C51 changed from SMD to a radial through-hole electrolytic, aligned to its two
  back-photo joints. Diameter, capacitance, height, and polarity remain uncertain.
- C50 became **provisional D1**: a molded, banded two-terminal part marked `KE`.
  A diode is inferred; exact type and polarity are not established. SMB is a proxy.
- Added missed MLCCs, 11 resistor candidates, L2/L3, five-pin U2, and two LEDs
  with bent leads (D2/D3). Printed resistor codes are stored as `MARK:...`, not
  silently promoted to measured resistance values.
- All nonstandard source footprints are now local to this project, with an
  `fp-lib-table`; J3/U1 no longer depend on the sibling project's paths.
- The old generator's manual image S-expression injection was removed.
  Board and new footprint writes now use KiCad's native pcbnew API exclusively.

## Inventory and evidence

| Group | Count | Status |
|---|---:|---|
| MLCC candidates | 36 | Generic 0603 proxy; unknown values |
| Radial electrolytic C51 | 1 | Through-hole joints visible; polarity unknown |
| Resistor candidates R1–R11 | 11 | Printed codes retained; R9 uses 1206 proxy |
| Connectors J1–J4 | 4 | USB/SFP candidates and traced barrel jack |
| Inductors L1–L3 | 3 | Size proxies; L1 adjacent silk reads 10uH |
| D1 and LEDs D2/D3 | 3 | D1 type and all polarities uncertain |
| ICs U1/U2 | 2 | U1 VL813 candidate on back; U2 unidentified SOT-23-5 |
| Crystal Y1 | 1 | 25.000 MHz visible; pin functions unverified |

Each footprint includes hidden `Trace confidence`, `Trace evidence`, and
`Trace source` fields. These fields distinguish photo observations from package
or identity assumptions. There are no confirmed manufacturer part selections.

## Geometry and images

- **Preserve user orientation:** top unchanged, bottom uses the existing mirrored,
  pre-aligned `board_bottom-gimp.jpg` copy. Do not apply another mirror.
- Both embedded images remain pixel-identical to `images/*.png`, at **148.5,105 mm**,
  native image scale **0.455365**, **25.9375 px/mm**, frame **1030 × 1601 px**.
- Front image: `Dwgs.User`; bottom image: `Cmts.User`. Toggle those layers to view
  the corresponding reference. Local image opacity was previously 0.45.
- `x_mm = 148.5 - 1030/(2*25.9375) + x_px/25.9375`;
  `y_mm = 105 - 1601/(2*25.9375) + y_px/25.9375`.
- The aligned top image is essentially a crop of `photos/board_top.jpg` with
  offset **(-247,-183) px**, established by SIFT/RANSAC registration. It clips
  actual board edges. The old 39.711 × 61.725 mm figure describes the image frame,
  not a physically measured board size.
- Edge.Cuts now follows approximate full-photo corner picks, transformed into
  the crop frame: `(8,17), (1032,8), (1040,1626), (-16,1622)` px.
  The resulting quadrilateral retains camera perspective; do not fabricate from
  these dimensions. The mounting hole and SFP cage mechanics are not yet modeled.

## Validation and remaining issues

See `kicad/board_trace/review/PLACEMENT_REVIEW.md` and the two `overlay_*.png` files.
Structural checks passed: 61 unique refs, no retired refs, closed four-segment
outline, unchanged image pixels/scale/location, no tracks/named nets, and all
**77 U1 pads on B.Cu only** (76 perimeter contacts plus exposed pad).

Native KiCad DRC ran and reported **287 violations (112 errors, 175 warnings)**.
It did **not** pass. No unconnected-item findings are expected on a board with no
named nets and do not demonstrate connectivity. Do not relax rules to hide these
findings just to make the tracing project appear ready for fabrication.

Important unresolved items:

1. **U1 package/pad fit and pin-1 orientation.** The inherited QFN rows sit inward
   of some visible photo terminations. Check local image registration/scale and
   the package drawing before changing its physical dimensions or assigning nets.
2. **J3 contact rows and footprint.** Locating pegs fit, but contact rows do not
   fully coincide with visible joints. The inherited locating pads are modeled as
   PTH with zero annulus, generating DRC findings. Verify actual peg/hole type.
3. **Unknown component identities and pinouts:** U2, D1, jack, LEDs, crystal and
   polarized capacitor. Stock footprint numbering is not verified board pinout.
4. **Approximate packages:** J4 slots/drills, inductor sizes/heights, radial can,
   bent LED bodies. Dense stock courtyards overlap; no fabrication fit is claimed.
5. **Remaining mechanical work:** cage footprint/mounts, board mounting hole,
   physical board dimensions, and the unpopulated two-pad site near `(320,977)`.
6. **Electrical reconstruction:** identify power parts and trace continuity before
   creating a connected schematic. The sibling project may supply candidate
   symbols, but its topology must not be assumed to match this board.

## Reproduce / continue

Windows KiCad 10.0.5 binaries: `C:\Program Files\KiCad\10.0\bin\`.
System Python provides numpy/PIL/cv2; KiCad Python provides pcbnew/PIL.
No Konnect MCP tools were available; native pcbnew editing was already authorized
in the earlier session and was continued here. Never hand-edit PCB S-expressions.

The authoritative manual inventory is in `scripts/04_review_plan.py`, which emits
`placement_plan.json`. To make a persistent placement change, edit that inventory.
`placement.json` and `verify_boxes.json` are generated outputs.

```powershell
python kicad\board_trace\scripts\04_review_plan.py
& 'C:\Program Files\KiCad\10.0\bin\python.exe' kicad\board_trace\scripts\02_place.py
& 'C:\Program Files\KiCad\10.0\bin\python.exe' kicad\board_trace\scripts\03_verify.py
python kicad\board_trace\scripts\05_overlay.py
& 'C:\Program Files\KiCad\10.0\bin\python.exe' kicad\board_trace\scripts\06_check_saved.py
& 'C:\Program Files\KiCad\10.0\bin\kicad-cli.exe' pcb drc kicad\board_trace\board_trace.kicad_pcb --format json --output kicad\board_trace\review\drc.json
```

`02_place.py` uses the committed board as its **native reference-image seed**.
It preserves those image objects, rebuilds managed footprints/Edge.Cuts, checks a
temporary saved board, then replaces the target. It saves timestamped backups in
`review/backups/` (git-ignored), and refuses rebuilding if routing, named nets, or
unknown references have been added. Rework this generator before electrical design
begins; it is intentionally for the placement-only phase.

`01_detect.py` is now historical exploratory detection, not the placement source.
Its old exclusions and temporary-output path should not be used for the cleaned
inventory. EasyEDA fetch/conversion scripts also retain their old external temp
paths; do not rerun unless intentionally rebuilding and validating that footprint.
