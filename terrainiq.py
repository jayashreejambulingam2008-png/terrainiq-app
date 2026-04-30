import streamlit as st
import plotly.graph_objects as go
import numpy as np
import time

# --- CONSTANTS ---
CAT_YELLOW = "#ffcd00"
HEX_RADIUS = 13

st.set_page_config(page_title="CAT Autonomous Command", layout="wide")

# Custom CSS for that specific "Command Center" look
st.markdown(f"""
    <style>
    .main {{ background-color: #000000; color: white; }}
    [data-testid="stSidebar"] {{ background-color: #1a1a1a; border-right: 2px solid #333; }}
    div.stButton > button {{ background-color: {CAT_YELLOW}; color: black; font-weight: bold; border-radius: 0px; border: none; }}
    .stat-box {{ background: black; border-left: 4px solid {CAT_YELLOW}; padding: 10px; margin-bottom: 10px; }}
    .stat-label {{ color: {CAT_YELLOW}; font-size: 0.7rem; font-weight: bold; }}
    .stat-value {{ font-size: 1.2rem; font-family: monospace; font-weight: bold; color: white; }}
    </style>
    """, unsafe_allow_html=True)

if 'running' not in st.session_state: st.session_state.running = False
if 'total_tons' not in st.session_state: st.session_state.total_tons = 14400

# --- SIDEBAR ---
with st.sidebar:
    st.markdown(f'<div class="stat-box"><div class="stat-label">SYSTEM STATUS</div><div class="stat-value">{"OPERATING" if st.session_state.running else "SHUTDOWN"}</div></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="stat-box"><div class="stat-label">PAYLOAD MOVED (TONS)</div><div class="stat-value">{st.session_state.total_tons:,}</div></div>', unsafe_allow_html=True)
    
    st.caption("OPERATIONAL BOUNDARY POLYGON")
    st.code("[[120, 20], [480, 20], \n [450, 280], [120, 280]]")
    
    t_count = st.number_input("ACTIVE UNITS", 1, 8, 8)
    
    if st.button("ENGAGE FLEET", use_container_width=True): st.session_state.running = True
    st.button("10X SPEED", use_container_width=True)
    if st.button("HALT", use_container_width=True): 
        st.session_state.running = False
        st.rerun()

# --- UNIQUE PATH DATA ---
# This replicates the jagged branching paths from your screenshot
PATHS = {
    0: {'x': [130, 200, 300, 480], 'y': [50, 70, 60, 80]},
    1: {'x': [130, 220, 350, 485], 'y': [80, 110, 100, 120]},
    2: {'x': [130, 180, 280, 480], 'y': [120, 140, 130, 150]},
    3: {'x': [130, 250, 380, 485], 'y': [150, 180, 170, 190]},
    4: {'x': [130, 210, 320, 480], 'y': [190, 220, 210, 230]},
    5: {'x': [130, 190, 300, 485], 'y': [220, 250, 240, 260]},
    6: {'x': [130, 240, 360, 480], 'y': [250, 270, 260, 275]},
    7: {'x': [130, 170, 290, 485], 'y': [270, 290, 280, 295]}
}

def get_hex_shape(cx, cy, r):
    angles = np.linspace(0, 2*np.pi, 7)
    return cx + r * np.cos(angles + np.pi/2), cy + r * np.sin(angles + np.pi/2)

def draw_map(step):
    fig = go.Figure()
    
    # 1. Hex Grid
    hex_width, vert_spacing = np.sqrt(3) * HEX_RADIUS, (2 * HEX_RADIUS) * 0.75
    for r in range(13):
        for c in range(18):
            hx, hy = 150 + c * hex_width + (hex_width/2 if r % 2 == 1 else 0), 40 + r * vert_spacing
            color = "#00cc44"
            if c > 15: color = "#cc0000"
            elif c > 14: color = "#0055ff"
            
            x_pts, y_pts = get_hex_shape(hx, hy, HEX_RADIUS-1)
            fig.add_trace(go.Scatter(x=x_pts, y=y_pts, fill="toself", mode='lines', 
                                     fillcolor=color, line=dict(color="black", width=0.5), showlegend=False))

    # 2. Unique Paths & Trucks
    for i in range(t_count):
        path = PATHS[i]
        # Draw the Return Path (Dashed White)
        fig.add_trace(go.Scatter(x=path['x'], y=path['y'], mode='lines', 
                                 line=dict(color="white", width=1, dash='dot'), opacity=0.3, showlegend=False))
        
        # Calculate truck position along its unique path
        progress = (step + (i * 20)) % 100
        # Simple interpolation for movement
        idx = int(progress / 34) % (len(path['x'])-1)
        tx = path['x'][idx] + (path['x'][idx+1] - path['x'][idx]) * (progress % 34 / 34)
        ty = path['y'][idx] + (path['y'][idx+1] - path['y'][idx]) * (progress % 34 / 34)

        fig.add_trace(go.Scatter(x=[tx], y=[ty], mode='markers+text', 
                                 text=f"T{i+1}", textfont=dict(color="black", size=8, family="Arial Black"),
                                 marker=dict(symbol='square', size=20, color=CAT_YELLOW, line=dict(color="black", width=1)),
                                 showlegend=False))

    fig.update_layout(
        template="plotly_dark", paper_bgcolor='black', plot_bgcolor='black',
        xaxis=dict(range=[0, 550], visible=False), yaxis=dict(range=[0, 320], visible=False, scaleanchor="x"),
        margin=dict(l=0, r=0, t=0, b=0), height=600, hovermode=False
    )
    return fig

# --- MAIN RENDER ---
st.markdown(f"### CATERPILLAR ® <span style='float:right; font-size:14px; color:{CAT_YELLOW};'>V19.0 - FAR END FILL</span>", unsafe_allow_html=True)

placeholder = st.empty()

if st.session_state.running:
    # This loop updates the placeholder directly, which prevents the whole page from blinking
    for s in range(200):
        if not st.session_state.running: break
        with placeholder.container():
            fig = draw_map(s)
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False}, key=f"v_{s}")
        time.sleep(0.01)
else:
    placeholder.plotly_chart(draw_map(0), use_container_width=True, config={'displayModeBar': False}, key="init")
