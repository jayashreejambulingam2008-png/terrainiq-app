import pygame
import math
import json

# --- CONFIGURATION & COLORS ---
CAT_YELLOW = (255, 205, 0)
CAT_BLACK = (26, 26, 26)
BG_BLACK = (0, 0, 0)
SAFE_GREEN = (0, 204, 68)
FILLING_BLUE = (0, 85, 255)
FULL_RED = (204, 0, 0)
LOCKED_GRAY = (50, 50, 50)
WHITE = (255, 255, 255)

HEX_RADIUS = 13
TRUCK_SIZE = 22
SIM_SPEED = 2

# --- UTILITY FUNCTIONS ---
def point_in_polygon(x, y, poly):
    n = len(poly)
    inside = False
    p1x, p1y = poly[0]
    for i in range(n + 1):
        p2x, p2y = poly[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xints = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xints:
                        inside = not inside
        p1x, p1y = p2x, p2y
    return inside

class Hex:
    def __init__(self, id_str, x, y):
        self.id = id_str
        self.x = x
        self.y = y
        self.height = 0  # 0: Empty, 1: Filling, 2: Full
        self.locked = False
        self.traffic = 0

    def get_color(self):
        if self.height >= 2: return FULL_RED
        if self.height == 1: return FILLING_BLUE
        return SAFE_GREEN

class Truck:
    def __init__(self, id_num, start_x, start_y):
        self.id = id_num
        self.start_x = start_x
        self.start_y = start_y
        self.x = start_x
        self.y = start_y
        self.status = "IDLE"  # IDLE, HAULING, RETURNING
        self.target_hex = None
        self.route = []
        self.route_idx = 0
        self.payload = 400

# --- SIMULATION ENGINE ---
class Simulation:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((900, 500))
        pygame.display.set_caption("CAT Autonomous Command - Far End Fill")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Arial", 12, bold=True)
        
        self.poly = [[120, 50], [600, 50], [550, 400], [120, 400]]
        self.hexes = []
        self.trucks = []
        self.total_tons = 0
        self.setup_site()

    def setup_site(self):
        hex_width = math.sqrt(3) * HEX_RADIUS
        vert_spacing = (2 * HEX_RADIUS) * 0.75
        
        # Generate Hex Grid
        for r in range(25):
            for c in range(35):
                hx = 120 + c * hex_width + (hex_width/2 if r % 2 == 1 else 0)
                hy = 50 + r * vert_spacing
                if point_in_polygon(hx, hy, self.poly):
                    self.hexes.append(Hex(f"{r}-{c}", hx, hy))
        
        # Generate Fleet
        for i in range(8):
            self.trucks.append(Truck(i + 1, 50, 80 + i * 45))

    def get_dist(self, x1, y1, x2, y2):
        return math.hypot(x2 - x1, y2 - y1)

    def find_route(self, start_pos, target_hex):
        # Simplified direct pathing for simulation (mimics the JS logic)
        path = [start_pos]
        # In a full Dijkstra implementation, you'd traverse hex neighbors here
        # For this version, we move directly toward the target
        path.append((target_hex.x, target_hex.y))
        return path

    def update(self):
        for t in self.trucks:
            if t.status == "IDLE":
                # Find Far-End candidate (Highest X value)
                available = [h for h in self.hexes if not h.locked and h.height < 2]
                if available:
                    available.sort(key=lambda h: (-h.x, abs(h.y - t.start_y)))
                    target = available[0]
                    target.locked = True
                    t.target_hex = target
                    t.route = self.find_route((t.x, t.y), target)
                    t.status = "HAULING"
                    t.route_idx = 0

            elif t.status in ["HAULING", "RETURNING"]:
                target_pt = t.route[1] if len(t.route) > 1 else (t.x, t.y)
                dx, dy = target_pt[0] - t.x, target_pt[1] - t.y
                dist = self.get_dist(t.x, t.y, target_pt[0], target_pt[1])
                
                # Collision Avoidance
                blocked = False
                for other in self.trucks:
                    if other.id != t.id and self.get_dist(t.x, t.y, other.x, other.y) < 30:
                        if t.status == "RETURNING" and other.status == "HAULING":
                            blocked = True # Haulers have Right of Way
                
                if not blocked and dist > 0:
                    speed = 2 * SIM_SPEED
                    t.x += (dx / dist) * min(speed, dist)
                    t.y += (dy / dist) * min(speed, dist)
                    
                    if dist < 2:
                        if t.status == "HAULING":
                            t.target_hex.height += 1
                            t.target_hex.locked = False
                            t.status = "RETURNING"
                            t.route = [(t.x, t.y), (t.start_x, t.start_y)]
                            self.total_tons += t.payload
                        else:
                            t.status = "IDLE"

    def draw_hex(self, hex_obj):
        pts = []
        for i in range(6):
            angle = math.radians(60 * i - 30)
            px = hex_obj.x + HEX_RADIUS * math.cos(angle)
            py = hex_obj.y + HEX_RADIUS * math.sin(angle)
            pts.append((px, py))
        pygame.draw.polygon(self.screen, hex_obj.get_color(), pts)
        pygame.draw.polygon(self.screen, BG_BLACK, pts, 1)

    def run(self):
        running = True
        while running:
            self.screen.fill(BG_BLACK)
            for event in pygame.event.get():
                if event.type == pygame.QUIT: running = False

            self.update()

            # Draw Boundary
            pygame.draw.lines(self.screen, CAT_YELLOW, True, self.poly, 2)
            
            # Draw Terrain
            for h in self.hexes:
                self.draw_hex(h)
            
            # Draw Trucks
            for t in self.trucks:
                rect = pygame.Rect(t.x - 11, t.y - 11, TRUCK_SIZE, TRUCK_SIZE)
                pygame.draw.rect(self.screen, CAT_YELLOW, rect)
                pygame.draw.rect(self.screen, BG_BLACK, rect, 2)
                lbl = self.font.render(f"T{t.id}", True, BG_BLACK)
                self.screen.blit(lbl, (t.x - 8, t.y - 7))

            # UI Header
            pygame.draw.rect(self.screen, CAT_YELLOW, (0, 0, 900, 40))
            header_txt = self.font.render(f"CATERPILLAR AUTONOMOUS COMMAND | TOTAL TONS: {self.total_tons}", True, BG_BLACK)
            self.screen.blit(header_txt, (20, 12))

            pygame.display.flip()
            self.clock.tick(60)
        pygame.quit()

if __name__ == "__main__":
    Simulation().run()
