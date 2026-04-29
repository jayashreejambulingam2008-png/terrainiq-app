import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import math
import time

# --- PAGE CONFIG ---
st.set_page_config(page_title="CAT Autonomous Command", layout="wide", page_icon="🚛")

# --- CSS ---
st.markdown("""
<style>
    .stApp { background: linear-gradient(135deg, #1a1a1a 0%, #000000 100%); }
    .cat-header { background: #ffcd00; padding: 15px 30px; border-radius: 5px; margin-bottom: 20px; color: #000; }
    .cat-header h1 { margin: 0; font-family: 'Arial Black', sans-serif; display: inline-block; }
    .stat-box { background: #000; border-left: 4px solid #ffcd00; padding: 15px; margin: 10px 0; border-radius: 5px; }
    .stat-label { font-size: 0.7rem; color: #ffcd00; text-transform: uppercase; letter-spacing: 1px; }
    .stat-value { font-size: 1.8rem; font-weight: bold; font-family: monospace; }
    .control-panel { background: #1a1a1a; padding: 20px; border-radius: 10px; border: 1px solid #333; }
    div.stButton > button { background-color: #ffcd00; color: #000; font-weight: bold; width: 100%; }
</style>
""", unsafe_allow_html=True)

# --- CLASSES ---
class Hexagon:
    def __init__(self, x, y, lane_id, col_id):
        self.x = x; self.y = y; self.lane_id = lane_id; self.col_id = col_id; self.height = 0.0; self.locked = False; self.dump_count = 0; self.id = f"H{lane_id}-{col_id}"
    def get_color(self):
        if self.height >= 2.4: return '#cc0000'
        elif self.height > 0.8: return '#0055ff'
        else: return '#00cc44'

class Truck:
    def __init__(self, truck_id, start_x, start_y, lane_id):
        self.id = f"CAT-{truck_id:03d}"; self.start_x = start_x; self.start_y = start_y; self.x = start_x; self.y = start_y; self.lane_id = lane_id; self.status = "IDLE"; self.target = None; self.progress = 0.0; self.loads = 0; self.waypoints = []; self.waiting = False; self.wait_timer = 0; self.turning_radius = 25
    def check_collision(self, other_trucks):
        for other in other_trucks:
            if other == self or other.status == "IDLE": continue
            if math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2) < 35: return True
        return False
    def update(self, hexes, all_trucks, stats):
        if self.check_collision(all_trucks):
            self.waiting = True; self.wait_timer += 1
            if self.wait_timer > 10: self.waiting = False; self.wait_timer = 0
            return
        self.waiting = False; self.wait_timer = 0
        if self.status == "IDLE":
            targets = [h for h in hexes if h.lane_id == self.lane_id and not h.locked and h.height < 2.4]
            if targets:
                targets.sort(key=lambda h: h.x, reverse=True); self.target = targets[0]; self.target.locked = True; self.status = "HAULING"; self.progress = 0.0
                self.waypoints = [(self.start_x, self.start_y), (self.start_x, self.target.y - 15), (self.target.x - self.turning_radius, self.target.y - 15), (self.target.x, self.target.y)]
        elif self.status == "HAULING":
            self.progress += 0.02
            if self.progress >= 1.0:
                self.target.height = min(2.5, self.target.height + 0.6); self.target.locked = False; self.target.dump_count += 1; self.status = "RETURNING"; self.progress = 0.0; stats['tonnage'] += 400; stats['dumps'] += 1; self.loads += 1
                self.waypoints = [(self.target.x, self.target.y), (self.target.x - self.turning_radius, self.target.y), (self.start_x, self.target.y), (self.start_x, self.start_y)]
            else:
                 t = self.progress / 0.33 if self.progress < 0.33 else ((self.progress - 0.33)/0.33 if self.progress < 0.66 else (self.progress - 0.66)/0.34)
        elif self.status == "RETURNING":
            self.progress += 0.025
            if self.progress >= 1.0: self.status = "IDLE"; self.x = self.start_x; self.y = self.start_y; self.target = None
    def get_status_color(self):
        if self.waiting: return '#ff6600'
        elif self.status == "HAULING": return '#00ff00'
        elif self.status == "RETURNING": return '#ffcd00'
        return '#555555'

# --- HELPERS ---
def create_map_figure(hexes, trucks):
    fig = go.Figure()
    for hex_cell in hexes:
        points = []
        for i in range(6):
            angle_rad = math.radians(60 * i + 30)
            points.append((hex_cell.x + 14 * math.cos(angle_rad), hex_cell.y + 14 * math.sin(angle_rad)))
        color = hex_cell.get_color() if not hex_cell.locked else '#555555'
        fig.add_trace(go.Scatter(x=[p[0] for p in points], y=[p[1] for p in points], mode='lines', fill='toself', fillcolor=color, line=dict(color='#333', width=1), showlegend=False))
    
    for truck in trucks:
        fig.add_trace(go.Scatter(x=[truck.x], y=[truck.y], mode='markers', marker=dict(symbol='square', size=28, color='#ffcd00', line=dict(color=truck.get_status_color(), width=3)), showlegend=False))
    
    fig.update_layout(xaxis=dict(showgrid=False, fixedrange=True, showticklabels=False, range=[200, 950]), yaxis=dict(showgrid=False, fixedrange=True, showticklabels=False, range=[0, 650]), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', margin=dict(l=0, r=0, t=0, b=0), height=680)
    return fig

# --- MAIN ---
def main():
    if 'initialized' not in st.session_state: st.session_state.initialized = False
    if 'sim_active' not in st.session_state: st.session_state.sim_active = False

    st.markdown('<div class="cat-header"><h1>CATERPILLAR ®</h1></div>', unsafe_allow_html=True)
    
    col_side, col_main = st.columns([1, 3])
    
    with col_side:
        st.markdown('<div class="control-panel">', unsafe_allow_html=True)
        if st.button("🚀 START LIVE", type="primary"):
            hex_radius = 15; hex_width = math.sqrt(3) * hex_radius; vert_spacing = (2 * hex_radius) * 0.75
            hexes = [Hexagon(280 + c * hex_width + ((hex_width/2) if r % 2 == 1 else 0), 80 + r * vert_spacing, r // 3, 20-c) for r in range(14) for c in range(20)]
            st.session_state.hexes = hexes
            st.session_state.trucks = [Truck(i + 1, 250, 200 + (i * 30), i % 3) for i in range(6)]
            st.session_state.stats = {'tonnage': 0, 'dumps': 0}
            st.session_state.initialized = True
            st.session_state.sim_active = True
        if st.button("🔄 RESET"):
            st.session_state.initialized = False
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    with col_main:
        if st.session_state.initialized:
            @st.fragment(run_every=0.15)
            def live_view():
                if st.session_state.sim_active:
                    for truck in st.session_state.trucks:
                        truck.update(st.session_state.hexes, st.session_state.trucks, st.session_state.stats)
                
                fig = create_map_figure(st.session_state.hexes, st.session_state.trucks)
                # Using st.plotly_chart with a key is the stable way to render
                st.plotly_chart(fig, use_container_width=True, key="cat_map_chart", config={'displayModeBar': False})
            
            live_view()
        else:
            st.info("Click 'START LIVE' to begin.")

if __name__ == "__main__":
    main()
