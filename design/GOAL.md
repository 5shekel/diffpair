# USB3-only hub over SFP+ — active objective

User objective: **"is to have a board that offer usb3 hub (no usb2) over sfp+"**.
This objective is not complete. A photo placement model, an ERC result, or a pin
map is not evidence of a working optical USB hub.

## Working design intent

- One optical upstream link in an SFP+ socket, feeding a SuperSpeed hub.
- Four downstream USB-A ports, following the photographed four-port board and
  existing VL813 choice. Four ports and 5 Gb/s are working assumptions from those
  references, not additional user requirements.
- No USB2 data path: omit upstream/downstream D+/D- wiring. A dual-bus hub IC may
  contain USB2 circuitry internally, but no USB2 transport is being implemented.
- Remote board locally powered; optical fiber carries no VBUS. Port power,
  upstream presence and disconnect/reset policy still need an explicit design.
- The existing host-side endpoint is unbranded; the user supplied its top photo
  (`photos/recieve_top.png`), showing a USB-A socket and SFP cage. Its observed PCB
  marking is `123486S_Y171`. The user confirms the receiver and hub came together
  and work. Reuse that matched receiver/cable/module set as the compatibility
  baseline. Module markings are unavailable; wiring and negotiated-speed evidence
  remain to be recorded. See `design/receiver/README.md`.

## Authoritative artifacts

| Artifact | What it proves | What it does not prove |
|---|---|---|
| `kicad/board_trace/` | Photo placement and geometry observations | Connectivity or operation |
| `kicad/usb3_sfp_hub/libs/lcsc/` | Salvaged VL813 and SFP+ vendor symbols, footprint and 3D models, with provenance in `provenance.json` | Component qualification; import geometry not independently checked |
| `kicad/usb3_sfp_hub/usb3_sfp_hub.kicad_sch` | New connected downstream electrical draft | A complete circuit or optical bridge |
| `kicad/usb3_sfp_hub/sfp_support.kicad_sch` | Selected filter L/bulk C/damping R, management pullups and access connected across sheets | Qualified analog behavior or link controller; illustrative SPICE load-step fails voltage target |
| `kicad/usb3_sfp_hub/sfp_supply.kicad_sch` | Independent 3.3 V regulator, selected inductors/local land patterns, soft-start and PG test access connected to the filters | Selected capacitors, actual voltage margins, stability, thermal or startup qualification |
| `kicad/usb3_sfp_hub/hub_support.kicad_sch` | Candidate hub supply, decoupling, clock and reset topology | Analog qualification, resolved pin 40/bias, complete power or recovery policy |
| `kicad/usb3_sfp_hub/port_power.kicad_sch` | Current-limited outputs, gang enable and fault aggregation | Firmware, supply/transient/thermal or USB compliance validation |
| `design/vl813_pin_contract.json` | Source-linked pin names and proposed dispositions | Full datasheet extraction or board-level validation |
| `kicad/usb3_sfp_hub/validation/connectivity_checks.json` | Implemented nets match stated draft checks | Hardware functionality |

## Completion requirements and current evidence

| Requirement | Required evidence | Current state |
|---|---|---|
| USB3 hub | Hub enumerates at SuperSpeed; multiple devices operate concurrently | Not tested; draft only |
| No USB2 | Netlist/PCB D+/D- isolation, plus enumeration/behavior checks | Draft netlist has 18 isolated USB2 contacts; PCB and hardware unverified |
| SFP+ upstream transport | Documented reference interface and successful end-to-end tests with retained peer/modules | Existing matched pair works per user; new board physical interface not implemented |
| Link training and recovery | Cold boot, host reboot, module/fiber hot plug, one-way loss, U-state wake tests | No hardware evidence |
| Usable board | Complete power/protection/clock/reset/configuration; matching schematic and routed PCB | Incomplete |
| Electrical correctness | Datasheet-checked design, resolved ERC/DRC, appropriate SI/power checks | Native draft ERC fails on pending circuits |
| Working end state | Built board transfers integrity-checked data over the optical link | No build/test evidence |

## Immediate work

Current draft after reset update: 105 components on six sheets. U12 supervises
3.3V and J9 exposes manual/open-drain reset. Static logic/threshold checks pass;
the 3.3V LDO must meet a new >=3.20V steady requirement for reset release.
Core-rail sequencing and optical recovery remain open. This is progress toward
the hardware design, not proof of a working board.

Latest implemented change: U8–U11 provide USB3 signal TVS shunts on all four
downstream ports, with a native local DQA footprint. The current draft contains
102 components on six sheets. Pin/net and footprint geometry checks pass their
limited scope; VBUS/input protection and board SI/ESD testing remain pending.
This continuation is **progress**, not completion: the optical front end and
hardware remain unimplemented/unverified.

Latest passive filter comparison is documented in `sfp_filter_comparison.md`.
An alternative 0.11 uH / two 22 uF / 0.100 ohm branch passes the expanded
passive sensitivity screen, but noise attenuation and converter-loop behavior
remain unqualified. It is not selected in the schematic. TI's retrieved model
is encrypted for PSpice and was not run. Preserve the original filter failure;
independent clock/protection work can proceed without repeating passive tuning.

1. Trace the supplied working reference pair and its cable; retain its receiver and
   optical modules for initial compatibility tests. Record module identity if it
   later becomes available; establish the interface from circuit evidence and
   measured behavior. Do not join hub USB pins to SFP pins merely
   because both use differential pairs.
2. Complete hub clock/bias, supplies/decoupling, reset/VBUS policy, port power and
   protection. The VL813 local datasheet does not provide all application values.
3. Implement and qualify the optical front end and its recovery control.
4. Complete the electrical schematic, then transfer checked nets into a new routed
   design. Preserve the photo-trace project as evidence, not as a fabricated board.
5. Resolve checks and perform the end-to-end hardware tests above.

Previous goal continuation classification: **progress** — inductors and native
power footprints were selected and checked. This continuation selected filter
capacitors/damping resistors from current primary data and ran passive SPICE.
It exposed a voltage dip below the target for an explicit assumed load step;
the filter therefore remains unqualified despite passing connectivity/DC checks.
The design now has 98 components across five sheets; native ERC reports 7 errors
and 20 warnings. Connectivity/DC checks pass their stated scope. The full objective
remains incomplete and no working new-board claim is made.

Latest continuation classification: **progress** — expanded passive comparison
completed (192 transient runs plus 96 AC sweeps), with circuit-algebra checks.
One candidate passes the explicit sensitivity screen; it remains outside the
schematic pending noise and converter interaction checks. The downloaded TI
converter model is encrypted and was not run. This is not a completed board.
