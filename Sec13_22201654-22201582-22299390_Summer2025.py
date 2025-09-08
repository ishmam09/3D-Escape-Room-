import math
import time
import random
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
WIN_W, WIN_H = 1000, 800
ASPECT = WIN_W / WIN_H
FOVY = 75.0
#Room size
PLAY_INNER = 400.0
WALL_THICK = 20.0
TOTAL_INNER = PLAY_INNER + 2 * WALL_THICK
HALF_PLAY = PLAY_INNER / 2
HALF_TOTAL = TOTAL_INNER / 2
CEILING_Z = 220.0
FLOOR_Z = 0.0
NUM_ROOMS = 3
gate_open_time = [0.0, 0.0, 0.0]
#Player
player_pos = [0.0, -HALF_PLAY + 60.0, 30.0]
player_yaw = 0.0
player_speed = 160.0
turn_speed = 140.0
player_radius = 14.0
#Camera
camera_mode = 0  #0 third 1 first
cam_free = False
#Third person
tp_orbit_yaw = 0.0
tp_orbit_pitch = 20.0
tp_orbit_dist = 160.0
#First person
fp_look_yaw = 0.0
fp_look_pitch = 0.0
#Timer
current_room = 0
gate_open = [False, False, False]
ROOM_TIMES = [60.0, 40.0, 25.0]
room_start_time = time.time()
dead = False
keys_down = set()
death_animation_progress = 0.0
death_animation_duration = 1.5
death_animation_start = 0.0
MAZE_SIZE = 5
CELL_SIZE = PLAY_INNER / MAZE_SIZE
MAZE_WALLS = []
TRAPS = []
maze_exit = (0, 0, 60, 40)
trap_triggered = False
congratulations = False
game_complete_time = 0
ROOM3_COLLIDERS = []

def room_offset_y(i):
    return i * (TOTAL_INNER)

def clamp(v, a, b):
    return a if v < a else b if v > b else v

def draw_text(x, y, text, font=GLUT_BITMAP_HELVETICA_18):
    glColor3f(1, 1, 1)
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, WIN_W, 0, WIN_H)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    glRasterPos2f(x, y)
    for ch in text:
        glutBitmapCharacter(font, ord(ch))
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

def draw_box(ax, ay, az):
    glPushMatrix()
    glScalef(ax, ay, az)
    glutSolidCube(1.0)
    glPopMatrix()

def draw_panel(w, h):
    glBegin(GL_QUADS)
    glVertex3f(-w / 2, -h / 2, 0)
    glVertex3f(w / 2, -h / 2, 0)
    glVertex3f(w / 2, h / 2, 0)
    glVertex3f(-w / 2, h / 2, 0)
    glEnd()

#Room 1
def draw_table(x, y, z=FLOOR_Z, top_w=130, top_h=80, top_t=6, leg_h=42, leg_t=10):
    glPushMatrix()
    glTranslatef(x, y, z)
    #Table top
    glColor3f(0.55, 0.35, 0.2)
    glPushMatrix()
    glTranslatef(0, 0, leg_h + top_t / 2)
    draw_box(top_w, top_h, top_t)
    glPopMatrix()
    #Table legs
    glColor3f(0.35, 0.2, 0.1)
    inset_x = top_w / 2 - leg_t * 1.5
    inset_y = top_h / 2 - leg_t * 1.5
    for sx in (-1, 1):
        for sy in (-1, 1):
            glPushMatrix()
            glTranslatef(sx * inset_x, sy * inset_y, leg_h / 2)
            draw_box(leg_t, leg_t, leg_h)
            glPopMatrix()
    glPopMatrix()

def draw_chair(x, y, facing_angle=0, z=FLOOR_Z, seat=36, seat_h=22, back_h=36, leg_t=8):
    glPushMatrix()
    glTranslatef(x, y, z)
    glRotatef(facing_angle, 0, 0, 1)
    #Seat
    glColor3f(0.45, 0.3, 0.15)
    glPushMatrix()
    glTranslatef(0, 0, seat_h)
    draw_box(seat, seat, 4)
    glPopMatrix()
    #Legs
    glColor3f(0.35, 0.2, 0.1)
    for sx in (-1, 1):
        for sy in (-1, 1):
            glPushMatrix()
            glTranslatef(sx * (seat / 2 - leg_t / 2), sy * (seat / 2 - leg_t / 2), seat_h / 2)
            draw_box(leg_t, leg_t, seat_h)
            glPopMatrix()
    #Backrest
    glPushMatrix()
    glTranslatef(0, -seat / 2 + leg_t / 2, seat_h + back_h / 2)
    draw_box(seat - 6, leg_t, back_h)
    glPopMatrix()
    glPopMatrix()

TABLE_POS = (-150.0, 150.0)
CHAIRS = [(TABLE_POS[0], TABLE_POS[1] - 80, 0), ]
PROP_COLLIDERS = []
def rebuild_prop_colliders():
    global PROP_COLLIDERS
    PROP_COLLIDERS = []
    t_w, t_h = 120.0, 70.0
    PROP_COLLIDERS.append((TABLE_POS[0], TABLE_POS[1], t_w * 0.45, t_h * 0.45))
    seat = 36.0
    chair_hx, chair_hy = seat * 0.45, seat * 0.45
    for (cx, cy, angle) in CHAIRS:
        PROP_COLLIDERS.append((cx, cy, chair_hx, chair_hy))

#Room 1 Puzzle
PLAT_L_POS = (-80.0, 20.0, FLOOR_Z + 4.0)
PLAT_R_POS = (80.0, 20.0, FLOOR_Z + 4.0)
PLAT_SIZE = (90.0, 90.0, 8.0)
BALANCE_TOL = 0.05
require_nonempty = True
objs = [{"pos": [-160, -20, PLAT_SIZE[2] / 2 + FLOOR_Z], "w": 3.0, "held": False, "on": "none", "col": (0.8, 0.3, 0.3), "size": 22},
        {"pos": [-170, 80, PLAT_SIZE[2] / 2 + FLOOR_Z], "w": 2.0, "held": False, "on": "none", "col": (0.3, 0.8, 0.3), "size": 20},
        {"pos": [160, 0, PLAT_SIZE[2] / 2 + FLOOR_Z], "w": 4.0, "held": False, "on": "none", "col": (0.3, 0.4, 0.9), "size": 24},
        {"pos": [120, -90, PLAT_SIZE[2] / 2 + FLOOR_Z], "w": 1.0, "held": False, "on": "none", "col": (0.9, 0.8, 0.2), "size": 18},
        {"pos": [0, -140, PLAT_SIZE[2] / 2 + FLOOR_Z], "w": 5.0, "held": False, "on": "none", "col": (0.8, 0.5, 0.2), "size": 26},]
held_index = -1

def altar_platforms_and_objects():
    #Platforms
    glColor3f(0.2, 0.2, 0.2)
    for cx, cy, cz in [PLAT_L_POS, PLAT_R_POS]:
        glPushMatrix()
        glTranslatef(cx, cy, cz)
        draw_box(PLAT_SIZE[0], PLAT_SIZE[1], PLAT_SIZE[2])
        glPopMatrix()
    #Center line
    glColor3f(0.3, 0.28, 0.35)
    glPushMatrix()
    glTranslatef(0, 20.0, FLOOR_Z + 12)
    draw_box(40, PLAY_INNER * 0.6, 6)
    glPopMatrix()
    #Objects
    for o in objs:
        glColor3f(*o["col"])
        glPushMatrix()
        glTranslatef(o["pos"][0], o["pos"][1], o["pos"][2])
        glutSolidCube(o["size"])
        glPopMatrix()

def try_pick_or_place():
    global held_index
    if held_index != -1:
        o = objs[held_index]
        yaw = math.radians(player_yaw)
        fx, fy = math.sin(yaw), math.cos(yaw)
        drop_x = player_pos[0] + fx * 28
        drop_y = player_pos[1] + fy * 28
        drop_x = clamp(drop_x, -HALF_PLAY + 28, HALF_PLAY - 28)
        drop_y = clamp(drop_y, -HALF_PLAY + 28, HALF_PLAY - 28)
        o["pos"][0], o["pos"][1] = drop_x, drop_y

        def inside(px, py, cx, cy):
            return (abs(px - cx) <= PLAT_SIZE[0] / 2 - 4) and (abs(py - cy) <= PLAT_SIZE[1] / 2 - 4)
        if inside(drop_x, drop_y, PLAT_L_POS[0], PLAT_L_POS[1]):
            o["on"] = "L"
        elif inside(drop_x, drop_y, PLAT_R_POS[0], PLAT_R_POS[1]):
            o["on"] = "R"
        else:
            o["on"] = "none"
        o["held"] = False
        held_index = -1
        wL, wR, nL, nR = compute_weights()
        print(f"Left = {wL}, Right = {wR}")
        if require_nonempty and nL > 0 and nR > 0:
            diff = abs(wL - wR) / max(1.0, (wL + wR) / 2.0)
            if diff <= BALANCE_TOL:
                print("Weights balanced! Proceed to next room.")
        return
    nearest_i = -1;
    nearest_d2 = 999999
    for i, o in enumerate(objs):
        if o["held"]: continue
        dx = o["pos"][0] - player_pos[0];
        dy = o["pos"][1] - player_pos[1]
        d2 = dx * dx + dy * dy
        if d2 < nearest_d2: nearest_d2 = d2; nearest_i = i
    if nearest_i != -1 and nearest_d2 <= (36 * 36):
        objs[nearest_i]["held"] = True
        objs[nearest_i]["on"] = "none"
        held_index = nearest_i

def update_held_object():
    if held_index == -1: return
    o = objs[held_index]
    yaw = math.radians(player_yaw)
    fx, fy = math.sin(yaw), math.cos(yaw)
    o["pos"][0] = player_pos[0] + fx * 30
    o["pos"][1] = player_pos[1] + fy * 30
    o["pos"][2] = FLOOR_Z + PLAT_SIZE[2] / 2 + 8 + 3 * math.sin(time.time() * 6.0)

def compute_weights():
    wL = sum(o["w"] for o in objs if o["on"] == "L")
    wR = sum(o["w"] for o in objs if o["on"] == "R")
    nL = sum(1 for o in objs if o["on"] == "L")
    nR = sum(1 for o in objs if o["on"] == "R")
    return wL, wR, nL, nR

def check_balance_and_open_gate():
    if gate_open[0]: return
    wL, wR, nL, nR = compute_weights()
    if require_nonempty and (nL == 0 or nR == 0): return
    total = wL + wR
    if total <= 0: return
    diff = abs(wL - wR) / max(1.0, (wL + wR) / 2.0)
    if diff <= BALANCE_TOL:
        gate_open[0] = True
        gate_open_time[0] = time.time()

# Room 2
COLOR_SEQUENCE = ['red', 'blue', 'green', 'yellow']
AVAILABLE_COLORS = ['red', 'blue', 'green', 'yellow']
color_switches = [{"pos": [-120, 80], "color": "red", "active": False, "col": (0.9, 0.2, 0.2)},
                  {"pos": [120, 80], "color": "blue", "active": False, "col": (0.2, 0.2, 0.9)},
                  {"pos": [-120, -80], "color": "green", "active": False, "col": (0.2, 0.9, 0.2)},
                  {"pos": [120, -80], "color": "yellow", "active": False, "col": (0.9, 0.9, 0.2)}, ]
current_sequence = []
sequence_correct = False
last_switch_time = 0
SWITCH_COOLDOWN = 0.5
ROOM2_COLLIDERS = []
def rebuild_room2_colliders():
    global ROOM2_COLLIDERS
    ROOM2_COLLIDERS = []
    for switch in color_switches:
        x, y = switch["pos"]
        ROOM2_COLLIDERS.append((x, y, 30, 30))
    ROOM2_COLLIDERS.append((0, 0, 35, 35))

def randomize_color_sequence():
    global COLOR_SEQUENCE
    COLOR_SEQUENCE = AVAILABLE_COLORS.copy()
    random.shuffle(COLOR_SEQUENCE)
    print(f"New color sequence: {COLOR_SEQUENCE}")

def draw_cylinder(radius, height, slices=16):
    #Bottom cap
    glBegin(GL_POLYGON)
    for i in range(slices):
        angle = 2.0 * math.pi * i / slices
        x = radius * math.cos(angle)
        y = radius * math.sin(angle)
        glVertex3f(x, y, 0)
    glEnd()
    #Top cap
    glBegin(GL_POLYGON)
    for i in range(slices):
        angle = 2.0 * math.pi * i / slices
        x = radius * math.cos(angle)
        y = radius * math.sin(angle)
        glVertex3f(x, y, height)
    glEnd()
    #Side wall
    glBegin(GL_QUAD_STRIP)
    for i in range(slices + 1):
        angle = 2.0 * math.pi * i / slices
        x = radius * math.cos(angle)
        y = radius * math.sin(angle)
        glVertex3f(x, y, 0)
        glVertex3f(x, y, height)
    glEnd()

def draw_color_switches(room_base_y):
    for switch in color_switches:
        x, y = switch["pos"]
        y += room_base_y
        glColor3f(0.3, 0.3, 0.3)
        glPushMatrix()
        glTranslatef(x, y, FLOOR_Z)
        draw_cylinder(25, 30)
        glPopMatrix()
        if switch["active"]:
            glow_factor = 1.5
            glColor3f(min(1.0, switch["col"][0] * glow_factor), min(1.0, switch["col"][1] * glow_factor), min(1.0, switch["col"][2] * glow_factor))
        else:
            glColor3f(*switch["col"])
        glPushMatrix()
        glTranslatef(x, y, FLOOR_Z + 35 + (5 if switch["active"] else 0))
        glutSolidSphere(15, 16, 16)
        glPopMatrix()

def draw_central_buzzer(room_base_y):
    y = room_base_y
    glColor3f(0.4, 0.4, 0.4)
    glPushMatrix()
    glTranslatef(0, y, FLOOR_Z)
    draw_cylinder(30, 50)
    glPopMatrix()
    if sequence_correct and not gate_open[1]:
        pulse = 0.3 + 0.2 * math.sin(time.time() * 4.0)
        glColor3f(0.2 + pulse, 1.0, 0.2 + pulse)
    elif gate_open[1]:
        glColor3f(1.0, 1.0, 1.0)
    else:
        glColor3f(0.5, 0.1, 0.1)
    glPushMatrix()
    glTranslatef(0, y, FLOOR_Z + 55 + (5 if sequence_correct else 0))
    glutSolidSphere(20, 16, 16)
    glPopMatrix()

def try_activate_switch():
    global current_sequence, sequence_correct, last_switch_time
    if time.time() - last_switch_time < SWITCH_COOLDOWN:
        return
    room_base_y = room_offset_y(current_room)
    if sequence_correct and not gate_open[1]:
        buzzer_x, buzzer_y = 0, room_base_y
        buzzer_dist = math.sqrt((player_pos[0] - buzzer_x) ** 2 + (player_pos[1] - buzzer_y) ** 2)
        if buzzer_dist < 60:
            last_switch_time = time.time()
            gate_open[1] = True
            gate_open_time[1] = time.time()
            print(f"Buzzer activated! Next room gate opening!")
            return
    nearest_switch = None
    nearest_dist = float('inf')
    for switch in color_switches:
        x, y = switch["pos"]
        y += room_base_y
        dist = math.sqrt((player_pos[0] - x) ** 2 + (player_pos[1] - y) ** 2)
        if dist < 50 and dist < nearest_dist:
            nearest_dist = dist
            nearest_switch = switch
    if nearest_switch:
        last_switch_time = time.time()
        expected_next = len(current_sequence)
        if (expected_next < len(COLOR_SEQUENCE) and
                nearest_switch["color"] == COLOR_SEQUENCE[expected_next]):
            nearest_switch["active"] = True
            current_sequence.append(nearest_switch["color"])
            print(f"Activated {nearest_switch['color']} switch. Sequence: {current_sequence}")
            if len(current_sequence) == len(COLOR_SEQUENCE):
                sequence_correct = True
                print("Color sequence complete! Go to central buzzer and press E")
        else:
            print(f"Wrong switch! Expected {COLOR_SEQUENCE[expected_next] if expected_next < len(COLOR_SEQUENCE) else 'none'}, got {nearest_switch['color']}")
            reset_color_sequence()

def reset_color_sequence():
    global current_sequence, sequence_correct
    current_sequence = []
    sequence_correct = False
    for switch in color_switches:
        switch["active"] = False

#Room 3
def rebuild_room3_colliders():
    global ROOM3_COLLIDERS
    ROOM3_COLLIDERS = []
    base_y = room_offset_y(2)
    for (cx, cy, w, h) in MAZE_WALLS:
        ROOM3_COLLIDERS.append((cx, base_y + cy, w / 2 - 2, h / 2 - 2))
    for (tx, ty, tw, th) in TRAPS:
        ROOM3_COLLIDERS.append((tx, base_y + ty, tw / 2 - 2, th / 2 - 2))
    ex, ey, ew, eh = maze_exit
    ROOM3_COLLIDERS.append((ex, base_y + ey, ew / 2 - 2, eh / 2 - 2))

def draw_maze_and_traps(base_y):
    glColor3f(0.35, 0.2, 0.1)
    for (cx, cy, w, h) in MAZE_WALLS:
        glPushMatrix()
        glTranslatef(cx, base_y + cy, FLOOR_Z + 30)
        draw_box(w, h, 60)
        glPopMatrix()
    for (tx, ty, tw, th) in TRAPS:
        glPushMatrix()
        glTranslatef(tx, base_y + ty, FLOOR_Z + 10)
        pulse = 0.3 + 0.2 * math.sin(time.time() * 4.0)
        glColor3f(1.0, 0.2 + pulse, 0.0)
        draw_box(tw, th, 20)
        glPopMatrix()
    glPushMatrix()
    glTranslatef(maze_exit[0], base_y + maze_exit[1], FLOOR_Z + 5)
    glColor3f(0.0, 1.0, 0.0)
    draw_box(maze_exit[2], maze_exit[3], 10)
    glPopMatrix()

def generate_random_maze():
    global MAZE_WALLS, TRAPS, maze_exit
    MAZE_WALLS = []
    TRAPS = []
    #maze (1 = wall, 0 = passage)
    grid = [[1 for _ in range(MAZE_SIZE)] for _ in range(MAZE_SIZE)]
    def neighbors(r, c):
        dirs = [(-2, 0), (2, 0), (0, -2), (0, 2)]
        result = []
        for dr, dc in dirs:
            nr, nc = r + dr, c + dc
            if 0 <= nr < MAZE_SIZE and 0 <= nc < MAZE_SIZE:
                if grid[nr][nc] == 1:
                    result.append((nr, nc, dr, dc))
        return result
    start_r, start_c = MAZE_SIZE - 1, MAZE_SIZE // 2
    stack = [(start_r, start_c)]
    grid[start_r][start_c] = 0
    while stack:
        r, c = stack[-1]
        ns = neighbors(r, c)
        if ns:
            nr, nc, dr, dc = random.choice(ns)
            grid[r + dr // 2][c + dc // 2] = 0
            grid[nr][nc] = 0
            stack.append((nr, nc))
        else:
            stack.pop()
    exit_r, exit_c = 0, MAZE_SIZE // 2
    maze_exit = (-HALF_PLAY + (exit_c + 0.5) * CELL_SIZE, HALF_PLAY - 20, CELL_SIZE * 0.8, 40)
    from collections import deque
    queue = deque([(start_r, start_c)])
    came_from = {(start_r, start_c): None}
    while queue:
        r, c = queue.popleft()
        if (r, c) == (exit_r, exit_c):
            break
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < MAZE_SIZE and 0 <= nc < MAZE_SIZE and grid[nr][nc] == 0 and (nr, nc) not in came_from:
                came_from[(nr, nc)] = (r, c)
                queue.append((nr, nc))
    path_cells = set()
    cur = (exit_r, exit_c)
    while cur is not None:
        path_cells.add(cur)
        cur = came_from.get(cur)
    for i in range(MAZE_SIZE):
        for j in range(MAZE_SIZE):
            if grid[i][j] == 1:
                cx = -HALF_PLAY + (j + 0.5) * CELL_SIZE
                cy = (i + 0.5) * CELL_SIZE - HALF_PLAY
                MAZE_WALLS.append((cx, cy, CELL_SIZE * 0.95, CELL_SIZE * 0.95))
    passages = [(i, j) for i in range(MAZE_SIZE) for j in range(MAZE_SIZE) if grid[i][j] == 0]
    dead_ends = []
    for i, j in passages:
        cnt = 0
        for di, dj in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            if 0 <= i + di < MAZE_SIZE and 0 <= j + dj < MAZE_SIZE and grid[i + di][j + dj] == 0:
                cnt += 1
        if cnt == 1 and (i, j) not in path_cells:
            dead_ends.append((i, j))
    for (i, j) in random.sample(dead_ends, min(len(dead_ends), MAZE_SIZE)):
        cx = -HALF_PLAY + (j + 0.5) * CELL_SIZE
        cy = (i + 0.5) * CELL_SIZE - HALF_PLAY
        TRAPS.append((cx, cy, CELL_SIZE * 0.6, CELL_SIZE * 0.6))

def check_maze_logic():
    global dead, trap_triggered, congratulations, gate_open, game_complete_time
    if dead or congratulations:
        return
    base_y = room_offset_y(2)
    px, py = player_pos[0], player_pos[1]
    for (tx, ty, tw, th) in TRAPS:
        if aabb_point_hit(tx, base_y + ty, tw / 2, th / 2, px, py, pad=player_radius):
            trap_triggered = True
            dead = True
            print("Triggered a trap! You died.")
            return
    ex, ey, ew, eh = maze_exit
    if aabb_point_hit(ex, base_y + ey, ew / 2, eh / 2, px, py, pad=player_radius):
        congratulations = True
        gate_open[2] = True
        game_complete_time = time.time()
        print("Congratulations! You escaped the maze!")

def draw_room_shell(room_index, elapsed, tleft):
    base_y = room_offset_y(room_index)
    if room_index == 0:
        glColor3f(0.15, 0.14, 0.18)
    elif room_index == 1:
        glColor3f(0.18, 0.17, 0.22)
    else:
        glColor3f(0.0, 0.0, 0.0)
    glPushMatrix()
    glTranslatef(0, base_y, FLOOR_Z - 1)
    draw_panel(PLAY_INNER, PLAY_INNER)
    glPopMatrix()
    if room_index == 0:
        west_col = east_col = south_col = north_col = (0.75, 0.75, 0.75)
    elif room_index == 1:
        west_col = (0.6, 0.1, 0.1)
        east_col = (0.1, 0.1, 0.6)
        south_col = (0.1, 0.6, 0.1)
        north_col = (0.8, 0.6, 0.1)
    else:  #Room 3
        west_col = east_col = south_col = north_col = (0.35, 0.2, 0.1)
    #West wall
    glColor3f(*west_col)
    glPushMatrix()
    glTranslatef(-HALF_PLAY - WALL_THICK / 2, base_y, CEILING_Z / 2)
    draw_box(WALL_THICK, PLAY_INNER, CEILING_Z)
    glPopMatrix()
    #East wall
    glColor3f(*east_col)
    glPushMatrix()
    glTranslatef(HALF_PLAY + WALL_THICK / 2, base_y, CEILING_Z / 2)
    draw_box(WALL_THICK, PLAY_INNER, CEILING_Z)
    glPopMatrix()
    #South wall
    glColor3f(*south_col)
    glPushMatrix()
    glTranslatef(0, base_y - HALF_PLAY - WALL_THICK / 2, CEILING_Z / 2)
    draw_box(PLAY_INNER, WALL_THICK, CEILING_Z)
    glPopMatrix()
    #North wall
    glColor3f(*north_col)
    if room_index < NUM_ROOMS - 1:
        gate_w, gate_h = 160.0, 120.0
        seg_w = (PLAY_INNER - gate_w) / 2.0
        ny = base_y + HALF_PLAY + WALL_THICK / 2
        zc = CEILING_Z / 2
        #Left wall
        glPushMatrix()
        glTranslatef(-gate_w / 2 - seg_w / 2, ny, zc)
        draw_box(seg_w, WALL_THICK, CEILING_Z)
        glPopMatrix()
        #Right wall
        glPushMatrix()
        glTranslatef(gate_w / 2 + seg_w / 2, ny, zc)
        draw_box(seg_w, WALL_THICK, CEILING_Z)
        glPopMatrix()
        #Above gate
        glPushMatrix()
        glTranslatef(0, ny, (CEILING_Z + gate_h) / 2)
        draw_box(gate_w, WALL_THICK, CEILING_Z - gate_h)
        glPopMatrix()
        #Gate
        if gate_open[room_index]:
            t_open = min(1.0, (time.time() - gate_open_time[room_index]) / 2.0)
            lift = t_open * (gate_h + 10.0)
        else:
            lift = 0.0
        glColor3f(0.58, 0.29, 0.0)
        glPushMatrix()
        glTranslatef(0, ny, gate_h / 2 + lift)
        draw_box(gate_w, WALL_THICK, gate_h)
        glPopMatrix()
    else:
        glPushMatrix()
        glTranslatef(0, base_y + HALF_PLAY + WALL_THICK / 2, CEILING_Z / 2)
        draw_box(PLAY_INNER, WALL_THICK, CEILING_Z)
        glPopMatrix()

    def draw_torch(x, y, z_base, flicker_offset=0.0):
        glColor3f(0.4, 0.2, 0.1)
        glPushMatrix()
        glTranslatef(x, y, z_base + 30)
        draw_box(6, 6, 60)
        glPopMatrix()
        flicker = 1.0 + 0.2 * math.sin(time.time() * 8.0 + flicker_offset)
        glColor3f(1.0, 0.5 + 0.3 * random.random(), 0.0)
        glPushMatrix()
        glTranslatef(x, y, z_base + 70)
        glScalef(flicker, flicker, flicker)
        quad = gluNewQuadric()
        gluSphere(quad, 10, 12, 12)
        glPopMatrix()
    z_base = FLOOR_Z
    torch_spacing = 120.0
    draw_torch(-HALF_PLAY, base_y - torch_spacing, z_base, 0.0)
    draw_torch(-HALF_PLAY, base_y + torch_spacing, z_base, 1.0)
    draw_torch(HALF_PLAY, base_y - torch_spacing, z_base, 2.0)
    draw_torch(HALF_PLAY, base_y + torch_spacing, z_base, 3.0)
    draw_torch(-torch_spacing, base_y - HALF_PLAY, z_base, 4.0)
    draw_torch(torch_spacing, base_y - HALF_PLAY, z_base, 5.0)
    #Poison
    room_time_elapsed = time.time() - room_start_time
    room_time_left = max(0, ROOM_TIMES[room_index] - room_time_elapsed)
    start_fill_at = ROOM_TIMES[room_index] * 0.20
    if room_index == 2 and congratulations:
        pass
    elif room_time_left <= start_fill_at or dead:
        frac = 1.0 if dead else clamp((start_fill_at - room_time_left) / start_fill_at, 0.0, 1.0)
        h = CEILING_Z * frac
        glColor3f(0.0, 0.9, 0.35)
        glPushMatrix()
        glTranslatef(0, base_y, h / 2.0)
        draw_box(PLAY_INNER, PLAY_INNER, h)
        glPopMatrix()

def draw_room_contents(room_index):
    base_y = room_offset_y(room_index)
    if room_index == 0:
        draw_table(TABLE_POS[0], base_y + TABLE_POS[1])
        for (cx, cy, angle) in CHAIRS:
            draw_chair(cx, base_y + cy, angle)
        glPushMatrix()
        glTranslatef(0, base_y, 0)
        altar_platforms_and_objects()
        glPopMatrix()
    elif room_index == 1:
        draw_central_buzzer(base_y)
        draw_color_switches(base_y)
        glColor3f(0.18, 0.17, 0.22)
        glPushMatrix()
        glTranslatef(0, base_y, FLOOR_Z - 0.5)
        draw_panel(PLAY_INNER * 0.9, PLAY_INNER * 0.9)
        glPopMatrix()
    elif room_index == 2:
        draw_maze_and_traps(base_y)

#Player
def draw_player():
    glPushMatrix()
    glTranslatef(player_pos[0], player_pos[1], FLOOR_Z)
    glRotatef(player_yaw, 0, 0, 1)
    if dead:
        fall_rotation = death_animation_progress * 90
        glRotatef(fall_rotation, 1, 0, 0)
        sink_amount = death_animation_progress * 10
        glTranslatef(0, 0, -sink_amount)
    #Body
    glPushMatrix()
    glColor3f(0.2, 0.2, 0.2)
    glTranslatef(0, 0, 30)
    glScalef(1.6, 1.0, 2.4)
    glutSolidCube(20)
    glPopMatrix()
    #Head
    glColor3f(1.0, 0.85, 0.7)
    glPushMatrix()
    glTranslatef(0, 0, 65)
    glutSolidCube(18)
    #Face
    glPushMatrix()
    glTranslatef(0, 9.5, 0)
    #Eyes and Nose
    glColor3f(0, 0, 0)
    glPointSize(4.0)
    glBegin(GL_POINTS)
    glVertex3f(-4, 0, 2)  #Left eye
    glVertex3f(4, 0, 2)  #Right eye
    glVertex3f(0, 0, 0)  #Nose
    glEnd()
    #Mouth
    glLineWidth(2.0)
    glBegin(GL_LINES)
    glVertex3f(-4, 0, -3)  #Left corner
    glVertex3f(4, 0, -3)  #Right corner
    glEnd()
    glPopMatrix()
    glPopMatrix()
    #Arms
    glColor3f(1.0, 0.85, 0.7)
    for sx in (-1, 1):
        glPushMatrix()
        glTranslatef(18 * sx, 0, 40)
        glScalef(0.6, 1.0, 2.0)
        glutSolidCube(10)
        glPopMatrix()
    #Legs
    glColor3f(0.2, 0.2, 0.8)
    for sx in (-1, 1):
        glPushMatrix()
        glTranslatef(6 * sx, 0, 10)
        glScalef(0.8, 1.0, 2.4)
        glutSolidCube(12)
        glPopMatrix()
    glPopMatrix()

#Camera
def compute_camera():
    px, py, pz = player_pos
    #First-person
    if camera_mode == 1:
        yaw = player_yaw + (fp_look_yaw if cam_free else 0.0)
        pitch = clamp(fp_look_pitch if cam_free else 0.0, -60.0, 60.0)
        yaw_r = math.radians(yaw)
        pitch_r = math.radians(pitch)
        fx = math.cos(pitch_r) * math.sin(yaw_r)
        fy = math.cos(pitch_r) * math.cos(yaw_r)
        fz = math.sin(pitch_r)
        cx, cy, cz = px, py, pz + 22
        tx, ty, tz = cx + fx * 60.0, cy + fy * 60.0, cz + fz * 60.0
        return (cx, cy, cz), (tx, ty, tz)
    #Third-person
    yaw_total = player_yaw + tp_orbit_yaw
    yaw_r = math.radians(yaw_total)
    pitch_r = math.radians(clamp(tp_orbit_pitch, -60.0, 80.0))
    ox = tp_orbit_dist * math.cos(pitch_r) * math.sin(yaw_r)
    oy = tp_orbit_dist * math.cos(pitch_r) * math.cos(yaw_r)
    oz = tp_orbit_dist * math.sin(pitch_r)
    cx, cy, cz = px - ox, py - oy, pz + 40 + oz
    tx, ty, tz = px, py, pz + 20
    # Camera stays inside room
    base_y = room_offset_y(current_room)
    minx = -HALF_PLAY + 10
    maxx = HALF_PLAY - 10
    miny = base_y - HALF_PLAY + 10
    maxy = base_y + HALF_PLAY - 10
    cx = clamp(cx, minx, maxx)
    cy = clamp(cy, miny, maxy)
    return (cx, cy, cz), (tx, ty, tz)

def setup_camera():
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(FOVY, ASPECT, 0.1, 4000.0)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    cam, tgt = compute_camera()
    gluLookAt(cam[0], cam[1], cam[2], tgt[0], tgt[1], tgt[2], 0, 0, 1)

#Time Calculation
def time_left():
    global dead, death_animation_progress, death_animation_start
    if congratulations:
        return ROOM_TIMES[current_room] - (game_complete_time - room_start_time)
    left = ROOM_TIMES[current_room] - (time.time() - room_start_time)
    if left <= 0 and not dead:
        dead = True
        death_animation_start = time.time()
        return 0.0
    return max(0.0, left)

def reset_room_timer():
    global room_start_time
    room_start_time = time.time()

#Restart
def full_restart():
    global current_room, player_pos, player_yaw, dead, gate_open
    global held_index, fp_look_yaw, fp_look_pitch, tp_orbit_yaw, tp_orbit_pitch
    global death_animation_progress, death_animation_start
    global trap_triggered, congratulations, game_complete_time
    if NUM_ROOMS >= 3:
        generate_random_maze()
    current_room = 0
    player_pos[:] = [0.0, -HALF_PLAY + 60.0, 30.0]
    player_yaw = 0.0
    trap_triggered = False
    congratulations = False
    dead = False
    death_animation_progress = 0.0
    death_animation_start = 0.0
    gate_open = [False, False, False]
    #Randomize Room 1 puzzle
    randomize_objects()
    #Randomize Room 2 color
    held_index = -1
    fp_look_yaw = 0.0
    fp_look_pitch = 0.0
    tp_orbit_yaw = 0.0
    tp_orbit_pitch = 20.0
    #Reset Room 2 color puzzle
    reset_color_sequence()
    print("Welcome to Room 1")
    reset_room_timer()

#Collisions
def aabb_point_hit(cx, cy, hx, hy, px, py, pad=0.0):
    return (px >= cx - hx - pad and px <= cx + hx + pad and py >= cy - hy - pad and py <= cy + hy + pad)

def collide_player_with_props(prev_x, prev_y):
    px, py = player_pos[0], player_pos[1]
    #Room 1
    if current_room == 0:
        for (cx, cy, hx, hy) in PROP_COLLIDERS:
            if aabb_point_hit(cx, cy, hx, hy, px, py, pad=player_radius):
                player_pos[0], player_pos[1] = prev_x, prev_y
                return
    #Room 2
    elif current_room == 1:
        base_y = room_offset_y(current_room)
        for (cx, cy, hx, hy) in ROOM2_COLLIDERS:
            world_cy = cy + base_y
            if aabb_point_hit(cx, world_cy, hx, hy, px, py, pad=player_radius):
                player_pos[0], player_pos[1] = prev_x, prev_y
                return
    #Room 3
    elif current_room == 2:
        base_y = room_offset_y(current_room)
        for (cx, cy, hx, hy) in ROOM3_COLLIDERS:
            if aabb_point_hit(cx, cy, hx, hy, px, py, pad=player_radius):
                player_pos[0], player_pos[1] = prev_x, prev_y
                return

def collide_player_with_walls_and_gate():
    base_y = room_offset_y(current_room)
    minx = -HALF_PLAY + player_radius
    maxx = HALF_PLAY - player_radius
    miny = base_y - HALF_PLAY + player_radius
    maxy = base_y + HALF_PLAY - player_radius
    #Gate
    gate_closed_y = base_y + HALF_PLAY - player_radius
    if current_room < NUM_ROOMS - 1 and not gate_open[current_room]:
        maxy = base_y + HALF_PLAY - WALL_THICK - player_radius
    player_pos[0] = clamp(player_pos[0], minx, maxx)
    player_pos[1] = clamp(player_pos[1], miny, maxy)

def try_room_transition():
    global current_room
    if current_room >= NUM_ROOMS - 1:
        return
    base_y = room_offset_y(current_room)
    if gate_open[current_room] and player_pos[1] >= base_y + HALF_PLAY - WALL_THICK - player_radius - 2:
        current_room += 1
        player_pos[1] = room_offset_y(current_room) - HALF_PLAY + 60.0
        reset_room_timer()
        print(f"Welcome to Room {current_room + 1}")
        if current_room == 1:
            randomize_color_sequence()
        elif current_room == 2:
            generate_random_maze()
            rebuild_room3_colliders()

last_frame_time = time.time()
def keyboard_down(key, x, y):
    global cam_free
    keys_down.add(key)
    if key == b'r':
        full_restart()
    elif key in (b'E', b'e'):
        if current_room == 0 and not dead:
            try_pick_or_place()
        elif current_room == 1 and not dead:
            try_activate_switch()
    elif key in (b'c', b'C'):
        cam_free = not cam_free

def keyboard_up(key, x, y):
    if key in keys_down: keys_down.discard(key)

def special_down(key, x, y):
    if cam_free:
        if camera_mode == 0:
            #Third-person
            if key == GLUT_KEY_LEFT:  adjust_tp_orbit(-6.0, 0.0)
            if key == GLUT_KEY_RIGHT: adjust_tp_orbit(+6.0, 0.0)
            if key == GLUT_KEY_UP:    adjust_tp_orbit(0.0, +4.0)
            if key == GLUT_KEY_DOWN:  adjust_tp_orbit(0.0, -4.0)
        else:
            #First-person
            if key == GLUT_KEY_LEFT:  adjust_fp_look(-6.0, 0.0)
            if key == GLUT_KEY_RIGHT: adjust_fp_look(+6.0, 0.0)
            if key == GLUT_KEY_UP:    adjust_fp_look(0.0, +4.0)
            if key == GLUT_KEY_DOWN:  adjust_fp_look(0.0, -4.0)

def special_up(key, x, y):
    pass

def adjust_tp_orbit(dyaw, dpitch):
    global tp_orbit_yaw, tp_orbit_pitch
    tp_orbit_yaw += dyaw
    tp_orbit_pitch = clamp(tp_orbit_pitch + dpitch, -60.0, 80.0)

def adjust_fp_look(dyaw, dpitch):
    global fp_look_yaw, fp_look_pitch
    fp_look_yaw += dyaw
    fp_look_pitch = clamp(fp_look_pitch + dpitch, -60.0, 60.0)

def mouse(button, state, x, y):
    global camera_mode
    if button == GLUT_RIGHT_BUTTON and state == GLUT_DOWN:
        camera_mode = 1 - camera_mode

def update_player(dt):
    global player_yaw
    prev_x, prev_y = player_pos[0], player_pos[1]
    if b'q' in keys_down: player_yaw += turn_speed * dt
    if b'e' in keys_down: player_yaw -= turn_speed * dt
    move_x = (b'd' in keys_down) - (b'a' in keys_down)
    move_y = (b'w' in keys_down) - (b's' in keys_down)
    if move_x or move_y:
        mag = math.sqrt(move_x * move_x + move_y * move_y)
        move_x /= mag
        move_y /= mag
        yaw_r = math.radians(player_yaw)
        f = (math.sin(yaw_r), math.cos(yaw_r))
        r = (f[1], -f[0])
        vx = (f[0] * move_y + r[0] * move_x) * player_speed * dt
        vy = (f[1] * move_y + r[1] * move_x) * player_speed * dt
        player_pos[0] += vx
        player_pos[1] += vy
    collide_player_with_walls_and_gate()
    collide_player_with_props(prev_x, prev_y)

def try_room_logic(dt):
    if current_room == 0 and not dead:
        update_held_object()
        check_balance_and_open_gate()
    elif current_room == 1 and not dead:
        pass
    elif current_room == 2 and not dead:
        check_maze_logic()
    try_room_transition()

objs = []
held_index = -1
def randomize_objects():
    global objs, held_index
    objs = []
    num_objects = random.randint(4, 6)
    total_weight = random.randint(num_objects * 2, num_objects * 6)
    if total_weight % 2 != 0:
        total_weight += 1
    parts = [1] * num_objects
    remaining = total_weight - num_objects
    for _ in range(remaining):
        parts[random.randint(0, num_objects - 1)] += 1
    random.shuffle(parts)
    for w in parts:
        size = 16 + w * 2
        color = (random.random(), random.random(), random.random())
        x = random.randint(int(-HALF_PLAY + 40), int(HALF_PLAY - 40))
        y = random.randint(int(-HALF_PLAY + 40), int(HALF_PLAY - 40))
        objs.append({"pos": [x, y, PLAT_SIZE[2] / 2 + FLOOR_Z], "w": int(w), "held": False, "on": "none", "col": color, "size": size})
    held_index = -1

def idle():
    global last_frame_time, death_animation_progress
    if congratulations and time.time() - game_complete_time > 10:
        glutDestroyWindow(glutGetWindow())
        return
    now = time.time()
    dt = now - last_frame_time
    last_frame_time = now
    if not dead:
        update_player(dt)
        try_room_logic(dt)
    else:
        time_since_death = now - death_animation_start
        death_animation_progress = min(1.0, time_since_death / death_animation_duration)
    glutPostRedisplay()

def draw_hud():
    mode = "First-Person" if camera_mode == 1 else "Third-Person"
    camtag = "CAMERA-ONLY: arrows control camera" if cam_free else "Player Mode"
    draw_text(10, WIN_H - 30, f"Room {current_room + 1}/{NUM_ROOMS}  |  Camera: {mode}  |  {camtag}")
    draw_text(10, WIN_H - 60, "WASD move, Q/E turn, E pick/place/activate, Right-Click FP/TP, C camera-only, R restart")
    tleft = int(time_left())
    draw_text(WIN_W - 140, WIN_H - 30, f"Time: {tleft:02d}s")
    if current_room == 0:
        wL, wR, nL, nR = compute_weights()
        draw_text(10, 20, f"Balance: L={wL:.1f}(n={nL})  R={wR:.1f}(n={nR})  Target ±5% & both non-empty")
        if gate_open[0]:
            draw_text(WIN_W // 2 - 80, WIN_H // 2, "GATE OPEN! Proceed ➜")
    elif current_room == 1:
        seq_text = "Sequence: " + " → ".join(COLOR_SEQUENCE)
        draw_text(10, 20, seq_text)
        current_text = "Current: " + " → ".join(current_sequence) if current_sequence else "Current: (none)"
        draw_text(10, 50, current_text)
        if gate_open[1]:
            draw_text(WIN_W // 2 - 100, WIN_H // 2, "GATE OPEN! Proceed ➜")
        elif sequence_correct:
            draw_text(10, 80, "Sequence complete! Press E at central buzzer to open gate")
        else:
            draw_text(10, 80, "Stand near colored switches and press E to activate in sequence")
    elif current_room == 2:
        draw_text(10, 20, "Navigate the maze to find the exit!")
        draw_text(10, 50, "Avoid the red traps!")
        if congratulations:
            draw_text(WIN_W // 2 - 200, WIN_H // 2 + 40, "CONGRATULATIONS!", GLUT_BITMAP_TIMES_ROMAN_24)
            draw_text(WIN_W // 2 - 180, WIN_H // 2, "NOW YOU ARE FREE!", GLUT_BITMAP_TIMES_ROMAN_24)
    if dead:
        draw_text(WIN_W // 2 - 80, WIN_H // 2 + 40, "YOU DIED")
        draw_text(WIN_W // 2 - 220, WIN_H // 2 - 0, "Press R to restart from Room 1")

def render_scene():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glViewport(0, 0, WIN_W, WIN_H)
    setup_camera()
    tleft = time_left()
    elapsed = time.time() - room_start_time
    for i in range(NUM_ROOMS):
        draw_room_shell(i, elapsed, tleft)
        draw_room_contents(i)
    if camera_mode == 0:
        draw_player()
    draw_hud()
    glutSwapBuffers()

def init_gl():
    glClearColor(0.02, 0.02, 0.03, 1.0)
    glEnable(GL_DEPTH_TEST)
    glShadeModel(GL_SMOOTH)
    glEnable(GL_CULL_FACE)
    glCullFace(GL_BACK)

def main():
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(WIN_W, WIN_H)
    glutInitWindowPosition(60, 30)
    glutCreateWindow(b"Escape Room Game")
    init_gl()
    rebuild_prop_colliders()
    rebuild_room2_colliders()
    rebuild_room3_colliders()
    full_restart()
    glutDisplayFunc(render_scene)
    glutKeyboardFunc(keyboard_down)
    glutKeyboardUpFunc(keyboard_up)
    glutSpecialFunc(special_down)
    glutSpecialUpFunc(special_up)
    glutMouseFunc(mouse)
    glutIdleFunc(idle)
    glutMainLoop()
main()