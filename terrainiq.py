import streamlit as st
import plotly.graph_objects as go
import math

# --- PAGE CONFIG ---
st.set_page_config(page_title="CAT Autonomous Command", layout="wide")

st.title("CATERPILLAR® Autonomous Routing")
st.sidebar.header("Fleet Control")

# --- INPUTS ---
t_count = st.sidebar.slider("Active Units", 1, 8, 4)
sim_speed = st.sidebar.selectbox("Sim Speed", [1, 2, 5, 10])

# --- MAPPING LOGIC (Replacement for Pygame) ---
def draw_map():
    fig = go.Figure()

    # Example Boundary
    poly_x = [120, 480, 450, 120, 120]
    poly_y = [20, 20, 280, 280, 20]
    
    fig.add_trace(go.Scatter(x=poly_x, y=poly_y, mode='lines', 
                             line=dict(color='#ffcd00', dash='dash'),
                             name='Boundary'))

    # Add Truck Placeholders
    for i in range(t_count):
        fig.add_trace(go.Scatter(x=[50], y=[40 + (i*35)], 
                                 mode='markers+text',
                                 marker=dict(symbol='square', size=15, color='#ffcd00'),
                                 text=f"T{i+1}", textposition="top center",
                                 name=f"Truck {i+1}"))

    fig.update_layout(
        template="plotly_dark",
        xaxis=dict(visible=False),
        yaxis=dict(visible=False, scaleanchor="x"),
        margin=dict(l=0, r=0, t=0, b=0),
        height=600,
        paper_bgcolor='black',
        plot_bgcolor='black'
    )
    return fig

# --- DISPLAY ---
map_plot = draw_map()
st.plotly_chart(map_plot, use_container_width=True)

st.success(f"Fleet of {t_count} units initialized and standing by.")
