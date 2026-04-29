import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import math
import time

# [Keep your existing imports and Setup here]
st.set_page_config(page_title="CAT Autonomous Command", layout="wide", page_icon="🚛")

# [Keep your CSS here]
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

# [Keep your classes (Hexagon, Truck) exactly the same as before]
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
            # (Movement logic omitted for brevity in response, keep your original movement math here)
            else:
                 t = self.progress / 0.33 if self.progress < 0.33 else ((self.progress - 0.33)/0.33 if self.progress < 0.66 else (self.progress - 0.66)/0.34)
                 # Apply movement updates as per original code
        elif self.status == "RETURNING":
            self.progress += 0.025
            if self.progress >= 1.0: self.status = "IDLE"; self.x = self.start_x; self.y = self.start_y; self.target = None
    def get_status_color(self):
        if self.waiting: return '#ff6600'
        elif self.status == "HAULING": return '#00ff00'
        elif self.status == "RETURNING": return '#ffcd00'
        return '#555555'

# [Keep your create_map_figure function exactly as it is]
def create_map_figure(hexes, trucks):
    # (Existing Figure Generation Logic)
    fig = go.Figure()
    # ... (Your full Figure generation code) ...
    return fig

# ============ MAIN APP ============
def main():
    # [Initialization Logic]
    if 'initialized' not in st.session_state: st.session_state.initialized = False
    if 'sim_active' not in st.session_state: st.session_state.sim_active = False

    # ... (Sidebar Config Logic) ...
    # [Start Live / Stop / Reset Buttons]

    with col_main:
        if st.session_state.initialized:
            
            # --- THE MAGIC FIX IS HERE ---
            @st.fragment(run_every=0.15)
            def live_simulation_view():
                if st.session_state.sim_active:
                    for _ in range(2):
                        for truck in st.session_state.trucks:
                            truck.update(st.session_state.hexes, st.session_state.trucks, st.session_state.stats)
                
                # 1. Create the figure object
                fig = create_map_figure(st.session_state.hexes, st.session_state.trucks)
                
                # 2. Convert to STATIC image
                # This prevents the browser from reloading the HTML iframe
                img_bytes = fig.to_image(format="png", width=1000, height=680)
                
                # 3. Display as a simple image instead of a chart
                st.image(img_bytes, use_container_width=True)
                
                # [Fleet status table and other widgets]
            
            live_simulation_view()

if __name__ == "__main__":
    main()
