import streamlit as st
import plotly.graph_objects as go
import numpy as np
import time

# --- CONFIGURATION ---
CAT_YELLOW = "#ffcd00"
CAT_BLACK = "#1a1a1a"
HEX_RADIUS = 13

st.set_page_config(page_title="CAT Autonomous Command", layout="wide")

# Custom CSS to match the UI screenshot
st.markdown(f"""
    <style>
    .main {{ background-color: #000000; color: white; }}
    [data-testid="stSidebar"] {{ background-color: {CAT_BLACK}; border-right: 2px solid #333; }}
    div.stButton > button {{ background-color: {CAT_YELLOW}; color: black; font-weight: bold; border-radius: 0px; border: none; }}
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

# --- SIDEBAR ---
with st.sidebar:
    st.markdown(f'<div class="stat-box"><div class="stat-label">System Status</div><div class="stat-value">{"OPERATING" if st.session_state.running else "SHUTDOWN"}</div></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="stat-box"><div class="stat-label">Payload Moved (Tons)</div><div class="stat-value">{st.session_state.total_tons:,}</div></div>', unsafe_allow_html=True)
    
    st.caption("OPERATIONAL BOUNDARY")
    st.text_area("", "[[120, 20], [480, 20], [450, 280], [120, 280]]", height=60, label_visibility="collapsed")
    
    t_count = st.number_input("ACTIVE UNITS", 1, 8, 8)
    
    if st.button("ENGAGE FLEET"):
        st.session_state.running = True
    
    st.button("10X SPEED", use_container_width=True)
    
    if st.button("HALT"):
        st.session_state.running = False
        st.rerun()

# --- HELPER: HEXAGON MATH ---
def get_hex_shape(cx, cy, r):
    angles = np.linspace(0, 2*np.pi, 7)
    return cx + r * np.cos(angles + np.pi/2), cy + r * np.sin(angles + np.pi/2)

# --- MAP GENERATOR ---
def create_map(step):
    fig = go.Figure()

    # 1. Draw Hexagonal Grid (Far End Fill logic)
    hex_width = np.sqrt(3) * HEX_RADIUS
    vert_spacing = (2 * HEX_RADIUS) * 0.75
    
    for r in range(13):
        for c in range(18):
            hx = 150 + c * hex_width + (hex_width/2 if r % 2 == 1 else 0)
            hy = 40 + r * vert_spacing
            
            # Color logic: Red (Right), Blue (Transition), Green (Safe)
            color = "#00cc44"
            if c > 15: color = "#cc0000"
            elif c > 14: color = "#0055ff"
            
            x_pts, y_pts = get_hex_shape(hx, hy, HEX_RADIUS-1)
            fig.add_trace(go.Scatter(x=x_pts, y=y_pts, fill="toself", mode='lines', 
                                     fillcolor=color, line=dict(color="black", width=0.5), showlegend=False, hoverinfo='skip'))

    # 2. Add Routes (As per the picture)
    # Haul Path (Solid Yellow)
    fig.add_trace(go.Scatter(x=[180, 250, 350, 480], y=[210, 230, 190, 210], 
                             mode='lines', line=dict(color=CAT_YELLOW, width=2.5), name="Haul Path"))
    # Return Path (Dashed White)
    fig.add_trace(go.Scatter(x=[480, 400, 300, 180], y=[210, 160, 150, 110], 
                             mode='lines', line=dict(color="white", width=2, dash='dot'), name="Return Path"))

    # 3. Add Trucks (Animated)
    for i in range(t_count):
        # Movement logic
        offset = (step + (i * 35)) % 300
        tx, ty = 160 + offset, 50 + (i * 28)
        
        fig.add_trace(go.Scatter(x=[tx], y=[ty], mode='markers+text', 
                                 text=f"T{i+1}", textfont=dict(color="black", size=8, family="Arial Black"),
                                 marker=dict(symbol='square', size=20, color=CAT_YELLOW, line=dict(color="black", width=1.5)),
                                 showlegend=False))

    # Layout Configuration
    fig.update_layout(
        template="plotly_dark", paper_bgcolor='black', plot_bgcolor='black',
        xaxis=dict(range=[0, 550], visible=False), yaxis=dict(range=[0, 320], visible=False, scaleanchor="x"),
        margin=dict(l=0, r=0, t=0, b=0), height=650,
        hovermode=False, dragmode=False
    )
    return fig

# --- MAIN RENDER ---
st.markdown(f"### CATERPILLAR ® <span style='float:right; font-size:14px; color:{CAT_YELLOW};'>V19.0 - FAR END FILL</span>", unsafe_allow_html=True)

map_placeholder = st.empty()

if st.session_state.running:
    step = 0
    # Use a loop to update the placeholder
    while st.session_state.running:
        fig = create_map(step)
        
        # We update the chart using the same placeholder to keep it in position
        # We append the 'step' to the key to satisfy Streamlit's unique ID requirement
        map_placeholder.plotly_chart(
            fig, 
            use_container_width=True, 
            config={'displayModeBar': False}, 
            key=f"sim_{step}" 
        )
        
        step += 4
        time.sleep(0.01)
        
        # Increment tonnage
        if step % 50 == 0:
            st.session_state.total_tons += 40
else:
    # Static view when system is SHUTDOWN
    map_placeholder.plotly_chart(create_map(0), use_container_width=True, config={'displayModeBar': False}, key="static_view")
