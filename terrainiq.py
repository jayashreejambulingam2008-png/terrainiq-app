import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.patches import RegularPolygon

# Configuration
HEX_RADIUS = 13
WIDTH = 240
LENGTH = 160
T_COUNT = 4

class Hex:
    def __init__(self, x, y, lane_id):
        self.x = x
        self.y = y
        self.lane_id = lane_id
        self.height = 0
        self.locked = False

class Truck:
    def __init__(self, id, start_x, start_y, lane_id, color):
        self.id = id
        self.startX = start_x
        self.startY = start_y
        self.x = start_x
        self.y = start_y
        self.status = "IDLE"
        self.color = color
        self.route = None
        self.progress = 0
        self.myLane = lane_id
        self.target = None

# 1. Initialize Site Data
def initialize_site():
    hex_width = np.sqrt(3) * HEX_RADIUS
    vert_spacing = (2 * HEX_RADIUS) * 0.75
    
    cols = int(WIDTH // hex_width)
    rows = int(LENGTH // vert_spacing)
    
    hexes = []
    for r in range(rows):
        lane_id = int(r // (rows / T_COUNT))
        for c in range(cols):
            x_offset = (hex_width / 2) if (r % 2 == 1) else 0
            hexes.append(Hex(c * hex_width + x_offset + 40, r * vert_spacing + 20, lane_id))
            
    trucks = []
    colors = ['#e91e63', '#9c27b0', '#3f51b5', '#00bcd4', '#009688', '#ff9800']
    
    for i in range(T_COUNT):
        lane_hexes = [h for h in hexes if h.lane_id == i]
        avg_y = sum(h.y for h in lane_hexes) / len(lane_hexes)
        trucks.append(Truck(f"T-{i+1}", 10, avg_y, i, colors[i % len(colors)]))
        
    return hexes, trucks

hexes, trucks = initialize_site()

# 2. Setup Visualization
fig, ax = plt.subplots(figsize=(10, 6))

def update(frame):
    # Logic Update
    for t in trucks:
        if t.status == "IDLE":
            # Find available target
            possible = [h for h in hexes if h.lane_id == t.myLane and not h.locked and h.height < 2.4]
            if possible:
                target = max(possible, key=lambda h: h.x)
                target.locked = True
                t.status = "LOADED"
                t.target = target
                t.progress = 0
                t.route = [(t.startX, t.startY), (target.x, target.y)]
        
        elif t.status == "LOADED":
            t.progress += 0.03
            t.x = t.startX + (t.target.x - t.startX) * t.progress
            t.y = t.startY + (t.target.y - t.startY) * t.progress
            if t.progress >= 1:
                t.target.height += 0.8
                t.target.locked = False
                t.status = "EMPTY"
                t.progress = 0
                t.route = [(t.target.x, t.target.y), (t.startX, t.startY)]
        
        elif t.status == "EMPTY":
            t.progress += 0.05
            t.x = t.target.x + (t.startX - t.target.x) * t.progress
            t.y = t.target.y + (t.startY - t.target.y) * t.progress
            if t.progress >= 1:
                t.status = "IDLE"
                t.route = None
                t.x, t.y = t.startX, t.startY

    # Redraw
    ax.clear()
    ax.set_xlim(-10, WIDTH + 60)
    ax.set_ylim(-10, LENGTH + 40)
    
    # Draw Hexes
    for h in hexes:
        color = '#00cc44' # Empty
        if h.height >= 2.4: color = '#cc0000'
        elif h.height > 0.8: color = '#0055ff'
        
        hex_patch = RegularPolygon((h.x, h.y), numVertices=6, radius=HEX_RADIUS-1, 
                                   orientation=np.pi/2, facecolor=color, edgecolor='white')
        ax.add_patch(hex_patch)

    # Draw Trucks
    for t in trucks:
        ax.plot(t.x, t.y, 's', color=t.color, markersize=10, markeredgecolor='white')
        ax.text(t.x, t.y, t.id, color='white', ha='center', va='center', fontsize=8, fontweight='bold')

ani = animation.FuncAnimation(fig, update, interval=50, cache_frame_data=False)
plt.show()
