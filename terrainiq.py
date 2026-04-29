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
    .stPlotlyChart {
        background: radial-gradient(circle, #222 0%, #000 100%);
        border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)

# ============ SIMULATION CLASS ============
class CATSimulation:
    def __init__(self):
        self.hexes = []
        self.trucks = []
        self.is_running = False
        self.total_tons = 0
        self.total_dumps = 0
        self.hex_radius = 10
        self.last_update = datetime.now()
    
    def initialize_site(self, yard_width, yard_length, num_trucks):
        """Initialize the dumpyard with hex grid and trucks"""
        self.is_running = False
        self.total_tons = 0
        self.total_dumps = 0
        
        hex_width = math.sqrt(3) * self.hex_radius
        vert_spacing = self.hex_radius * 1.5
        
        # Calculate grid size based on yard dimensions
        cols = max(15, min(35, int(yard_width / hex_width)))
        rows = max(10, min(25, int(yard_length / vert_spacing)))
        
        # Distribute trucks across lanes
        lanes = max(1, min(num_trucks, 12))
        
        self.hexes = []
        for r in range(rows):
            lane_id = r % lanes
            for c in range(cols):
                x_offset = hex_width / 2 if r % 2 == 1 else 0
                x_pos = 280 + c * hex_width + x_offset
                y_pos = r * vert_spacing + 50
                
                self.hexes.append({
                    'id': f"{r}-{c}",
                    'x': x_pos,
                    'y': y_pos,
                    'height': random.uniform(0, 1.5),
                    'locked': False,
                    'lane_id': lane_id,
                    'dump_count': 0
                })
        
        # Create trucks
        self.trucks = []
        truck_spacing = min(50, yard_length / max(1, num_trucks))
        
        for i in range(num_trucks):
            lane_id = i % lanes
            start_y = 70 + (i * truck_spacing)
            start_y = min(start_y, yard_length + 30)
            
            self.trucks.append({
                'id': f'CAT-{i+1:03d}',
                'start_x': 230,
                'start_y': start_y,
                'x': 230,
                'y': start_y,
                'status': 'IDLE',
                'progress': 0,
                'my_lane': lane_id,
                'target': None,
                'route': [],
                'loads': 0
            })
        
        return True
    
    def get_lowest_hex_in_lane(self, lane_id):
        """Find lowest unfilled hex in specific lane"""
        available = [h for h in self.hexes if h['lane_id'] == lane_id and not h['locked'] and h['height'] < 2.4]
        if available:
            return min(available, key=lambda x: x['height'])
        return None
    
    def update_simulation(self):
        """Update simulation state"""
        if not self.is_running:
            return
        
        # Check if all hexes are filled
        if all(h['height'] >= 2.4 for h in self.hexes):
            self.is_running = False
            return
        
        for truck in self.trucks:
            if truck['status'] == 'IDLE':
                target = self.get_lowest_hex_in_lane(truck['my_lane'])
                if target:
                    target['locked'] = True
                    truck['status'] = 'HAULING'
                    truck['target'] = target
                    truck['progress'] = 0
                    
                    mid_x = truck['start_x'] + (target['x'] - truck['start_x']) * 0.3
                    truck['route'] = [
                        [truck['start_x'], truck['start_y']],
                        [mid_x, truck['start_y']],
                        [target['x'], target['y']]
                    ]
            
            elif truck['status'] in ['HAULING', 'RETURNING']:
                speed = 0.02 if truck['status'] == 'HAULING' else 0.03
                truck['progress'] += speed
                
                if len(truck['route']) >= 3:
                    p_start = truck['route'][0]
                    p_mid = truck['route'][1]
                    p_end = truck['route'][2]
                    
                    if truck['status'] == 'RETURNING':
                        p_start, p_mid, p_end = p_end, p_mid, p_start
                    
                    if truck['progress'] < 0.5:
                        s = truck['progress'] * 2
                        truck['x'] = p_start[0] + (p_mid[0] - p_start[0]) * s
                        truck['y'] = p_start[1] + (p_mid[1] - p_start[1]) * s
                    else:
                        s = (truck['progress'] - 0.5) * 2
                        truck['x'] = p_mid[0] + (p_end[0] - p_mid[0]) * s
                        truck['y'] = p_mid[1] + (p_end[1] - p_mid[1]) * s
                    
                    if truck['progress'] >= 1:
                        if truck['status'] == 'HAULING':
                            fill_amount = 0.7
                            truck['target']['height'] = min(2.5, truck['target']['height'] + fill_amount)
                            truck['target']['locked'] = False
                            truck['target']['dump_count'] += 1
                            self.total_tons += 400
                            self.total_dumps += 1
                            truck['loads'] += 1
                            truck['status'] = 'RETURNING'
                            truck['progress'] = 0
                        else:
                            truck['status'] = 'IDLE'
                            truck['x'] = truck['start_x']
                            truck['y'] = truck['start_y']
                            truck['target'] = None
    
    def get_color_for_height(self, height):
        if height >= 2.4:
            return '#cc0000'
        elif height > 0.8:
            return '#0055ff'
        else:
            return '#00cc44'

# ============ MAIN APP ============
def main():
    # Initialize session state
    if 'sim' not in st.session_state:
        st.session_state.sim = CATSimulation()
    if 'initialized' not in st.session_state:
        st.session_state.initialized = False
    if 'simulation_step' not in st.session_state:
        st.session_state.simulation_step = 0
    
    # CAT Header
    st.markdown("""
    <div class="cat-header">
        <h1>CATERPILLAR ®</h1>
        <span style="float: right; background: #000; color: #ffcd00; padding: 5px 10px; border-radius: 3px;">
            AUTONOMOUS COMMAND CENTER | V10.5
        </span>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar and Main Layout
    col_side, col_main = st.columns([1, 3])
    
    with col_side:
        st.markdown('<div class="control-panel">', unsafe_allow_html=True)
        
        # Status Box
        if st.session_state.initialized and st.session_state.sim.is_running:
            status_text = "🔥 HAULING ACTIVE"
            status_color = "#00cc44"
        elif st.session_state.initialized:
            status_text = "⏸️ PAUSED"
            status_color = "#ffcd00"
        else:
            status_text = "⚪ STANDBY"
            status_color = "#888"
        
        st.markdown(f"""
        <div class="stat-box">
            <div class="stat-label">Fleet Status</div>
            <div class="stat-value" style="color: {status_color};">{status_text}</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Tonnage Box
        tons_moved = st.session_state.sim.total_tons if st.session_state.initialized else 0
        st.markdown(f"""
        <div class="stat-box">
            <div class="stat-label">Material Moved (Tons)</div>
            <div class="stat-value">{tons_moved:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Dumps Box
        dumps_count = st.session_state.sim.total_dumps if st.session_state.initialized else 0
        st.markdown(f"""
        <div class="stat-box">
            <div class="stat-label">Total Dumps</div>
            <div class="stat-value">{dumps_count}</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.divider()
        
        # Controls
        st.subheader("🏗️ Site Configuration")
        
        yard_width = st.number_input("Site Width (M)", min_value=200, max_value=600, value=400, step=10, key="width")
        yard_length = st.number_input("Site Length (M)", min_value=200, max_value=500, value=300, step=10, key="length")
        num_trucks = st.number_input("Active CAT Units (25-60)", min_value=25, max_value=60, value=35, step=5, key="trucks")
        
        col_btn1, col_btn2 = st.columns(2)
        
        with col_btn1:
            if st.button("🚛 BEGIN OPERATIONS", type="primary", use_container_width=True):
                st.session_state.sim.initialize_site(yard_width, yard_length, int(num_trucks))
                st.session_state.initialized = True
                st.session_state.sim.is_running = True
                st.rerun()
        
        with col_btn2:
            if st.button("⏹️ HALT FLEET", use_container_width=True):
                st.session_state.sim.is_running = False
                st.rerun()
        
        if st.button("🔄 RESET TERRAIN", use_container_width=True):
            st.session_state.initialized = False
            st.session_state.sim = CATSimulation()
            st.rerun()
        
        st.markdown("---")
        
        # Fleet summary
        if st.session_state.initialized:
            active_trucks = len([t for t in st.session_state.sim.trucks if t['status'] != 'IDLE'])
            st.caption(f"🚛 Active Trucks: {active_trucks}/{len(st.session_state.sim.trucks)}")
            
            filled = len([h for h in st.session_state.sim.hexes if h['height'] >= 2.4])
            total = len(st.session_state.sim.hexes)
            progress = (filled / total) * 100 if total > 0 else 0
            st.progress(progress / 100)
            st.caption(f"Site Fill: {filled}/{total} zones ({progress:.1f}%)")
        
        st.caption("🔒 SECURED BY TEAM SILENT HACKER")
        
        st.markdown("""
        <div class="legend">
            <div><span style="background:#cc0000; width:12px; height:12px; display:inline-block;"></span> Full Grade</div>
            <div><span style="background:#0055ff; width:12px; height:12px; display:inline-block;"></span> Filling</div>
            <div><span style="background:#00cc44; width:12px; height:12px; display:inline-block;"></span> Empty</div>
            <div><span style="background:#ffcd00; width:12px; height:12px; display:inline-block;"></span> CAT Truck</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col_main:
        if st.session_state.initialized and st.session_state.sim.hexes:
            # Update simulation - NO auto-refresh, just update on button click
            if st.button("🔄 UPDATE SIMULATION", use_container_width=True):
                for _ in range(5):  # Run 5 steps per click for visible movement
                    st.session_state.sim.update_simulation()
                st.rerun()
            
            # Also update if running (but manual step control for smoothness)
            if st.session_state.sim.is_running:
                for _ in range(3):
                    st.session_state.sim.update_simulation()
            
            # Create figure
            fig = go.Figure()
            
            # Add hexagons
            for hex_cell in st.session_state.sim.hexes:
                cx, cy = hex_cell['x'], hex_cell['y']
                radius = 10
                angles = np.linspace(0, 2*np.pi, 7)
                x_verts = [cx + radius * np.cos(a) for a in angles]
                y_verts = [cy + radius * np.sin(a) for a in angles]
                
                color = st.session_state.sim.get_color_for_height(hex_cell['height'])
                
                fig.add_trace(go.Scatter(
                    x=x_verts,
                    y=y_verts,
                    mode='lines',
                    fill='toself',
                    fillcolor=color,
                    line=dict(color='#000', width=1),
                    showlegend=False,
                    hoverinfo='text',
                    hovertext=f"Zone: {hex_cell['id']}<br>Height: {hex_cell['height']:.2f}m<br>Dumps: {hex_cell['dump_count']}"
                ))
            
            # Add trucks
            for truck in st.session_state.sim.trucks:
                if truck['status'] == 'HAULING':
                    border_color = '#00ff00'
                elif truck['status'] == 'RETURNING':
                    border_color = '#ffcd00'
                else:
                    border_color = '#555555'
                
                fig.add_trace(go.Scatter(
                    x=[truck['x']],
                    y=[truck['y']],
                    mode='markers+text',
                    marker=dict(
                        symbol='square',
                        size=24,
                        color='#ffcd00',
                        line=dict(color=border_color, width=3)
                    ),
                    text=[truck['id'].split('-')[1]],
                    textfont=dict(color='#000', size=9, family='Arial Black'),
                    textposition='middle center',
                    showlegend=False,
                    hoverinfo='text',
                    hovertext=f"{truck['id']}<br>Status: {truck['status']}<br>Loads: {truck['loads']}"
                ))
            
            # Layout
            fig.update_layout(
                xaxis=dict(
                    showgrid=False,
                    zeroline=False,
                    fixedrange=True,
                    showticklabels=False
                ),
                yaxis=dict(
                    showgrid=False,
                    zeroline=False,
                    fixedrange=True,
                    scaleanchor='x',
                    showticklabels=False
                ),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=0, r=0, t=0, b=0),
                height=650,
                dragmode=False
            )
            
            st.plotly_chart(fig, use_container_width=True, config={'staticPlot': False, 'scrollZoom': False})
            
            # Manual step button for smooth control
            col_step1, col_step2, col_step3 = st.columns(3)
            with col_step2:
                if st.button("▶️ STEP SIMULATION", use_container_width=True):
                    for _ in range(5):
                        st.session_state.sim.update_simulation()
                    st.rerun()
            
            # Fleet Status Table
            with st.expander("🚛 View Full Fleet Status", expanded=False):
                fleet_data = []
                for truck in st.session_state.sim.trucks:
                    status_icon = '🟡 Hauling' if truck['status'] == 'HAULING' else ('🟢 Returning' if truck['status'] == 'RETURNING' else '⚪ Idle')
                    fleet_data.append({
                        'Truck': truck['id'],
                        'Status': status_icon,
                        'Loads': truck['loads'],
                        'Target': truck['target']['id'] if truck['target'] else 'None'
                    })
                st.dataframe(pd.DataFrame(fleet_data), use_container_width=True, hide_index=True)
            
        else:
            st.info("👈 Configure site settings and click 'BEGIN OPERATIONS' to start")
            
            # Placeholder
            fig = go.Figure()
            fig.add_annotation(
                text="CAT Autonomous Command Center<br>Configure 25-60 Trucks | Click 'Begin Operations'",
                x=0.5, y=0.5, xref='paper', yref='paper',
                showarrow=False, font=dict(size=18, color='#ffcd00')
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
