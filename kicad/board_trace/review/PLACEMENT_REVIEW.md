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
