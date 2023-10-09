from cadquery.occ_impl.shapes import Wire, Face as cqFace
from shapely.geometry import Polygon
from dataclasses import dataclass
from svgpath import transforms
from typing import List, Tuple
import numpy as np
import svgpath

small_number = 1e-10


@dataclass
class Face:
    outer: List[Tuple[float, float]]
    inner: List[List[Tuple[float, float]]]


@dataclass
class Shape:
    shapely: Polygon
    points: List[Tuple[float, float]]
    parent: "Shape"
    children: List["Shape"]


def print_hierarchy(shape: Shape, depth=0):
    for i, shape in enumerate(shape):
        print(f"{'-'*depth}shape {i}")
        print_hierarchy(shape.children, depth + 1)


def contained_hierarchy(parent: Shape, children: List[Shape], processed: List[Shape]):
    """recursive creation of hierarchy"""
    for i, child_candidate in enumerate(children):
        if child_candidate in processed:
            continue
        if parent.shapely.contains(child_candidate.shapely):
            parent.children.append(child_candidate)
            child_candidate.parent = parent
            processed.append(child_candidate)
            contained_hierarchy(child_candidate, children[i:], processed)


def build_hierarchy(points: List[List[Tuple[float, float]]]) -> List[Shape]:
    """build tree of shapes, shapes that are inside other shapes are child shapes"""
    shapes: List[Shape] = [Shape(Polygon(p), p, None, []) for p in points]
    shapes = sorted(shapes, key=lambda s: -s.shapely.area)
    processed: List = []
    for i, parent in enumerate(shapes):
        contained_hierarchy(parent, shapes[i + 1 :], processed)
    return [s for s in shapes if s.parent is None]


def build_faces(shapes: List[Shape]):
    """build hierarchy of shapes mod2: inner.inner shapes are treated as a new independent shape"""
    faces = []
    def build(shapes, faces):
        for shape in shapes:
            outer = shape.points
            inner = [c.points for c in shape.children]
            faces.append(Face(outer, inner))
            for s in shape.children:
                build(s.children, faces)
    build(shapes, faces)
    return faces


def seperate_line_shape(
    paths: List[List[Tuple[float, float]]]
) -> Tuple[List[Tuple[float, float]], List[Tuple[float, float]]]:
    """seperate paths into lines and closed shapes"""
    lines = []
    polygons = []
    for points in paths:
        if len(points) <= 1:
            continue
        if len(points) < 3:
            lines.append(points)
        else:
            p = Polygon(points)
            area = p.area > small_number
            closed = np.linalg.norm(points[0] - points[-1]) < small_number
            if area and closed:
                polygons.append(points)
            else:
                lines.append(points)
    return lines, polygons


def lines_shapes_svg(
    file: str,
    density: int = 100,
    scale: Tuple[float, float] = (1, 1),
) -> Tuple[List[Tuple[float, float]], List[Face]]:
    """return the lines and shapes from files"""

    with open(file, "r") as f:
        svg = f.read()

    tree = svgpath.parse(svg)
    paths = [[t for t in p] for p in svgpath.tree_to_paths(tree)]
    gen = svgpath.paths_to_points(paths, resolution=density)
    point_paths = [remove_duplicates(trace) for paths in gen for trace in paths]
    x, y, w, h = transforms.bounds(point_paths)
    point_paths = transforms.translate(-x, -y, point_paths)
    point_paths = transforms.scale(1 / w * scale[0], 1 / h * scale[1], point_paths)
    lines, polygons = seperate_line_shape(point_paths)
    hierarchy = build_hierarchy(polygons)
    faces = build_faces(hierarchy)
    return lines, faces


def remove_duplicates(points: Tuple[float, float]):
    """removes sequential duplicate points"""
    diff = np.linalg.norm(np.diff(points, axis=0), axis=1) > small_number
    mask = np.concatenate([diff, [True]])
    return points[mask]


def homogenous(points: Tuple[float, float]) -> Tuple[float, float, float]:
    points = np.array(points)
    ones = np.zeros((len(points), 1))
    return np.hstack((points, ones)).tolist()


def Face2Face(face: Face) -> cqFace:
    outer: Wire = Wire.makePolygon(homogenous(face.outer))
    inner = [Wire.makePolygon(homogenous(f)) for f in face.inner]
    return cqFace.makeFromWires(outer, inner)


def line_offset(line: List[Tuple[float, float]], thickness: float) -> cqFace:
    if len(line) == 2:
        line = np.vstack((line, line[0]))
    wire = Wire.makePolygon(homogenous(line))
    offset = wire.offset2D(thickness / 2, "arc")[0]
    return cqFace.makeFromWires(offset)


def svg_pattern(
    file: str,
    scale: Tuple[float, float] = (1, 1),
    density: float = 100,
    repeat: Tuple[float, float] = (1, 1),
    thickness: float = 0.1,
    lines_enabled: bool = False,
) -> list[cqFace]:
    adjusted_scale = (scale[0] / repeat[0], scale[1] / repeat[1])
    lines, faces = lines_shapes_svg(file, density, scale=adjusted_scale)

    faces = [Face2Face(f) for f in faces]
    if lines_enabled:
        faces.extend(line_offset(l, thickness) for l in lines)

    bb = adjusted_scale
    lop_left_x = -bb[0] / 2 * (repeat[0] - 1)
    lop_left_y = -bb[1] / 2 * (repeat[1] - 1)
    abs_padding_x = bb[0]
    abs_padding_y = bb[1]
    xo = lambda z: lop_left_x + abs_padding_x * z
    yo = lambda z: lop_left_y + abs_padding_y * z

    lfaces = []
    for i in range(repeat[0]):
        for j in range(repeat[1]):
            for face in faces:
                lfaces.append(face.translate((xo(i), yo(j), 0)))

    return lfaces
