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
    return base_dir, tiles_csv_path, mobs_csv_path, lines_json_path


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
    if os.path.exists(csv_path):
        grid = []
        with open(csv_path, newline="") as f:
            reader = csv.reader(f)
            for row in reader:
                if not row:
                    continue
                grid.append([int(cell) for cell in row if cell != ""])

        if grid:
            if len(grid) > rows:
                grid = grid[:rows]
            else:
                while len(grid) < rows:
                    grid.append([0] * cols)
            for r in range(rows):
                if len(grid[r]) > cols:
                    grid[r] = grid[r][:cols]
                else:
                    grid[r].extend([0] * (cols - len(grid[r])))
            return grid

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


def main():
    if len(sys.argv) > 1:
        try:
            map_id = int(sys.argv[1])
        except ValueError:
            print("Usage: python map_editor.py [map_id]")
            return
    else:
        map_id = DEFAULT_MAP_ID

    base_dir, tiles_csv_path, mobs_csv_path, lines_json_path = get_paths(map_id)
    tile_entries = load_tile_manifest(base_dir)
    mob_types = discover_mob_types(base_dir)

    pygame.init()
    pygame.display.set_caption(f"Map Editor - map{map_id}")
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))

    viewport_width = WINDOW_WIDTH - PALETTE_WIDTH
    viewport_rect = pygame.Rect(0, 0, viewport_width, WINDOW_HEIGHT)
    palette_rect = pygame.Rect(viewport_width, 0, PALETTE_WIDTH, WINDOW_HEIGHT)

    tile_images = load_tile_images(base_dir, tile_entries)
    mob_images = load_mob_images(base_dir, mob_types, TILE_HEIGHT)

    grid = load_or_create_grid(tiles_csv_path, GRID_COLS, GRID_ROWS)
    mobs = load_mobs(mobs_csv_path)
    lines = load_lines(lines_json_path)

    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 20)

    camera_x = 0
    camera_y = 0
    move_left = move_right = move_up = move_down = False

    palette_scroll = 0
    selected_tile_id = 0
    selected_tile_id = 0
    mode = "tiles"  # tiles, mobs, lines
    current_mob_index = 0
    
    # Line editing state
    line_start_point = None
    line_type = "floor" # floor, wall

    running = True
    while running:
        dt = clock.tick(60)

        # camera movement
        if move_left:
            camera_x -= CAMERA_SPEED
        if move_right:
            camera_x += CAMERA_SPEED
        if move_up:
            camera_y -= CAMERA_SPEED
        if move_down:
            camera_y += CAMERA_SPEED

        max_cam_x = max(0, GRID_COLS * TILE_WIDTH - viewport_width)
        max_cam_y = max(0, GRID_ROWS * TILE_HEIGHT - WINDOW_HEIGHT)
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
                elif event.key == pygame.K_TAB:
                    if mode == "tiles": mode = "mobs"
                    elif mode == "mobs": mode = "lines"
                    else: mode = "tiles"
                    line_start_point = None
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
                    max_scroll = max(0, len(tile_entries) * PALETTE_ENTRY_HEIGHT - WINDOW_HEIGHT + 40)
                    palette_scroll = clamp(palette_scroll, 0, max_scroll)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if palette_rect.collidepoint(event.pos):
                    local_y = event.pos[1] + palette_scroll
                    idx = int(local_y // PALETTE_ENTRY_HEIGHT)
                    if 0 <= idx < len(tile_entries):
                        selected_tile_id = tile_entries[idx]["id"]
                elif viewport_rect.collidepoint(event.pos):
                    world_x = camera_x + event.pos[0]
                    world_y = camera_y + event.pos[1]
                    col = int(world_x // TILE_WIDTH)
                    row = int(world_y // TILE_HEIGHT)
                    if 0 <= col < GRID_COLS and 0 <= row < GRID_ROWS:
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

        # --- drawing ---
        screen.fill(VIEWPORT_BG)

        # draw tiles (only visible region)
        start_col = max(0, int(camera_x // TILE_WIDTH))
        end_col = min(GRID_COLS, int(math.ceil((camera_x + viewport_width) / TILE_WIDTH)))
        start_row = max(0, int(camera_y // TILE_HEIGHT))
        end_row = min(GRID_ROWS, int(math.ceil((camera_y + WINDOW_HEIGHT) / TILE_HEIGHT)))

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
            if 0 <= highlight_col < GRID_COLS and 0 <= highlight_row < GRID_ROWS:
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

        # palette
        pygame.draw.rect(screen, PALETTE_BG, palette_rect)
        y_offset = 10 - palette_scroll
        for entry in tile_entries:
            tile_id = entry["id"]
            rect = pygame.Rect(palette_rect.x + 10, y_offset, PALETTE_WIDTH - 20, PALETTE_ENTRY_HEIGHT - 6)
            if rect.bottom < 0:
                y_offset += PALETTE_ENTRY_HEIGHT
                continue
            if rect.top > WINDOW_HEIGHT:
                break

            bg_color = (60, 60, 70) if tile_id != selected_tile_id else (90, 120, 200)
            pygame.draw.rect(screen, bg_color, rect, border_radius=6)
            if tile_id == selected_tile_id:
                pygame.draw.rect(screen, (255, 255, 255), rect, width=2, border_radius=6)

            img_data = tile_images.get(tile_id)
            if img_data:
                preview_pos_x = rect.x + 8 + img_data['preview_ox']
                preview_pos_y = rect.y + 6 + img_data['preview_oy']
                # Blit scaled preview, centered
                screen.blit(img_data['preview_img'], (preview_pos_x, preview_pos_y))

            label = f"ID {tile_id}: {entry['label']}"
            text = font.render(label, True, PALETTE_TEXT)
            screen.blit(text, (rect.x + PREVIEW_WIDTH + 16, rect.y + 10))

            y_offset += PALETTE_ENTRY_HEIGHT

        # instructions
        info_lines = [
            f"map{map_id} | mode: {mode} | camera: arrows/WASD | TAB switches tiles/mobs/lines",
            "Tiles: Left click = paint selected tile, Right click = erase, Mousewheel in palette = scroll",
            f"Mobs: 1..{len(mob_types)} select type (current: {mob_types[current_mob_index]}), Left click = add, Right click = remove",
            f"Lines: Left click = start/end line (auto-connects), Right click = cancel/delete, T = toggle type ({line_type})",
            "S = save tiles, mobs & lines, ESC/Q = quit",
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