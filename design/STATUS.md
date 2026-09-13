# Board status — 2026-09-13

Naming here follows the user's description: **receiver** means the small PC-side
USB-to-fiber unit; **hub/transmitter** means the four-port remote unit. The optical
link is bidirectional, so these names do not imply one-way signal flow.

| Deliverable | PC-side receiver | Four-port hub/transmitter |
|---|---|---|
| Existing hardware | Supplied with hub and works as a pair, per user | Supplied with receiver and works as a pair, per user |
| Evidence | Top photo, enclosure photo, observation notes; no measured signal nets | Top/back photos and component placement model |
| Reconstructed schematic | None | Partial: 105 physical components on six sheets |
| Electrical PCB layout | None | None |
| Photo placement model | None | 61 footprints, approximate outline, no named nets or routed tracks |
| ERC | Not applicable without schematic | 7 errors and 20 warnings |
| Fabrication ready | No | No |
| New-board operation tested | No | No |

The hub schematic includes the VL813 pin mapping, four USB3-A ports and coupling
capacitors, candidate hub power/clock, a 3.3V reset supervisor with manual request,
switched port power, SFP supplies and
management access, and downstream signal ESD arrays. **The optical signal
interface remains open.** Bias/pin-40 decisions, control/firmware, protection and
power qualification also remain incomplete. The photo placement model is a
separate project and is not a routed version of this schematic.

On 2026-09-13 the unreferenced `kicad/usb3_over_optical_hub/` starting point was
removed and its VL813 (LCSC C69418) and SFP+ 20-pin (C42418480) symbols, footprint
and 3D models were salvaged byte-identically into `kicad/usb3_sfp_hub/libs/lcsc/`,
with provenance in `provenance.json`. This made no functional schematic change;
the electrical state below is unchanged.

The design is **USB3 only**. All ten hub USB2 data pins and all eight downstream
USB2 contacts are isolated in the current native netlist. No USB2 management
channel is being added. The existing receiver/cable/modules are the current
compatibility reference; no replacement receiver design has been reconstructed.

The user confirms the working pair is disconnected from this PC. The read-only
capture at 2026-09-12 09:08:09 UTC saw no active SuperSpeed connections and no
query errors. This tests the capture tool on the current PC only; it is not a
test of the disconnected optical pair. Hardware signal tracing still needs the
receiver underside/cable connections and negotiated-speed/recovery evidence.

Files:

- Hub schematic: `kicad/usb3_sfp_hub/usb3_sfp_hub.kicad_sch`
- Vendor library provenance: `kicad/usb3_sfp_hub/libs/lcsc/provenance.json`
- Photo model: `kicad/board_trace/board_trace.kicad_pcb`
- Receiver evidence: `design/receiver/README.md`
- USB3 capture: `design/receiver/capture_usb3.ps1`
