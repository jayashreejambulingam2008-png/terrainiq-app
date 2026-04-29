import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import math
import time

st.set_page_config(page_title="CAT Autonomous Command", layout="wide", page_icon="🚛")

# ============ HEXAGON CLASS ============
class Hexagon:
    def __init__(self, x, y, lane_id, col_id):
        self.x = x
        self.y = y
        self.lane_id = lane_id
        self.col_id = col_id
        self.height = 0.0
        self.locked = False
        self.dump_count = 0

    def get_color(self):
        if self.height >= 2.4:
            return '#cc0000'
        elif self.height > 0.8:
            return '#0055ff'
        else:
            return '#00cc44'


# ============ TRUCK CLASS ============
class Truck:
    def __init__(self, truck_id, start_x, start_y, lane_id):
        self.id = f"CAT-{truck_id:03d}"
        self.start_x = start_x
        self.start_y = start_y
        self.x = start_x
        self.y = start_y
        self.lane_id = lane_id
        self.status = "IDLE"
        self.target = None
        self.progress = 0.0
        self.loads = 0
        self.waypoints = []

    def update(self, hexes, stats):
        if self.status == "IDLE":
            targets = [h for h in hexes if h.lane_id == self.lane_id and not h.locked and h.height < 2.4]
            if targets:
                targets.sort(key=lambda h: h.x, reverse=True)
                self.target = targets[0]
                self.target.locked = True
                self.status = "HAULING"
                self.progress = 0.0

                self.waypoints = [
                    (self.start_x, self.start_y),
                    (self.start_x, self.target.y),
                    (self.target.x - 20, self.target.y),
                    (self.target.x, self.target.y)
                ]

        elif self.status == "HAULING":
            self.progress += 0.03

            p1, p2 = self.waypoints[0], self.waypoints[-1]
            self.x = p1[0] + (p2[0] - p1[0]) * self.progress
            self.y = p1[1] + (p2[1] - p1[1]) * self.progress

            if self.progress >= 1.0:
                self.target.height = min(2.5, self.target.height + 0.6)
                self.target.locked = False
                self.target.dump_count += 1
                self.status = "RETURNING"
                self.progress = 0.0
                stats['tonnage'] += 400
                stats['dumps'] += 1
                self.loads += 1

        elif self.status == "RETURNING":
            self.progress += 0.04

            p1, p2 = self.waypoints[-1], self.waypoints[0]
            self.x = p1[0] + (p2[0] - p1[0]) * self.progress
            self.y = p1[1] + (p2[1] - p1[1]) * self.progress

            if self.progress >= 1.0:
                self.status = "IDLE"
                self.x = self.start_x
                self.y = self.start_y
                self.target = None


# ============ MAP ============
def create_map(hexes, trucks):
    fig = go.Figure()

    for h in hexes:
        fig.add_trace(go.Scatter(
            x=[h.x], y=[h.y],
            mode='markers',
            marker=dict(size=12, color=h.get_color()),
            showlegend=False
        ))

    for t in trucks:
        fig.add_trace(go.Scatter(
            x=[t.x], y=[t.y],
            mode='markers+text',
            marker=dict(size=20, color='yellow'),
            text=[t.id],
            textposition='top center',
            showlegend=False
        ))

    fig.update_layout(
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        height=600
    )

    return fig


# ============ MAIN ============
def main():

    if "initialized" not in st.session_state:
        st.session_state.initialized = False
    if "sim_active" not in st.session_state:
        st.session_state.sim_active = False

    st.title("🚛 CAT Autonomous Command")

    col1, col2 = st.columns([1, 3])

    # -------- SIDE PANEL --------
    with col1:
        if st.button("🚀 START"):
            hexes = []
            for i in range(10):
                for j in range(10):
                    hexes.append(Hexagon(300 + j*40, 100 + i*40, i//2, j))

            trucks = []
            for i in range(5):
                trucks.append(Truck(i+1, 200, 100 + i*80, i))

            st.session_state.hexes = hexes
            st.session_state.trucks = trucks
            st.session_state.stats = {'tonnage': 0, 'dumps': 0}
            st.session_state.initialized = True
            st.session_state.sim_active = True

        if st.button("⏹ STOP"):
            st.session_state.sim_active = False

    # -------- MAIN PANEL --------
    with col2:
        if st.session_state.initialized:

            placeholder = st.empty()

            # 🔥 NO BLINK LOOP
            while st.session_state.sim_active:

                for t in st.session_state.trucks:
                    t.update(st.session_state.hexes, st.session_state.stats)

                fig = create_map(st.session_state.hexes, st.session_state.trucks)
                placeholder.plotly_chart(fig, use_container_width=True)

                time.sleep(0.05)

            # show final state when stopped
            fig = create_map(st.session_state.hexes, st.session_state.trucks)
            placeholder.plotly_chart(fig, use_container_width=True)

        else:
            st.info("Click START to begin simulation")


if __name__ == "__main__":
    main()
