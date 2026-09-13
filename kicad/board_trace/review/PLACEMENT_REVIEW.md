# Photo placement cleanup — 2026-09-11

This review covers photo tracing and saved-file integrity, not electrical design
verification. Evidence is the supplied front/back photos, native KiCad footprints,
the saved PCB, and native DRC. No schematic, datasheet pinout verification, sourcing,
EMC, SPICE, thermal, or fabrication assessment was performed in this placement pass.

## Visual evidence

- [Front pad overlay](overlay_top.png)
- [Back pad overlay](overlay_bottom.png)
- [Reviewed placement plan and evidence](../placement_plan.json)
- [Connector observations and fit](connector_fit.json)
- [Independent saved-file checks](saved_checks.json)
- [Native DRC](drc.json)

Cyan outlines show SMD pad bounding rectangles. Yellow outlines show through-hole
pad bounding rectangles. Crosses show actual saved pad centers; these are not drill
diameter outlines. Magenta is the approximate photo-traced Edge.Cuts. Hidden pads
under components are overlaid intentionally. The images retain the user's chosen
orientation, including the bottom image's existing mirror.

## Results and confidence

**Photo-measured:** Both USB connector footprints match 22 distinct joints each.
Saved-board J1 RMS/max deviation: 0.0749/0.2158 mm; J2: 0.0715/0.1607 mm. The maximum
residuals occur within a fit affected by manual center picking and photo distortion.
This verifies the saved geometry against these observations, not connector pinout.

**High-confidence visual corrections:** C52 was a barrel jack; its tabs had been
mistaken for C32–C34. C51 has two through-hole joints. Several original passive
detections were individual terminations of one component. Refer to `retired_refs`
in the plan for the mapping; surviving real-component references were retained.

**Inferred:** Capacitor/resistor package sizes, inductor heights, diode D1 identity,
all uncertain polarities, the barrel jack's slots and pin functions, and U2 identity.
Each footprint carries its own evidence/uncertainty fields. Resistor printed codes
are preserved verbatim as `MARK:...`; `68?` is intentionally ambiguous.

**Unresolved photo fit:** U1's inherited QFN rows sit inward of some visible joints;
J3's locating pegs align, but the contact rows need further checking. The soldered
component heights and camera perspective can affect visible body positions. Do not
stretch manufacturer footprint geometry merely to fit the photo without checking
the package and registration. Stock LED bodies do not represent the bent leads.

The new outline is closed but approximate. The original image frame clipped the
board perimeter. Full-photo corner picks were transformed by the observed crop
offset; perspective was retained. It is not a verified mechanical drawing.

## Native DRC — not passed

| Severity | Finding | Count |
|---|---|---:|
| Error | Copper clearance | 75 |
| Error | Courtyard overlap | 29 |
| Error | PTH inside another courtyard | 5 |
| Error | Annular width | 2 |
| Error | Copper-to-edge clearance | 1 |
| Warning | Silk over copper | 66 |
| Warning | Text height | 61 |
| Warning | Silk overlap | 38 |
| Warning | Library footprint mismatch | 6 |
| Warning | Silk-to-edge clearance | 2 |
| Warning | Padstack | 2 |

Total: **112 errors + 175 warnings = 287 violations**. Zero unconnected items does
not indicate routed connectivity: this board has no named nets. Many clearance
findings concern U1's 0.18 mm adjacent-pad spacing against inherited 0.20 mm rules.
Other findings involve dense stock proxies, reference labels and overlapping
courtyards. J3 has inherited PTH locating pads with zero annulus. These issues were
recorded rather than hidden by relaxing the rules.

Saved-file checks passed for 61 unique references, absence of retired references,
all 77 U1 pads on B.Cu only, a closed outline, and reference-image pixel hashes,
position and scale. These checks are reproducible with `scripts/06_check_saved.py`.

Next work: resolve U1/J3 fit and pin orientation, identify power circuitry, measure
the mechanical features, and reconstruct nets from continuity evidence before
building a connected schematic.

## 2026-09-13 — real-part fit (SFP cage, DC jack)

The photo-placement pass was then closed and real LCSC parts were fitted on top of
it. `placement_plan.json` now carries **62 parts**, and `06_check_saved.py` passes
again (the cage commit had left the plan/check stale):

- **CAGE1** — CND-tek SFP+ 1x1 cage (LCSC C5441174), 17 legs on the J3 locating
  holes; see `cage_fit.svg`/`cage_fit.pdf`.
- **J4** — XKB **DC-005-2.5A-2.0** panel-mount DC power jack (LCSC C319099),
  replacing the provisional `BarrelJack_PhotoTrace` proxy. The footprint is
  transcribed from the vendor datasheet "PCB HOLES (TOP VIEW)" drawing (three
  3.0 x 0.8 mm slots; the two collinear terminals 6.10 mm apart, the break terminal
  4.60 mm to the side and centred) and the EasyEDA package (1.8 x 4.2 mm pad).
  Origin = pin 1 (tip) and the barrel faces the board edge. Pin numbers follow the
  datasheet SCHEDULE (1 = tip/centre, 2 = break/switch, 3 = outer/sleeve); the
  EasyEDA package numbers the two collinear terminals 1/2 instead. J4 is placed on
  the two photo-measured collinear holes, and its break terminal lands within about
  0.65 mm of the old proxy's third joint. Electrical use is not established.
- **C51** was downsized from a D8.0 mm to a D5.0 mm radial can: the real jack body
  is longer than the photo proxy and encroached on an 8 mm capacitor. Both stock
  footprints share the 2.50 mm lead pitch, so the leads stay in the same
  photo-measured holes. Capacitance and height remain unmeasured.

Native DRC after these changes: **283 violations (128 errors, 155 warnings)**, with
0 unconnected items and still no tracks or named nets. This is **better** than the
pre-jack board (322): the smaller C51 silkscreen alone removes 37 silk
overlap/over-copper warnings, and replacing the jack removes one courtyard overlap
and one PTH-inside-courtyard finding. J4 and C51 courtyards clear each other by
0.37 mm. The DC jack has no F.SilkS outline on purpose (its body overhangs the
board edge in a dense area, so silkscreen there would only add warnings).

Because the edit went through pcbnew, the save re-serialised the whole board and
the cage's 17 pads lost their explicit `"*.Mask"` wildcard (it is re-derived from
the project on load, so the mask openings are unaffected; every other PTH pad on
the board was already written that way). A handful of coordinates also round at
the 1e-6 mm level. No other footprint's content changed.
