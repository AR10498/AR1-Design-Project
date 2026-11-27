import math
import pandas as pd

def assign_materials_to_members(members, manual_assignments, material_df, default_material):
    """
    Assign material properties to members based on manual_assignments.
    Behavior:
      - manual_assignments: dict {material_label: [member_names]}
      - If a property is missing, use sensible default values.
      - If a member is not listed, assign default_material.
    """
    # Reverse mapping: member_name -> material_label
    member_to_material = {}
    for mat_label, member_list in manual_assignments.items():
        for member_name in member_list:
            member_to_material[member_name] = mat_label

    # Assign materials to each member
    for m in members.values():
        mat_label = member_to_material.get(m.name, default_material)

        m.material = mat_label
        props = material_df[mat_label]

        for prop in props.keys():
            m.properties[prop] = props[prop] 

# ==========================
#   SUPPORT CONDITIONS
# ==========================
def apply_joint_conditions(nodes, joint_conditions):
    for n in nodes.values():
        n.condition = "Pinned"
    for condition, labels in joint_conditions.items():
        for label in labels:
            if label not in nodes:
                print(  f"Warning: node '{label}' not found "
                        f"when assigning {condition}"  )
                continue
            nodes[label].condition = condition

# ==========================
#   LOAD ASSIGNMENT
# ==========================
def calculate_total_forces(nodes, members):
    """
    Apply global UDLs (uniformly distributed loads) to members,
    Vertical loads (Fy) always act straight down (+Y downward),
    and horizontal loads (Fx) always act left-to-right (+X).
    Equivalent nodal loads are computed and added to nodes.
    """
    for n in nodes.values():
        n.F_xtotal = n.F_x
        n.F_ytotal = n.F_y
    
    for m in members.values():                
        Fx_udl = m.F_x  # global X
        Fy_udl = m.F_y  # global Y (downward positive)
        
        L = m.length
        
        # Equivalent nodal loads due to global UDL 
        Fx_eq = Fx_udl * L / 2
        Fy_eq = Fy_udl * L / 2
        
        # Add loads in global direction 
        m.node_start().F_xtotal += Fx_eq
        m.node_start().F_ytotal += Fy_eq
        m.node_end().F_xtotal += Fx_eq
        m.node_end().F_ytotal += Fy_eq
