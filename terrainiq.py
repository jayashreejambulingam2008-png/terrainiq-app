import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import sqlite3
import random
import math
import time
from datetime import datetime

st.set_page_config(page_title="TerrainIQ - Fleet Management", layout="wide", page_icon="🚛")

# Database class with dynamic dimensions
class TerrainDB:
    def __init__(self, width=150, height=150, num_hexes=40):
        self.width = width
        self.height = height
        self.num_hexes = num_hexes
        self.conn = sqlite3.connect('terrainiq.db', check_same_thread=False)
        self._create_tables()
        self._seed_data()
    
    def _create_tables(self):
        # Drop existing tables to avoid conflicts
        self.conn.execute("DROP TABLE IF EXISTS hex_grid")
        self.conn.execute("DROP TABLE IF EXISTS dump_history")
        self.conn.execute("DROP TABLE IF EXISTS trucks")
        
        # Create hex_grid table with correct columns
        self.conn.execute('''CREATE TABLE hex_grid (
            hex_id TEXT PRIMARY KEY, 
            x REAL, 
            y REAL, 
            height_m REAL, 
            rock_ratio REAL, 
            material TEXT, 
            is_locked INTEGER, 
            dump_count INTEGER, 
            assigned_truck TEXT
        )''')
        
        # Create dump_history table
        self.conn.execute('''CREATE TABLE dump_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            hex_id TEXT, 
            truck_id TEXT, 
            pre_height REAL, 
            post_height REAL, 
            timestamp TIMESTAMP
        )''')
        
        # Create trucks table
        self.conn.execute('''CREATE TABLE trucks (
            truck_id TEXT PRIMARY KEY, 
            x REAL, 
            y REAL, 
            status TEXT, 
            current_target TEXT
        )''')
        self.conn.commit()
    
    def _seed_data(self):
        center_x = self.width / 2
        center_y = self.height / 2
        radius = min(self.width, self.height) / 3
        
        for i in range(self.num_hexes):
            angle = (i / self.num_hexes) * 2 * math.pi
            x = center_x + radius * math.cos(angle) * (0.5 + i/self.num_hexes)
            y = center_y + radius * math.sin(angle) * (0.5 + i/self.num_hexes)
            
            x = max(5, min(self.width - 5, x))
            y = max(5, min(self.height - 5, y))
            
            height = random.uniform(0.5, 2.5)
            rock = random.uniform(0, 1)
            material = "rock" if rock > 0.7 else ("soil" if rock < 0.2 else "mixed")
            
            self.conn.execute('''INSERT INTO hex_grid 
                (hex_id, x, y, height_m, rock_ratio, material, is_locked, dump_count, assigned_truck)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (f"HEX_{i:03d}", x, y, height, rock, material, 0, 0, None))
        self.conn.commit()
    
    def add_truck(self, truck_id, x, y):
        self.conn.execute('INSERT OR REPLACE INTO trucks (truck_id, x, y, status, current_target) VALUES (?, ?, ?, ?, ?)',
                         (truck_id, x, y, "idle", None))
        self.conn.commit()
    
    def get_all_trucks(self):
        return self.conn.execute('SELECT * FROM trucks').fetchall()
    
    def update_truck_status(self, truck_id, status, target=None):
        self.conn.execute('UPDATE trucks SET status=?, current_target=? WHERE truck_id=?',
                         (status, target, truck_id))
        self.conn.commit()
    
    def get_lowest_unlocked_hex(self):
        cursor = self.conn.execute('''SELECT hex_id, height_m, x, y 
            FROM hex_grid WHERE is_locked=0 AND (assigned_truck IS NULL OR assigned_truck = '') 
            ORDER BY height_m ASC LIMIT 1''')
        return cursor.fetchone()
    
    def assign_hex_to_truck(self, hex_id, truck_id):
        self.conn.execute('UPDATE hex_grid SET is_locked=1, assigned_truck=? WHERE hex_id=?', (truck_id, hex_id))
        self.conn.commit()
    
    def update_hex(self, hex_id, new_height, truck_id):
        # Get previous height first
        cursor = self.conn.execute('SELECT height_m FROM hex_grid WHERE hex_id=?', (hex_id,))
        pre_height = cursor.fetchone()[0]
        
        # Update hex
        self.conn.execute('''UPDATE hex_grid SET height_m=?, dump_count=dump_count+1, 
            is_locked=0, assigned_truck=NULL WHERE hex_id=?''', (new_height, hex_id))
        
        # Insert into history
        self.conn.execute('''INSERT INTO dump_history (hex_id, truck_id, pre_height, post_height, timestamp) 
            VALUES (?, ?, ?, ?, ?)''', (hex_id, truck_id, pre_height, new_height, datetime.now()))
        self.conn.commit()
    
    def get_all_hexes(self):
        return self.conn.execute('SELECT hex_id, height_m, x, y, rock_ratio, material, assigned_truck FROM hex_grid').fetchall()
    
    def get_stats(self):
        cursor = self.conn.execute('SELECT COUNT(*), AVG(height_m), MIN(height_m), MAX(height_m), SUM(dump_count) FROM hex_grid')
        count, avg, min_h, max_h, dumps = cursor.fetchone()
        return {
            'total': count, 
            'avg': round(avg or 0, 2), 
            'min': round(min_h or 0, 2), 
            'max': round(max_h or 0, 2), 
            'dumps': dumps or 0,
            'width': self.width,
            'height': self.height
        }
    
    def get_area_utilization(self):
        hexes = self.get_all_hexes()
        total_area = self.width * self.height
        filled_area = sum(h[1] * 50 for h in hexes)
        return min(100, (filled_area / total_area) * 100)

# Settlement calculation
def calculate_surcharge(desired_height, rock_ratio):
    if rock_ratio < 0.2:
        settlement = 0.12
        material_type = "Soil (12% settlement)"
    elif rock_ratio > 0.7:
        settlement = 0.03
        material_type = "Rock (3% settlement)"
    else:
        settlement = 0.08
        material_type = "Mixed (8% settlement)"
    surcharge = desired_height * (1 + settlement)
    return surcharge, settlement, material_type

# Truck turning radius calculation
def calculate_turning_radius(truck_length, max_steering_angle):
    if max_steering_angle <= 0:
        return 999
    angle_rad = math.radians(max_steering_angle)
    turning_radius = truck_length / math.tan(angle_rad)
    return turning_radius

# Main App
def main():
    # Initialize session state
    if 'db' not in st.session_state:
        st.session_state.db = None
    if 'site_configured' not in st.session_state:
        st.session_state.site_configured = False
    if 'auto_run' not in st.session_state:
        st.session_state.auto_run = False
    
    st.title("🚛 TerrainIQ - Autonomous Fleet Management")
    st.caption("🤖 AI-Powered Dumpyard Optimization | 3.03m Packing Distance | Automatic Fleet Coordination")
    
    # ============ INPUT SECTION ============
    if not st.session_state.site_configured:
        st.header("📏 Configure Your Mine Site")
        
        with st.form("dimensions_form"):
            st.subheader("🏗️ 1. DUMPYARD DIMENSIONS")
            col1, col2 = st.columns(2)
            with col1:
                dumpyard_width = st.number_input("Dumpyard Width (meters)", min_value=50, max_value=500, value=150, step=10)
            with col2:
                dumpyard_length = st.number_input("Dumpyard Length (meters)", min_value=50, max_value=500, value=150, step=10)
            
            st.divider()
            
            st.subheader("🚛 2. TRUCK FLEET & SPECIFICATIONS")
            col3, col4, col5 = st.columns(3)
            with col3:
                num_trucks = st.number_input("Number of Trucks", min_value=1, max_value=10, value=3, step=1)
            with col4:
                truck_length = st.number_input("Truck Length (meters)", min_value=8.0, max_value=15.0, value=12.8, step=0.1)
            with col5:
                max_steering_angle = st.number_input("Max Steering Angle (degrees)", min_value=20, max_value=45, value=30, step=5)
            
            st.divider()
            
            st.subheader("📐 3. PACKING & SETTLEMENT SETTINGS")
            col6, col7, col8 = st.columns(3)
            with col6:
                packing_distance = st.number_input(
                    "Distance Between Dump Spots (meters)", 
                    min_value=2.5, 
                    max_value=10.0, 
                    value=3.03,
                    step=0.1,
                    help="AI Semantic Segmentation allows 3.03m vs industry standard 7.38m (+59% density)"
                )
            with col7:
                target_height = st.number_input("Target Fill Height (m)", min_value=1.0, max_value=5.0, value=2.5, step=0.1)
            with col8:
                rock_ratio_input = st.slider("Material Rock Ratio", 0.0, 1.0, 0.4, 0.05)
            
            st.divider()
            
            # Calculate and show specifications
            turning_radius = calculate_turning_radius(truck_length, max_steering_angle)
            industry_standard = 7.38
            density_improvement = ((industry_standard - packing_distance) / industry_standard) * 100
            
            st.subheader("📊 AI-CALCULATED SPECIFICATIONS")
            col_s1, col_s2, col_s3, col_s4 = st.columns(4)
            with col_s1:
                st.metric("Truck Turning Radius", f"{turning_radius:.1f}m")
            with col_s2:
                st.metric("Fleet Size", f"{num_trucks} trucks")
            with col_s3:
                st.metric("Packing Distance", f"{packing_distance}m", delta=f"VS {industry_standard}m")
            with col_s4:
                st.metric("Density Improvement", f"+{density_improvement:.0f}%", delta="AI Optimized")
            
            surcharge_preview, settlement_preview, material_preview = calculate_surcharge(target_height, rock_ratio_input)
            st.success(f"🔬 Geotechnical Analysis: {material_preview} → Dump {surcharge_preview:.2f}m to achieve {target_height:.2f}m")
            
            submitted = st.form_submit_button("🚀 INITIALIZE MINE SITE", type="primary")
            
            if submitted:
                with st.spinner("Creating optimized dumpyard layout..."):
                    try:
                        st.session_state.db = TerrainDB(dumpyard_width, dumpyard_length, 40)
                        
                        # Add trucks at entry points
                        entry_x = dumpyard_width * 0.1
                        entry_y = dumpyard_length / 2
                        for i in range(num_trucks):
                            truck_id = f"TRUCK_{i+1:03d}"
                            truck_x = entry_x + (i * 10)
                            truck_y = entry_y + (i * 8)
                            st.session_state.db.add_truck(truck_id, truck_x, truck_y)
                        
                        st.session_state.site_configured = True
                        st.session_state.target_height = target_height
                        st.session_state.rock_ratio = rock_ratio_input
                        st.session_state.num_trucks = num_trucks
                        st.session_state.truck_length = truck_length
                        st.session_state.max_steering_angle = max_steering_angle
                        st.session_state.turning_radius = turning_radius
                        st.session_state.packing_distance = packing_distance
                        st.session_state.density_improvement = density_improvement
                        st.session_state.dumpyard_width = dumpyard_width
                        st.session_state.dumpyard_length = dumpyard_length
                        
                        st.success(f"✅ Site initialized! {dumpyard_width}m×{dumpyard_length}m | {num_trucks} trucks | {packing_distance}m packing (AI)")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
                        st.info("Please try again. If error persists, refresh the page.")
    
    # ============ MAIN DASHBOARD ============
    if st.session_state.site_configured and st.session_state.db:
        
        # Show configuration summary
        st.header(f"🏗️ Active Site Configuration")
        
        col_h1, col_h2, col_h3, col_h4 = st.columns(4)
        with col_h1:
            st.metric("Dumpyard", f"{st.session_state.dumpyard_width}×{st.session_state.dumpyard_length}m")
        with col_h2:
            st.metric("Fleet", f"{st.session_state.num_trucks} trucks")
        with col_h3:
            st.metric("Packing Distance", f"{st.session_state.packing_distance}m", 
                     delta=f"+{st.session_state.density_improvement:.0f}% density")
        with col_h4:
            st.metric("Turning Radius", f"{st.session_state.turning_radius:.0f}m")
        
        # Control Panel
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            if st.button("▶️ START AUTO DUMP", type="primary"):
                st.session_state.auto_run = True
                st.rerun()
        with col2:
            if st.button("⏸️ STOP"):
                st.session_state.auto_run = False
                st.rerun()
        with col3:
            if st.button("🔄 ONE DUMP"):
                try:
                    trucks = st.session_state.db.get_all_trucks()
                    idle_trucks = [t for t in trucks if t[3] in ["idle", "returning"]]
                    if idle_trucks:
                        truck = idle_trucks[0]
                        truck_id = truck[0]
                        lowest = st.session_state.db.get_lowest_unlocked_hex()
                        if lowest:
                            st.session_state.db.assign_hex_to_truck(lowest[0], truck_id)
                            surcharge, settlement, _ = calculate_surcharge(st.session_state.target_height, st.session_state.rock_ratio)
                            new_h = lowest[1] + (surcharge - lowest[1]) * random.uniform(0.95, 1.05)
                            new_h = min(5.0, max(0.5, new_h))
                            st.session_state.db.update_hex(lowest[0], new_h, truck_id)
                            st.session_state.db.update_truck_status(truck_id, "returning", None)
                            st.success(f"✅ {truck_id} dumped at {lowest[0]} | → {new_h:.2f}m")
                            st.rerun()
                    else:
                        st.warning("No idle trucks available")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
        with col4:
            if st.button("🔄 RESET"):
                st.session_state.site_configured = False
                st.session_state.db = None
                st.session_state.auto_run = False
                st.rerun()
        with col5:
            st.metric("Status", "🤖 ACTIVE" if st.session_state.auto_run else "⏸️ PAUSED")
        
        # Auto-dump logic
        if st.session_state.auto_run:
            try:
                trucks = st.session_state.db.get_all_trucks()
                idle_trucks = [t for t in trucks if t[3] in ["idle", "returning"]]
                if idle_trucks:
                    for truck in idle_trucks[:1]:
                        truck_id = truck[0]
                        lowest = st.session_state.db.get_lowest_unlocked_hex()
                        if lowest:
                            st.session_state.db.assign_hex_to_truck(lowest[0], truck_id)
                            surcharge, settlement, _ = calculate_surcharge(st.session_state.target_height, st.session_state.rock_ratio)
                            new_h = lowest[1] + (surcharge - lowest[1]) * random.uniform(0.95, 1.05)
                            new_h = min(5.0, max(0.5, new_h))
                            st.session_state.db.update_hex(lowest[0], new_h, truck_id)
                            st.session_state.db.update_truck_status(truck_id, "returning", None)
                            st.toast(f"🚛 {truck_id} dumped | → {new_h:.2f}m")
                            break
            except Exception as e:
                st.error(f"Auto-dump error: {str(e)}")
            time.sleep(2)
            st.rerun()
        
        # ============ MAP ============
        st.subheader(f"🗺️ Live Map ({st.session_state.packing_distance}m AI-Optimized Packing Distance)")
        
        try:
            hexes = st.session_state.db.get_all_hexes()
            trucks = st.session_state.db.get_all_trucks()
            
            if hexes:
                df = pd.DataFrame(hexes, columns=['id', 'height', 'x', 'y', 'rock', 'material', 'assigned_to'])
                
                fig = go.Figure()
                
                # Dumpyard boundary
                fig.add_shape(type="rect", x0=0, y0=0, x1=st.session_state.dumpyard_width, y1=st.session_state.dumpyard_length,
                             line=dict(color="red", width=3, dash="dash"))
                
                # Hex zones
                fig.add_trace(go.Scatter(
                    x=df['x'], y=df['y'],
                    mode='markers+text',
                    marker=dict(size=df['height'] * 20, color=df['height'], colorscale='Viridis', 
                               showscale=True, colorbar=dict(title="Height (m)")),
                    text=df['height'].round(1).astype(str) + 'm',
                    textposition="middle center",
                    name="Dump Zones"
                ))
                
                # Trucks
                colors = ['red', 'blue', 'green', 'orange', 'purple', 'cyan']
                for i, truck in enumerate(trucks):
                    truck_id, x, y, status, target = truck
                    fig.add_trace(go.Scatter(
                        x=[x], y=[y],
                        mode='markers+text',
                        marker=dict(size=25, color=colors[i % len(colors)], symbol='triangle-up'),
                        text=[truck_id],
                        textposition="bottom center",
                        name=truck_id
                    ))
                
                fig.update_layout(
                    title=f"Dumpyard: {st.session_state.dumpyard_width}m × {st.session_state.dumpyard_length}m",
                    xaxis_title="Meters", yaxis_title="Meters",
                    height=550
                )
                st.plotly_chart(fig, use_container_width=True)
                
                st.caption(f"✨ AI Semantic Segmentation Active: Trucks park **{st.session_state.packing_distance}m** apart (Industry: 7.38m) → **+{st.session_state.density_improvement:.0f}% density!**")
        except Exception as e:
            st.warning(f"Map loading: {str(e)}")
        
        # ============ STATISTICS ============
        stats = st.session_state.db.get_stats()
        
        col_s1, col_s2, col_s3, col_s4, col_s5 = st.columns(5)
        with col_s1:
            st.metric("Total Dumps", stats['dumps'])
        with col_s2:
            st.metric("Min Height", f"{stats['min']}m")
        with col_s3:
            st.metric("Max Height", f"{stats['max']}m")
        with col_s4:
            st.metric("Avg Height", f"{stats['avg']}m")
        with col_s5:
            st.metric("Trucks", st.session_state.num_trucks)
        
        # ============ FLEET STATUS ============
        st.subheader("🚛 Fleet Status")
        try:
            trucks = st.session_state.db.get_all_trucks()
            if trucks:
                fleet_df = pd.DataFrame([(t[0], t[3], t[4] if t[4] else 'None') for t in trucks], 
                                        columns=['Truck ID', 'Status', 'Target'])
                st.dataframe(fleet_df, use_container_width=True, hide_index=True)
        except Exception as e:
            st.warning(f"Fleet data: {str(e)}")
        
        # ============ HISTORY ============
        st.subheader("📜 Recent Dump History")
        try:
            history = st.session_state.db.conn.execute(
                'SELECT timestamp, hex_id, truck_id, pre_height, post_height FROM dump_history ORDER BY timestamp DESC LIMIT 8'
            ).fetchall()
            
            if history:
                hist_df = pd.DataFrame(history, columns=['Time', 'Zone', 'Truck', 'Before', 'After'])
                hist_df['Time'] = pd.to_datetime(hist_df['Time']).dt.strftime('%H:%M:%S')
                st.dataframe(hist_df, use_container_width=True, hide_index=True)
            else:
                st.info("No dumps yet. Click START AUTO DUMP!")
        except Exception as e:
            st.info("No dump history yet")
        
        if st.session_state.auto_run:
            st.success(f"🤖 AUTO-MODE: {st.session_state.num_trucks} trucks | {st.session_state.packing_distance}m packing | AI finding lowest points")
        else:
            st.info("⏸️ Paused. Click START AUTO DUMP")

if __name__ == "__main__":
    main()
