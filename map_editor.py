import json
import math
import os
import sys
import csv
import pygame


"""
Scrollable tile + mob editor.

Usage (from project root):
    python map_editor.py [map_id]

Highlights
----------
- Paint tiles by selecting any sprite from sprites/maps/tile/*
- Tile data is stored as numeric IDs defined in maps/tile_manifest.json
- Viewport can scroll (arrow keys / WASD) so the map can be wider than the window
- Palette on the right lists every tile (scroll with mouse-wheel)
- Toggle between tile editing and mob placement with TAB
- Tiles now rendered at ORIGINAL PIXEL SIZE (no scaling/stretch), DYNAMICALLY ALIGNED in cells
  based on content (top-heavy -> top-align, bottom-heavy -> bottom-align, balanced -> center)
  for perfect island/cliff/ground fitting without distortion, CLIPPED if larger than cell.
- Restored TILE_HEIGHT=60 for better sprite fit and seamless connections (no gaps between adjacent tiles).
- Increased GRID_ROWS=40 to maintain vertical coverage with finer control.
"""


# ------- CONFIG SETTINGS -------
DEFAULT_MAP_ID = 0
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
PALETTE_WIDTH = 320
VIEWPORT_BG = (240, 240, 245)
GRID_COLOR = (205, 205, 205)
HILIGHT_COLOR = (255, 255, 0, 120)
PALETTE_BG = (30, 30, 35)
PALETTE_TEXT = (220, 220, 220)

TILE_WIDTH = 90
TILE_HEIGHT = 60  # Restored from 30 to 60 for seamless tile connections (matches sprite designs)
GRID_COLS = 80
GRID_ROWS = 40  # Increased from 20 to 40 for finer vertical placement while keeping fit
CAMERA_SPEED = 20
PALETTE_ENTRY_HEIGHT = TILE_HEIGHT + 16

PREVIEW_WIDTH = TILE_WIDTH // 2
PREVIEW_HEIGHT = TILE_HEIGHT // 2

# Mob defaults
MOB_DEFAULT_HEALTH = {
    "slime": 100,
    "stump": 150,
    "mushroom": 200,
}


def get_paths(map_id: int):
    """Return CSV paths for a given map id."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    tiles_csv_path = os.path.join(base_dir, "maps", f"map{map_id}_tiles.csv")
    mobs_csv_path = os.path.join(base_dir, "maps", f"map{map_id}_mobs.csv")
    lines_json_path = os.path.join(base_dir, "maps", f"map{map_id}_lines.json")
    backgrounds_json_path = os.path.join(base_dir, "maps", f"map{map_id}_backgrounds.json")
    spawn_json_path = os.path.join(base_dir, "maps", f"map{map_id}_spawn.json")
    return base_dir, tiles_csv_path, mobs_csv_path, lines_json_path, backgrounds_json_path, spawn_json_path


def discover_mob_types(base_dir: str):
    mobs_root = os.path.join(base_dir, "sprites", "mobs")
    types = []
    if os.path.exists(mobs_root):
        for name in os.listdir(mobs_root):
            path = os.path.join(mobs_root, name)
            if os.path.isdir(path):
                types.append(name)
    types.sort()
    return types or ["slime"]


def load_tile_manifest(base_dir: str):
    manifest_path = os.path.join(base_dir, "maps", "tile_manifest.json")
    if not os.path.exists(manifest_path):
        raise FileNotFoundError("Missing maps/tile_manifest.json. Please create one that maps tile IDs to sprite paths.")
    with open(manifest_path) as f:
        data = json.load(f)

    entries = [{"id": 0, "label": "Empty", "path": None, "solid": False}]
    entries.extend(sorted(data.get("tiles", []), key=lambda e: e["id"]))
    return entries


def load_tile_images(base_dir: str, tile_entries):
    tile_root = os.path.join(base_dir, "sprites", "maps", "tile")
    cache = {}
    for entry in tile_entries:
        tile_id = entry["id"]
        path = entry.get("path")
        if tile_id == 0 or not path:
            continue
        full_path = os.path.join(tile_root, path)
        if not os.path.exists(full_path):
            print(f"[map_editor] Missing tile sprite for id={tile_id}: {full_path}")
            continue
        try:
            img_orig = pygame.image.load(full_path).convert_alpha()
        except pygame.error:
            continue

        ow, oh = img_orig.get_size()
        if ow == 0 or oh == 0:
            continue

        # Compute dynamic vertical alignment based on opacity distribution
        mask = pygame.mask.from_surface(img_orig)
        half_h = oh // 2
        top_surf = pygame.Surface((ow, half_h), pygame.SRCALPHA)
        top_surf.blit(img_orig, (0, 0), (0, 0, ow, half_h))
        top_mask = pygame.mask.from_surface(top_surf)
        top_count = top_mask.count()

        bottom_h = oh - half_h
        bottom_surf = pygame.Surface((ow, bottom_h), pygame.SRCALPHA)
        bottom_surf.blit(img_orig, (0, 0), (0, half_h, ow, bottom_h))
        bottom_mask = pygame.mask.from_surface(bottom_surf)
        bottom_count = bottom_mask.count()

        if top_count > bottom_count:
            grid_oy = 0  # Top-align (e.g., for top-heavy grass/upper cliffs)
        elif bottom_count > top_count:
            grid_oy = TILE_HEIGHT - oh  # Bottom-align (e.g., for ground/dirt bases)
        else:
            grid_oy = (TILE_HEIGHT - oh) // 2  # Center-align for balanced

        # Horizontal always center
        grid_ox = (TILE_WIDTH - ow) // 2

        # For PALETTE PREVIEW: Proportional CONTAIN scale (min ratio), center
        scale_prev = min(PREVIEW_WIDTH / ow, PREVIEW_HEIGHT / oh)
        pw = int(ow * scale_prev)
        ph = int(oh * scale_prev)
        preview_img = pygame.transform.scale(img_orig, (pw, ph))  # Bilinear for small previews
        prev_ox = (PREVIEW_WIDTH - pw) // 2
        prev_oy = (PREVIEW_HEIGHT - ph) // 2

        cache[tile_id] = {
            'img': img_orig,
            'grid_ox': grid_ox,
            'grid_oy': grid_oy,
            'preview_img': preview_img,
            'preview_ox': prev_ox,
            'preview_oy': prev_oy,
        }
    return cache


def load_or_create_grid(csv_path: str, cols: int, rows: int):
    """
    Load grid from CSV, preserving its EXACT dimensions from the file.
    Only uses cols/rows as defaults when creating a NEW grid.
    """
    if os.path.exists(csv_path):
        grid = []
        with open(csv_path, newline="") as f:
            reader = csv.reader(f)
            for row in reader:
                if not row:
                    continue
                grid.append([int(cell) if cell else 0 for cell in row])

        if grid:
            # Find the maximum column count to ensure all rows have the same width
            max_cols = max(len(row) for row in grid) if grid else 0
            actual_rows = len(grid)
            
            # Use the ACTUAL dimensions from the CSV file (preserve what was saved)
            # Don't enforce minimum - preserve exact size
            actual_cols = max_cols if max_cols > 0 else cols
            
            # Pad rows to match the widest row (ensure consistency)
            for r in range(len(grid)):
                if len(grid[r]) < actual_cols:
                    grid[r].extend([0] * (actual_cols - len(grid[r])))
            
            # Return grid with its exact saved dimensions
            return grid

    # Only use default size when creating a NEW grid (file doesn't exist)
    return [[0 for _ in range(cols)] for _ in range(rows)]


def save_grid(csv_path: str, grid):
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        for row in grid:
            writer.writerow(row)
    print(f"[map_editor] Saved tilemap to {csv_path}")


def load_mobs(csv_path: str):
    mobs = []
    if not os.path.exists(csv_path):
        return mobs
    with open(csv_path, newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) < 3:
                continue
            name = row[0]
            try:
                x = int(row[1])
                y = int(row[2])
            except ValueError:
                continue
            if len(row) >= 4 and row[3]:
                try:
                    health = int(row[3])
                except ValueError:
                    health = MOB_DEFAULT_HEALTH.get(name, 100)
            else:
                health = MOB_DEFAULT_HEALTH.get(name, 100)
            mobs.append({"mob_name": name, "x": x, "y": y, "health": health})
    return mobs


def save_mobs(csv_path: str, mobs):
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        for mob in mobs:
            writer.writerow(
                [
                    mob.get("mob_name", "slime"),
                    mob.get("x", 0),
                    mob.get("y", 0),
                    mob.get("health", MOB_DEFAULT_HEALTH.get(mob.get("mob_name", "slime"), 100)),
                ]
            )
    print(f"[map_editor] Saved mobs to {csv_path}")


def load_lines(json_path: str):
    if not os.path.exists(json_path):
        return []
    try:
        with open(json_path, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading lines: {e}")
        return []


def save_lines(json_path: str, lines):
    try:
        with open(json_path, "w") as f:
            json.dump(lines, f, indent=2)
        print(f"[map_editor] Saved lines to {json_path}")
    except Exception as e:
        print(f"Error saving lines: {e}")


def load_background_manifest(base_dir: str):
    manifest_path = os.path.join(base_dir, "maps", "background_manifest.json")
    if not os.path.exists(manifest_path):
        return [{"id": 0, "label": "Empty", "path": None}]
    with open(manifest_path) as f:
        data = json.load(f)
    entries = [{"id": 0, "label": "Empty", "path": None}]
    entries.extend(sorted(data.get("backgrounds", []), key=lambda e: e["id"]))
    return entries


def load_background_images(base_dir: str, bg_entries):
    backgrounds_root = os.path.join(base_dir, "sprites", "maps", "back")
    cache = {}
    for entry in bg_entries:
        bg_id = entry["id"]
        path = entry.get("path")
        if bg_id == 0 or not path:
            continue
        full_path = os.path.join(backgrounds_root, path)
        if not os.path.exists(full_path):
            print(f"[map_editor] Missing background sprite for id={bg_id}: {full_path}")
            continue
        try:
            img = pygame.image.load(full_path).convert_alpha()
            # Scale preview for palette
            ow, oh = img.get_size()
            if ow > 0 and oh > 0:
                scale_prev = min(PREVIEW_WIDTH / ow, PREVIEW_HEIGHT / oh)
                pw = int(ow * scale_prev)
                ph = int(oh * scale_prev)
                preview_img = pygame.transform.scale(img, (pw, ph))
                prev_ox = (PREVIEW_WIDTH - pw) // 2
                prev_oy = (PREVIEW_HEIGHT - ph) // 2
                cache[bg_id] = {
                    'img': img,
                    'preview_img': preview_img,
                    'preview_ox': prev_ox,
                    'preview_oy': prev_oy,
                }
        except pygame.error:
            continue
    return cache


def load_backgrounds(json_path: str):
    if not os.path.exists(json_path):
        return []
    try:
        with open(json_path, "r") as f:
            data = json.load(f)
            return data.get("layers", [])
    except Exception as e:
        print(f"Error loading backgrounds: {e}")
        return []


def save_backgrounds(json_path: str, layers):
    try:
        os.makedirs(os.path.dirname(json_path), exist_ok=True)
        with open(json_path, "w") as f:
            json.dump({"layers": layers}, f, indent=2)
        print(f"[map_editor] Saved backgrounds to {json_path}")
    except Exception as e:
        print(f"Error saving backgrounds: {e}")


def load_spawn(json_path: str):
    """Load spawn point from JSON."""
    if not os.path.exists(json_path):
        return {"x": 400, "y": 200}  # Default spawn
    try:
        with open(json_path, "r") as f:
            data = json.load(f)
            return {"x": data.get("x", 400), "y": data.get("y", 200)}
    except Exception as e:
        print(f"Error loading spawn: {e}")
        return {"x": 400, "y": 200}


def save_spawn(json_path: str, spawn):
    """Save spawn point to JSON."""
    try:
        os.makedirs(os.path.dirname(json_path), exist_ok=True)
        with open(json_path, "w") as f:
            json.dump(spawn, f, indent=2)
        print(f"[map_editor] Saved spawn point to {json_path}")
    except Exception as e:
        print(f"Error saving spawn: {e}")


def get_snapped_point(lines, world_x, world_y, threshold=15):
    """Find a point to snap to within threshold distance."""
    best_pt = None
    min_dist = threshold * threshold
    
    points = []
    for line in lines:
        points.append(tuple(line['p1']))
        points.append(tuple(line['p2']))
        
    for pt in points:
        dx = pt[0] - world_x
        dy = pt[1] - world_y
        dist = dx*dx + dy*dy
        if dist < min_dist:
            min_dist = dist
            best_pt = pt
            
    return best_pt


def load_mob_images(base_dir: str, mob_types, target_height: int):
    mob_images = {}
    for name in mob_types:
        img_path = os.path.join(base_dir, "sprites", "mobs", name, "stand", "0.png")
        if not os.path.exists(img_path):
            continue
        try:
            img = pygame.image.load(img_path).convert_alpha()
        except pygame.error:
            continue
        if img.get_height() > 0:
            scale = target_height / img.get_height()
            img = pygame.transform.scale(img, (int(img.get_width() * scale), target_height))
        mob_images[name] = img
    return mob_images


def clamp(value, minimum, maximum):
    return max(minimum, min(value, maximum))


def calculate_optimal_map_width(bg_layers, bg_images):
    """
    Calculate optimal map width that fits background images perfectly.
    Returns the LCM of all background image widths, or a reasonable default.
    """
    if not bg_layers:
        return GRID_COLS * TILE_WIDTH
    
    widths = []
    for layer in bg_layers:
        bg_id = layer.get("background_id", 0)
        if bg_id == 0:
            continue
        bg_img_data = bg_images.get(bg_id)
        if bg_img_data:
            widths.append(bg_img_data['img'].get_width())
    
    if not widths:
        return GRID_COLS * TILE_WIDTH
    
    # Find LCM of all widths (simplified: use max width as base)
    # For simplicity, we'll use the maximum width and ensure map is a multiple
    max_width = max(widths)
    # Round up to nearest multiple of max_width
    current_map_width = GRID_COLS * TILE_WIDTH
    optimal_width = ((current_map_width // max_width) + 1) * max_width if max_width > 0 else current_map_width
    return optimal_width


def main():
    if len(sys.argv) > 1:
        try:
            map_id = int(sys.argv[1])
        except ValueError:
            print("Usage: python map_editor.py [map_id]")
            return
    else:
        map_id = DEFAULT_MAP_ID

    base_dir, tiles_csv_path, mobs_csv_path, lines_json_path, backgrounds_json_path, spawn_json_path = get_paths(map_id)
    tile_entries = load_tile_manifest(base_dir)
    mob_types = discover_mob_types(base_dir)
    bg_entries = load_background_manifest(base_dir)

    pygame.init()
    pygame.display.set_caption(f"Map Editor - map{map_id}")
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))

    viewport_width = WINDOW_WIDTH - PALETTE_WIDTH
    viewport_rect = pygame.Rect(0, 0, viewport_width, WINDOW_HEIGHT)
    palette_rect = pygame.Rect(viewport_width, 0, PALETTE_WIDTH, WINDOW_HEIGHT)

    tile_images = load_tile_images(base_dir, tile_entries)
    mob_images = load_mob_images(base_dir, mob_types, TILE_HEIGHT)
    bg_images = load_background_images(base_dir, bg_entries)

    # Load grid - it will preserve actual dimensions from CSV
    grid = load_or_create_grid(tiles_csv_path, GRID_COLS, GRID_ROWS)
    mobs = load_mobs(mobs_csv_path)
    lines = load_lines(lines_json_path)
    bg_layers = load_backgrounds(backgrounds_json_path)
    spawn_point = load_spawn(spawn_json_path)

    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 20)

    camera_x = 0
    camera_y = 0
    move_left = move_right = move_up = move_down = False

    palette_scroll = 0
    selected_tile_id = 0
    selected_bg_id = 0
    mode = "tiles"  # tiles, mobs, lines, backgrounds, spawn
    current_mob_index = 0
    current_layer_index = 0  # Z-order for backgrounds (lower = behind)
    
    # Border dragging state
    dragging_border = None  # "left", "right", "top", "bottom", or None
    drag_start_pos = None  # World position when drag started
    drag_start_screen_pos = None  # Screen position when drag started (for stable calculation)
    drag_start_grid_size = None  # (cols, rows) when drag started
    drag_start_camera = None  # (camera_x, camera_y) when drag started
    RESIZE_SNAP_INTERVAL = 2  # Resize every N tiles for better control (2 = every 2 tiles)
    
    # Line editing state
    line_start_point = None
    line_type = "floor" # floor, wall

    running = True
    while running:
        dt = clock.tick(60)

        # camera movement (disabled when dragging borders)
        if not dragging_border:
            if move_left:
                camera_x -= CAMERA_SPEED
            if move_right:
                camera_x += CAMERA_SPEED
            if move_up:
                camera_y -= CAMERA_SPEED
            if move_down:
                camera_y += CAMERA_SPEED

        actual_cols = len(grid[0]) if grid else GRID_COLS
        actual_rows = len(grid) if grid else GRID_ROWS
        max_cam_x = max(0, actual_cols * TILE_WIDTH - viewport_width)
        max_cam_y = max(0, actual_rows * TILE_HEIGHT - WINDOW_HEIGHT)
        camera_x = clamp(camera_x, 0, max_cam_x)
        camera_y = clamp(camera_y, 0, max_cam_y)

        mouse_x, mouse_y = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_q):
                    running = False
                elif event.key == pygame.K_s:
                    save_grid(tiles_csv_path, grid)
                    save_mobs(mobs_csv_path, mobs)
                    save_lines(lines_json_path, lines)
                    save_backgrounds(backgrounds_json_path, bg_layers)
                    save_spawn(spawn_json_path, spawn_point)
                elif event.key == pygame.K_PLUS or event.key == pygame.K_EQUALS:
                    if mode == "backgrounds":
                        current_layer_index = min(10, current_layer_index + 1)
                elif event.key == pygame.K_MINUS:
                    if mode == "backgrounds":
                        current_layer_index = max(0, current_layer_index - 1)
                elif event.key == pygame.K_r and mode == "backgrounds":
                    # Resize map to fit backgrounds perfectly
                    optimal_width = calculate_optimal_map_width(bg_layers, bg_images)
                    optimal_cols = max(len(grid[0]) if grid else GRID_COLS, int(math.ceil(optimal_width / TILE_WIDTH)))
                    # Resize grid
                    for row in grid:
                        while len(row) < optimal_cols:
                            row.append(0)
                    print(f"[map_editor] Resized map to {optimal_cols} columns ({optimal_cols * TILE_WIDTH}px) to fit backgrounds")
                elif event.key == pygame.K_TAB:
                    if mode == "tiles": mode = "mobs"
                    elif mode == "mobs": mode = "lines"
                    elif mode == "lines": mode = "backgrounds"
                    elif mode == "backgrounds": mode = "spawn"
                    else: mode = "tiles"
                    line_start_point = None
                    dragging_border = None
                elif event.key == pygame.K_t and mode == "lines":
                    line_type = "wall" if line_type == "floor" else "floor"
                elif event.key in (pygame.K_LEFT, pygame.K_a):
                    move_left = True
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    move_right = True
                elif event.key in (pygame.K_UP, pygame.K_w):
                    move_up = True
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    move_down = True
                elif event.unicode.isdigit():
                    idx = int(event.unicode) - 1
                    if 0 <= idx < len(mob_types):
                        current_mob_index = idx
            elif event.type == pygame.KEYUP:
                if event.key in (pygame.K_LEFT, pygame.K_a):
                    move_left = False
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    move_right = False
                elif event.key in (pygame.K_UP, pygame.K_w):
                    move_up = False
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    move_down = False
            elif event.type == pygame.MOUSEWHEEL:
                if palette_rect.collidepoint(mouse_x, mouse_y):
                    palette_scroll -= event.y * 30
                    if mode == "backgrounds":
                        max_scroll = max(0, len(bg_entries) * PALETTE_ENTRY_HEIGHT - WINDOW_HEIGHT + 40)
                    else:
                        max_scroll = max(0, len(tile_entries) * PALETTE_ENTRY_HEIGHT - WINDOW_HEIGHT + 40)
                    palette_scroll = clamp(palette_scroll, 0, max_scroll)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if palette_rect.collidepoint(event.pos):
                    local_y = event.pos[1] + palette_scroll
                    idx = int(local_y // PALETTE_ENTRY_HEIGHT)
                    if mode == "backgrounds":
                        if 0 <= idx < len(bg_entries):
                            selected_bg_id = bg_entries[idx]["id"]
                    else:
                        if 0 <= idx < len(tile_entries):
                            selected_tile_id = tile_entries[idx]["id"]
                elif viewport_rect.collidepoint(event.pos):
                    world_x = camera_x + event.pos[0]
                    world_y = camera_y + event.pos[1]
                    col = int(world_x // TILE_WIDTH)
                    row = int(world_y // TILE_HEIGHT)
                    actual_cols = len(grid[0]) if grid else GRID_COLS
                    actual_rows = len(grid) if grid else GRID_ROWS
                    
                    # Check for border dragging first (only in tiles mode)
                    border_clicked = False
                    if mode == "tiles" and event.button == 1 and not dragging_border:
                        map_right = actual_cols * TILE_WIDTH
                        map_bottom = actual_rows * TILE_HEIGHT
                        BORDER_THRESHOLD = 20
                        
                        if abs(world_x) < BORDER_THRESHOLD and 0 <= world_y <= map_bottom:
                            dragging_border = "left"
                            drag_start_pos = world_x
                            drag_start_screen_pos = event.pos[0]  # Screen X
                            drag_start_grid_size = (actual_cols, actual_rows)
                            drag_start_camera = (camera_x, camera_y)
                            border_clicked = True
                        elif abs(world_x - map_right) < BORDER_THRESHOLD and 0 <= world_y <= map_bottom:
                            dragging_border = "right"
                            drag_start_pos = world_x
                            drag_start_screen_pos = event.pos[0]  # Screen X
                            drag_start_grid_size = (actual_cols, actual_rows)
                            drag_start_camera = (camera_x, camera_y)
                            border_clicked = True
                        elif abs(world_y) < BORDER_THRESHOLD and 0 <= world_x <= map_right:
                            dragging_border = "top"
                            drag_start_pos = world_y
                            drag_start_screen_pos = event.pos[1]  # Screen Y
                            drag_start_grid_size = (actual_cols, actual_rows)
                            drag_start_camera = (camera_x, camera_y)
                            border_clicked = True
                        elif abs(world_y - map_bottom) < BORDER_THRESHOLD and 0 <= world_x <= map_right:
                            dragging_border = "bottom"
                            drag_start_pos = world_y
                            drag_start_screen_pos = event.pos[1]  # Screen Y
                            drag_start_grid_size = (actual_cols, actual_rows)
                            drag_start_camera = (camera_x, camera_y)
                            border_clicked = True
                    
                    # Only process other clicks if not clicking on border
                    if not border_clicked and 0 <= col < actual_cols and 0 <= row < actual_rows:
                        if mode == "tiles":
                            if event.button == 1:
                                grid[row][col] = selected_tile_id
                            elif event.button == 3:
                                grid[row][col] = 0
                        elif mode == "mobs":
                            if event.button == 1:
                                mob_name = mob_types[current_mob_index]
                                health = MOB_DEFAULT_HEALTH.get(mob_name, 100)
                                mobs.append(
                                    {
                                        "mob_name": mob_name,
                                        "x": world_x,
                                        "y": world_y,
                                        "health": health,
                                    }
                                )
                            elif event.button == 3 and mobs:
                                closest_idx = None
                                closest_dist = 25 ** 2
                                for i, mob in enumerate(mobs):
                                    dx = mob["x"] - world_x
                                    dy = mob["y"] - world_y
                                    dist = dx * dx + dy * dy
                                    if dist <= closest_dist:
                                        closest_dist = dist
                                        closest_idx = i
                                if closest_idx is not None:
                                    mobs.pop(closest_idx)
                        elif mode == "lines":
                            if event.button == 1: # Left click
                                # Check for snap
                                snap_pt = get_snapped_point(lines, world_x, world_y)
                                pt = snap_pt if snap_pt else (world_x, world_y)
                                
                                if line_start_point is None:
                                    line_start_point = pt
                                else:
                                    # Finish line
                                    lines.append({
                                        "p1": line_start_point,
                                        "p2": pt,
                                        "type": line_type
                                    })
                                    line_start_point = pt # Continue from this point
                            elif event.button == 3: # Right click - cancel or delete
                                if line_start_point:
                                    line_start_point = None
                                else:
                                    # Delete nearest line
                                    closest_line_idx = None
                                    min_dist = 20 * 20
                                    for i, line in enumerate(lines):
                                        # Check distance to p1 and p2
                                        p1 = line['p1']
                                        p2 = line['p2']
                                        d1 = (p1[0]-world_x)**2 + (p1[1]-world_y)**2
                                        d2 = (p2[0]-world_x)**2 + (p2[1]-world_y)**2
                                        if d1 < min_dist or d2 < min_dist:
                                            min_dist = min(d1, d2)
                                            closest_line_idx = i
                                    
                                    if closest_line_idx is not None:
                                        lines.pop(closest_line_idx)
                        elif mode == "backgrounds":
                            if event.button == 1:  # Left click - place background layer
                                if selected_bg_id != 0:
                                    # Check if layer already exists at this Y position
                                    existing_idx = None
                                    for i, layer in enumerate(bg_layers):
                                        if abs(layer.get("y", 0) - world_y) < 10:
                                            existing_idx = i
                                            break
                                    
                                    if existing_idx is not None:
                                        # Update existing layer
                                        bg_layers[existing_idx] = {
                                            "background_id": selected_bg_id,
                                            "y": world_y,
                                            "layer_index": current_layer_index,
                                            "scroll_speed": 1.0
                                        }
                                    else:
                                        # Add new layer
                                        bg_layers.append({
                                            "background_id": selected_bg_id,
                                            "y": world_y,
                                            "layer_index": current_layer_index,
                                            "scroll_speed": 1.0
                                        })
                            elif event.button == 3:  # Right click - delete layer
                                closest_idx = None
                                closest_dist = 50 ** 2
                                for i, layer in enumerate(bg_layers):
                                    # Check distance to the Y position of the layer
                                    layer_y = layer.get("y", 0)
                                    dy = layer_y - world_y
                                    dist = dy * dy
                                    if dist <= closest_dist:
                                        closest_dist = dist
                                        closest_idx = i
                                if closest_idx is not None:
                                    deleted_layer = bg_layers.pop(closest_idx)
                                    print(f"[map_editor] Deleted background layer at Y={deleted_layer.get('y', 0)}")
                                else:
                                    print(f"[map_editor] No background layer found near Y={world_y}")
                        elif mode == "spawn":
                            if event.button == 1:  # Left click - set spawn point
                                spawn_point = {"x": world_x, "y": world_y}
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    dragging_border = None
                    drag_start_pos = None
                    drag_start_screen_pos = None
                    drag_start_grid_size = None
                    drag_start_camera = None
            elif event.type == pygame.MOUSEMOTION:
                if dragging_border and drag_start_pos is not None and drag_start_screen_pos is not None and drag_start_grid_size is not None and drag_start_camera is not None:
                    # Lock camera during drag - use screen coordinates for stable calculation
                    start_cam_x, start_cam_y = drag_start_camera
                    start_cols, start_rows = drag_start_grid_size
                    
                    current_cols = len(grid[0]) if grid else start_cols
                    current_rows = len(grid) if grid else start_rows
                    
                    if dragging_border == "left":
                        # Use screen coordinates for stable calculation
                        screen_delta_x = event.pos[0] - drag_start_screen_pos
                        # Convert screen delta to world delta (camera is locked, so this is accurate)
                        world_delta_x = screen_delta_x
                        # Calculate target columns with snap interval
                        # Dragging right (positive delta) = shrink (remove columns from left)
                        # Dragging left (negative delta) = expand (add columns to left)
                        delta_tiles = int(world_delta_x // TILE_WIDTH)
                        # Calculate base target: negative delta expands, positive shrinks
                        base_target = start_cols - delta_tiles
                        # Snap to interval
                        if base_target < start_cols:
                            # Shrinking: round down
                            target_cols = (base_target // RESIZE_SNAP_INTERVAL) * RESIZE_SNAP_INTERVAL
                        else:
                            # Expanding: round up
                            target_cols = ((base_target + RESIZE_SNAP_INTERVAL - 1) // RESIZE_SNAP_INTERVAL) * RESIZE_SNAP_INTERVAL
                        target_cols = max(1, target_cols)
                        
                        # Only resize if different from current
                        if target_cols != current_cols:
                            cols_delta = target_cols - current_cols
                            # Adjust grid
                            for row in grid:
                                if target_cols < current_cols:
                                    # Remove columns from left
                                    cols_removed = current_cols - target_cols
                                    row[:] = row[cols_removed:]
                                else:
                                    # Add columns to left
                                    row[:0] = [0] * (target_cols - current_cols)
                            
                            # Adjust all world coordinates to maintain visual position
                            if cols_delta < 0:
                                # Shrinking from left - move everything left by the removed width
                                shift_x = abs(cols_delta) * TILE_WIDTH
                                # Adjust spawn point
                                spawn_point["x"] = max(0, spawn_point["x"] - shift_x)
                                # Adjust lines
                                for line in lines:
                                    line["p1"][0] = max(0, line["p1"][0] - shift_x)
                                    line["p2"][0] = max(0, line["p2"][0] - shift_x)
                                # Adjust mobs
                                for mob in mobs:
                                    mob["x"] = max(0, mob["x"] - shift_x)
                                # Background layers don't need adjustment (they use Y only)
                            elif cols_delta > 0:
                                # Expanding from left - move everything right by the added width
                                shift_x = cols_delta * TILE_WIDTH
                                # Adjust spawn point
                                spawn_point["x"] += shift_x
                                # Adjust lines
                                for line in lines:
                                    line["p1"][0] += shift_x
                                    line["p2"][0] += shift_x
                                # Adjust mobs
                                for mob in mobs:
                                    mob["x"] += shift_x
                            
                            # Adjust camera to keep view stable (maintain screen position)
                            camera_x = start_cam_x + (target_cols - start_cols) * TILE_WIDTH
                    elif dragging_border == "right":
                        # Use screen coordinates for stable calculation
                        screen_delta_x = event.pos[0] - drag_start_screen_pos
                        world_delta_x = screen_delta_x
                        # Calculate target columns with snap interval
                        delta_tiles = int(world_delta_x // TILE_WIDTH)
                        target_cols = max(1, start_cols + delta_tiles)
                        # Snap to interval
                        target_cols = ((target_cols + RESIZE_SNAP_INTERVAL - 1) // RESIZE_SNAP_INTERVAL) * RESIZE_SNAP_INTERVAL
                        
                        # Only resize if different from current
                        if target_cols != current_cols:
                            # Adjust grid
                            for row in grid:
                                if target_cols < current_cols:
                                    # Remove columns from right
                                    row[:] = row[:target_cols]
                                else:
                                    # Add columns to right
                                    row.extend([0] * (target_cols - current_cols))
                            # Camera stays the same for right border
                            camera_x = start_cam_x
                    elif dragging_border == "top":
                        # Use screen coordinates for stable calculation
                        screen_delta_y = event.pos[1] - drag_start_screen_pos
                        world_delta_y = screen_delta_y
                        # Calculate target rows with snap interval
                        # Dragging down (positive delta) = shrink (remove rows from top)
                        # Dragging up (negative delta) = expand (add rows to top)
                        delta_tiles = int(world_delta_y // TILE_HEIGHT)
                        # Calculate base target: negative delta expands, positive shrinks
                        base_target = start_rows - delta_tiles
                        # Snap to interval
                        if base_target < start_rows:
                            # Shrinking: round down
                            target_rows = (base_target // RESIZE_SNAP_INTERVAL) * RESIZE_SNAP_INTERVAL
                        else:
                            # Expanding: round up
                            target_rows = ((base_target + RESIZE_SNAP_INTERVAL - 1) // RESIZE_SNAP_INTERVAL) * RESIZE_SNAP_INTERVAL
                        target_rows = max(1, target_rows)
                        
                        # Only resize if different from current
                        if target_rows != current_rows:
                            rows_delta = target_rows - current_rows
                            # Adjust grid
                            if target_rows < current_rows:
                                # Remove rows from top
                                rows_removed = current_rows - target_rows
                                grid[:] = grid[rows_removed:]
                            else:
                                # Add rows to top
                                grid[:0] = [[0] * len(grid[0]) for _ in range(target_rows - current_rows)]
                            
                            # Adjust all world coordinates to maintain visual position
                            if rows_delta < 0:
                                # Shrinking from top - move everything up by the removed height
                                shift_y = abs(rows_delta) * TILE_HEIGHT
                                # Adjust spawn point
                                spawn_point["y"] = max(0, spawn_point["y"] - shift_y)
                                # Adjust lines
                                for line in lines:
                                    line["p1"][1] = max(0, line["p1"][1] - shift_y)
                                    line["p2"][1] = max(0, line["p2"][1] - shift_y)
                                # Adjust mobs
                                for mob in mobs:
                                    mob["y"] = max(0, mob["y"] - shift_y)
                                # Adjust background layers
                                for layer in bg_layers:
                                    layer["y"] = max(0, layer["y"] - shift_y)
                            elif rows_delta > 0:
                                # Expanding from top - move everything down by the added height
                                shift_y = rows_delta * TILE_HEIGHT
                                # Adjust spawn point
                                spawn_point["y"] += shift_y
                                # Adjust lines
                                for line in lines:
                                    line["p1"][1] += shift_y
                                    line["p2"][1] += shift_y
                                # Adjust mobs
                                for mob in mobs:
                                    mob["y"] += shift_y
                                # Adjust background layers
                                for layer in bg_layers:
                                    layer["y"] += shift_y
                            
                            # Adjust camera to keep view stable
                            camera_y = start_cam_y + (target_rows - start_rows) * TILE_HEIGHT
                    elif dragging_border == "bottom":
                        # Use screen coordinates for stable calculation
                        screen_delta_y = event.pos[1] - drag_start_screen_pos
                        world_delta_y = screen_delta_y
                        # Calculate target rows with snap interval
                        delta_tiles = int(world_delta_y // TILE_HEIGHT)
                        target_rows = max(1, start_rows + delta_tiles)
                        # Snap to interval
                        target_rows = ((target_rows + RESIZE_SNAP_INTERVAL - 1) // RESIZE_SNAP_INTERVAL) * RESIZE_SNAP_INTERVAL
                        
                        # Only resize if different from current
                        if target_rows != current_rows:
                            # Adjust grid
                            if target_rows < current_rows:
                                # Remove rows from bottom
                                grid[:] = grid[:target_rows]
                            else:
                                # Add rows to bottom
                                actual_cols = len(grid[0]) if grid else GRID_COLS
                                grid.extend([[0] * actual_cols for _ in range(target_rows - current_rows)])
                            # Camera stays the same for bottom border
                            camera_y = start_cam_y

        # --- drawing ---
        screen.fill(VIEWPORT_BG)

        # draw background layers (behind everything)
        for layer in sorted(bg_layers, key=lambda l: l.get("layer_index", 0)):
            bg_id = layer.get("background_id", 0)
            if bg_id == 0:
                continue
            bg_img_data = bg_images.get(bg_id)
            if not bg_img_data:
                continue
            bg_img = bg_img_data['img']
            y_pos = layer.get("y", 0)
            img_width = bg_img.get_width()
            img_height = bg_img.get_height()
            
            # Draw repeating background horizontally
            start_x = -camera_x % img_width - img_width
            end_x = viewport_width + img_width
            screen_y = y_pos - camera_y
            
            # Only draw if visible
            if screen_y + img_height >= 0 and screen_y < WINDOW_HEIGHT:
                for x in range(start_x, end_x, img_width):
                    temp = bg_img.copy()
                    temp.set_alpha(180)  # Semi-transparent in editor
                    screen.blit(temp, (x, screen_y))

        # draw tiles (only visible region)
        actual_cols = len(grid[0]) if grid else GRID_COLS
        actual_rows = len(grid) if grid else GRID_ROWS
        start_col = max(0, int(camera_x // TILE_WIDTH))
        end_col = min(actual_cols, int(math.ceil((camera_x + viewport_width) / TILE_WIDTH)))
        start_row = max(0, int(camera_y // TILE_HEIGHT))
        end_row = min(actual_rows, int(math.ceil((camera_y + WINDOW_HEIGHT) / TILE_HEIGHT)))

        for row in range(start_row, end_row):
            for col in range(start_col, end_col):
                tile_id = grid[row][col]
                if tile_id == 0:
                    continue
                img_data = tile_images.get(tile_id)
                if img_data is None:
                    continue
                screen_x = col * TILE_WIDTH - camera_x
                screen_y = row * TILE_HEIGHT - camera_y
                # Blit directly without clipping to allow overflow for taller/wider tiles
                screen.blit(img_data['img'], (screen_x + img_data['grid_ox'], screen_y + img_data['grid_oy']))

        # Draw map borders (highlighted when hoverable)
        actual_cols = len(grid[0]) if grid else GRID_COLS
        actual_rows = len(grid) if grid else GRID_ROWS
        map_right = actual_cols * TILE_WIDTH
        map_bottom = actual_rows * TILE_HEIGHT
        
        BORDER_THRESHOLD = 20
        border_color = (255, 200, 0, 180)  # Orange/yellow for borders
        
        # Check if mouse is near borders (for highlighting)
        world_mouse_x = camera_x + mouse_x if viewport_rect.collidepoint(mouse_x, mouse_y) else None
        world_mouse_y = camera_y + mouse_y if viewport_rect.collidepoint(mouse_x, mouse_y) else None
        
        if world_mouse_x is not None and world_mouse_y is not None and mode == "tiles":
            # Left border
            if abs(world_mouse_x) < BORDER_THRESHOLD:
                pygame.draw.line(screen, (255, 200, 0), (0 - camera_x, 0), (0 - camera_x, WINDOW_HEIGHT), 4)
            # Right border
            if abs(world_mouse_x - map_right) < BORDER_THRESHOLD:
                pygame.draw.line(screen, (255, 200, 0), (map_right - camera_x, 0), (map_right - camera_x, WINDOW_HEIGHT), 4)
            # Top border
            if abs(world_mouse_y) < BORDER_THRESHOLD:
                pygame.draw.line(screen, (255, 200, 0), (0, 0 - camera_y), (viewport_width, 0 - camera_y), 4)
            # Bottom border
            if abs(world_mouse_y - map_bottom) < BORDER_THRESHOLD:
                pygame.draw.line(screen, (255, 200, 0), (0, map_bottom - camera_y), (viewport_width, map_bottom - camera_y), 4)
        
        # Draw border outlines (subtle)
        border_alpha = 100
        border_color_rgb = (255, 200, 0)
        # Left border (only if visible)
        if -camera_x < viewport_width:
            border_surf = pygame.Surface((viewport_width, WINDOW_HEIGHT), pygame.SRCALPHA)
            pygame.draw.line(border_surf, (*border_color_rgb, border_alpha), (max(0, 0 - camera_x), 0), (max(0, 0 - camera_x), WINDOW_HEIGHT), 2)
            screen.blit(border_surf, (0, 0))
        # Right border (only if visible)
        if map_right - camera_x > 0:
            border_surf = pygame.Surface((viewport_width, WINDOW_HEIGHT), pygame.SRCALPHA)
            right_x = min(viewport_width, map_right - camera_x)
            pygame.draw.line(border_surf, (*border_color_rgb, border_alpha), (right_x, 0), (right_x, WINDOW_HEIGHT), 2)
            screen.blit(border_surf, (0, 0))
        # Top border (only if visible)
        if -camera_y < WINDOW_HEIGHT:
            border_surf = pygame.Surface((viewport_width, WINDOW_HEIGHT), pygame.SRCALPHA)
            pygame.draw.line(border_surf, (*border_color_rgb, border_alpha), (0, max(0, 0 - camera_y)), (viewport_width, max(0, 0 - camera_y)), 2)
            screen.blit(border_surf, (0, 0))
        # Bottom border (only if visible)
        if map_bottom - camera_y > 0:
            border_surf = pygame.Surface((viewport_width, WINDOW_HEIGHT), pygame.SRCALPHA)
            bottom_y = min(WINDOW_HEIGHT, map_bottom - camera_y)
            pygame.draw.line(border_surf, (*border_color_rgb, border_alpha), (0, bottom_y), (viewport_width, bottom_y), 2)
            screen.blit(border_surf, (0, 0))

        # grid lines
        for col in range(start_col, end_col + 1):
            x = col * TILE_WIDTH - camera_x
            pygame.draw.line(screen, GRID_COLOR, (x, 0), (x, WINDOW_HEIGHT), 1)
        for row in range(start_row, end_row + 1):
            y = row * TILE_HEIGHT - camera_y
            pygame.draw.line(screen, GRID_COLOR, (0, y), (viewport_width, y), 1)

        # tile highlight (full cell)
        if viewport_rect.collidepoint(mouse_x, mouse_y):
            world_x = camera_x + mouse_x
            world_y = camera_y + mouse_y
            highlight_col = int(world_x // TILE_WIDTH)
            highlight_row = int(world_y // TILE_HEIGHT)
            if 0 <= highlight_col < actual_cols and 0 <= highlight_row < actual_rows:
                overlay = pygame.Surface((TILE_WIDTH, TILE_HEIGHT), pygame.SRCALPHA)
                overlay.fill(HILIGHT_COLOR)
                screen.blit(overlay, (highlight_col * TILE_WIDTH - camera_x, highlight_row * TILE_HEIGHT - camera_y))

        # draw mobs
        for mob in mobs:
            img = mob_images.get(mob["mob_name"])
            screen_x = mob["x"] - camera_x
            screen_y = mob["y"] - camera_y
            if img:
                rect = img.get_rect(center=(screen_x, screen_y))
                screen.blit(img, rect)
            else:
                pygame.draw.circle(screen, (255, 0, 0), (int(screen_x), int(screen_y)), 10)

        if mode == "mobs" and viewport_rect.collidepoint(mouse_x, mouse_y):
            preview = mob_images.get(mob_types[current_mob_index])
            if preview:
                temp = preview.copy()
                temp.set_alpha(160)
                rect = temp.get_rect(center=(mouse_x, mouse_y))
                screen.blit(temp, rect)

        if mode == "backgrounds" and viewport_rect.collidepoint(mouse_x, mouse_y):
            world_y = camera_y + mouse_y
            
            # Show which background layer would be deleted (if right-clicking)
            closest_layer_idx = None
            closest_dist = 50 ** 2
            for i, layer in enumerate(bg_layers):
                layer_y = layer.get("y", 0)
                dy = layer_y - world_y
                dist = dy * dy
                if dist <= closest_dist:
                    closest_dist = dist
                    closest_layer_idx = i
            
            # Draw existing background layers with indicators
            for i, layer in enumerate(bg_layers):
                bg_id = layer.get("background_id", 0)
                if bg_id == 0:
                    continue
                bg_img_data = bg_images.get(bg_id)
                if not bg_img_data:
                    continue
                bg_img = bg_img_data['img']
                layer_y = layer.get("y", 0)
                img_width = bg_img.get_width()
                screen_layer_y = layer_y - camera_y
                
                # Highlight layer that would be deleted
                if i == closest_layer_idx and closest_dist <= 50 ** 2:
                    # Draw red highlight line
                    pygame.draw.line(screen, (255, 0, 0), (0, screen_layer_y), (viewport_width, screen_layer_y), 3)
                    # Draw delete indicator
                    delete_text = font.render("RIGHT-CLICK TO DELETE", True, (255, 0, 0))
                    screen.blit(delete_text, (viewport_width // 2 - delete_text.get_width() // 2, screen_layer_y - 20))
                else:
                    # Draw subtle line for other layers
                    pygame.draw.line(screen, (100, 100, 100), (0, screen_layer_y), (viewport_width, screen_layer_y), 1)
            
            # Draw preview for placing new background
            bg_img_data = bg_images.get(selected_bg_id)
            if bg_img_data:
                bg_img = bg_img_data['img']
                img_width = bg_img.get_width()
                img_height = bg_img.get_height()
                # Draw preview repeating horizontally
                start_x = -camera_x % img_width - img_width
                end_x = viewport_width + img_width
                screen_y = world_y - camera_y
                temp = bg_img.copy()
                temp.set_alpha(160)
                for x in range(start_x, end_x, img_width):
                    screen.blit(temp, (x, screen_y))
                # Draw horizontal line at Y position for new placement
                pygame.draw.line(screen, (255, 255, 0), (0, mouse_y), (viewport_width, mouse_y), 2)

        # draw lines
        for line in lines:
            p1 = (line['p1'][0] - camera_x, line['p1'][1] - camera_y)
            p2 = (line['p2'][0] - camera_x, line['p2'][1] - camera_y)
            color = (0, 255, 0) if line.get('type') == 'floor' else (255, 0, 0)
            pygame.draw.line(screen, color, p1, p2, 3)
            pygame.draw.circle(screen, (255, 255, 255), (int(p1[0]), int(p1[1])), 3)
            pygame.draw.circle(screen, (255, 255, 255), (int(p2[0]), int(p2[1])), 3)

        if mode == "lines":
            # Draw cursor snap indicator
            world_x = camera_x + mouse_x
            world_y = camera_y + mouse_y
            snap_pt = get_snapped_point(lines, world_x, world_y)
            
            cursor_color = (0, 255, 0) if line_type == 'floor' else (255, 0, 0)
            
            if snap_pt:
                sx, sy = snap_pt
                pygame.draw.circle(screen, (255, 255, 0), (sx - camera_x, sy - camera_y), 6, 2)
                
            if line_start_point:
                p1 = (line_start_point[0] - camera_x, line_start_point[1] - camera_y)
                p2 = (mouse_x, mouse_y)
                if snap_pt:
                    p2 = (snap_pt[0] - camera_x, snap_pt[1] - camera_y)
                
                pygame.draw.line(screen, cursor_color, p1, p2, 2)
                pygame.draw.circle(screen, (255, 255, 255), (int(p1[0]), int(p1[1])), 3)

        # Draw spawn point
        spawn_screen_x = spawn_point["x"] - camera_x
        spawn_screen_y = spawn_point["y"] - camera_y
        if -50 < spawn_screen_x < viewport_width + 50 and -50 < spawn_screen_y < WINDOW_HEIGHT + 50:
            # Draw spawn point indicator
            spawn_color = (0, 255, 0) if mode == "spawn" else (100, 255, 100)
            pygame.draw.circle(screen, spawn_color, (int(spawn_screen_x), int(spawn_screen_y)), 15, 3)
            pygame.draw.circle(screen, spawn_color, (int(spawn_screen_x), int(spawn_screen_y)), 8, 2)
            # Draw label
            if mode == "spawn":
                label_text = font.render("SPAWN", True, spawn_color)
                screen.blit(label_text, (int(spawn_screen_x) - label_text.get_width() // 2, int(spawn_screen_y) - 30))

        # palette
        pygame.draw.rect(screen, PALETTE_BG, palette_rect)
        y_offset = 10 - palette_scroll
        
        # Show different palette based on mode
        if mode == "backgrounds":
            entries_to_show = bg_entries
            selected_id = selected_bg_id
            images_dict = bg_images
        else:
            entries_to_show = tile_entries
            selected_id = selected_tile_id
            images_dict = tile_images
        
        for entry in entries_to_show:
            entry_id = entry["id"]
            rect = pygame.Rect(palette_rect.x + 10, y_offset, PALETTE_WIDTH - 20, PALETTE_ENTRY_HEIGHT - 6)
            if rect.bottom < 0:
                y_offset += PALETTE_ENTRY_HEIGHT
                continue
            if rect.top > WINDOW_HEIGHT:
                break

            bg_color = (60, 60, 70) if entry_id != selected_id else (90, 120, 200)
            pygame.draw.rect(screen, bg_color, rect, border_radius=6)
            if entry_id == selected_id:
                pygame.draw.rect(screen, (255, 255, 255), rect, width=2, border_radius=6)

            img_data = images_dict.get(entry_id)
            if img_data:
                if mode == "backgrounds":
                    preview_pos_x = rect.x + 8 + img_data['preview_ox']
                    preview_pos_y = rect.y + 6 + img_data['preview_oy']
                    screen.blit(img_data['preview_img'], (preview_pos_x, preview_pos_y))
                else:
                    preview_pos_x = rect.x + 8 + img_data['preview_ox']
                    preview_pos_y = rect.y + 6 + img_data['preview_oy']
                    screen.blit(img_data['preview_img'], (preview_pos_x, preview_pos_y))

            label = f"ID {entry_id}: {entry['label']}"
            text = font.render(label, True, PALETTE_TEXT)
            screen.blit(text, (rect.x + PREVIEW_WIDTH + 16, rect.y + 10))

            y_offset += PALETTE_ENTRY_HEIGHT

        # instructions
        info_lines = [
            f"map{map_id} | mode: {mode} | camera: arrows/WASD | TAB switches tiles/mobs/lines/backgrounds",
            "Tiles: Left click = paint selected tile, Right click = erase, Mousewheel in palette = scroll",
            f"Mobs: 1..{len(mob_types)} select type (current: {mob_types[current_mob_index]}), Left click = add, Right click = remove",
            f"Lines: Left click = start/end line (auto-connects), Right click = cancel/delete, T = toggle type ({line_type})",
            f"Backgrounds: Left click = place layer at Y, Right click = delete layer (click near Y position), +/- = change layer index ({current_layer_index}), R = resize map",
            f"Spawn: Left click = set spawn point (current: {spawn_point['x']}, {spawn_point['y']})",
            "Map Resize: In tiles mode, drag map borders (highlighted in yellow) to resize",
            "S = save tiles, mobs, lines, backgrounds & spawn, ESC/Q = quit",
        ]
        y = 5
        for line in info_lines:
            text = font.render(line, True, (20, 20, 20))
            screen.blit(text, (10, y))
            y += text.get_height() + 2

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()