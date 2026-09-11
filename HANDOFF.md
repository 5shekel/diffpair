# HANDOFF — diffpair reverse-engineering → KiCad

_Last updated: 2026-09-11_

This documents the work done in this session: building a **new KiCad project** that
puts the front/back board photos behind the layout as reference images, and placing
the board's components onto it by tracing the photos.

---

## 1. TL;DR

- New project: **`kicad/board_trace/`** (KiCad 10).
- Both photos are embedded as **Reference Images** (KiCad 10 feature), dimmed so they
  act as a tracing background:
  - front photo → `User.Drawings` (Dwgs.User)
  - back photo → `User.Comments` (Cmts.User)
- **43 footprints** placed by geometry traced from the photos — **no routing**.
- Board size established as **≈ 39.7 × 61.7 mm** (the images were initially ~2.2× too big).
- KiCad is **not** version-controlled in this repo yet; the `.kicad_pcb` is ~6 MB
  because the two PNGs are base64-embedded.

---

## 2. Environment

| Thing | Value |
|---|---|
| KiCad | 10.0.5 |
| Binaries | `C:\Program Files\KiCad\10.0\bin\` (`kicad.exe`, `pcbnew.exe`, `kicad-cli.exe`, `python.exe`) |
| Python w/ `pcbnew` | `C:\Program Files\KiCad\10.0\bin\python.exe` (has numpy + PIL, **no cv2**) |
| System Python | has `cv2`, `numpy`, `PIL`, `pypdf` |
| git | `origin = https://github.com/5shekel/diffpair.git`, branch `master` |

> **Tooling note:** the `konnect` skill (registered in this environment) says all
> `.kicad_*` edits must go through Konnect MCP tools. **The Konnect MCP server is not
> connected here**, so — with the user's explicit go-ahead — all board writes were
> done with KiCad's own `pcbnew` Python API. Do not hand-edit `.kicad_pcb` as text.

---

## 3. Files

```
kicad/board_trace/
├─ board_trace.kicad_pro          project (settings cloned from the old hub project)
├─ board_trace.kicad_pcb          board: 2 reference images + 43 footprints (~6 MB)
├─ board_trace.kicad_sch          empty schematic stub
├─ board_trace.kicad_prl          local view settings (Images opacity = 0.45)
├─ images/board_top.png           front photo, pre-aligned (300 DPI, 1030×1601)
├─ images/board_bottom.png        back photo, pre-aligned
├─ libs/lcsc.pretty/HC-USB3.0-L175-2X1-P.kicad_mod   USB3 connector footprint (converted)
├─ detect.json                    passive detections (top/bottom), image px
├─ placement.json                 every placed ref → fp / x / y / rot / side
├─ verify_boxes.json              per-footprint pad bounding boxes (image px)
└─ scripts/
   ├─ 01_detect.py                photos → detect.json (cv2, system python)
   ├─ 02_place.py                 build board + place footprints (KiCad python)
   ├─ 03_verify.py                board → verify_boxes.json (KiCad python)
   ├─ easyeda_fetch.py            pull EasyEDA component JSON by LCSC id
   └─ easyeda_convert.py          EasyEDA footprint JSON → .kicad_mod
```

---

## 4. Coordinate system & scale

The two photos are the **pre-aligned `-gimp` copies** (same 1030×1601 frame, both
cropped to the board). They are placed at **300 DPI** with an explicit
`(scale 0.4554)` so the rendered size matches reality.

**True scale = 25.9375 px/mm**, cross-checked three ways:

| Ruler | Measurement | px/mm |
|---|---|---|
| SFP 20-pin pads, 0.8 mm pitch | 20.75 px across 9 pads | **25.94** |
| VL813 QFN-76, 9×9 mm body (datasheet) | 233 px | 25.9 |
| USB-A shell, 13.10 mm | 349 px | 26.6 |

Resulting image / board size: **39.711 × 61.725 mm**.

Geometry constants (used by all scripts):

```
PX_PER_MM = 25.9375
IMG_W, IMG_H = 39.711, 61.725 mm      # 1030 / 1601 px
IMG_CX, IMG_CY = 148.5, 105.0 mm      # centre on an A4 sheet
LEFT = IMG_CX - IMG_W/2 = 128.6445
TOP  = IMG_CY - IMG_H/2 = 74.1375

image px -> board mm:   x = LEFT + px / PX_PER_MM
                        y = TOP  + py / PX_PER_MM
```

The `Edge.Cuts` rectangle is a **placeholder** matching the image extents — the real
outline has not been drawn.

### Image orientation (as instructed by the user)

- **Top = `board_top.jpg`, NOT flipped.**
- **Bottom = `board_bottom.jpg`, flipped** (the pre-aligned `-gimp` copy is the mirror
  of the raw photo, so it overlays the top frame). `board_bottom-gimp` correlates 0.60
  with `flip(board_bottom.jpg)` vs 0.42 with the unflipped original.

> ⚠️ **Open question.** In this orientation the **top silkscreen reads mirrored**
> (e.g. "25MHZ 12PF ±10PPM", "100µF") — and the crystal's *own* "25.000 MHz" marking
> is mirrored too, which normally means the image is a mirror. The user states the top
> is correct as-is, so it was left that way. If the physical top should read normally,
> **mirror both images and all placement X coordinates together** (a single transform).

### Viewing the bottom image
Reference-image visibility follows the layer it's on:
- hide **User.Drawings** (front photo), show **User.Comments** (back photo).
- Images opacity: **Preferences → PCB Editor → Colors → Images** (set to 0.45).

---

## 5. Components placed (43)

No schematic / netlist exists — these are board-only placements traced from the photos.
**All passives are 0603 capacitors** (R-vs-C not distinguished) with no values.

| Ref(s) | Qty | Footprint | Side |
|---|---|---|---|
| C1–C31 | 31 | `Capacitor_SMD:C_0603_1608Metric` | front (auto-detected) |
| C32–C34 | 3 | `C_0603_1608Metric` | **back** |
| **J1, J2** | 2 | `HC-USB3.0-L175-2X1-P` (LCSC **C7501881**) | front |
| **J3** | 1 | `C42418480_CONN-SMD_20P-P0_80_SFP20P` | front |
| **Y1** | 1 | `Crystal_SMD_3225-4Pin_3.2x2.5mm` | front |
| **L1** | 1 | `L_Sunlord_SWPA5040S` (5×4 mm) | front |
| **C50** | 1 | `CP_EIA-7343-30_AVX-N` (the black "KC" part — model assumed a cap) | front |
| **C51** | 1 | `CP_Elec_6.3x5.4` (small silver-topped can) | front |
| **C52** | 1 | `CP_Elec_10x10.5` (large can at board edge) | front |
| **U1** | 1 | `C69418_QFN-76_9x9_P0.40_EP6.4` (VL813) | **back** |

Exact coordinates are in `placement.json`; pad-level boxes in `verify_boxes.json`.

### Footprint sources
- Standard KiCad libs under `C:\Program Files\KiCad\10.0\share\kicad\footprints\`.
- **U1 + J3** use the LCSC footprints already in the sibling project:
  `kicad/usb3_over_optical_hub/.../libs/lcsc/footprints.pretty/`
  (`C69418_QFN-76…`, `C42418480_CONN-SMD_20P-P0_80_SFP20P`).
- **J1/J2** footprint was converted from the manufacturer's EasyEDA data:
  - LCSC **C7501881** = Hong Cheng **HC‑USB3.0‑L175‑2X1‑P** — USB 3.0 Type‑A, 9P×2,
    through-hole right-angle, 2 ports (stacked).
  - EasyEDA API: `https://easyeda.com/api/products/C7501881/components?version=6.5.36`
  - **Conversion factor: 1 EasyEDA unit = 0.254 mm (10 mil)**; the PAD `hole` field is a
    **radius** (drill Ø = 2 × field × 0.254). Validated: shell mounts land 13.1 mm apart
    with Ø2.3 mm holes, signal pins Ø0.7 mm, 8 mm pin field.
  - Result: 22 pads, 14.1 × 7.7 mm pad field.

---

## 6. How it was built (reproduce)

Order matters; run detection with **system** python, board ops with **KiCad** python.

```powershell
# 1) regenerate images + detect passives  -> detect.json
python            kicad\board_trace\scripts\01_detect.py
# 2) build a fresh board + place all footprints + embed images
& "C:\Program Files\KiCad\10.0\bin\python.exe" kicad\board_trace\scripts\02_place.py
# 3) dump pad bounding boxes for review -> verify_boxes.json
& "C:\Program Files\KiCad\10.0\bin\python.exe" kicad\board_trace\scripts\03_verify.py

# (only if the USB footprint must be rebuilt)
python kicad\board_trace\scripts\easyeda_fetch.py     # saves EasyEDA JSON
python kicad\board_trace\scripts\easyeda_convert.py   # -> libs/lcsc.pretty/*.kicad_mod
```

`02_place.py` rewrites `board_trace.kicad_pcb` from scratch, so it is the single source
of truth for placement. Detection is deterministic, so re-running is safe.

---

## 7. Known issues / TODO

**Placement**
- **J1/J2 vertical (Y) position is approximate** — pad *width* and footprint are correct,
  but confirm the pad field sits on the connector's through-holes and nudge if needed.
- Passive detection has a few **false positives** (bright vias / value-label silk) and
  some **misses** — review C1–C31 against the photo.
- The 3 bottom passives (C32–C34) were placed by hand (vias defeat auto-detection there).
- **C50's part type is a guess** — the black "KC" part was modeled as a rectangular SMD
  capacitor (tantalum/polymer). Confirm it isn't a fuse / inductor.
- No board **outline** beyond the placeholder rectangle; no routing; no nets.

**Data**
- No values, no R/C classification, no MPNs (except the connectors/IC).
- Silkscreen values readable from the photos include: 10 µH, 100 µF, 1R0, 331, 4R7, 2R2,
  473, 12A, 27W, "KC", "25MHZ 12PF ±10PPM".

**Process**
- `SetLayer(B_Cu)` does **not** flip pads — it must be `Footprint.Flip(pos, FLIP_DIRECTION_LEFT_RIGHT)`
  (this bit us once: U1's pads stayed on F.Cu). Do not regress.
- Repo is a git repo; the new `kicad/board_trace` tree is currently untracked/not committed.

---

## 8. Suggested next steps

1. Verify/nudge **J1/J2** onto the connector holes; confirm C50/C51/C52 shapes.
2. Clean the passive set (remove false positives, add misses); consider full-res photos
   (1425×1900) for finer tracing, re-registering the pair.
3. Draw the real **Edge.Cuts** outline.
4. Read silkscreen values → assign to passives; split R vs C.
5. Bring in the **VL813 + SFP** symbols from `kicad/usb3_over_optical_hub/` and build the
   schematic (currently an empty stub), then sync to the PCB.
6. Commit `kicad/board_trace` (mind the ~6 MB `.kicad_pcb`; consider Git LFS).
