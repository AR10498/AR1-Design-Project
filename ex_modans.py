#!/usr/bin/env python
# coding: utf-8

# ### Exercise model answer

# In[ ]:


### Compute combined stresses (axial + bending) for all members.
### =======
### MODEL ANSWER
### ==========
import numpy as np 

def calculate_stresses(members):
    stresses = {}
    max_stress = 0.0
    for m in members.values():
        props = m.properties
        A = props['A'] 
        if m.rotation==0:     
            I = props['I_xx'] 
            y = props['y_xx']
        else: 
            I = props['I_yy'] 
            y = props['y_yy']
    
        # Axial stress
        F = m.force 
        sigma_axial = (1e3*F) / (A*1e2)  # tension positive #N/mm^2
    
        # Bending stress
        sigma_bending_max_abs = 0.0
    
        moments = m.moments

        M_curve = moments["points"]
        if len(M_curve) > 0:
            M_max = moments["M_max"]
            M_min = moments["M_min"]
            M_max_abs = max(abs(M_max), abs(M_min))
            sigma_bending_max_abs = ((M_max_abs)*1e6) * (y*10) / (I*1e4)
    
        # Combined total stress (select most critical)
        sigma_total_pos = sigma_axial + sigma_bending_max_abs
        sigma_total_neg = sigma_axial - sigma_bending_max_abs
        sigma_total = sigma_total_pos if abs(sigma_total_pos) >= abs(sigma_total_neg) else sigma_total_neg
    
        m.stress = sigma_total
        stresses[m.name] = sigma_total
        max_stress = max(max_stress, abs(sigma_total))
    return max_stress, stresses

max_stress,stresses = calculate_stresses(members)

viz.visualize_truss(nodes, members, textscale=0.9, show_reactions=True, plot_loads=True, show_node_labels=True, show_load_labels=True, show_stresses=True, show_colorbar=True )

