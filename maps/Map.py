import json
import os
import csv
import pygame
from mobs.Mob import Mob
from maps import map0

TILE_WIDTH = 90
TILE_HEIGHT = 60


class Map:
    def __init__(self, screen, players, map_id=0):
        self.screen = screen
        self.players = players
        self.mobs = pygame.sprite.Group()
        self.tiles = []
        self.tile_grid = []

        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.project_root = os.path.dirname(base_dir)
        self.tile_manifest_path = os.path.join(base_dir, "tile_manifest.json")
        self.tile_defs = self.load_tile_manifest()
        self.solid_tile_ids = {
            tile_id for tile_id, data in self.tile_defs.items()
            if data.get("solid", True) and tile_id != 0
        }
        self.tile_images = self.load_tile_images()
        self.set_map(map_id)

    def set_map(self, map_id):
        """Sets the map to the requested map."""
        self.map_id = map_id
        # load collision / platform tiles for this map from CSV
        self.load_tiles_from_csv(map_id)

        mobs_from_csv = self.load_mobs_from_csv(map_id)
        if mobs_from_csv:
            self.set_mobs(mobs_from_csv)
        elif map_id == 0:
            # fallback to old hard-coded list for map0 if no CSV exists
            self.set_mobs(map0.mobs_list)

    def load_tiles_from_csv(self, map_id: int):
        """
        Load tile data from a CSV file named `map{map_id}_tiles.csv`.

        Each cell in the CSV is expected to be:
            0 -> empty / non‑solid
            1 -> solid tile

        Tiles are automatically scaled to the current screen size based on
        the CSV's rows/columns.
        """
        self.tiles = []
        self.tile_grid = []

        csv_path = os.path.join(
            os.path.dirname(__file__),
            f"map{map_id}_tiles.csv"
        )

        if not os.path.exists(csv_path):
            # No tilemap for this map – just leave tiles empty.
            return

        grid: list[list[int]] = []
        with open(csv_path, newline="") as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                # skip empty rows (e.g. trailing newlines)
                if not row:
                    continue
                grid.append([int(cell) if cell else 0 for cell in row])

        self.tile_grid = grid
        if not grid:
            return

        for y, row in enumerate(grid):
            for x, cell in enumerate(row):
                if cell in self.solid_tile_ids:
                    rect = pygame.Rect(
                        x * TILE_WIDTH,
                        y * TILE_HEIGHT,
                        TILE_WIDTH,
                        TILE_HEIGHT,
                    )
                    self.tiles.append(rect)

    def load_tile_manifest(self):
        """Load tile definitions (id -> path/solid)."""
        tile_defs = {
            0: {"id": 0, "label": "Empty", "path": None, "solid": False}
        }
        if os.path.exists(self.tile_manifest_path):
            with open(self.tile_manifest_path) as f:
                data = json.load(f)
                for entry in data.get("tiles", []):
                    tile_defs[entry["id"]] = entry
        else:
            print("[Map] WARNING: tile_manifest.json missing; using default empty tiles only.")
        return tile_defs

    def load_tile_images(self):
        """Load pygame surfaces for every tile that has a sprite path."""
        cache = {}
        tiles_root = os.path.join(self.project_root, "sprites", "maps", "tile")
        for tile_id, entry in self.tile_defs.items():
            path = entry.get("path")
            if tile_id == 0 or not path:
                continue
            sprite_path = os.path.join(tiles_root, path)
            if not os.path.exists(sprite_path):
                print(f"[Map] WARNING: missing sprite for tile id {tile_id}: {sprite_path}")
                continue
            img_orig = pygame.image.load(sprite_path).convert_alpha()

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

            cache[tile_id] = {
                'img': img_orig,
                'grid_ox': grid_ox,
                'grid_oy': grid_oy,
            }
        return cache

    def draw(self, surface):
        """Render the tile grid onto the provided surface."""
        if not self.tile_grid:
            return
        for y, row in enumerate(self.tile_grid):
            for x, tile_id in enumerate(row):
                img_data = self.tile_images.get(tile_id)
                if img_data:
                    screen_x = x * TILE_WIDTH
                    screen_y = y * TILE_HEIGHT
                    # Blit original with dynamic offset, clip to cell (handles overflow/negative oy)
                    cell_surf = pygame.Surface((TILE_WIDTH, TILE_HEIGHT), pygame.SRCALPHA)
                    cell_surf.blit(img_data['img'], (img_data['grid_ox'], img_data['grid_oy']))
                    surface.blit(cell_surf, (screen_x, screen_y))

    def load_mobs_from_csv(self, map_id: int):
        """
        Load mobs for this map from `map{map_id}_mobs.csv`.

        CSV format per line:
            mob_name,x,y,health
        """
        csv_path = os.path.join(
            os.path.dirname(__file__),
            f"map{map_id}_mobs.csv"
        )

        if not os.path.exists(csv_path):
            return []

        mobs: list[dict] = []
        with open(csv_path, newline="") as csvfile:
            reader = csv.reader(csvfile)
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
                        health = 100
                else:
                    health = 100
                mobs.append(
                    {
                        "mob_name": name,
                        "x": x,
                        "y": y,
                        "health": health,
                    }
                )
        return mobs

    def set_mobs(self, mobs_list):
        """Spawn the mobs on map."""
        for mob in mobs_list:
            print(f"[Map] Spawning mob -> name={mob.get('mob_name')} x={mob.get('x')} y={mob.get('y')} health={mob.get('health')}")
            self.mobs.add(Mob(self.screen, self.players, self.tiles, **mob))

    def get_mobs(self):
        """Returns mobs list."""
        return self.mobs