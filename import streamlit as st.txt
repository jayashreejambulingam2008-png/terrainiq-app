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

# Database
class TerrainDB:
    def __init__(self):
        self.conn = sqlite3.connect('terrainiq.db', check_same_thread=False)
        self._create_tables()
        self._seed_data()
    
    def _create_tables(self):
        self.conn.execute('''CREATE TABLE IF NOT EXISTS hex_grid (
            hex_id TEXT PRIMARY KEY, x REAL, y REAL, height_m REAL, 
            rock_ratio REAL, material TEXT, is_locked INTEGER, dump_count INTEGER
        )''')
        self.conn.execute('''CREATE TABLE IF NOT EXISTS dump_history (
            id INTEGER PRIMARY KEY, hex_id TEXT, truck_id TEXT, 
            pre_height REAL, post_height REAL, timestamp TIMESTAMP
        )''')
        self.conn.commit()
    
    def _seed_data(self):
        cursor = self.conn.execute("SELECT COUNT(*) FROM hex_grid")
        if cursor.fetchone()[0] == 0:
            for i in range(40):
                angle = (i / 40) * 2 * 3.14159
                x = 75 + 50 * math.cos(angle)
                y = 75 + 50 * math.sin(angle)
                height = random.uniform(0.5, 2.5)
                rock = random.uniform(0, 1)
                material = "rock" if rock > 0.7 else ("soil" if rock < 0.2 else "mixed")
                self.conn.execute('INSERT INTO hex_grid VALUES (?,?,?,?,?,?,?,?)',
                    (f"HEX_{i:03d}", x, y, height, rock, material, 0, 0))
            self.conn.commit()
    
    def get_lowest_hex(self):
        cursor = self.conn.execute('SELECT hex_id, height_m, x, y FROM hex_grid WHERE is_locked=0 ORDER BY height_m LIMIT 1')
        return cursor.fetchone()
    
    def update_hex(self, hex_id, new_height):
        self.conn.execute('UPDATE hex_grid SET height_m=?, dump_count=dump_count+1 WHERE hex_id=?', (new_height, hex_id))
        self.conn.execute('INSERT INTO dump_history (hex_id, truck_id, pre_height, post_height, timestamp) VALUES (?,?,?,?,?)',
                         (hex_id, "TRUCK_001", 0, new_height, datetime.now()))
        self.conn.commit()
    
    def get_all_hexes(self):
        return self.conn.execute('SELECT hex_id, height_m, x, y, rock_ratio, material FROM hex_grid').fetchall()
    
    def get_stats(self):
        cursor = self.conn.execute('SELECT COUNT(*), AVG(height_m), MIN(height_m), MAX(height_m), SUM(dump_count) FROM hex_grid')
        count, avg, min_h, max_h, dumps = cursor.fetchone()
        return {'total': count, 'avg': round(avg or 0, 2), 'min': round(min_h or 0, 2), 'max': round(max_h or 0, 2), 'dumps': dumps or 0}

# Main App
def main():
    if 'db' not in st.session_state:
        st.session_state.db = TerrainDB()
    if 'auto_run' not in st.session_state:
        st.session_state.auto_run = False
    
    st.title("🚛 TerrainIQ - Autonomous Fleet Management")
    st.caption("🤖 Automated Dump Point Selection | Real-time Updates")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("▶️ START AUTO DUMP", type="primary"):
            st.session_state.auto_run = True
    with col2:
        if st.button("⏸️ STOP"):
            st.session_state.auto_run = False
    with col3:
        if st.button("🔄 ONE DUMP"):
            lowest = st.session_state.db.get_lowest_hex()
            if lowest:
                new_h = lowest[1] + random.uniform(0.3, 0.8)
                st.session_state.db.update_hex(lowest[0], min(5.0, new_h))
                st.success(f"Dumped at {lowest[0]}")
                st.rerun()
    
    if st.session_state.auto_run:
        lowest = st.session_state.db.get_lowest_hex()
        if lowest:
            new_h = lowest[1] + random.uniform(0.3, 0.8)
            st.session_state.db.update_hex(lowest[0], min(5.0, new_h))
            st.toast(f"🤖 Auto-dumped at {lowest[0]} | Height: {lowest[1]:.2f}m → {new_h:.2f}m")
        time.sleep(2)
        st.rerun()
    
    # Map
    hexes = st.session_state.db.get_all_hexes()
    if hexes:
        df = pd.DataFrame(hexes, columns=['id', 'height', 'x', 'y', 'rock', 'material'])
        
        fig = go.Figure(go.Scatter(
            x=df['x'], y=df['y'],
            mode='markers+text',
            marker=dict(size=df['height']*20, color=df['height'], colorscale='Viridis', showscale=True),
            text=df['height'].round(1).astype(str),
            textposition="middle center",
            hovertemplate="<b>%{customdata[0]}</b><br>Height: %{customdata[1]:.2f}m<br>Material: %{customdata[2]}<extra></extra>",
            customdata=df[['id', 'height', 'material']].values
        ))
        fig.update_layout(xaxis_title="Meters", yaxis_title="Meters", height=500)
        st.plotly_chart(fig, use_container_width=True)
    
    # Stats
    stats = st.session_state.db.get_stats()
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Hexes", stats['total'])
    c2.metric("Total Dumps", stats['dumps'])
    c3.metric("Min Height", f"{stats['min']}m")
    c4.metric("Max Height", f"{stats['max']}m")
    c5.metric("Avg Height", f"{stats['avg']}m")
    
    st.info("🤖 AUTO MODE: System automatically finds and dumps at the lowest hex every 2 seconds")

if __name__ == "__main__":
    main()