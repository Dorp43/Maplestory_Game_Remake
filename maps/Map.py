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
        self.slope_tiles = []
        self.lines = []
        self.animation_time = 0.0  # Track time for background animations

        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.project_root = os.path.dirname(base_dir)
        self.tile_manifest_path = os.path.join(base_dir, "tile_manifest.json")
        self.tile_defs = self.load_tile_manifest()
        self.solid_tile_ids = {
            tile_id for tile_id, data in self.tile_defs.items()
            if data.get("solid", True) and tile_id != 0
        }
        self.tile_images = self.load_tile_images()
        self.background_manifest_path = os.path.join(base_dir, "background_manifest.json")
        self.background_defs = self.load_background_manifest()
        self.background_images = self.load_background_images()
        self.background_layers = []
        self.global_bg_start_y = None  # Global top boundary for all backgrounds
        self.global_bg_end_y = None  # Global bottom boundary for all backgrounds
        self.spawn_point = {"x": 400, "y": 200}  # Default spawn
        self.set_map(map_id)

    def set_map(self, map_id):
        """Sets the map to the requested map."""
        self.map_id = map_id
        # load collision / platform tiles for this map from CSV
        self.load_tiles_from_csv(map_id)
        self.load_lines_from_json(map_id)
        # load background layers
        self.load_backgrounds_from_json(map_id)
        # load spawn point
        self.load_spawn_from_json(map_id)

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
        self.slope_tiles = []

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

        # Calculate map boundaries (find the actual content bounds)
        self.map_min_x, self.map_max_x, self.map_min_y, self.map_max_y = self.calculate_map_bounds()

        for y, row in enumerate(grid):
            for x, cell in enumerate(row):
                if cell in self.solid_tile_ids:
                    tile_def = self.tile_defs.get(cell, {})
                    img_data = self.tile_images.get(cell)
                    label = (tile_def.get("label") or "").lower()

                    if label.startswith("sl") and img_data:
                        slope_entry = self._build_slope_entry(cell, x, y, img_data)
                        if slope_entry:
                            self.slope_tiles.append(slope_entry)
                        continue

                    if img_data:
                        ox = img_data['grid_ox']
                        oy = img_data['grid_oy']
                        ow = img_data['img'].get_width()
                        oh = img_data['img'].get_height()
                        solid_top_rel = img_data.get('solid_top_rel', 0)
                        collision_y = y * TILE_HEIGHT + oy + solid_top_rel
                        collision_h = max(1, oh - solid_top_rel)
                        rect = pygame.Rect(
                            x * TILE_WIDTH + ox,
                            collision_y,
                            ow,
                            collision_h,
                        )
                        self.tiles.append(rect)
                    else:
                        # Fallback to full cell if no image data
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
                solid_top_rel = 0  # Full for top-heavy
            elif bottom_count > top_count:
                grid_oy = TILE_HEIGHT - oh  # Bottom-align (e.g., for ground/dirt bases)
                # Find solid top: first row from top with >10% opaque (lower threshold to close small gaps)
                solid_top_rel = oh  # Default to bottom if no dense row
                for rel_y in range(oh):
                    row_count = 0
                    for rel_x in range(ow):
                        if mask.get_at((rel_x, rel_y)):
                            row_count += 1
                    if row_count > ow // 10:  # 10% threshold for even fainter edges
                        solid_top_rel = rel_y
                        break
            else:
                grid_oy = (TILE_HEIGHT - oh) // 2  # Center-align for balanced
                solid_top_rel = 0  # Full for balanced

            # Horizontal always center
            grid_ox = (TILE_WIDTH - ow) // 2

            column_profiles = []
            for rel_x in range(ow):
                top = None
                bottom = None
                for rel_y in range(oh):
                    if mask.get_at((rel_x, rel_y)):
                        if top is None:
                            top = rel_y
                        bottom = rel_y
                column_profiles.append(
                    {
                        'top': top,
                        'bottom': bottom,
                    }
                )

            cache[tile_id] = {
                'img': img_orig,
                'grid_ox': grid_ox,
                'grid_oy': grid_oy,
                'solid_top_rel': solid_top_rel,
                'column_profiles': column_profiles,
            }
        return cache

    def _build_slope_entry(self, tile_id, grid_x, grid_y, img_data):
        """Convert a slope sprite into column-based collision data."""
        column_profiles = img_data.get('column_profiles')
        if not column_profiles:
            return None

        img = img_data['img']
        ow, oh = img.get_size()
        world_x = grid_x * TILE_WIDTH + img_data['grid_ox']
        world_y = grid_y * TILE_HEIGHT + img_data['grid_oy']
        rect = pygame.Rect(world_x, world_y, ow, oh)

        column_tops = []
        column_bottoms = []
        for profile in column_profiles:
            top = profile['top']
            bottom = profile['bottom']
            column_tops.append(world_y + top if top is not None else None)
            column_bottoms.append(world_y + bottom if bottom is not None else None)

        return {
            'tile_id': tile_id,
            'rect': rect,
            'column_tops': column_tops,
            'column_bottoms': column_bottoms,
        }

    def calculate_map_bounds(self):
        """
        Calculate the actual boundaries of the map based on non-empty tiles.
        Returns (min_x, max_x, min_y, max_y) in world coordinates.
        """
        if not self.tile_grid:
            return 0, 0, 0, 0

        min_x = None
        max_x = None
        min_y = None
        max_y = None

        for y, row in enumerate(self.tile_grid):
            for x, tile_id in enumerate(row):
                if tile_id != 0:  # Non-empty tile
                    img_data = self.tile_images.get(tile_id)
                    if img_data:
                        world_x = x * TILE_WIDTH + img_data['grid_ox']
                        world_y = y * TILE_HEIGHT + img_data['grid_oy']
                        img = img_data['img']
                        tile_right = world_x + img.get_width()
                        tile_bottom = world_y + img.get_height()

                        if min_x is None or world_x < min_x:
                            min_x = world_x
                        if max_x is None or tile_right > max_x:
                            max_x = tile_right
                        if min_y is None or world_y < min_y:
                            min_y = world_y
                        if max_y is None or tile_bottom > max_y:
                            max_y = tile_bottom

        # Default to screen size if no tiles found
        if min_x is None:
            return 0, self.screen.get_width(), 0, self.screen.get_height()

        return min_x, max_x, min_y, max_y

    def get_map_bounds(self):
        """Get the map boundaries. Returns (min_x, max_x, min_y, max_y)"""
        if hasattr(self, 'map_min_x'):
            return self.map_min_x, self.map_max_x, self.map_min_y, self.map_max_y
        return 0, self.screen.get_width(), 0, self.screen.get_height()

    def draw(self, surface, camera_x=0, camera_y=0):
        """Render backgrounds first, then the tile grid onto the provided surface with camera offset."""
        # Draw background layers (back to front, sorted by layer index)
        self.draw_backgrounds(surface, camera_x, camera_y)
        
        # Draw tiles
        if not self.tile_grid:
            return
        for y, row in enumerate(self.tile_grid):
            for x, tile_id in enumerate(row):
                img_data = self.tile_images.get(tile_id)
                if img_data:
                    world_x = x * TILE_WIDTH + img_data['grid_ox']
                    world_y = y * TILE_HEIGHT + img_data['grid_oy']
                    # Convert world position to screen position
                    screen_x = world_x - camera_x
                    screen_y = world_y - camera_y
                    # Only draw if tile is visible on screen (optional optimization)
                    img = img_data['img']
                    if (screen_x + img.get_width() >= 0 and screen_x < surface.get_width() and
                        screen_y + img.get_height() >= 0 and screen_y < surface.get_height()):
                        surface.blit(img, (screen_x, screen_y))

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
        map_bounds = self.get_map_bounds()
        for mob in mobs_list:
            print(f"[Map] Spawning mob -> name={mob.get('mob_name')} x={mob.get('x')} y={mob.get('y')} health={mob.get('health')}")
            self.mobs.add(Mob(self.screen, self.players, self.tiles, self.slope_tiles, lines=self.lines, map_bounds=map_bounds, **mob))

    def get_mobs(self):
        """Returns mobs list."""
        return self.mobs

    def load_lines_from_json(self, map_id: int):
        """Load collision lines from map{id}_lines.json."""
        self.lines = []
        json_path = os.path.join(
            os.path.dirname(__file__),
            f"map{map_id}_lines.json"
        )
        
        if not os.path.exists(json_path):
            return

        try:
            with open(json_path, "r") as f:
                self.lines = json.load(f)
        except Exception as e:
            print(f"[Map] Error loading lines: {e}")

    def load_background_manifest(self):
        """Load background definitions (id -> path)."""
        bg_defs = {
            0: {"id": 0, "label": "Empty", "path": None}
        }
        if os.path.exists(self.background_manifest_path):
            with open(self.background_manifest_path) as f:
                data = json.load(f)
                for entry in data.get("backgrounds", []):
                    bg_defs[entry["id"]] = entry
        else:
            print("[Map] WARNING: background_manifest.json missing; using default empty backgrounds only.")
        return bg_defs

    def load_background_images(self):
        """Load pygame surfaces for every background that has a sprite path."""
        cache = {}
        backgrounds_root = os.path.join(self.project_root, "sprites", "maps", "back")
        for bg_id, entry in self.background_defs.items():
            path = entry.get("path")
            if bg_id == 0 or not path:
                continue
            sprite_path = os.path.join(backgrounds_root, path)
            if not os.path.exists(sprite_path):
                print(f"[Map] WARNING: missing background sprite for id {bg_id}: {sprite_path}")
                continue
            try:
                img = pygame.image.load(sprite_path).convert_alpha()
                cache[bg_id] = img
            except pygame.error as e:
                print(f"[Map] Error loading background {bg_id}: {e}")
        return cache

    def load_backgrounds_from_json(self, map_id: int):
        """Load background layers from map{id}_backgrounds.json."""
        self.background_layers = []
        json_path = os.path.join(
            os.path.dirname(__file__),
            f"map{map_id}_backgrounds.json"
        )
        
        if not os.path.exists(json_path):
            return

        try:
            with open(json_path, "r") as f:
                data = json.load(f)
                layers = data.get("layers", [])
                # Set defaults for backward compatibility
                for layer in layers:
                    if "repeat" not in layer:
                        layer["repeat"] = False
                    if "x" not in layer and not layer.get("repeat", False):
                        layer["x"] = 0  # Default X for non-repeating
                    if "animated" not in layer:
                        layer["animated"] = False
                    if "animation_speed" not in layer:
                        layer["animation_speed"] = 20.0
                self.background_layers = layers
                # Load global bounds
                self.global_bg_start_y = data.get("global_start_y", None)
                self.global_bg_end_y = data.get("global_end_y", None)
                # Sort layers by layer_index (lower = drawn first/behind)
                self.background_layers.sort(key=lambda l: l.get("layer_index", 0))
        except Exception as e:
            print(f"[Map] Error loading backgrounds: {e}")

    def draw_backgrounds(self, surface, camera_x=0, camera_y=0):
        """Draw all background layers with optional horizontal repeating."""
        screen_width = surface.get_width()
        screen_height = surface.get_height()
        
        # If global bounds are set, calculate scale factor to fit all backgrounds between boundaries
        has_global_bounds = self.global_bg_start_y is not None and self.global_bg_end_y is not None
        scale_factor = 1.0
        min_bg_y = 0
        
        if has_global_bounds:
            bounds_height = self.global_bg_end_y - self.global_bg_start_y
            if bounds_height > 0 and len(self.background_layers) > 0:
                # Find the min and max Y positions of all backgrounds to determine their total range
                min_y = float('inf')
                max_y = float('-inf')
                for layer in self.background_layers:
                    bg_id = layer.get("background_id", 0)
                    if bg_id == 0:
                        continue
                    bg_img = self.background_images.get(bg_id)
                    if not bg_img:
                        continue
                    layer_y = layer.get("y", 0)
                    img_height = bg_img.get_height()
                    min_y = min(min_y, layer_y)
                    max_y = max(max_y, layer_y + img_height)
                
                # Calculate original height range of backgrounds
                if min_y != float('inf') and max_y != float('-inf'):
                    original_height = max_y - min_y
                    if original_height > 0:
                        # Scale factor to fit original height into bounds height
                        # This ensures backgrounds fill from top boundary to bottom boundary
                        scale_factor = bounds_height / original_height
                        min_bg_y = min_y
                    else:
                        # If all backgrounds are at the same Y, use a default scale
                        scale_factor = 1.0
                        min_bg_y = min_y if min_y != float('inf') else 0
        
        for layer in self.background_layers:
            bg_id = layer.get("background_id", 0)
            if bg_id == 0:
                continue
                
            bg_img = self.background_images.get(bg_id)
            if not bg_img:
                continue
            
            # Get layer properties
            y_pos = layer.get("y", 0)
            scroll_speed = layer.get("scroll_speed", 1.0)  # Parallax effect (1.0 = normal, <1.0 = slower)
            repeat = layer.get("repeat", False)  # Default to False (non-repeating)
            animated = layer.get("animated", False)
            animation_speed = layer.get("animation_speed", 20.0)
            
            # Calculate scroll offset with parallax
            scroll_x = int(camera_x * scroll_speed)
            img_width = bg_img.get_width()
            img_height = bg_img.get_height()
            
            # If global bounds are set, scale all backgrounds uniformly to fit between boundaries
            # Maintain aspect ratio and relative positions - just scale everything proportionally
            if has_global_bounds:
                # Scale the background image maintaining aspect ratio
                scaled_width = int(img_width * scale_factor)
                scaled_height = int(img_height * scale_factor)
                scaled_img = pygame.transform.scale(bg_img, (scaled_width, scaled_height))
                
                # Calculate screen positions - scale the Y position proportionally
                # Original Y position relative to minimum background Y
                relative_y = y_pos - min_bg_y
                # Scale the relative position
                scaled_relative_y = relative_y * scale_factor
                # Screen Y position relative to top boundary (stays between boundaries)
                screen_y = int(self.global_bg_start_y + scaled_relative_y - camera_y)
                
                # Only draw if within screen bounds AND between boundary lines
                screen_start_y = self.global_bg_start_y - camera_y
                screen_end_y = self.global_bg_end_y - camera_y
                
                # Ensure backgrounds fill from top boundary to bottom boundary
                # Clip to boundaries if needed, but always draw to fill the space
                draw_y = max(screen_y, screen_start_y)
                draw_bottom = min(screen_y + scaled_height, screen_end_y)
                draw_height = draw_bottom - draw_y
                
                # Only draw if there's visible area
                if draw_height > 0 and draw_y < screen_end_y:
                    # Create clipped surface if needed
                    final_img = scaled_img
                    if screen_y < screen_start_y or screen_y + scaled_height > screen_end_y:
                        # Need to clip
                        clip_top = max(0, screen_start_y - screen_y)
                        clip_bottom = min(scaled_height, screen_end_y - screen_y)
                        clip_height = clip_bottom - clip_top
                        if clip_height > 0:
                            clipped_surf = pygame.Surface((scaled_width, clip_height))
                            clipped_surf.blit(scaled_img, (0, -clip_top), (0, clip_top, scaled_width, clip_height))
                            final_img = clipped_surf
                        else:
                            continue  # Skip if no visible area
                    
                    # Draw to fill the space - NO VERTICAL TILING, just scale to fit
                    if repeat:
                        # Draw repeating background - cover entire horizontal space only
                        anim_offset = 0
                        if animated:
                            # Scale animation offset too
                            anim_offset = int((self.animation_time * animation_speed) * scale_factor) % scaled_width
                        
                        # Calculate start position to ensure full horizontal coverage
                        base_x = (-scroll_x - anim_offset) % scaled_width
                        start_x = base_x - scaled_width
                        end_x = screen_width + scaled_width
                        
                        # Draw repeating scaled background - ONE instance per X position, NO vertical tiling
                        for x in range(start_x, end_x, scaled_width):
                            surface.blit(final_img, (x, draw_y))
                    else:
                        # For non-repeating backgrounds, scale X position too
                        x_pos = layer.get("x", 0)
                        screen_x = int(x_pos * scale_factor - scroll_x)
                        
                        # Draw ONCE - NO vertical tiling
                        if screen_x + scaled_width >= 0 and screen_x < screen_width:
                            surface.blit(final_img, (screen_x, draw_y))
                continue  # Skip the normal drawing code
            
            # Normal drawing (no global bounds or only one bound set)
            screen_y = y_pos - camera_y
            
            # Clip background vertically if global bounds are set
            clip_top = 0
            clip_bottom = img_height
            if self.global_bg_start_y is not None:
                # Clip top if background starts above the boundary
                if y_pos < self.global_bg_start_y:
                    clip_top = self.global_bg_start_y - y_pos
            if self.global_bg_end_y is not None:
                # Clip bottom if background extends below the boundary
                if y_pos + img_height > self.global_bg_end_y:
                    clip_bottom = self.global_bg_end_y - y_pos
            
            # Only draw if layer is visible on screen vertically and within bounds
            if screen_y + clip_bottom >= 0 and screen_y + clip_top < screen_height and clip_bottom > clip_top:
                if repeat:
                    # Draw repeating background - cover entire horizontal space
                    # Calculate animation offset (moves right to left, so negative)
                    anim_offset = 0
                    if animated:
                        anim_offset = int(self.animation_time * animation_speed) % img_width
                    
                    # Calculate how many times to repeat horizontally
                    # Start from leftmost visible position
                    start_x = (-scroll_x - anim_offset) % img_width - img_width
                    # Extend well beyond screen to ensure full coverage
                    end_x = screen_width + img_width * 2
                    
                    # Draw repeating background with vertical clipping
                    for x in range(start_x, end_x, img_width):
                        if clip_top > 0 or clip_bottom < img_height:
                            # Create a clipped surface
                            clipped_surf = pygame.Surface((img_width, clip_bottom - clip_top), pygame.SRCALPHA)
                            clipped_surf.blit(bg_img, (0, -clip_top), (0, clip_top, img_width, clip_bottom - clip_top))
                            surface.blit(clipped_surf, (x, screen_y + clip_top))
                        else:
                            surface.blit(bg_img, (x, screen_y))
                else:
                    # Draw single instance (no repeating) with vertical clipping
                    x_pos = layer.get("x", 0)  # X position for non-repeating backgrounds
                    screen_x = x_pos - scroll_x
                    # Only draw if visible on screen
                    if screen_x + img_width >= 0 and screen_x < screen_width:
                        if clip_top > 0 or clip_bottom < img_height:
                            # Create a clipped surface
                            clipped_surf = pygame.Surface((img_width, clip_bottom - clip_top), pygame.SRCALPHA)
                            clipped_surf.blit(bg_img, (0, -clip_top), (0, clip_top, img_width, clip_bottom - clip_top))
                            surface.blit(clipped_surf, (screen_x, screen_y + clip_top))
                        else:
                            surface.blit(bg_img, (screen_x, screen_y))

    def load_spawn_from_json(self, map_id: int):
        """Load spawn point from map{id}_spawn.json."""
        json_path = os.path.join(
            os.path.dirname(__file__),
            f"map{map_id}_spawn.json"
        )
        
        if not os.path.exists(json_path):
            return

        try:
            with open(json_path, "r") as f:
                data = json.load(f)
                self.spawn_point = {"x": data.get("x", 400), "y": data.get("y", 200)}
        except Exception as e:
            print(f"[Map] Error loading spawn point: {e}")

    def get_spawn_point(self):
        """Get the spawn point coordinates. Returns (x, y) tuple."""
        return self.spawn_point.get("x", 400), self.spawn_point.get("y", 200)