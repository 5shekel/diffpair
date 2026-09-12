# PC-side receiver evidence

**Current status:** no reconstructed receiver schematic or PCB exists. The user
confirms the working pair is disconnected from this PC. See
[`design/STATUS.md`](../STATUS.md) for the status of both units. USB2 support is
not part of the new design, including any optional management channel.

## Read-only USB3 connection capture

`usb3_capture.cpp` queries Windows hub interfaces with three GET IOCTLs and
records only active SuperSpeed connections. It requests zero data access when
opening hub handles. It performs no port reset, port cycle, configuration
change, payload transfer, or serial-number request. Other attached devices
are counted but omitted from the connection list. Hub indices are local to a
single capture and must not be treated as persistent topology identities.

Build and run from the workspace root:

```powershell
.\design\receiver\build_usb3_capture.cmd
.\design\receiver\build\usb3_capture.exe --self-test
.\design\receiver\capture_usb3.ps1 -Label 'working_pair_connected'
```

The build script uses the detected Visual Studio 2019 Community installation
and installed Microsoft Windows SDK. Captures get unique UTC timestamps in
`captures/`, with source/executable hashes and an operator label. The label
does not itself prove the kit was connected. Nonzero query-error counts make
a capture incomplete. The operating-speed flags come from
[Microsoft's EX_V2 interface](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/usbioctl/ns-usbioctl-_usb_node_connection_information_ex_v2).
The older EX speed field alone cannot establish SuperSpeed, as explained in
[Microsoft's EX documentation](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/usbioctl/ns-usbioctl-_usb_node_connection_information_ex).
Capability flags, bcdUSB and port support are not substitutes for operating speed.

The initial run passed classification self-tests and queried 3 hub interfaces /
32 ports without errors. It reported **zero active USB3 connections**, with the
reference pair disconnected as confirmed by the user. This exercises the capture
mechanism but does not validate a positive physical USB3 connection, identify
the optical kit, or measure throughput/recovery. Capture the working pair before
using this tool's output as a baseline for the new board.

The user identified this as the existing unbranded receiver, with an SFP+ port
and a USB female socket connected by cable to the PC. Source:
[`photos/recieve_top.png`](../../photos/recieve_top.png). The user confirms that the
receiver and pictured hub came together and work. Treat them as a **working matched
reference pair (user-reported)**. Module markings are unavailable; PC-end connector
type and cable wiring remain unknown. No negotiated-speed capture has been supplied.
This replaces the earlier assumption that no host-side adapter information exists.

The user also supplied an [external view](../../photos/external%20view.png) and
confirms both units are the same size. Record this as **equal enclosure size,
user-reported**; no absolute dimensions or equal internal PCB dimensions are
established. The upper visible panel reads `PC-USB3.0 Port`; the lower visible
panel shows `DC 5V`, a barrel input, TX/RX indicators and an optical module with
TX/RX labels. No module model marking is visible. The stacked arrangement alone
does not establish that the lower panel belongs to the photographed PC-side PCB.
Keep physical dimensions and panel-to-board association separate from electrical
pin assignments when reconstructing the design.

See [annotated photo](annotated_top.png), [observations](observations.json), and
[enlarged power area](power_detail.png). Run `python design/inspect_receiver.py`
to reproduce these artifacts. Letter labels are observation regions, not schematic
references. The script preserves the supplied photo and records its SHA-256 hash.
It also preserves an existing connection worksheet so entered measurements are
not overwritten when regenerating the images.

## What the photo establishes

- **High confidence, visual:** the PCB marking reads `123486S_Y171`. The hub photo
  reads `123486S_Y167-230605`. Their shared prefix is observable; a common design
  family is a **medium-confidence inference**, not a manufacturer identification.
- **High confidence, visual:** a USB-A-shaped socket, SFP cage, five-pin IC,
  `1R0`-marked resistor and two leaded LEDs are present. Four smaller resistors
  appear marked `331` (**medium confidence**). Values have not been measured.
- **Medium confidence, visual:** two magnetic components with adjacent ceramic
  capacitor candidates resemble the hub's SFP-area network. The five-pin IC may
  be a regulator, but its marking, pinout and output voltage are unknown. A shared
  appearance is insufficient to copy a power circuit or select a replacement IC.
- No large controller is visible in the exposed top area. The underside and
  regions under both metal shells are not visible. This cannot establish that the
  complete receiver lacks active signal-conditioning or control circuitry.

## Consequence for the design

Retain this receiver, its cable and the existing optical modules as the compatibility
baseline for the new hub. Missing module markings do not invalidate the reported
operation or prevent tracing the reference circuit. They do prevent selecting an
equivalent replacement from a model number alone. A direct optical USB
path remains a hypothesis, with the cable and module pair included in the system.
The photo does not establish an Ethernet transport or prove USB receiver detection,
LFPS, electrical idle, or disconnect recovery. Keep the draft hub's upstream USB
and SFP signal nets separate until the actual interface is established.

The receiver's Standard-A socket also makes the cable mapping significant. If the
PC end is Standard-A, do not assume a same-number cable or that it carries VBUS.
USB-IF's USB 3.0 cable compliance document, section 4.10.1.1 (PDF page 20), says
the defined A-to-A assembly does not interconnect VBUS or the USB2 data pair.
If this receiver is powered through that cable, its actual power wiring must be
characterized. A Type-C PC end needs its own mapping; the A-to-A statement would
not apply. [USB-IF cable compliance document](https://www.usb.org/sites/default/files/CabConn_3_0_Compliance_Document_v1.02_2011-10-04.pdf).

## Connection worksheet

[`connection_measurements.csv`](connection_measurements.csv) contains **unmeasured**
checks for the cable, all four USB SuperSpeed contacts against all four SFP data
contacts, power branches and control straps. It intentionally does not assume
which receiver socket pair carries host TX; that depends on the cable and board.

Perform resistance/continuity measurements with PC, power, and optical modules
disconnected. Identify contacts from connector documentation or a numbered
breakout, not from the orientation of this photograph. Record actual resistance
and any intervening component. A series capacitor produces a DC-open reading, so
absence of a continuity beep is not proof of no signal path. This worksheet does
not verify high-frequency behavior, receiver detection or optical operation.

SFP contact names are taken from the retained SFF-8431 Table 3 (PDF page 23):
TD+ 18, TD- 19, RD+ 13, RD- 12, VccR 15, VccT 16. These are connector functions,
not observed connections on this board. [SNIA archive](https://members.snia.org/document/dl/25891).

Use the working pair to establish a measured baseline: capture the negotiated
USB speed and hub identity, exercise multiple USB3 devices, verify file hashes,
then check boot, sleep/wake and fiber unplug/replug recovery. A lit LED or a device
appearing in Windows alone does not establish a working 5 Gb/s optical link.

Then repeat the same tests with the new hub, holding the receiver, cable and modules
constant. Compatibility of the original pair does not establish compatibility of
the unfinished new schematic or of other SFP+ modules.

**Trust summary:** photo observations plus the user's report that the supplied pair
works; zero electrical connections measured, no module identity, and no independent
speed or recovery test results. This is
an evidence update, not a schematic/PCB design review or a fabrication assessment.
