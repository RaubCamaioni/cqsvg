from cadquery import Solid, Face
from typing import List
from pathlib import Path
import cadquery as cq
import time

from cq_svg import svg_pattern
from functools import reduce

_show = globals().get("show_object", lambda *args, **kwargs: print("show disabled"))


def show_object(shape: cq.Shape, name: str):
    return _show(shape, name)


def loft_faces(f1: Face, f2: Face) -> Solid:
    solid = cq.Solid.makeLoft([f1.outerWire(), f2.outerWire()])
    for inner1, inner2 in zip(f1.innerWires(), f2.innerWires()):
        solid_inner = cq.Solid.makeLoft([inner1, inner2])
        solid = solid.cut(solid_inner)
    return solid


def loftz(f: Face, d: float):
    return loft_faces(f, f.translate(cq.Vector(0, 0, d)))


def cut(subject: Solid, tool: Solid):
    return subject.cut(tool)


def main(svg_file: Path):
    scale = (0.9, 0.9)
    tile = (1, 1)

    faces = svg_pattern(
        svg_file,
        scale=scale,
        density=10,
        repeat=tile,
        thickness=0.01,
    )

    face_solids = [loftz(f.translate((0, 0, 0.01)), -0.1) for f in faces]
    back_place = cq.Workplane("XY").rect(1, 1).extrude(-0.12)
    solid = reduce(cut, face_solids, back_place)

    stl_file = f"stl_files/{'{}'}_{int(time.time())}_{svg_file.stem}.stl"

    cq.exporters.export(solid, stl_file.format("solid"))
    cq.exporters.export(cq.Compound.makeCompound(faces), stl_file.format("face"))

    # show_object(solid, name="solid")
    # show_object(faces, name="faces")


def cqeditor():
    import traceback

    svg_file = "patterns/blobs.svg"
    try:
        main(svg_file)
    except Exception as e:
        print(traceback.print_exc())


if __name__ == "__cq_main__":
    cqeditor()

if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("-i", type=str)
    args = p.parse_args()
    main(Path(args.i))
