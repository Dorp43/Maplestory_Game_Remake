import os
import sys
import csv
import pygame


"""
Simple tile-map editor for your game.

Usage (from project root):
    python map_editor.py [map_id]

Examples:
    python map_editor.py        # defaults to map 0
    python map_editor.py 1      # edits map1 background and CSV

Controls:
    - Left click  : toggle tile (empty <-> solid)
    - Right click : clear tile (set to empty)
    - S key       : save CSV to maps/map{map_id}_tiles.csv
    - ESC / Q     : quit editor

The editor:
    - Loads sprites/maps/{map_id}.png as background.
    - Uses a configurable grid (cols/rows) to match your CSV.
    - Visualizes solid tiles with a semi-transparent overlay.
"""


# ------- CONFIGURABLE SETTINGS -------
# You can tweak these if you want a different grid resolution.
DEFAULT_MAP_ID = 0
GRID_COLS = 16   # number of columns in the CSV
GRID_ROWS = 12   # number of rows in the CSV

# Mob default health per type (used when saving/loading mobs)
MOB_DEFAULT_HEALTH = {
    "slime": 100,
    "stump": 150,
    "mushroom": 200,
}

# Colors
GRID_COLOR = (200, 200, 200)
SOLID_COLOR = (0, 255, 0, 100)  # RGBA for solid tile overlay
HILIGHT_COLOR = (255, 255, 0, 120)
MOB_COLOR = (255, 0, 0)         # mob marker color


def get_paths(map_id: int):
    """Return the background image path and CSV path for a given map id."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    bg_path = os.path.join(base_dir, "sprites", "maps", f"{map_id}.png")
    tiles_csv_path = os.path.join(base_dir, "maps", f"map{map_id}_tiles.csv")
    mobs_csv_path = os.path.join(base_dir, "maps", f"map{map_id}_mobs.csv")
    return bg_path, tiles_csv_path, mobs_csv_path


def discover_mob_types(base_dir: str):
    """
    Discover mob types based on folders under sprites/mobs.
    Returns a sorted list of folder names.
    """
    mobs_root = os.path.join(base_dir, "sprites", "mobs")
    types = []
    if os.path.exists(mobs_root):
        for name in os.listdir(mobs_root):
            path = os.path.join(mobs_root, name)
            if os.path.isdir(path):
                types.append(name)
    types.sort()
    # Fallback to slime if no folders found
    return types or ["slime"]


def load_mob_images(base_dir: str, mob_types, target_height: int):
    """
    Load a preview image for each mob type (sprites/mobs/<mob>/stand/0.png),
    scaled to roughly match the grid cell height.
    """
    mob_images = {}
    for name in mob_types:
        img_path = os.path.join(base_dir, "sprites", "mobs", name, "stand", "0.png")
        if not os.path.exists(img_path):
            continue
        try:
            img = pygame.image.load(img_path).convert_alpha()
        except pygame.error:
            continue

        if img.get_height() > 0 and target_height > 0:
            scale = target_height / img.get_height()
            # Slightly larger than a tile so mobs stand out
            scale *= 1.2
            new_w = int(img.get_width() * scale)
            new_h = int(img.get_height() * scale)
            img = pygame.transform.scale(img, (new_w, new_h))

        mob_images[name] = img
    return mob_images


def load_or_create_grid(csv_path: str, cols: int, rows: int):
    """Load a grid from CSV or create an empty grid if it doesn't exist."""
    if os.path.exists(csv_path):
        grid = []
        with open(csv_path, newline="") as f:
            reader = csv.reader(f)
            for row in reader:
                if not row:
                    continue
                grid.append([int(cell) for cell in row if cell != ""])
        # If file exists but has different size, normalize it
        if grid:
            # Trim or extend rows
            if len(grid) > rows:
                grid = grid[:rows]
            else:
                while len(grid) < rows:
                    grid.append([0] * cols)
            # Trim or extend columns in each row
            for r in range(rows):
                if len(grid[r]) > cols:
                    grid[r] = grid[r][:cols]
                else:
                    grid[r].extend([0] * (cols - len(grid[r])))
            return grid

    # Default: empty grid
    return [[0 for _ in range(cols)] for _ in range(rows)]


def save_grid(csv_path: str, grid):
    """Save the grid to CSV."""
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        for row in grid:
            writer.writerow(row)
    print(f"[map_editor] Saved tilemap to {csv_path}")


def load_mobs(csv_path: str):
    """
    Load mobs from CSV.
    CSV format: mob_name,x,y,health
    """
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
            mobs.append(
                {"mob_name": name, "x": x, "y": y, "health": health}
            )
    return mobs


def save_mobs(csv_path: str, mobs):
    """Save mobs to CSV."""
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


def main():
    # ---- parse map id from args ----
    if len(sys.argv) > 1:
        try:
            map_id = int(sys.argv[1])
        except ValueError:
            print("Usage: python map_editor.py [map_id]")
            return
    else:
        map_id = DEFAULT_MAP_ID

    base_dir = os.path.dirname(os.path.abspath(__file__))
    mob_types = discover_mob_types(base_dir)

    bg_path, tiles_csv_path, mobs_csv_path = get_paths(map_id)

    if not os.path.exists(bg_path):
        print(f"[map_editor] Background image not found: {bg_path}")
        return

    pygame.init()
    pygame.display.set_caption(f"Map Editor - map{map_id}")

    # Load background (need size first, then convert after setting display mode)
    bg_raw = pygame.image.load(bg_path)
    screen_width, screen_height = bg_raw.get_width(), bg_raw.get_height()
    screen = pygame.display.set_mode((screen_width, screen_height))
    bg_image = bg_raw.convert()

    # Grid / tiles
    tile_w = screen_width // GRID_COLS
    tile_h = screen_height // GRID_ROWS

    # Load mob preview images after we know tile size
    mob_images = load_mob_images(base_dir, mob_types, tile_h)

    grid = load_or_create_grid(tiles_csv_path, GRID_COLS, GRID_ROWS)
    mobs = load_mobs(mobs_csv_path)

    clock = pygame.time.Clock()
    running = True

    font = pygame.font.SysFont(None, 20)

    # editor state
    mode = "tiles"  # or "mobs"
    current_mob_index = 0

    while running:
        clock.tick(60)

        mouse_x, mouse_y = pygame.mouse.get_pos()
        col = mouse_x // tile_w
        row = mouse_y // tile_h

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_q):
                    running = False
                elif event.key == pygame.K_s:
                    save_grid(tiles_csv_path, grid)
                    save_mobs(mobs_csv_path, mobs)
                elif event.key == pygame.K_TAB:
                    mode = "mobs" if mode == "tiles" else "tiles"
                elif event.unicode.isdigit():
                    # select mob type by index (1..N)
                    idx = int(event.unicode) - 1
                    if 0 <= idx < len(mob_types):
                        current_mob_index = idx
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if mode == "tiles":
                    if 0 <= col < GRID_COLS and 0 <= row < GRID_ROWS:
                        if event.button == 1:  # left click -> toggle
                            grid[row][col] = 0 if grid[row][col] == 1 else 1
                        elif event.button == 3:  # right click -> clear
                            grid[row][col] = 0
                elif mode == "mobs":
                    if event.button == 1:
                        # add mob at mouse position
                            mob_name = mob_types[current_mob_index]
                            health = MOB_DEFAULT_HEALTH.get(mob_name, 100)
                            mobs.append(
                                {"mob_name": mob_name, "x": mouse_x, "y": mouse_y, "health": health}
                            )
                    elif event.button == 3:
                        # remove nearest mob within a small radius
                        if mobs:
                            mx, my = mouse_x, mouse_y
                            closest_idx = None
                            closest_dist_sq = 20 * 20
                            for i, mob in enumerate(mobs):
                                dx = mob["x"] - mx
                                dy = mob["y"] - my
                                dist_sq = dx * dx + dy * dy
                                if dist_sq <= closest_dist_sq:
                                    closest_dist_sq = dist_sq
                                    closest_idx = i
                            if closest_idx is not None:
                                mobs.pop(closest_idx)

        # Draw background
        screen.blit(bg_image, (0, 0))

        # Semi-transparent surface for tiles
        overlay = pygame.Surface((tile_w, tile_h), pygame.SRCALPHA)
        overlay_hilight = pygame.Surface((tile_w, tile_h), pygame.SRCALPHA)
        overlay.fill(SOLID_COLOR)
        overlay_hilight.fill(HILIGHT_COLOR)

        # Draw solid tiles
        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                x = c * tile_w
                y = r * tile_h
                if grid[r][c] == 1:
                    screen.blit(overlay, (x, y))

        # Draw mobs using their stand/0.png preview (fallback: red circle)
        for mob in mobs:
            name = mob.get("mob_name", "slime")
            img = mob_images.get(name)
            pos = (int(mob["x"]), int(mob["y"]))
            if img is not None:
                rect = img.get_rect(center=pos)
                screen.blit(img, rect)
            else:
                pygame.draw.circle(
                    screen,
                    MOB_COLOR,
                    pos,
                    8,
                )

        # In mobs mode, show a preview of the current mob at the mouse position
        if mode == "mobs":
            preview_name = mob_types[current_mob_index]
            preview_img = mob_images.get(preview_name)
            if preview_img is not None:
                preview = preview_img.copy()
                preview.set_alpha(180)
                rect = preview.get_rect(center=(mouse_x, mouse_y))
                screen.blit(preview, rect)

        # Draw hilight under mouse
        if 0 <= col < GRID_COLS and 0 <= row < GRID_ROWS:
            screen.blit(overlay_hilight, (col * tile_w, row * tile_h))

        # Draw grid lines
        for c in range(GRID_COLS + 1):
            x = c * tile_w
            pygame.draw.line(screen, GRID_COLOR, (x, 0), (x, screen_height), 1)
        for r in range(GRID_ROWS + 1):
            y = r * tile_h
            pygame.draw.line(screen, GRID_COLOR, (0, y), (screen_width, y), 1)

        # Small help text
        current_mob_name = mob_types[current_mob_index]
        info_lines = [
            f"map{map_id}   mode: {mode}   S: save   ESC/Q: quit   TAB: toggle tiles/mobs",
            "Tiles mode:   Left click: toggle tile   Right click: clear",
            f"Mobs mode:    1-3 select mob type (current: {current_mob_name})   Left click: add   Right click: remove",
        ]
        y_text = 5
        for line in info_lines:
            text_surf = font.render(line, True, (255, 255, 255))
            screen.blit(text_surf, (5, y_text))
            y_text += text_surf.get_height() + 2

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()


