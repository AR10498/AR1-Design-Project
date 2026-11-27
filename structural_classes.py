import math

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
    Structural node (joint).

    A node stores its coordinates, support condition,
    applied loads, support reactions and connections
    to other nodes.

    Parameters
    ----------
    id : int
        Unique node number.

    coords : tuple
        Coordinates in the form (x, y, z).

    label : str, optional
        Node name. If not supplied, a label is
        generated automatically.

    condition : str, optional
        Support condition such as:
        - "Pinned"
        - "Fixed"
        - "Reaction_Pinned"
        - "Reaction_Roller_H"

    Attributes
    ----------
    label : str
        Node label.

    coords : tuple
        Node coordinates.

    F_x, F_y : float
        Applied nodal loads.

    R_x, R_y : float
        Support reactions.

    connectivity : list
        Labels of connected nodes.
    """
    def __init__(self, id, coords, label=None, condition="Pinned"):

        self.id = id
        self.coords = tuple(float(n) for n in coords)

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
        
    @property
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
        
    def __repr__(self):
        return f"Node({self.label}, {self.coords})"

    


# MEMBER
class Member:
    """
    Structural member connecting two nodes.

    A member stores its end nodes, applied loads,
    material properties and analysis results.

    Parameters
    ----------
    id : int
        Unique member number.

    start_node : Node
        Node at one end of the member.

    end_node : Node
        Node at the other end of the member.

    Attributes
    ----------
    name : str
        Member label (e.g. A-B).

    force : float
        Axial force in the member.

    stress : float
        Member stress.

    utilisation : float
        Utilisation ratio.

    properties : dict
        Member properties such as area or stiffness.

    moments : dict
        Bending moment results.
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
        self.udl_y = 0.0      # vertical UDL (kN/m)

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

    @property
    def vector(self):
        """
        Member vector from start node to end node.
    
        Returns
        -------
        (dx, dy)
        """
        return ( self.end_node.coords[0] - self.start_node.coords[0], 
                 self.end_node.coords[1] - self.start_node.coords[1] )

    @property
    def length(self):
        """
        Calculate member length from node coordinates.

        Returns
        -------
        float
            Member length.
        """
        dx, dy = self.vector
        return math.hypot(dx, dy)

    @property
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
        dx, dy = self.vector
        L = self.length
        return (dx / L, dy / L)

    def __repr__(self):
        return f"Member({self.name})"