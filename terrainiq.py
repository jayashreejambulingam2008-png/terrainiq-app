import streamlit as st
import plotly.graph_objects as go
import numpy as np
import time

# --- CONFIGURATION ---
CAT_YELLOW = "#ffcd00"
CAT_BLACK = "#1a1a1a"
HEX_RADIUS = 13

st.set_page_config(page_title="CAT Autonomous Command", layout="wide")

# Custom CSS to match your screenshot exactly
st.markdown(f"""
    <style>
    .main {{ background-color: #000000; color: white; }}
    [data-testid="stSidebar"] {{ background-color: {CAT_BLACK}; border-right: 2px solid #333; }}
    div.stButton > button {{ background-color: {CAT_YELLOW}; color: black; font-weight: bold; border: none; border-radius: 0px; }}
    .stat-box {{ background: black; border-left: 4px solid {CAT_YELLOW}; padding: 10px; margin-bottom: 10px; }}
    .stat-label {{ color: {CAT_YELLOW}; font-size: 0.7rem; font-weight: bold; text-transform: uppercase; }}
    .stat-value {{ font-size: 1.2rem; font-family: monospace; font-weight: bold; color: white; }}
    </style>
    """, unsafe_allow_html=True)

# --- SESSION STATE ---
if 'running' not in st.session_state:
    st.session_state.running = False
if 'total_tons' not in st.session_state:
    st.session_state.total_tons = 14400

# --- SIDEBAR UI ---
with st.sidebar:
    st.markdown(f'<div class="stat-box"><div class="stat-label">System Status</div><div class="stat-value">{"OPERATING" if st.session_state.running else "SHUTDOWN"}</div></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="stat-box"><div class="stat-label">Payload Moved (Tons)</div><div class="stat-value">{st.session_state.total_tons:,}</div></div>', unsafe_allow_html=True)
    
    st.caption("OPERATIONAL BOUNDARY POLYGON")
    st.text_area("", "[[120, 20], [480, 20], [450, 280], [120, 280]]", height=70, label_visibility="collapsed")
    
    st.caption("ACTIVE UNITS")
    t_count = st.number_input("", 1, 8, 8, label_visibility="collapsed")
    
    if st.button("ENGAGE FLEET"): st.session_state.running = True
    st.button("10X SPEED", use_container_width=True) # Decorative
    if st.button("HALT"): 
        st.session_state.running = False
        st.rerun()
    st.button("GENERATE MAP", use_container_width=True)

# --- PLOTLY GRID GENERATION ---
def get_hex_coords(cx, cy, r):
    angles = np.linspace(0, 2*np.pi, 7)
    return cx + r * np.cos(angles + np.pi/2), cy + r * np.sin(angles + np.pi/2)

def create_full_simulation_map(frame):
    fig = go.Figure()
    
    # Operational Boundary
    poly = np.array([[120, 20], [480, 20], [450, 280], [120, 280], [120, 20]])
    fig.add_trace(go.Scatter(x=poly[:,0], y=poly[:,1], mode='lines', line=dict(color=CAT_YELLOW, width=2, dash='dash'), showlegend=False))

    # Hex Grid Logic (Replicating your screenshot's "Far End Fill")
    hex_width = np.sqrt(3) * HEX_RADIUS
    vert_spacing = (2 * HEX_RADIUS) * 0.75
    
    for r in range(13):
        for c in range(18):
            hx = 150 + c * hex_width + (hex_width/2 if r % 2 == 1 else 0)
            hy = 40 + r * vert_spacing
            
            # Color logic based on "Far End Fill"
            # Far right column = Red, Middle-Right = Blue, Rest = Green
            color = "#00cc44" # Safe Traverse (Green)
            if c > 15: color = "#cc0000" # Full Zone (Red)
            elif c > 14: color = "#0055ff" # Filling (Blue)
            
            hx_pts, hy_pts = get_hex_coords(hx, hy, HEX_RADIUS-1)
            fig.add_trace(go.Scatter(x=hx_pts, y=hy_pts, fill="toself", mode='lines', 
                                     fillcolor=color, line=dict(color="black", width=0.5), showlegend=False, hoverinfo='skip'))

    # Add Trucks (T1 - T8)
    # They move slightly based on 'frame'
    for i in range(t_count):
        tx = 180 + (i * 30) + (frame % 100 if st.session_state.running else 0)
        ty = 80 + (i * 20)
        fig.add_trace(go.Scatter(x=[tx], y=[ty], mode='markers+text', 
                                 text=f"T{i+1}", textfont=dict(color="black", size=8, family="Arial Black"),
                                 marker=dict(symbol='square', size=20, color=CAT_YELLOW, line=dict(color='black', width=2)),
                                 showlegend=False))

    fig.update_layout(
        template="plotly_dark", paper_bgcolor='black', plot_bgcolor='black',
        xaxis=dict(range=[0, 550], visible=False), yaxis=dict(range=[0, 320], visible=False, scaleanchor="x"),
        margin=dict(l=0, r=0, t=0, b=0), height=700
    )
    return fig

# --- MAIN VIEW ---
st.markdown(f"<h2 style='color:white; margin-top:-50px;'>CATERPILLAR <span style='font-size:15px;'>®</span> <span style='float:right; font-size:14px; color:{CAT_YELLOW};'>V19.0 - FAR END FILL</span></h2>", unsafe_allow_html=True)

placeholder = st.empty()

if st.session_state.running:
    for i in range(100):
        if not st.session_state.running: break
        fig = create_full_simulation_map(i * 2)
        placeholder.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False}, key=f"sim_{i}")
        time.sleep(0.05)
else:
    placeholder.plotly_chart(create_full_simulation_map(0), use_container_width=True, key="static")
