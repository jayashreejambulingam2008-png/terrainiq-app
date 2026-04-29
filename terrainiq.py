import pygame
import math
import random

# --- Config ---
WIDTH, HEIGHT = 1200, 800
SIDEBAR = 250
HEX_RADIUS = 10  # Slightly smaller to fit more hexes
FPS = 60
TRUCK_CAPACITY = 400

# Colors
COLORS = {
    "yellow": (255, 205, 0),
    "black": (0, 0, 0),
    "dark": (26, 26, 26),
    "gray": (51, 51, 51),
    "empty": (0, 204, 68),
    "filling": (0, 85, 255),
    "full": (204, 0, 0),
    "text": (255, 255, 255),
    "red": (200, 0, 0),
    "green": (0, 200, 0)
}

# --- Truck Class ---
class Truck:
    def __init__(self, start_pos, lane_id, truck_id):
        self.start_x, self.start_y = start_pos
        self.x, self.y = start_pos
        self.lane = lane_id
        self.status = "IDLE"
        self.progress = 0
        self.target = None
        self.id = truck_id
        self.route = []
        self.wait_cycles = 0
    
    def update(self, hexes, stats):
        if self.status == "IDLE":
            # Find available hex in lane
            lane_hexes = [h for h in hexes if h["lane"] == self.lane and not h["locked"] and h["height"] < 2.4]
            if lane_hexes:
                # Pick the lowest height hex for efficiency (not just farthest)
                lane_hexes.sort(key=lambda h: h["height"])
                self.target = lane_hexes[0]
                self.target["locked"] = True
                
                # Create smoother path
                mid_x = self.start_x + (self.target["x"] - self.start_x) * 0.4
                self.route = [
                    (self.start_x, self.start_y),
                    (mid_x, self.start_y),
                    (self.target["x"], self.target["y"])
                ]
                self.progress = 0
                self.status = "HAULING"
        
        elif self.status in ["HAULING", "RETURNING"]:
            speed = 0.008 if self.status == "HAULING" else 0.015
            self.progress += speed
            
            if len(self.route) >= 3:
                p0, p1, p2 = self.route
                if self.progress < 0.5:
                    s = self.progress * 2
                    self.x = p0[0] + (p1[0] - p0[0]) * s
                    self.y = p0[1] + (p1[1] - p0[1]) * s
                else:
                    s = (self.progress - 0.5) * 2
                    self.x = p1[0] + (p2[0] - p1[0]) * s
                    self.y = p1[1] + (p2[1] - p1[1]) * s
                
                if self.progress >= 1:
                    if self.status == "HAULING":
                        # Add more realistic fill increment
                        fill_amount = 0.6 + random.uniform(0, 0.4)
                        self.target["height"] = min(2.5, self.target["height"] + fill_amount)
                        self.target["locked"] = False
                        stats["tons"] += TRUCK_CAPACITY
                        stats["dumps"] += 1
                        self.status = "RETURNING"
                        self.progress = 0
                    else:
                        self.status = "IDLE"
                        self.x, self.y = self.start_x, self.start_y
                        self.target = None

# --- Draw Hex ---
def draw_hex(screen, color, x, y):
    points = []
    for i in range(6):
        angle = math.radians(60 * i - 30)
        px = x + HEX_RADIUS * math.cos(angle)
        py = y + HEX_RADIUS * math.sin(angle)
        points.append((px, py))
    pygame.draw.polygon(screen, color, points)
    pygame.draw.polygon(screen, (0, 0, 0), points, 1)

# --- Draw Button ---
def draw_button(screen, text, x, y, w, h, color, hover=False):
    mouse = pygame.mouse.get_pos()
    click = pygame.mouse.get_pressed()
    
    rect = pygame.Rect(x, y, w, h)
    btn_color = color if not rect.collidepoint(mouse) else (min(color[0]+30,255), min(color[1]+30,255), min(color[2]+30,255))
    pygame.draw.rect(screen, btn_color, rect)
    pygame.draw.rect(screen, COLORS["black"], rect, 2)
    
    font = pygame.font.SysFont("Arial", 14)
    text_surf = font.render(text, True, COLORS["black"])
    screen.blit(text_surf, (x + w//2 - text_surf.get_width()//2, y + h//2 - text_surf.get_height()//2))
    
    if rect.collidepoint(mouse) and click[0]:
        return True
    return False

# --- Main ---
def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("CAT Command Center - Heavy Fleet Edition")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Arial", 14)
    title_font = pygame.font.SysFont("Arial", 18, bold=True)
    
    # Default values
    num_trucks = 25
    yard_width = 400
    yard_height = 300
    
    # Simulation state
    sim_active = False
    hexes = []
    trucks = []
    stats = {"tons": 0, "dumps": 0}
    
    # Input boxes for configuration
    input_active = None
    input_text_trucks = "25"
    input_text_width = "400"
    input_text_height = "300"
    
    def create_site():
        nonlocal hexes, trucks, stats
        hexes = []
        trucks = []
        stats = {"tons": 0, "dumps": 0}
        
        hex_w = math.sqrt(3) * HEX_RADIUS
        vert = HEX_RADIUS * 1.5
        
        available_width = WIDTH - SIDEBAR - 50
        available_height = HEIGHT - 100
        
        cols = min(int(available_width / hex_w), 35)
        rows = min(int(available_height / vert), 25)
        
        lanes = max(1, num_trucks // 2)  # Distribute trucks across lanes
        
        for r in range(rows):
            lane_id = r % lanes if lanes > 0 else 0
            for c in range(cols):
                offset = hex_w / 2 if r % 2 else 0
                hexes.append({
                    "x": SIDEBAR + c * hex_w + offset + 30,
                    "y": r * vert + 50,
                    "height": random.uniform(0, 1.5),
                    "locked": False,
                    "lane": lane_id,
                    "row": r,
                    "col": c
                })
        
        # Create truck entry points spread across left side
        truck_spacing = available_height / max(1, num_trucks)
        for i in range(num_trucks):
            lane_id = i % lanes
            start_y = 80 + (i * truck_spacing)
            start_y = min(start_y, HEIGHT - 80)
            trucks.append(Truck((SIDEBAR - 15, start_y), lane_id, f"CAT-{i+1:03d}"))
    
    # Initial create
    create_site()
    
    # Button positions
    start_btn = pygame.Rect(20, 200, 200, 40)
    stop_btn = pygame.Rect(20, 250, 200, 40)
    reset_btn = pygame.Rect(20, 300, 200, 40)
    
    running = True
    while running:
        screen.fill(COLORS["black"])
        
        # Draw sidebar
        pygame.draw.rect(screen, COLORS["dark"], (0, 0, SIDEBAR, HEIGHT))
        
        # Title
        title = title_font.render("CAT AUTONOMOUS", True, COLORS["yellow"])
        screen.blit(title, (20, 20))
        sub = font.render("COMMAND CENTER", True, COLORS["yellow"])
        screen.blit(sub, (20, 45))
        
        # Status
        status_color = COLORS["green"] if sim_active else COLORS["red"]
        status_text = font.render(f"STATUS: {'ACTIVE' if sim_active else 'STANDBY'}", True, status_color)
        screen.blit(status_text, (20, 85))
        
        # Stats
        tons_text = font.render(f"TONS: {stats['tons']:,}", True, COLORS["yellow"])
        screen.blit(tons_text, (20, 120))
        dumps_text = font.render(f"DUMPS: {stats['dumps']}", True, COLORS["yellow"])
        screen.blit(dumps_text, (20, 140))
        trucks_text = font.render(f"TRUCKS: {len(trucks)}", True, COLORS["yellow"])
        screen.blit(trucks_text, (20, 160))
        
        # Input labels
        config_label = font.render("CONFIGURATION", True, COLORS["yellow"])
        screen.blit(config_label, (20, 320))
        
        # Trucks input
        pygame.draw.rect(screen, COLORS["gray"], (20, 345, 100, 30))
        pygame.draw.rect(screen, COLORS["black"], (20, 345, 100, 30), 1)
        trucks_input_display = font.render(input_text_trucks, True, COLORS["yellow"])
        screen.blit(trucks_input_display, (25, 350))
        trucks_label = font.render("Trucks (25-50):", True, COLORS["text"])
        screen.blit(trucks_label, (20, 335))
        
        # Width input
        pygame.draw.rect(screen, COLORS["gray"], (130, 345, 80, 30))
        pygame.draw.rect(screen, COLORS["black"], (130, 345, 80, 30), 1)
        width_input_display = font.render(input_text_width, True, COLORS["yellow"])
        screen.blit(width_input_display, (135, 350))
        width_label = font.render("Width (m):", True, COLORS["text"])
        screen.blit(width_label, (130, 335))
        
        # Height input
        pygame.draw.rect(screen, COLORS["gray"], (20, 400, 80, 30))
        pygame.draw.rect(screen, COLORS["black"], (20, 400, 80, 30), 1)
        height_input_display = font.render(input_text_height, True, COLORS["yellow"])

        screen.blit(height_input_display, (25, 405))
        height_label = font.render("Height (m):", True, COLORS["text"])
        screen.blit(height_label, (20, 390))

        # Update button
        if draw_button(screen, "UPDATE SITE", 20, 450, 200, 35, COLORS["yellow"]):
            try:
                new_trucks = int(input_text_trucks) if input_text_trucks else 25
                new_trucks = max(25, min(50, new_trucks))  # Allow 25-50 trucks
                num_trucks = new_trucks
                yard_width = int(input_text_width) if input_text_width else 400
                yard_height = int(input_text_height) if input_text_height else 300
                create_site()
                sim_active = False
            except:
                pass
        
        # Buttons
        if draw_button(screen, "START OPERATIONS", 20, 500, 200, 40, COLORS["yellow"]):
            sim_active = True
        
        if draw_button(screen, "HALT FLEET", 20, 550, 200, 40, COLORS["red"]):
            sim_active = False
        
        if draw_button(screen, "RESET SITE", 20, 600, 200, 40, COLORS["gray"]):
            sim_active = False
            create_site()
        
        # Input handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            elif event.type == pygame.MOUSEBUTTONDOWN:
                # Check which input box was clicked
                if pygame.Rect(20, 345, 100, 30).collidepoint(event.pos):
                    input_active = "trucks"
                elif pygame.Rect(130, 345, 80, 30).collidepoint(event.pos):
                    input_active = "width"
                elif pygame.Rect(20, 400, 80, 30).collidepoint(event.pos):
                    input_active = "height"
                else:
                    input_active = None
            
            elif event.type == pygame.KEYDOWN and input_active:
                if event.key == pygame.K_RETURN:
                    input_active = None
                elif event.key == pygame.K_BACKSPACE:
                    if input_active == "trucks":
                        input_text_trucks = input_text_trucks[:-1]
                    elif input_active == "width":
                        input_text_width = input_text_width[:-1]
                    elif input_active == "height":
                        input_text_height = input_text_height[:-1]
                else:
                    if event.unicode.isdigit():
                        if input_active == "trucks":
                            input_text_trucks += event.unicode
                        elif input_active == "width":
                            input_text_width += event.unicode
                        elif input_active == "height":
                            input_text_height += event.unicode
        
        # Update simulation
        if sim_active:
            for truck in trucks:
                truck.update(hexes, stats)
            
            # Check if all hexes are filled
            if all(h["height"] >= 2.4 for h in hexes):
                sim_active = False
        
        # Draw hex grid
        for h in hexes:
            color = COLORS["empty"]
            if h["height"] > 0.8:
                color = COLORS["filling"]
            if h["height"] >= 2.4:
                color = COLORS["full"]
            if h["locked"]:
                color = COLORS["gray"]
            draw_hex(screen, color, h["x"], h["y"])
        
        # Draw trucks
        for truck in trucks:
            # Draw truck body
            pygame.draw.rect(screen, COLORS["yellow"], (truck.x-12, truck.y-12, 24, 24))
            pygame.draw.rect(screen, COLORS["black"], (truck.x-12, truck.y-12, 24, 24), 2)
            
            # Draw truck ID
            id_font = pygame.font.SysFont("Arial", 8)
            id_text = id_font.render(str(truck.id.split('-')[1]), True, COLORS["black"])
            screen.blit(id_text, (truck.x-6, truck.y-4))
            
            # Status indicator
            status_color = COLORS["green"] if truck.status == "HAULING" else (COLORS["yellow"] if truck.status == "RETURNING" else COLORS["gray"])
            pygame.draw.circle(screen, status_color, (int(truck.x), int(truck.y-15)), 4)
        
        # Draw legend
        legend_y = HEIGHT - 100
        legend_items = [
            ("Empty", COLORS["empty"]),
            ("Filling", COLORS["filling"]),
            ("Full", COLORS["full"]),
            ("Locked", COLORS["gray"]),
            ("Truck", COLORS["yellow"])
        ]
        
        for i, (label, color) in enumerate(legend_items):
            x = SIDEBAR + 10 + (i * 100)
            pygame.draw.rect(screen, color, (x, legend_y, 15, 15))
            pygame.draw.rect(screen, COLORS["black"], (x, legend_y, 15, 15), 1)
            legend_text = font.render(label, True, COLORS["text"])
            screen.blit(legend_text, (x + 20, legend_y))
        
        # FPS display
        fps_text = font.render(f"FPS: {int(clock.get_fps())}", True, COLORS["gray"])
        screen.blit(fps_text, (WIDTH - 80, 10))
        
        pygame.display.flip()
        clock.tick(FPS)
    
    pygame.quit()

if __name__ == "__main__":
    main()
