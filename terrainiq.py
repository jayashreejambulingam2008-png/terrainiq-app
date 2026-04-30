import streamlit as st
import plotly.graph_objects as go
import time
import math

# --- CONFIGURATION ---
CAT_YELLOW = "#ffcd00"
CAT_BLACK = "#1a1a1a"

st.set_page_config(page_title="CAT Autonomous Command", layout="wide")

# Custom CSS for the CAT branding
st.markdown(f"""
    <style>
    .main {{ background-color: #000000; color: white; }}
    div.stButton > button {{ background-color: {CAT_YELLOW}; color: black; font-weight: bold; width: 100%; }}
    .stat-box {{ border-left: 4px solid {CAT_YELLOW}; padding: 10px; background: #1a1a1a; margin-bottom: 10px; border-radius: 0 5px 5px 0; }}
    </style>
    """, unsafe_allow_html=True)

# --- SESSION STATE ---
if 'running' not in st.session_state:
    st.session_state.running = False
if 'total_tons' not in st.session_state:
    st.session_state.total_tons = 0

# --- HEADER ---
st.markdown(f"<h1 style='color:{CAT_YELLOW}; font-family:Arial Black;'>CATERPILLAR <span style='font-size:15px; vertical-align:middle;'>®</span></h1>", unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.header("FLEET CONTROL")
    t_count = st.number_input("Active Units", 1, 8, 8)
    sim_speed = st.select_slider("Simulation Speed", options=[1, 2, 5, 10], value=1)
    
    btn_col1, btn_col2 = st.columns(2)
    with btn_col1:
        if st.button("ENGAGE"):
            st.session_state.running = True
    with btn_col2:
        if st.button("HALT"):
            st.session_state.running = False
            st.rerun()

# --- HELPER: CREATE THE MAP ---
def create_hex_map(frame_offset=0):
    fig = go.Figure()

    # Boundary
    poly_x = [120, 480, 450, 120, 120]
    poly_y = [20, 20, 280, 280, 20]
    fig.add_trace(go.Scatter(x=poly_x, y=poly_y, mode='lines', 
                             line=dict(color=CAT_YELLOW, width=2, dash='dash'),
                             showlegend=False, hoverinfo='skip'))

    # Draw Hexagons (Simplified for performance)
    # In a full simulation, these would change color based on fill height
    fig.add_trace(go.Scatter(x=[300, 330, 360], y=[150, 150, 150], mode='markers',
                             marker=dict(symbol='hexagon', size=18, color='#00cc44', line=dict(color='black', width=1)),
                             name='Terrain'))

    # Draw Trucks (Animated based on frame_offset)
    for i in range(t_count):
        # Calculate a simple movement back and forth for the demo
        move_x = 60 + (frame_offset % 400) if st.session_state.running else 60
        y_pos = 40 + (i * 35)
        
        fig.add_trace(go.Scatter(
            x=[move_x], y=[y_pos], 
            mode='markers+text',
            text=f"T{i+1}", 
            textfont=dict(color="black", size=8, family="Arial Black"),
            marker=dict(symbol='square', size=22, color=CAT_YELLOW, line=dict(color='black', width=2)),
            showlegend=False
        ))

    fig.update_layout(
        template="plotly_dark",
        xaxis=dict(range=[0, 520], visible=False),
        yaxis=dict(range=[0, 320], visible=False, scaleanchor="x"),
        margin=dict(l=0, r=0, t=0, b=0),
        height=600,
        paper_bgcolor='black',
        plot_bgcolor='black'
    )
    return fig

# --- UI LAYOUT ---
col_stats, col_map = st.columns([1, 4])

with col_stats:
    status = "OPERATING" if st.session_state.running else "STANDBY"
    st.markdown(f'<div class="stat-box"><p style="color:{CAT_YELLOW}; font-size:10px; margin:0;">SYSTEM STATUS</p><b style="font-size:18px;">{status}</b></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="stat-box"><p style="color:{CAT_YELLOW}; font-size:10px; margin:0;">PAYLOAD MOVED</p><b style="font-size:18px;">{st.session_state.total_tons:,} TONS</b></div>', unsafe_allow_html=True)

with col_map:
    # This is the empty space we fill with the map
    map_placeholder = st.empty()

    if st.session_state.running:
        # Loop for animation
        for i in range(200):
            if not st.session_state.running: break
            
            # Create unique key for every frame to avoid DuplicateElementId
            current_fig = create_hex_map(frame_offset=i * sim_speed * 5)
            map_placeholder.plotly_chart(
                current_fig, 
                use_container_width=True, 
                config={'displayModeBar': False},
                key=f"sim_frame_{i}" 
            )
            
            # Update Tonnage occasionally
            if i % 20 == 0:
                st.session_state.total_tons += (400 * t_count)
            
            time.sleep(0.05)
    else:
        # Static Map when not running
        static_fig = create_hex_map()
        map_placeholder.plotly_chart(static_fig, use_container_width=True, key="initial_map")
