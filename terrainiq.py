import pygame
import math

# --- CONFIGURATION & COLORS ---
CAT_YELLOW = (255, 205, 0)
CAT_BLACK = (0, 0, 0)
CAT_GRAY = (40, 40, 40)
DARK_BG = (20, 20, 20)
HEX_EMPTY = (0, 204, 68)
HEX_FILLING = (0, 85, 255)
HEX_FULL = (204, 0, 0)
LANE_MARKER = (255, 205, 0, 100)

SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 700
HEX_RADIUS = 15

class Hexagon:
    def __init__(self, x, y, lane_id):
        self.x = x
        self.y = y
        self.lane_id = lane_id
        self.height = 0.0
        self.locked = False

    def draw(self, surface):
        points = []
        for i in range(6):
            angle_deg = 60 * i + 30  # Flat-top orientation
            angle_rad = math.pi / 180 * angle_deg
            points.append((self.x + HEX_RADIUS * math.cos(angle_rad),
                           self.y + HEX_RADIUS * math.sin(angle_rad)))
        
        color = HEX_EMPTY
        if self.height > 0.8: color = HEX_FILLING
        if self.height >= 2.4: color = HEX_FULL
        if self.locked: color = (80, 80, 80)

        pygame.draw.polygon(surface, color, points)
        pygame.draw.polygon(surface, (0, 0, 0), points, 1) # Border

class Truck:
    def __init__(self, truck_id, start_x, start_y, lane_id):
        self.id = f"CAT-{truck_id}"
        self.start_pos = (start_x, start_y)
        self.pos = [start_x, start_y]
        self.lane_id = lane_id
        self.status = "IDLE" # IDLE, HAULING, RETURNING
        self.target = None
        self.progress = 0.0
        self.speed = 0.02

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
            self.progress += (0.01 if self.status == "HAULING" else 0.02)
            
            # L-Shape Path Logic
            p_start = self.start_pos if self.status == "HAULING" else (self.target.x, self.target.y)
            p_mid = (self.start_pos[0], self.target.y)
            p_end = (self.target.x, self.target.y) if self.status == "HAULING" else self.start_pos

            if self.progress < 0.5:
                s = self.progress * 2
                self.pos[0] = p_start[0] + (p_mid[0] - p_start[0]) * s
                self.pos[1] = p_start[1] + (p_mid[1] - p_start[1]) * s
            elif self.progress < 1.0:
                s = (self.progress - 0.5) * 2
                self.pos[0] = p_mid[0] + (p_end[0] - p_mid[0]) * s
                self.pos[1] = p_mid[1] + (p_end[1] - p_mid[1]) * s
            else:
                if self.status == "HAULING":
                    self.target.height += 0.8
                    self.target.locked = False
                    self.status = "RETURNING"
                    self.progress = 0
                    stats['tonnage'] += 400
                else:
                    self.status = "IDLE"
                    self.pos = list(self.start_pos)

    def draw(self, surface, font):
        # Draw Truck Body
        rect = pygame.Rect(self.pos[0]-12, self.pos[1]-10, 24, 20)
        pygame.draw.rect(surface, CAT_YELLOW, rect)
        pygame.draw.rect(surface, (0, 0, 0), rect, 2)
        # Label
        text = font.render(self.id, True, CAT_YELLOW)
        surface.blit(text, (self.pos[0]-20, self.pos[1]-25))

def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("CAT Autonomous Command - Silent Hacker")
    clock = pygame.time.Clock()
    font_small = pygame.font.SysFont("Arial", 12, bold=True)
    font_large = pygame.font.SysFont("Arial Black", 24)
    
    # Initialize Simulation
    hex_width = math.sqrt(3) * HEX_RADIUS
    vert_spacing = (2 * HEX_RADIUS) * 0.75
    hexes = []
    num_trucks = 4
    
    rows = 12
    cols = 15
    for r in range(rows):
        lane_id = r // (rows // num_trucks)
        for c in range(cols):
            x_off = (hex_width / 2) if r % 2 == 1 else 0
            hexes.append(Hexagon(350 + c * hex_width + x_off, 100 + r * vert_spacing, lane_id))

    trucks = []
    for i in range(num_trucks):
        lane_hexes = [h for h in hexes if h.lane_id == i]
        avg_y = sum(h.y for h in lane_hexes) / len(lane_hexes)
        trucks.append(Truck(i+1, 300, avg_y, i))

    stats = {'tonnage': 0}
    running = True
    sim_active = False

    while running:
        screen.fill(DARK_BG)
        
        # --- 1. EVENT HANDLING ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.MOUSEBUTTONDOWN:
                if 50 <= event.pos[0] <= 250 and 350 <= event.pos[1] <= 400:
                    sim_active = not sim_active

        # --- 2. UPDATE ---
        if sim_active:
            for t in trucks:
                t.update(hexes, stats)

        # --- 3. DRAWING ---
        # Sidebar
        pygame.draw.rect(screen, CAT_GRAY, (0, 0, 280, SCREEN_HEIGHT))
        title = font_large.render("CATERPILLAR", True, CAT_YELLOW)
        screen.blit(title, (20, 20))
        
        # Stats Boxes
        pygame.draw.rect(screen, (0,0,0), (20, 100, 240, 60))
        st_lbl = font_small.render("FLEET STATUS", True, CAT_YELLOW)
        st_val = font_small.render("OPERATING" if sim_active else "READY", True, (255,255,255))
        screen.blit(st_lbl, (30, 110))
        screen.blit(st_val, (30, 130))

        pygame.draw.rect(screen, (0,0,0), (20, 180, 240, 60))
        tn_lbl = font_small.render("MATERIAL MOVED (TONS)", True, CAT_YELLOW)
        tn_val = font_large.render(f"{stats['tonnage']:,}", True, (255,255,255))
        screen.blit(tn_lbl, (30, 190))
        screen.blit(tn_val, (30, 205))

        # Button
        btn_col = (200, 0, 0) if sim_active else CAT_YELLOW
        pygame.draw.rect(screen, btn_col, (50, 350, 200, 50))
        btn_txt = font_small.render("HALT FLEET" if sim_active else "BEGIN OPERATIONS", True, (0,0,0))
        screen.blit(btn_txt, (75, 365))

        # Safety Line
        pygame.draw.line(screen, CAT_YELLOW, (320, 0), (320, SCREEN_HEIGHT), 2)

        # Hexes & Trucks
        for h in hexes: h.draw(screen)
        for t in trucks: t.draw(screen, font_small)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()

if __name__ == "__main__":
    main()
