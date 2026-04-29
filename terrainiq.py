import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import random
import math
from datetime import datetime

st.set_page_config(page_title="CAT Autonomous Command", layout="wide", page_icon="🚛")

# Custom CSS for CAT styling
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #1a1a1a 0%, #000000 100%);
    }
    .cat-header {
        background: #ffcd00;
        padding: 15px 30px;
        border-radius: 5px;
        margin-bottom: 20px;
        color: #000;
    }
    .cat-header h1 {
        margin: 0;
        font-family: 'Arial Black', sans-serif;
        display: inline-block;
    }
    .stat-box {
        background: #000;
        border-left: 4px solid #ffcd00;
        padding: 15px;
        margin: 10px 0;
        border-radius: 5px;
    }
    .stat-label {
        font-size: 0.7rem;
        color: #ffcd00;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .stat-value {
        font-size: 1.8rem;
        font-weight: bold;
        font-family: monospace;
    }
    .control-panel {
        background: #1a1a1a;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #333;
    }
    .legend {
        background: rgba(0,0,0,0.8);
        padding: 10px;
        border-radius: 5px;
        font-size: 0.7rem;
    }
    div.stButton > button {
        background-color: #ffcd00;
        color: #000;
        font-weight: bold;
        width: 100%;
    }
    div.stButton > button:hover {
        background-color: #e5b800;
    }
</style>
""", unsafe_allow_html=True)

# ============ HEXAGON CLASS ============
class Hexagon:
    def __init__(self, x, y, lane_id):
        self.x = x
        self.y = y
        self.lane_id = lane_id
        self.height = random.uniform(0, 1.5)
        self.locked = False
        self.dump_count = 0

    def get_color(self):
        if self.height >= 2.4:
            return '#cc0000'  # Full
        elif self.height > 0.8:
            return '#0055ff'  # Filling
        else:
            return '#00cc44'  # Empty
        if self.locked:
            return '#555555'

# ============ TRUCK CLASS ============
class Truck:
    def __init__(self, truck_id, start_x, start_y, lane_id):
        self.id = f"CAT-{truck_id:03d}"
        self.start_x = start_x
        self.start_y = start_y
        self.x = start_x
        self.y = start_y
        self.lane_id = lane_id
        self.status = "IDLE"  # IDLE, HAULING, RETURNING
        self.target = None
        self.progress = 0.0
        self.speed = 0.02
        self.loads = 0

    def update(self, hexes, stats):
        if self.status == "IDLE":
            # Find furthest empty hex in assigned lane
            targets = [h for h in hexes if h.lane_id == self.lane_id and not h.locked and h.height < 2.4]
            if targets:
                self.target = max(targets, key=lambda h: h.x)
                self.target.locked = True
                self.status = "HAULING"
                self.progress = 0
        
        elif self.status in ["HAULING", "RETURNING"]:
            self.progress += (0.015 if self.status == "HAULING" else 0.025)
            
            # L-Shape Path Logic
            if self.status == "HAULING":
                p_start = (self.start_x, self.start_y)
                p_mid = (self.start_x, self.target.y)
                p_end = (self.target.x, self.target.y)
            else:
                p_start = (self.target.x, self.target.y)
                p_mid = (self.start_x, self.target.y)
                p_end = (self.start_x, self.start_y)

            if self.progress < 0.5:
                s = self.progress * 2
                self.x = p_start[0] + (p_mid[0] - p_start[0]) * s
                self.y = p_start[1] + (p_mid[1] - p_start[1]) * s
            elif self.progress < 1.0:
                s = (self.progress - 0.5) * 2
                self.x = p_mid[0] + (p_end[0] - p_mid[0]) * s
                self.y = p_mid[1] + (p_end[1] - p_mid[1]) * s
            else:
                if self.status == "HAULING":
                    self.target.height = min(2.5, self.target.height + 0.7)
                    self.target.locked = False
                    self.target.dump_count += 1
                    self.status = "RETURNING"
                    self.progress = 0
                    stats['tonnage'] += 400
                    stats['dumps'] += 1
                    self.loads += 1
                else:
                    self.status = "IDLE"
                    self.x = self.start_x
                    self.y = self.start_y
                    self.target = None

    def get_status_color(self):
        if self.status == "HAULING":
            return '#00ff00'
        elif self.status == "RETURNING":
            return '#ffcd00'
        else:
            return '#555555'

# ============ MAIN APP ============
def main():
    # Initialize session state
    if 'hexes' not in st.session_state:
        st.session_state.hexes = []
    if 'trucks' not in st.session_state:
        st.session_state.trucks = []
    if 'stats' not in st.session_state:
        st.session_state.stats = {'tonnage': 0, 'dumps': 0}
    if 'sim_active' not in st.session_state:
        st.session_state.sim_active = False
    if 'initialized' not in st.session_state:
        st.session_state.initialized = False

    # Header
    st.markdown("""
    <div class="cat-header">
        <h1>CATERPILLAR ®</h1>
        <span style="float: right; background: #000; color: #ffcd00; padding: 5px 10px; border-radius: 3px;">
            AUTONOMOUS COMMAND CENTER
        </span>
    </div>
    """, unsafe_allow_html=True)

    col_side, col_main = st.columns([1, 3])

    with col_side:
        st.markdown('<div class="control-panel">', unsafe_allow_html=True)

        # Status Box
        if st.session_state.initialized and st.session_state.sim_active:
            status_text = "🔥 OPERATING"
            status_color = "#00cc44"
        elif st.session_state.initialized:
            status_text = "⚪ READY"
            status_color = "#ffcd00"
        else:
            status_text = "⚪ STANDBY"
            status_color = "#888"

        st.markdown(f"""
        <div class="stat-box">
            <div class="stat-label">FLEET STATUS</div>
            <div class="stat-value" style="color: {status_color};">{status_text}</div>
        </div>
        """, unsafe_allow_html=True)

        # Tonnage Box
        st.markdown(f"""
        <div class="stat-box">
            <div class="stat-label">MATERIAL MOVED (TONS)</div>
            <div class="stat-value">{st.session_state.stats['tonnage']:,}</div>
        </div>
        """, unsafe_allow_html=True)

        # Dumps Box
        st.markdown(f"""
        <div class="stat-box">
            <div class="stat-label">TOTAL DUMPS</div>
            <div class="stat-value">{st.session_state.stats['dumps']}</div>
        </div>
        """, unsafe_allow_html=True)

        st.divider()

        # Controls
        st.subheader("Site Configuration")

        yard_width = st.number_input("Site Width (M)", 300, 800, 500, 20)
        yard_length = st.number_input("Site Length (M)", 250, 600, 400, 20)
        num_trucks = st.number_input("CAT Units", 1, 30, 8, 1)

        col_btn1, col_btn2 = st.columns(2)

        with col_btn1:
            if st.button("🚛 BEGIN OPERATIONS", type="primary"):
                # Initialize hex grid
                hex_radius = 15
                hex_width = math.sqrt(3) * hex_radius
                vert_spacing = (2 * hex_radius) * 0.75

                rows = 14
                cols = 18

                st.session_state.hexes = []
                for r in range(rows):
                    lane_id = r // (rows // max(1, num_trucks))
                    for c in range(cols):
                        x_off = (hex_width / 2) if r % 2 == 1 else 0
                        st.session_state.hexes.append(
                            Hexagon(330 + c * hex_width + x_off, 80 + r * vert_spacing, lane_id)
                        )

                # Create trucks
                st.session_state.trucks = []
                for i in range(num_trucks):
                    lane_hexes = [h for h in st.session_state.hexes if h.lane_id == i]
                    if lane_hexes:
                        avg_y = sum(h.y for h in lane_hexes) / len(lane_hexes)
                        st.session_state.trucks.append(Truck(i + 1, 280, avg_y, i))

                st.session_state.stats = {'tonnage': 0, 'dumps': 0}
                st.session_state.initialized = True
                st.session_state.sim_active = True
                st.rerun()

        with col_btn2:
            if st.button("⏹️ HALT FLEET"):
                st.session_state.sim_active = False
                st.rerun()

        if st.button("🔄 RESET"):
            st.session_state.initialized = False
            st.session_state.hexes = []
            st.session_state.trucks = []
            st.session_state.stats = {'tonnage': 0, 'dumps': 0}
            st.session_state.sim_active = False
            st.rerun()

        st.markdown("---")

        # Fleet summary
        if st.session_state.initialized:
            active_trucks = len([t for t in st.session_state.trucks if t.status != "IDLE"])
            st.caption(f"🚛 Active Trucks: {active_trucks}/{len(st.session_state.trucks)}")

            filled = len([h for h in st.session_state.hexes if h.height >= 2.4])
            total = len(st.session_state.hexes)
            progress = (filled / total) * 100 if total > 0 else 0
            st.progress(progress / 100)
            st.caption(f"Site Fill: {filled}/{total} zones ({progress:.1f}%)")

        st.caption("🔒 SECURED BY TEAM SILENT HACKER")

        # Legend
        st.markdown("""
        <div class="legend">
            <div><span style="background:#cc0000; width:14px; height:14px; display:inline-block;"></span> Full Grade (&gt;2.4m)</div>
            <div><span style="background:#0055ff; width:14px; height:14px; display:inline-block;"></span> Filling (0.8-2.4m)</div>
            <div><span style="background:#00cc44; width:14px; height:14px; display:inline-block;"></span> Empty (&lt;0.8m)</div>
            <div><span style="background:#ffcd00; width:14px; height:14px; display:inline-block;"></span> CAT Truck</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

    with col_main:
        if st.session_state.initialized and st.session_state.hexes:
            # Update simulation
            if st.session_state.sim_active:
                for _ in range(3):
                    for truck in st.session_state.trucks:
                        truck.update(st.session_state.hexes, st.session_state.stats)

            # Create figure
            fig = go.Figure()

            # Draw safety line
            fig.add_shape(
                type='line', x0=310, y0=0, x1=310, y1=800,
                line=dict(color='#ffcd00', width=2, dash='dash')
            )

            # Draw hexagons
            for hex_cell in st.session_state.hexes:
                points = []
                for i in range(6):
                    angle_deg = 60 * i + 30
                    angle_rad = math.radians(angle_deg)
                    px = hex_cell.x + 14 * math.cos(angle_rad)
                    py = hex_cell.y + 14 * math.sin(angle_rad)
                    points.append((px, py))

                x_verts = [p[0] for p in points]
                y_verts = [p[1] for p in points]

                color = hex_cell.get_color()
                if hex_cell.locked:
                    color = '#555555'

                fig.add_trace(go.Scatter(
                    x=x_verts, y=y_verts,
                    mode='lines', fill='toself',
                    fillcolor=color,
                    line=dict(color='#000', width=1),
                    showlegend=False,
                    hoverinfo='text',
                    hovertext=f"Lane: {hex_cell.lane_id}<br>Height: {hex_cell.height:.2f}m<br>Dumps: {hex_cell.dump_count}"
                ))

            # Draw trucks
            for truck in st.session_state.trucks:
                fig.add_trace(go.Scatter(
                    x=[truck.x], y=[truck.y],
                    mode='markers+text',
                    marker=dict(
                        symbol='square',
                        size=26,
                        color='#ffcd00',
                        line=dict(color=truck.get_status_color(), width=3)
                    ),
                    text=[truck.id.split('-')[1]],
                    textfont=dict(color='#000', size=9, family='Arial Black'),
                    textposition='middle center',
                    showlegend=False,
                    hoverinfo='text',
                    hovertext=f"{truck.id}<br>Status: {truck.status}<br>Loads: {truck.loads}"
                ))

            # Layout
            fig.update_layout(
                xaxis=dict(
                    showgrid=False,
                    zeroline=False,
                    fixedrange=True,
                    showticklabels=False,
                    scaleanchor='y',
                    scaleratio=1
                ),
                yaxis=dict(
                    showgrid=False,
                    zeroline=False,
                    fixedrange=True,
                    showticklabels=False
                ),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=0, r=0, t=0, b=0),
                height=700,
                dragmode=False
            )

            st.plotly_chart(fig, use_container_width=True, config={'staticPlot': False, 'scrollZoom': False})

            # Step button
            col_step1, col_step2, col_step3 = st.columns(3)
            with col_step2:
                if st.button("⏩ STEP SIMULATION", use_container_width=True):
                    for _ in range(5):
                        for truck in st.session_state.trucks:
                            truck.update(st.session_state.hexes, st.session_state.stats)
                    st.rerun()

            # Fleet Status Table
            with st.expander("🚛 View Fleet Status", expanded=False):
                fleet_data = []
                for truck in st.session_state.trucks:
                    status_icon = '🟡 Hauling' if truck.status == 'HAULING' else ('🟢 Returning' if truck.status == 'RETURNING' else '⚪ Idle')
                    fleet_data.append({
                        'Truck': truck.id,
                        'Status': status_icon,
                        'Loads': truck.loads,
                        'Target Lane': truck.lane_id
                    })
                st.dataframe(pd.DataFrame(fleet_data), use_container_width=True, hide_index=True)

        else:
            st.info("👈 Configure site and click 'BEGIN OPERATIONS' to start")

            # Placeholder
            fig = go.Figure()
            fig.add_annotation(
                text="CAT Autonomous Command Center<br>Click 'Begin Operations' to Start",
                x=0.5, y=0.5, xref='paper', yref='paper',
                showarrow=False, font=dict(size=20, color='#ffcd00')
            )
            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                height=500,
                xaxis=dict(visible=False),
                yaxis=dict(visible=False)
            )
            st.plotly_chart(fig, use_container_width=True)


if __name__ == "__main__":
    main()
