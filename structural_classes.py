from dataclasses import dataclass, field
from enum import Enum
import math

# SUPPORT TYPES
class SupportType(Enum):
    FREE = "Free"
    ROLLER = "Roller"
    PINNED = "Pinned"
    FIXED = "Fixed"


def index_to_label(idx):
    """
    Convert:
    0 -> A
    1 -> B
    ...
    25 -> Z
    26 -> AA
    27 -> AB
    ...
    """
    label = ""
    while True:
        idx, rem = divmod(idx, 26)
        label = chr(65 + rem) + label
        if idx == 0:
            break
        idx -= 1
    return label


# NODE
class Node:
    """
    Structural node with coordinates, loads, reactions and support condition.
    """
    def __init__(self, id, coords, label=None, condition="Pinned"):

        self.id = id
        self.coords = tuple([float(n) for n in coords])

        if label is None:
            label = index_to_label(id)

        self.label = label
        self.condition = condition

        # Applied loads
        self.F_x = 0.0
        self.F_y = 0.0

        # Support reactions
        self.R_x = 0.0
        self.R_y = 0.0

        # Connected node labels
        self.connectivity = []

    def unknowns(self):
    
        support_unknowns = {
            "Pinned": 0,
            "Fixed": 0,
    
            "Reaction_Roller_H": 1,
            "Reaction_Roller_V": 1,
    
            "Reaction_Pinned": 2,
            "Reaction_Fixed": 3,
        }
    
        return support_unknowns.get(self.condition, 0)


# MEMBER
class Member:
    """
    Structural member connecting two nodes.
    """
    def __init__(self, id, start_node, end_node):

        # Unique numerical identifier
        self.id = id

        # References to the nodes at each end
        self.start_node = start_node
        self.end_node = end_node

        # Material object
        # e.g. Steel, Timber, Aluminium
        self.material = None

        # Uniformly distributed loads
        # Applied in the global coordinate system
        self.udl_x = 0.0      # horizontal UDL (kN/m)
        self.udl_x = 0.0      # vertical UDL (kN/m)

        # Analysis results
        self.axial_force = 0.0        # axial force
        self.stress = 0.0       # axial stress
        self.utilisation = 0.0  # demand / capacity ratio

        # General property dictionary
        # Can store values such as:
        # E, A, I, density, section name, etc.
        self.properties = {}

        # End moments or other moment results
        self.bending_moments = {}

        # Create a consistent member name
        # Sorting ensures:
        # A-B and B-A become the same name
        labels = sorted([
            self.start_node.label,
            self.end_node.label
        ])

        self.name = "-".join(labels)

    def length(self):
        """
        Calculate member length from node coordinates.

        Returns
        -------
        float
            Member length.
        """
        dx = (self.end_node.coords[0] - self.start_node.coords[0])
        dy = (self.end_node.coords[1] - self.start_node.coords[1])
        return math.hypot(dx, dy)

    def direction_cosines(self):
        """
        Calculate direction cosines.

        These are the x and y components
        of a unit vector along the member.

        Returns
        -------
        (cx, cy)

        Example:
            Horizontal member -> (1, 0)
            Vertical member   -> (0, 1)
            45° member        -> (0.707, 0.707)
        """
        dx = (self.end_node.coords[0] - self.start_node.coords[0])
        dy = (self.end_node.coords[1] - self.start_node.coords[1])
        L = self.length()
        return (dx/L, dy/L)