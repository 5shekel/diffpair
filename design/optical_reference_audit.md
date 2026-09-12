# Optical reference audit — 2026-09-12

The downloaded [CN107276675B technical disclosure](https://patents.google.com/patent/CN107276675B/en)
does not supply a component-level Rx.Detect network. PDF page 22/Figure 4 shows
only an analog-load block. Pages 20–21 show a host-side hub and MCU. The text
describes coordinated reset/transmitter control at both endpoints and a USB2
management path. This is architectural background, not the schematic of the
user's receiver. Its USB2 management path is outside this USB3-only design.

The retained PDF is `design/references/CN107276675B.pdf`; drawings 20–26 are
rendered alongside it. Board-marking searches did not identify a matching
manufacturer circuit. Neither the patent nor the exposed receiver top proves
the electrical connectivity or recovery behavior of the supplied working pair.

Consequently, do not assign an invented termination or peer-handshake controller
to the draft. Establish the actual cable mapping, hub-to-module signal network,
receiver circuitry and LOS/TX_DISABLE behavior from the reference hardware.
The requested receiver underside photo remains absent.

The user confirms the pair is disconnected from this PC. A read-only Windows
capture tool is now built and exercised, ready to capture USB3 operation when
the pair is connected. It distinguishes operating speed from capability and
does not treat a USB3-capable root hub as an active USB3 device connection.
