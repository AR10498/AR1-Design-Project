from structural_classes import Node, Member
import ezdxf
from shapely.geometry import Point, LineString
import itertools 
import numpy as np
from scipy.spatial import KDTree
#from collections import defaultdict

import pandas as pd

def is_endpoint(point, line, tol):
    start = Point(line.coords[0])
    end = Point(line.coords[-1])
    return (point.distance(start) < tol or point.distance(end) < tol)

#############################
#   GEOMETRY EXTRACTION
#############################
def extract_structure_from_dxf(file_path, units='mm', tol=1e-3):
    """
    Import a DXF line drawing and convert it into a structural model.

    The function:
    1. Reads LINE entities from the DXF.
    2. Finds all line intersections.
    3. Creates nodes at endpoints and intersections.
    4. Merges nearby nodes within a tolerance.
    5. Splits members wherever a node lies along a line.
    6. Creates Node and Member objects.
    7. Builds nodal connectivity information.

    Parameters
    ----------
    file_path : str
        Path to the DXF file.

    units : str
        Either 'mm' or 'm'. If 'mm', coordinates are converted to metres.

    tol : float
        Distance tolerance used for node merging and geometric matching.

    Returns
    -------
    nodes : dict
        Dictionary of Node objects indexed by node label.

    members : dict
        Dictionary of Member objects indexed by member name.
    """

    MM_TO_M = 0.001  # conversion factor from mm to m

    # Read DXF file and access model space
    doc = ezdxf.readfile(file_path)
    msp = doc.modelspace()

    lines = []

    # Extract all DXF LINE entities
    for entity in msp.query("LINE"):

        start = (
            entity.dxf.start.x,
            entity.dxf.start.y,
            entity.dxf.start.z
        )

        end = (
            entity.dxf.end.x,
            entity.dxf.end.y,
            entity.dxf.end.z
        )

        lines.append((start, end))

    # Convert geometry into metres if required
    factor = MM_TO_M if units.lower() == 'mm' else 1.0

    lines_m = [
        (
            (s[0]*factor, s[1]*factor, s[2]*factor),
            (e[0]*factor, e[1]*factor, e[2]*factor)
        )
        for s, e in lines
    ]

    # Create Shapely line objects for geometric operations
    shapely_lines = [
        LineString([(s[0], s[1]), (e[0], e[1])])
        for s, e in lines_m
    ]

    # Find all intersections between line pairs
    intersections = set()

    for line1, line2 in itertools.combinations(shapely_lines, 2):
        inter = line1.intersection(line2)
        if inter.is_empty:
            continue
        if inter.geom_type == "Point":
            # Only create a structural node if the
            # intersection coincides with an endpoint
            # on at least one member.
            if (is_endpoint(inter, line1, tol) or is_endpoint(inter, line2, tol)):
                intersections.add((inter.x, inter.y, 0))
    
        elif inter.geom_type == "MultiPoint":
            for p in inter.geoms:
                if (is_endpoint(p, line1, tol) or is_endpoint(p, line2, tol)):
                    intersections.add((p.x, p.y, 0))

    # Add original member endpoints as nodes
    for start, end in lines_m:
        intersections.add(start)
        intersections.add(end)

    # Convert node set to NumPy array
    pts = np.array(list(intersections))

    # Merge nodes that are closer than the tolerance
    # Example:
    # (5.0000,0) and (5.0001,0)
    # become a single node.
    tree = KDTree(pts[:, :2])

    visited = np.zeros(len(pts), dtype=bool)

    merged_nodes = []
    conflict_groups = []

    for i, p in enumerate(pts):

        if visited[i]:
            continue

        # Find all nodes within tolerance
        idxs = tree.query_ball_point(p[:2], tol)

        visited[idxs] = True

        group_pts = pts[idxs]

        # Replace cluster by centroid
        merged_pt = np.mean(group_pts, axis=0)
        merged_nodes.append(merged_pt)

        # Store groups where multiple nodes merged
        if len(idxs) > 1:
            conflict_groups.append(group_pts)

    # Sort nodes to ensure repeatable numbering
    merged_nodes = sorted(merged_nodes, key=lambda p: (p[0], p[1], p[2]))
    node_coords = np.array(merged_nodes)

    # Split lines wherever a merged node lies on them:
    #
    # A---------B
    #      |
    #      |
    #
    # becomes
    #
    # A----I----B
    #      |
    #      |
    #
    # producing two members instead of one.
    split_segments = []

    for line in shapely_lines:
        pts = []
        # Find every node lying on this line
        for node_id, node in enumerate(node_coords):
            p = Point(node[0], node[1])
            # Distance along line to projected point
            d = line.project(p)
            # Nearest point on line
            p_proj = line.interpolate(d)
            # Check if node lies on line
            if p.distance(p_proj) < tol:
                pts.append((d, node_id))

        # Order nodes along the member
        pts.sort(key=lambda x: x[0])

        # Create segments between consecutive nodes
        for (_, n1), (_, n2) in zip(pts[:-1], pts[1:]):
            if n1 == n2:
                continue
            split_segments.append((n1, n2))

    # Create temporary Node objects
    # Key = integer index
    # Value = Node object
    nodes_tmp = {i: Node(i, tuple(coord)) for i, coord in enumerate(merged_nodes)}

    # Re-index using node labels
    # Example:
    # {'A': Node(...), 'B': Node(...)}
    nodes = {n.label: n for n in nodes_tmp.values()}

    members = {}
    
    for i, (n1, n2) in enumerate(split_segments):
    
        start_node = nodes_tmp[n1]
        end_node = nodes_tmp[n2]
    
        m = Member(i, start_node, end_node)
    
        members[m.name] = m
    
        # Build node connectivity lists
        # Example:
        # A connected to B and C
        # -> A.connectivity = [B, C]
    for m in members.values():
    
        n1 = m.start_node.label
        n2 = m.end_node.label
    
        m.start_node.connectivity.append(n2)
        m.end_node.connectivity.append(n1)

    return nodes, members

##############################
#   MATERIAL HANDLING (robust)
##############################
def read_materials_from_excel(file_path, print_contents=True):
    """
    Reads Excel and returns a normalized DataFrame keyed by Material name.
    Recognizes common column headers and maps them to: Material, E, Fy, Density.
    """
    df = pd.read_excel(file_path, skiprows=1)
    if df.empty or df.shape[1] < 1:
        raise ValueError("Excel file must have at least one column for material labels.")
    
    # normalize column names: 
    normalized = {}
    for c in df.columns:
        cl = c.strip().lower()
        if "label" in cl:
            normalized[c] = "Label"
        #!!! potential issue if any other column heading starts with the letter e or E !!!
        elif "e" == cl:
            normalized[c] = "E"
        elif "fc" == cl:
            normalized[c] = "fc"
        elif "ft" == cl:
            normalized[c] = "ft"
        elif "density" == cl or "rho" == cl:
            normalized[c] = "Density"
        else:
            # ignore unknown columns but keep them in case needed
            normalized[c] = c
    
    df = df.rename(columns=normalized)
    
    # require Material column
    if "Label" not in df.columns:
        raise ValueError("Excel file must contain a 'Label' column (header contains 'Label').")
    
    # Ensure the standard columns exist
    for std in ("E", "fc", "ft", "Density"):
        if std not in df.columns:
            df[std] = 0.0
    
    # Coerce numeric columns to floats, fill NaN with 0
    for std in ("E", "fc", "ft", "Density"):
        df[std] = pd.to_numeric(df[std], errors="coerce").fillna(0.0).astype(float)
    
    # Trim material names and convert to string
    df["Label"] = df["Label"].astype(str).str.strip()
    
    # transform to enable simple lookup
    df.set_index('Label', inplace=True)
    df = df.transpose()
    if print_contents:
        print("\n<= Imported Materials (normalized):\n")
        print(df)

    return df 


############
#   EXPORT
############
def export_to_dxf(nodes, members, filename="output.dxf", units='mm'):
    M_TO_MM = 1000.0  # millimeters to meters

    factor = M_TO_MM if units.lower() == 'mm' else 1.0
    
    doc = ezdxf.new(dxfversion="R2010")
    msp = doc.modelspace()
    for m in members.values():
        x1,y1 = m.start_node.coords[:2]
        x2,y2 = m.end_node.coords[:2]
        msp.add_line([x1*factor, y1*factor], [x2*factor, y2*factor])
    doc.saveas(filename)
    print(f"=> DXF exported to {filename}")
