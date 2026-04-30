import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import time

# --- CONFIGURATION ---
ST_YELLOW = "#ffcd00"
ST_BLACK = "#1a1a1a"
HEX_RADIUS = 13

st.set_page_config(page_title="CAT Autonomous Command", layout="wide")

# Custom CSS to match the CAT vibe
st.markdown(f"""
    <style>
    .main {{ background-color: #000000; color: white; }}
    div.stButton > button {{ background-color: {ST_YELLOW}; color: black; font-weight: bold; width: 100%; }}
    .stat-box {{ border-left: 4px solid {ST_YELLOW}; padding: 10px; background: #1a1a1a; margin-bottom: 10px; }}
    </style>
    """, unsafe_allow_html=True)

# --- SESSION STATE (To keep the simulation running) ---
if 'running' not in st.session_state:
    st.session_state.running = False
if 'total_tons' not in st.session_state:
    st.session_state.total_tons = 0

# --- SIDEBAR CONTROLS ---
with st.sidebar:
    st.header("FLEET CONTROL")
    t_count = st.number_input("Active Units", 1, 8, 8)
    sim_speed = st.select_slider("Simulation Speed", options=[1, 2, 5, 10], value=1)
    
    if st.button("ENGAGE FLEET"):
        st.session_state.running = True
    if st.button("HALT"):
        st.session_state.running = False
        st.rerun()

# --- THE MAPPING FUNCTION (The "Output" look) ---
def create_hex_map():
    fig = go.Figure()

    # Operational Boundary
    poly_x = [120, 480, 450, 120, 120]
    poly_y = [20, 20, 280, 280, 20]
    fig.add_trace(go.Scatter(x=poly_x, y=poly_y, mode='lines', 
                             line=dict(color=ST_YELLOW, width=2, dash='dash'),
                             showlegend=False))

    # Static Hex Grid (Example placeholders)
    # In a full version, you'd loop through your hexes here
    fig.add_trace(go.Scatter(x=[300], y=[150], mode='markers',
                             marker=dict(symbol='hexagon', size=20, color='#00cc44'),
                             name='Safe Zone'))

    # Truck Placeholder (This represents your T1-T8 trucks)
    for i in range(t_count):
        y_pos = 40 + (i * 35)
        fig.add_trace(go.Scatter(x=[60], y=[y_pos], mode='markers+text',
                                 text=f"T{i+1}", textfont=dict(color="black", size=9),
                                 marker=dict(symbol='square', size=22, color=ST_YELLOW),
                                 showlegend=False))

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

# --- MAIN DISPLAY ---
col1, col2 = st.columns([1, 4])

with col1:
    st.markdown(f'<div class="stat-box"><p style="color:{ST_YELLOW}; font-size:12px;">SYSTEM STATUS</p><b>' + 
                ("OPERATING" if st.session_state.running else "STANDBY") + '</b></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="stat-box"><p style="color:{ST_YELLOW}; font-size:12px;">PAYLOAD MOVED</p><b>{st.session_state.total_tons} Tons</b></div>', unsafe_allow_html=True)

with col2:
    placeholder = st.empty()
    
    # Simulation Loop
    if st.session_state.running:
        for _ in range(100): # Run for 100 ticks
            fig = create_hex_map()
            placeholder.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
            time.sleep(0.1 / sim_speed)
    else:
        fig = create_hex_map()
        placeholder.plotly_chart(fig, use_container_width=True)
