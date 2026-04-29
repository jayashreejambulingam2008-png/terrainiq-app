import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import random
import time
from datetime import datetime

st.set_page_config(page_title="CAT Autonomous Command", layout="wide", page_icon="🚛")

# Custom CSS to match CAT styling
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
</style>
""", unsafe_allow_html=True)

# ============ SIMULATION CLASS ============
class CATSimulation:
    def __init__(self):
        self.hexes = []
        self.trucks = []
        self.is_running = False
        self.total_tons = 0
        self.hex_radius = 13
    
    def initialize_site(self, yard_width, yard_length, num_trucks):
        """Initialize the dumpyard with hex grid and trucks"""
        self.is_running = False
        self.total_tons = 0
        
        hex_width = np.sqrt(3) * self.hex_radius
        vert_spacing = (2 * self.hex_radius) * 0.75
        
        cols = int(yard_width / hex_width)
        rows = int(yard_length / vert_spacing)
        
        self.hexes = []
        for r in range(rows):
            lane_id = int(r / (rows / max(1, num_trucks)))
            for c in range(cols):
                x_offset = hex_width / 2 if r % 2 == 1 else 0
                self.hexes.append({
                    'id': f"R{r}-C{c}",
                    'x': c * hex_width + x_offset + 90,
                    'y': r * vert_spacing + 30,
                    'height': random.uniform(0, 2.0),
                    'locked': False,
                    'lane_id': lane_id
                })
        
        # Create trucks
        lanes = list(set([h['lane_id'] for h in self.hexes]))
        self.trucks = []
        for i, lane_id in enumerate(lanes[:num_trucks]):
            lane_hexes = [h for h in self.hexes if h['lane_id'] == lane_id]
            if lane_hexes:
                avg_y = sum(h['y'] for h in lane_hexes) / len(lane_hexes)
                self.trucks.append({
                    'id': f'CAT-797F-{i+1}',
                    'start_x': 30,
                    'start_y': avg_y,
                    'x': 30,
                    'y': avg_y,
                    'status': 'IDLE',
                    'progress': 0,
                    'my_lane': lane_id,
                    'target': None,
                    'route': []
                })
        
        return True
    
    def get_lowest_hex_in_lane(self, lane_id):
        """Find lowest unfilled hex in specific lane"""
        available = [h for h in self.hexes if h['lane_id'] == lane_id and not h['locked'] and h['height'] < 2.4]
        if available:
            return min(available, key=lambda x: x['height'])
        return None
    
    def update_simulation(self):
        """Update simulation state - called in loop"""
        if not self.is_running:
            return
        
        # Check if all hexes are filled
        if all(h['height'] >= 2.4 for h in self.hexes):
            self.is_running = False
            return
        
        for truck in self.trucks:
            if truck['status'] == 'IDLE':
                # Find target in truck's lane
                target = self.get_lowest_hex_in_lane(truck['my_lane'])
                if target:
                    target['locked'] = True
                    truck['status'] = 'HAULING'
                    truck['target'] = target
                    truck['progress'] = 0
                    # Create route: start -> vertical move -> horizontal to target
                    truck['route'] = [
                        [truck['start_x'], truck['start_y']],
                        [truck['start_x'], target['y']],
                        [target['x'], target['y']]
                    ]
            
            elif truck['status'] in ['HAULING', 'RETURNING']:
                speed = 0.018 if truck['status'] == 'HAULING' else 0.03
                truck['progress'] += speed
                
                if truck['status'] == 'HAULING':
                    p_start = truck['route'][0]
                    p_mid = truck['route'][1]
                    p_end = truck['route'][2]
                else:
                    p_start = truck['route'][2]
                    p_mid = truck['route'][1]
                    p_end = truck['route'][0]
                
                # Interpolate position
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
                        # Dump material
                        truck['target']['height'] += 0.8
                        truck['target']['locked'] = False
                        truck['status'] = 'RETURNING'
                        truck['progress'] = 0
                        self.total_tons += 400
                    else:
                        # Return to idle position
                        truck['status'] = 'IDLE'
                        truck['x'] = truck['start_x']
                        truck['y'] = truck['start_y']
                        truck['target'] = None
    
    def get_color_for_height(self, height):
        """Get color based on fill height"""
        if height >= 2.4:
            return '#cc0000'  # Full
        elif height > 0.8:
            return '#0055ff'  # Filling
        else:
            return '#00cc44'  # Empty

# ============ MAIN APP ============
def main():
    # Initialize session state
    if 'sim' not in st.session_state:
        st.session_state.sim = CATSimulation()
    if 'initialized' not in st.session_state:
        st.session_state.initialized = False
    if 'auto_refresh' not in st.session_state:
        st.session_state.auto_refresh = False
    
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
        status_text = "🟢 OPERATING" if st.session_state.auto_refresh else "⚪ STANDBY"
        if st.session_state.initialized and st.session_state.sim.is_running:
            status_text = "🔥 HAULING ACTIVE"
        elif st.session_state.initialized and not st.session_state.auto_refresh:
            status_text = "⏸️ PAUSED"
        
        st.markdown(f"""
        <div class="stat-box">
            <div class="stat-label">Fleet Status</div>
            <div class="stat-value">{status_text}</div>
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
        
        st.divider()
        
        # Controls
        st.subheader("🏗️ Site Configuration")
        
        yard_width = st.number_input("Site Width (M)", min_value=100, max_value=500, value=240, step=10)
        yard_length = st.number_input("Site Length (M)", min_value=100, max_value=400, value=160, step=10)
        num_trucks = st.number_input("Active CAT 797F Units", min_value=1, max_value=12, value=4, step=1)
        
        col_btn1, col_btn2 = st.columns(2)
        
        with col_btn1:
            if st.button("🚛 BEGIN OPERATIONS", type="primary", use_container_width=True):
                with st.spinner("Initializing site..."):
                    st.session_state.sim.initialize_site(yard_width, yard_length, num_trucks)
                    st.session_state.initialized = True
                    st.session_state.auto_refresh = True
                    st.session_state.sim.is_running = True
                    st.rerun()
        
        with col_btn2:
            if st.button("⏹️ HALT FLEET", use_container_width=True):
                st.session_state.auto_refresh = False
                st.session_state.sim.is_running = False
        
        if st.button("🔄 RESET TERRAIN", use_container_width=True):
            st.session_state.initialized = False
            st.session_state.sim = CATSimulation()
            st.session_state.auto_refresh = False
            st.rerun()
        
        st.markdown("---")
        st.caption("🔒 SECURED BY TEAM SILENT HACKER")
        
        # Legend
        st.markdown("""
        <div class="legend">
            <div><span style="background:#cc0000; width:12px; height:12px; display:inline-block;"></span> Full Grade (>2.4m)</div>
            <div><span style="background:#0055ff; width:12px; height:12px; display:inline-block;"></span> Filling (0.8-2.4m)</div>
            <div><span style="background:#00cc44; width:12px; height:12px; display:inline-block;"></span> Empty (&lt;0.8m)</div>
            <div><span style="border:1px dashed #ffcd00; width:12px; height:12px; display:inline-block;"></span> Safety Zone</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col_main:
        # Map Container
        st.markdown("""
        <div style="background: radial-gradient(circle, #222 0%, #000 100%); border-radius: 10px; padding: 10px;">
        """, unsafe_allow_html=True)
        
        # Create plot
        if st.session_state.initialized and st.session_state.sim.hexes:
            # Update simulation if running
            if st.session_state.auto_refresh:
                st.session_state.sim.update_simulation()
            
            # Create figure
            fig = go.Figure()
            
            # Add safety zone line
            fig.add_shape(
                type='line',
                x0=70, y0=-10, x1=70, y1=st.session_state.sim.hexes[-1]['y'] + 50 if st.session_state.sim.hexes else 300,
                line=dict(color='#ffcd00', width=2, dash='dash')
            )
            
            # Add hexagons
            for hex_cell in st.session_state.sim.hexes:
                # Calculate hexagon vertices
                cx, cy = hex_cell['x'], hex_cell['y']
                radius = 12
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
                    hovertext=f"Height: {hex_cell['height']:.2f}m<br>Locked: {hex_cell['locked']}"
                ))
            
            # Add trucks
            for truck in st.session_state.sim.trucks:
                fig.add_trace(go.Scatter(
                    x=[truck['x']],
                    y=[truck['y']],
                    mode='markers+text',
                    marker=dict(
                        symbol='square',
                        size=25,
                        color='#ffcd00',
                        line=dict(color='#000', width=2)
                    ),
                    text=['CAT'],
                    textfont=dict(color='#000', size=9, family='Arial Black'),
                    textposition='middle center',
                    showlegend=False,
                    hoverinfo='text',
                    hovertext=f"{truck['id']}<br>Status: {truck['status']}"
                ))
            
            # Layout
            fig.update_layout(
                xaxis=dict(
                    range=[-10, st.session_state.sim.hexes[-1]['x'] + 50] if st.session_state.sim.hexes else [-10, 400],
                    showgrid=False,
                    zeroline=False,
                    fixedrange=True
                ),
                yaxis=dict(
                    range=[-10, st.session_state.sim.hexes[-1]['y'] + 50] if st.session_state.sim.hexes else [-10, 300],
                    showgrid=False,
                    zeroline=False,
                    fixedrange=True,
                    scaleanchor='x'
                ),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=0, r=0, t=0, b=0),
                height=700
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Truck status table
            st.subheader("🚛 Fleet Status")
            fleet_data = []
            for truck in st.session_state.sim.trucks:
                fleet_data.append({
                    'Truck ID': truck['id'],
                    'Status': '🟡 Hauling' if truck['status'] == 'HAULING' else ('🟢 Returning' if truck['status'] == 'RETURNING' else '⚪ Idle'),
                    'Position': f"({truck['x']:.0f}, {truck['y']:.0f})",
                    'Target': truck['target']['id'] if truck['target'] else 'None'
                })
            
            st.dataframe(pd.DataFrame(fleet_data), use_container_width=True, hide_index=True)
            
            # Progress stats
            filled = len([h for h in st.session_state.sim.hexes if h['height'] >= 2.4])
            total = len(st.session_state.sim.hexes)
            progress = (filled / total) * 100 if total > 0 else 0
            
            st.progress(progress / 100)
            st.caption(f"Site Fill Progress: {filled}/{total} zones complete ({progress:.1f}%)")
            
        else:
            st.info("👈 Click 'BEGIN OPERATIONS' to start the simulation")
            
            # Placeholder map
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
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Auto-refresh for real-time updates
    if st.session_state.auto_refresh and st.session_state.initialized and st.session_state.sim.is_running:
        time.sleep(0.5)
        st.rerun()

if __name__ == "__main__":
    main()
