"""Place the real DC input jack and downsize the adjacent bulk capacitor.

Run with KiCad 10's python.exe (pcbnew). This is the post-photo "real part"
phase: an LCSC footprint replaces a photo proxy on the saved board, the way the
SFP cage (C5441174) was fitted. It does not touch the reference images, the
outline, nets or tracks. The two footprints are edited in place so their UUIDs,
list positions and every other footprint stay put.

Part: XKB Connection DC-005-2.5A-2.0, a panel-mount 3-slot DC power jack
(LCSC C319099). Land/topology is transcribed from the vendor datasheet
(https://www.lcsc.com/datasheet/C319099.pdf, "PCB HOLES (TOP VIEW)"): three
3.0 x 0.8 mm slots, the two collinear terminals 6.10 mm apart and the break
terminal 4.60 mm to the side, centred. Pad copper (1.8 x 4.2 mm) follows the
vendor EasyEDA package. Pin numbers follow the datasheet SCHEDULE
(1 = tip/centre, 2 = break/switch, 3 = outer/sleeve); note the EasyEDA package
numbers the two collinear terminals 1/2 instead.

Orientation: the barrel/opening faces +Y (toward the board edge the panel jack
protrudes through), matching the photographed jack. Origin = pin 1. Placement
is fixed on the two photo-measured collinear holes.

C51 is downsized from a D8.0 mm to a D5.0 mm radial can because the real jack
body is longer than the photo proxy and would otherwise overlap the 8 mm cap.
Both stock footprints share the same 2.50 mm lead pitch, so the leads stay in
the same holes. Capacitance and height remain unmeasured.
"""
from pathlib import Path
from datetime import datetime
import os
import shutil
import tempfile
import pcbnew

PROJ = Path(__file__).resolve().parents[1]
PCB = PROJ / "board_trace.kicad_pcb"
LIB = PROJ / "libs" / "lcsc.pretty"
LIB.mkdir(parents=True, exist_ok=True)

NAME = "C319099_DC-005-2.5A-2.0"
DESCR = ("XKB Connection DC-005-2.5A-2.0 panel-mount DC power jack, LCSC C319099, "
         "datasheet-rated 30V/0.5A. Three 3.0x0.8mm slotted terminals: pin1 tip/centre, "
         "pin2 break/switch, pin3 outer/sleeve; collinear pins 6.10mm apart, break pin "
         "4.60mm to the side and centred. Barrel faces +Y (board edge); origin = pin1. "
         "Land from vendor datasheet 'PCB HOLES (TOP VIEW)' and EasyEDA package "
         "CONN-TH_DC-005-2.5A-2.0. EasyEDA numbers the collinear terminals 1/2.")
DATASHEET = "https://www.lcsc.com/datasheet/C319099.pdf"

J4_POS = (135.893, 131.470)   # board mm; placed on the two photo-measured collinear holes
J4_ROT = 0.0
# New local pad centres (mm), origin = pin1, y-down like the board.
PADS = [
    # number, x, y, pad_w, pad_h, drill_w, drill_h
    ("1", 0.00, 0.00, 4.2, 1.8, 3.0, 0.8),   # tip / centre pin
    ("3", 0.00, -6.10, 4.2, 1.8, 3.0, 0.8),  # outer / sleeve
    ("2", 4.60, -3.25, 1.8, 4.2, 0.8, 3.0),  # break / switch
]
BODY = (-4.60, -6.90, 4.60, 7.50)          # x0, y0, x1, y1: 9.2 x 14.4 mm, barrel axis on x=0
COURTYARD = (-4.85, -7.15, 4.85, 7.75)     # body + 0.25mm; the break terminal blade pokes past this


def vec(x, y):
    return pcbnew.VECTOR2I(pcbnew.FromMM(float(x)), pcbnew.FromMM(float(y)))


def thru_pad(fp, number, x, y, w, h, dw, dh):
    p = pcbnew.PAD(fp)
    p.SetNumber(str(number))
    p.SetAttribute(pcbnew.PAD_ATTRIB_PTH)
    p.SetShape(pcbnew.PAD_SHAPE_OVAL)
    p.SetPosition(vec(x, y))
    p.SetSize(vec(w, h))
    p.SetDrillShape(pcbnew.PAD_DRILL_SHAPE_OBLONG)
    p.SetDrillSize(vec(dw, dh))
    layers = pcbnew.LSET.AllCuMask()
    layers.AddLayer(pcbnew.F_Mask)
    layers.AddLayer(pcbnew.B_Mask)
    p.SetLayerSet(layers)
    fp.Add(p)
    return p


def rect(fp, x0, y0, x1, y1, layer, width):
    s = pcbnew.PCB_SHAPE(fp)
    s.SetShape(pcbnew.SHAPE_T_RECT)
    s.SetLayer(layer)
    s.SetStart(vec(x0, y0))
    s.SetEnd(vec(x1, y1))
    s.SetWidth(pcbnew.FromMM(width))
    fp.Add(s)
    return s


def populate(fp):
    """Add the C319099 pads and outline to a footprint (library or board copy)."""
    for number, x, y, w, h, dw, dh in PADS:
        thru_pad(fp, number, x, y, w, h, dw, dh)
    rect(fp, *COURTYARD, pcbnew.F_CrtYd, 0.05)
    rect(fp, *BODY, pcbnew.F_Fab, 0.10)
    # No F.SilkS outline: the jack sits against the board edge in a dense area and
    # an added silk rectangle/body would only spawn silk-overlap and silk-edge
    # warnings. The old photo proxy carried no silkscreen either.


def build_library_footprint():
    fp = pcbnew.FOOTPRINT(None)
    fp.SetFPID(pcbnew.LIB_ID("lcsc", NAME))
    fp.SetLibDescription(DESCR)
    fp.SetAttributes(pcbnew.FP_THROUGH_HOLE)
    fp.SetReference("REF**")
    fp.SetValue(NAME)
    populate(fp)
    fp.SetField("Datasheet", DATASHEET)
    fp.SetField("LCSC Part", "C319099")
    fp.SetField("MPN", "DC-005-2.5A-2.0")
    fp.SetField("Manufacturer", "XKB Connection")
    for field in fp.GetFields():
        field.SetVisible(False)
    fp.Reference().SetVisible(True)
    fp.Reference().SetPosition(vec(0, -2.0))
    fp.Reference().SetTextSize(vec(0.55, 0.55))
    fp.Reference().SetTextThickness(pcbnew.FromMM(0.1))
    return fp


_KEEP = []  # SWIG wrappers for removed items must outlive the footprint edits


def strip(fp):
    # Collect both containers before mutating: removing pads invalidates the
    # GraphicalItems() SWIG typemap until the footprint is re-queried.
    pads = list(fp.Pads())
    graphics = list(fp.GraphicalItems())
    for p in pads:
        fp.Remove(p)
    for g in graphics:
        fp.Remove(g)
    _KEEP.extend(pads)
    _KEEP.extend(graphics)


def pad_centres(fp):
    return {p.GetNumber(): (round(pcbnew.ToMM(p.GetPosition().x), 4),
                            round(pcbnew.ToMM(p.GetPosition().y), 4)) for p in fp.Pads()}


def courtyard_bbox(fp):
    poly = fp.GetCourtyard(pcbnew.F_CrtYd)
    if poly.OutlineCount() == 0:
        return None
    box = poly.BBox()
    return (pcbnew.ToMM(box.GetLeft()), pcbnew.ToMM(box.GetTop()),
            pcbnew.ToMM(box.GetRight()), pcbnew.ToMM(box.GetBottom()))


def main():
    lib_file = LIB / (NAME + ".kicad_mod")
    if not lib_file.exists():
        plugin = pcbnew.PCB_IO_MGR.FindPlugin(pcbnew.PCB_IO_MGR.KICAD_SEXP)
        plugin.FootprintSave(str(LIB), build_library_footprint())
    print("library footprint:", lib_file)

    board = pcbnew.LoadBoard(str(PCB))
    by_ref = {f.GetReference(): f for f in board.GetFootprints()}
    if "J4" not in by_ref or "C51" not in by_ref:
        raise SystemExit("Expected J4 and C51 on the board")
    old_pads = pad_centres(by_ref["J4"])

    backup = PROJ / "review" / "backups" / datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    backup.mkdir(parents=True)
    shutil.copy2(PCB, backup / PCB.name)

    # --- J4: replace the photo proxy with the real C319099 jack, in place ---
    # Work at the origin so pad/shape coordinates are plain local coordinates,
    # then move the whole footprint into place (KiCad transforms the children).
    j4 = by_ref["J4"]
    j4.SetOrientationDegrees(0.0)
    j4.SetPosition(vec(0, 0))
    strip(j4)
    j4.SetFPID(pcbnew.LIB_ID("lcsc", NAME))
    j4.SetLibDescription(DESCR)
    j4.SetAttributes(pcbnew.FP_THROUGH_HOLE)
    populate(j4)
    j4.SetValue("DC-005-2.5A-2.0")
    j4.SetField("Datasheet", DATASHEET)
    j4.SetField("LCSC Part", "C319099")
    j4.SetField("MPN", "DC-005-2.5A-2.0")
    j4.SetField("Manufacturer", "XKB Connection")
    j4.SetField("Trace limitations",
                "Vendor footprint (datasheet + EasyEDA); barrel faces board edge. "
                "Pin functions from datasheet SCHEDULE; electrical use still unverified")
    for field in j4.GetFields():
        field.SetVisible(False)
    j4.Reference().SetVisible(True)
    j4.Reference().SetPosition(vec(0, -2.0))
    j4.Reference().SetTextSize(vec(0.55, 0.55))
    j4.Reference().SetTextThickness(pcbnew.FromMM(0.1))
    j4.SetPosition(vec(*J4_POS))
    j4.SetOrientationDegrees(J4_ROT)

    # --- C51: same holes, smaller D5.0 mm radial can, in place ---
    c51 = by_ref["C51"]
    cap_lib = Path(os.environ.get("KICAD10_FOOTPRINT_DIR",
                                  r"C:\Program Files\KiCad\10.0\share\kicad\footprints")) / "Capacitor_THT.pretty"
    tpl = pcbnew.FootprintLoad(str(cap_lib), "CP_Radial_D5.0mm_P2.50mm")
    if tpl is None:
        raise RuntimeError("Cannot load CP_Radial_D5.0mm_P2.50mm")
    tpl_pads = list(tpl.Pads())
    tpl_graphics = list(tpl.GraphicalItems())
    ref_local = tpl.Reference().GetPosition()
    for p in tpl_pads:
        tpl.Remove(p)
    for g in tpl_graphics:
        tpl.Remove(g)
    c51_pos = c51.GetPosition()
    c51_rot = c51.GetOrientationDegrees()
    c51.SetOrientationDegrees(0.0)
    c51.SetPosition(vec(0, 0))
    strip(c51)
    for p in tpl_pads:
        c51.Add(p)
    for g in tpl_graphics:
        c51.Add(g)
    c51.SetFPID(pcbnew.LIB_ID("Capacitor_THT", "CP_Radial_D5.0mm_P2.50mm"))
    c51.SetLibDescription(tpl.GetLibDescription())
    c51.Reference().SetVisible(True)
    c51.Reference().SetPosition(ref_local)
    c51.Reference().SetTextSize(vec(0.55, 0.55))
    c51.Reference().SetTextThickness(pcbnew.FromMM(0.1))
    c51.Value().SetVisible(False)
    c51.SetPosition(c51_pos)
    c51.SetOrientationDegrees(c51_rot)

    # Saving goes through pcbnew, which re-serialises every PTH pad on the board
    # without the explicit "*.Mask" wildcard (KiCad re-derives it from the project
    # on load, so openings are unaffected). That normalises CAGE1's 17 pads to
    # match the rest of the board; nothing else in the cage placement is touched.
    temporary = Path(tempfile.gettempdir()) / "diffpair_board_trace.next.kicad_pcb"
    pcbnew.SaveBoard(str(temporary), board)
    check = pcbnew.LoadBoard(str(temporary))
    refs = {f.GetReference(): f for f in check.GetFootprints()}
    if sum(d.GetClass() == "PCB_REFERENCE_IMAGE" for d in check.GetDrawings()) != 2:
        raise SystemExit("Reference images were disturbed")

    new_pads = pad_centres(refs["J4"])
    print("J4 old pads:", old_pads)
    print("J4 new pads:", new_pads)
    print("C51 pads (unchanged holes):", pad_centres(refs["C51"]))
    j4_crt, c51_crt = courtyard_bbox(refs["J4"]), courtyard_bbox(refs["C51"])
    print("J4 courtyard:", j4_crt)
    print("C51 courtyard:", c51_crt)
    if j4_crt and c51_crt:
        print("gap J4-top to C51-bottom: %.3f mm" % (j4_crt[1] - c51_crt[3]))

    os.replace(temporary, PCB)
    print("Saved", PCB, "backup:", backup)


if __name__ == "__main__":
    main()
