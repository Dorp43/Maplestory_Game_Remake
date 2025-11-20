import pygame
import random
import os
from skills.Skill import Skill
from skills.Projectile import Projectile
from entities.HealthBar import HealthBar


class Player(pygame.sprite.Sprite):
    def __init__(self, screen, char_type, x, y, scale, speed, health, mobs, tiles, collision_lines=None, map_bounds=None):
        pygame.sprite.Sprite.__init__(self)
        self.alive = True
        self.screen = screen
        self.char_type = char_type
        self.speed = speed
        self.direction = -1
        self.vel_y = 0
        self.vel_x = 0
        self.max_health = health
        self.health = health
        self.mobs = mobs
        # list of pygame.Rect for solid tiles / platforms (legacy, may be empty if using lines)
        self.tiles = tiles
        self.collision_lines = collision_lines or []
        self.max_slope_step_up = 60
        self.max_slope_step_down = 25
        self.current_line_id = None  # Track which line the player is currently on for smooth transitions
        # Map boundaries: (min_x, max_x, min_y, max_y) - None means no boundaries
        self.map_bounds = map_bounds
        self.projectiles_group = pygame.sprite.Group()
        self.skills_group = pygame.sprite.Group()
        # Booleans
        self.attack = False
        self.is_hit = False
        self.jump = False
        self.in_air = True
        self.flip = False
        # Skills
        self.skill = False
        self.skill_big_star = False
        self.flash_jump = False
        # Cool downs
        self.flash_jump_cooldown = 0
        self.hit_cooldown = 0
        # Movement
        self.moving_left = False
        self.moving_right = False
        # Animation
        self.animation_list = []
        self.next_attack = 3
        self.frame_index = 0
        self.action = 0
        self.update_time = pygame.time.get_ticks()
        
        #load all images for the players
        animation_types = ['stand', 'walk', 'jump', 'attack1', 'attack2', 'attack3', 'attack_big_star', 'hit', 'stab']
        for animation in animation_types:
            #reset temporary list of images
            temp_list = []
            #count number of files in the folder
            num_of_frames = len(os.listdir(f'sprites/{self.char_type}/Thief/{animation}'))
            for i in range(num_of_frames):
                img = pygame.image.load(f'sprites/{self.char_type}/Thief/{animation}/{i}.png')
                img = pygame.transform.scale(img, (int(img.get_width() * scale), int(img.get_height() * scale)))
                temp_list.append(img)
            self.animation_list.append(temp_list)

        self.image = self.animation_list[self.action][self.frame_index]
        self.rect = self.image.get_rect()
        self.rect.center = (x, y)
        self.health_bar = HealthBar(self, screen, "green")


    def update(self, camera_x=0, camera_y=0):
        self.health_bar.update(camera_x, camera_y)
        self.update_animation()
        self.handle_cooldown()
        self.check_alive()
       

    def move(self, GRAVITY):
        #reset movement variables
        dx = 0
        dy = 0

        #assign movement variables if moving left or right
        if self.moving_left:
            dx = -self.speed
            self.flip = False
            self.direction = -1
        if self.moving_right:
            dx = self.speed
            self.flip = True
            self.direction = 1

        
        # Flash jump
        if self.flash_jump and self.in_air:
            self.handle_skill("flash_jump")
            self.play_sound("skills", "flash_jump")
            if self.flash_jump_cooldown == 0:
                self.flash_jump_cooldown = 70
                self.vel_y -= 7
                self.vel_x -= self.direction * -7
                self.flash_jump = False
        elif not self.flash_jump and not self.in_air:
            self.vel_x = 0


        #jump
        if self.jump == True and self.in_air == False:
            self.play_sound("player","jump")
            self.vel_y = -11
            self.jump = False
            self.in_air = True


        #apply gravity
        self.vel_y += GRAVITY
        if self.vel_y > 10:
            self.vel_y
        dy += self.vel_y
        if self.vel_x > 10:
            self.vel_x
        dx += self.vel_x

        # Use line-based collision if lines are available, otherwise fall back to tiles
        if self.collision_lines:
            # --- horizontal movement & collision against lines ---
            self.rect.x += dx
            self._handle_line_horizontal_collision(dx)
            
            # --- vertical movement & collision against lines ---
            self.rect.y += dy
            self.in_air = True
            self._handle_line_vertical_collision(dy)
        else:
            # Legacy tile-based collision
            # --- horizontal movement & collision against tiles ---
            self.rect.x += dx
            for tile in self.tiles:
                if self.rect.colliderect(tile):
                    if dx > 0:
                        self.rect.right = tile.left
                    elif dx < 0:
                        self.rect.left = tile.right

            # --- vertical movement & collision against tiles ---
            self.rect.y += dy
            self.in_air = True
            for tile in self.tiles:
                if self.rect.colliderect(tile):
                    if self.vel_y > 0:  # falling
                        self.rect.bottom = tile.top
                        self.vel_y = 0
                        self.in_air = False
                    elif self.vel_y < 0:  # jumping up
                        self.rect.top = tile.bottom
                        self.vel_y = 0

        # Clamp player to map boundaries if provided
        if self.map_bounds:
            map_min_x, map_max_x, map_min_y, map_max_y = self.map_bounds
            # Horizontal boundaries
            if self.rect.left < map_min_x:
                self.rect.left = map_min_x
            if self.rect.right > map_max_x:
                self.rect.right = map_max_x
            # Vertical boundaries (only clamp bottom, allow going above map top)
            if self.rect.bottom > map_max_y:
                self.rect.bottom = map_max_y
                self.vel_y = 0
                self.in_air = False

    def _handle_line_horizontal_collision(self, dx):
        """Handle horizontal collision with lines (walls/barriers)."""
        if dx == 0:
            return
        
        # Check collision with vertical or diagonal lines
        for line in self.collision_lines:
            x1, y1 = line["x1"], line["y1"]
            x2, y2 = line["x2"], line["y2"]
            
            # Skip horizontal lines (they're walkable surfaces, not barriers)
            if abs(y2 - y1) < 1:  # Essentially horizontal
                continue
            
            line_min_x = min(x1, x2)
            line_max_x = max(x1, x2)
            line_min_y = min(y1, y2)
            line_max_y = max(y1, y2)
            
            # Check if line is in player's horizontal range
            if line_max_x < self.rect.left or line_min_x > self.rect.right:
                continue
            
            # For vertical lines, check direct collision
            if abs(x2 - x1) < 1:  # Essentially vertical
                line_x = x1
                # Only block if line is actually in the player's vertical range
                if line_max_y >= self.rect.top and line_min_y <= self.rect.bottom:
                    if dx > 0 and self.rect.right >= line_x and self.rect.right - dx < line_x:
                        self.rect.right = line_x
                    elif dx < 0 and self.rect.left <= line_x and self.rect.left - dx > line_x:
                        self.rect.left = line_x
            else:
                # Diagonal line - only treat as barrier if player is NOT standing on it
                # Check if player's feet are on this line (if so, it's walkable, not a barrier)
                if abs(x2 - x1) > 0.001:
                    m = (y2 - y1) / (x2 - x1)
                    b = y1 - m * x1
                    
                    # Check if player is standing on this line
                    padding = min(12, max(2, self.rect.width // 6))
                    probe_points = [
                        self.rect.left + padding,
                        self.rect.centerx,
                        self.rect.right - padding,
                    ]
                    
                    is_standing_on = False
                    for foot_x in probe_points:
                        if line_min_x <= foot_x <= line_max_x:
                            surface_y = m * foot_x + b
                            # Check if player's feet are on or very close to the line
                            if abs(surface_y - self.rect.bottom) <= self.max_slope_step_down + 5:
                                is_standing_on = True
                                break
                    
                    # If player is standing on this line, skip it (it's a walkable surface)
                    if is_standing_on:
                        continue

                    # Check if this line is connected to ANY line we are currently standing on
                    # This handles the case where we are transitioning between lines but current_line_id is not set yet
                    # or we are standing on a line but the probe points haven't reached the new line yet
                    is_connected_to_standing = False
                    
                    # First, check if it's connected to current_line_id if we have one
                    standing_line_ids = set()
                    if self.current_line_id is not None:
                        standing_line_ids.add(self.current_line_id)
                    
                    # Also check other lines we might be standing on (using the same logic as is_standing_on)
                    # This is a bit expensive but necessary for robustness
                    for other_line in self.collision_lines:
                        if other_line is line: continue
                        
                        # Quick check if close enough
                        if other_line["x2"] < self.rect.left - 50 or other_line["x1"] > self.rect.right + 50:
                            continue
                            
                        o_x1, o_y1 = other_line["x1"], other_line["y1"]
                        o_x2, o_y2 = other_line["x2"], other_line["y2"]
                        
                        if abs(o_x2 - o_x1) > 0.001:
                            o_m = (o_y2 - o_y1) / (o_x2 - o_x1)
                            o_b = o_y1 - o_m * o_x1
                            
                            for foot_x in probe_points:
                                if min(o_x1, o_x2) <= foot_x <= max(o_x1, o_x2):
                                    surface_y = o_m * foot_x + o_b
                                    if abs(surface_y - self.rect.bottom) <= self.max_slope_step_down + 5:
                                        standing_line_ids.add(id(other_line))
                                        break
                    
                    if standing_line_ids:
                        # Check if target line is connected to any standing line
                        x1, y1 = line["x1"], line["y1"]
                        x2, y2 = line["x2"], line["y2"]
                        TOLERANCE = 5.0
                        
                        for s_id in standing_line_ids:
                            # Find the line object
                            s_line = None
                            for l in self.collision_lines:
                                if id(l) == s_id:
                                    s_line = l
                                    break
                            if not s_line: continue
                            
                            c_x1, c_y1 = s_line["x1"], s_line["y1"]
                            c_x2, c_y2 = s_line["x2"], s_line["y2"]
                            
                            if (abs(x1 - c_x1) < TOLERANCE and abs(y1 - c_y1) < TOLERANCE) or \
                               (abs(x1 - c_x2) < TOLERANCE and abs(y1 - c_y2) < TOLERANCE) or \
                               (abs(x2 - c_x1) < TOLERANCE and abs(y2 - c_y1) < TOLERANCE) or \
                               (abs(x2 - c_x2) < TOLERANCE and abs(y2 - c_y2) < TOLERANCE):
                                is_connected_to_standing = True
                                break
                    
                    if is_connected_to_standing:
                        continue
                    
                    # Otherwise, treat as barrier - check if player would intersect with it
                    # Check if line is in player's vertical range
                    if line_max_y < self.rect.top or line_min_y > self.rect.bottom:
                        continue
                    
                    # Check if player's left/right edge would cross the line
                    if dx > 0:  # Moving right
                        # Check right edge
                        test_x = self.rect.right
                        test_y = m * test_x + b
                        if line_min_x <= test_x <= line_max_x and line_min_y <= test_y <= line_max_y:
                            if self.rect.top <= test_y <= self.rect.bottom:
                                # Calculate where line intersects player's top/bottom
                                if abs(m) > 0.001:
                                    y_at_top = self.rect.top
                                    x_at_top = (y_at_top - b) / m
                                    y_at_bottom = self.rect.bottom
                                    x_at_bottom = (y_at_bottom - b) / m
                                    
                                    # If line crosses player's vertical range, stop at line
                                    # We want the MINIMUM x that intersects (first point of contact)
                                    valid_xs = []
                                    if line_min_x <= x_at_top <= line_max_x: valid_xs.append(x_at_top)
                                    if line_min_x <= x_at_bottom <= line_max_x: valid_xs.append(x_at_bottom)
                                    
                                    if valid_xs:
                                        self.rect.right = min(valid_xs)
                    elif dx < 0:  # Moving left
                        # Check left edge
                        test_x = self.rect.left
                        test_y = m * test_x + b
                        if line_min_x <= test_x <= line_max_x and line_min_y <= test_y <= line_max_y:
                            if self.rect.top <= test_y <= self.rect.bottom:
                                if abs(m) > 0.001:
                                    y_at_top = self.rect.top
                                    x_at_top = (y_at_top - b) / m
                                    y_at_bottom = self.rect.bottom
                                    x_at_bottom = (y_at_bottom - b) / m
                                    
                                    # We want the MAXIMUM x that intersects (first point of contact from right)
                                    valid_xs = []
                                    if line_min_x <= x_at_top <= line_max_x: valid_xs.append(x_at_top)
                                    if line_min_x <= x_at_bottom <= line_max_x: valid_xs.append(x_at_bottom)
                                    
                                    if valid_xs:
                                        self.rect.left = max(valid_xs)

    def _handle_line_vertical_collision(self, dy):
        """Handle vertical collision with lines (walkable surfaces).
        
        NEW MECHANISM: Treats connected lines as continuous surfaces.
        For each probe point, finds the best surface from all possible lines,
        prioritizing the current line and connected lines for smooth transitions.
        """
        # Skip collision entirely when moving upward (jumping) - allow natural jump movement
        if self.vel_y < 0 or dy < 0:  # Moving upward (jumping)
            # Clear current line tracking when jumping to allow free upward movement
            self.current_line_id = None
            return
        
        # Check if player's feet are on a line
        padding = min(12, max(2, self.rect.width // 6))
        probe_points = [
            self.rect.left + padding,
            self.rect.centerx,
            self.rect.right - padding,
        ]
        
        # Build connection graph: map each endpoint to all line IDs that share it
        ENDPOINT_TOLERANCE = 5.0  # Increased slightly for better matching
        endpoint_to_line_ids = {}  # (x, y) -> set of line IDs (using id() since lines are dicts)
        
        for line in self.collision_lines:
            x1, y1 = line["x1"], line["y1"]
            x2, y2 = line["x2"], line["y2"]
            if abs(x2 - x1) < 1:  # Skip vertical lines
                continue
            
            line_id = id(line)
            
            # Round endpoints to handle floating point issues
            p1 = (round(x1), round(y1))
            p2 = (round(x2), round(y2))
            
            # Find existing endpoint keys that are close to these points
            def find_matching_endpoint(point):
                px, py = point
                for (ex, ey) in endpoint_to_line_ids.keys():
                    if abs(px - ex) < ENDPOINT_TOLERANCE and abs(py - ey) < ENDPOINT_TOLERANCE:
                        return (ex, ey)
                return None
            
            key1 = find_matching_endpoint(p1) or p1
            key2 = find_matching_endpoint(p2) or p2
            
            if key1 not in endpoint_to_line_ids:
                endpoint_to_line_ids[key1] = set()
            if key2 not in endpoint_to_line_ids:
                endpoint_to_line_ids[key2] = set()
            
            endpoint_to_line_ids[key1].add(line_id)
            endpoint_to_line_ids[key2].add(line_id)
        
        # Get current line if we're on one
        current_line = None
        if self.current_line_id is not None:
            for line in self.collision_lines:
                if id(line) == self.current_line_id:
                    current_line = line
                    break
        
        # Find all line IDs connected to current line (for smooth transitions)
        connected_line_ids = set()
        if current_line:
            cx1, cy1 = current_line["x1"], current_line["y1"]
            cx2, cy2 = current_line["x2"], current_line["y2"]
            p1 = (round(cx1), round(cy1))
            p2 = (round(cx2), round(cy2))
            
            # Find matching endpoints
            for endpoint, line_ids in endpoint_to_line_ids.items():
                if (abs(p1[0] - endpoint[0]) < ENDPOINT_TOLERANCE and abs(p1[1] - endpoint[1]) < ENDPOINT_TOLERANCE) or \
                   (abs(p2[0] - endpoint[0]) < ENDPOINT_TOLERANCE and abs(p2[1] - endpoint[1]) < ENDPOINT_TOLERANCE):
                    connected_line_ids.update(line_ids)
        
        # Collect all valid surface positions for each probe point
        valid_surfaces = []  # List of (surface_y, line, foot_x, gap_abs, priority, is_extended)
        
        # For each probe point, find the best surface from all lines
        for foot_x in probe_points:
            # Check ALL lines - the new mechanism checks everything and uses priority
            for line in self.collision_lines:
                x1, y1 = line["x1"], line["y1"]
                x2, y2 = line["x2"], line["y2"]
                
                # Skip vertical lines (they're barriers, not walkable)
                if abs(x2 - x1) < 1:
                    continue
                
                line_min_x = min(x1, x2)
                line_max_x = max(x1, x2)
                line_min_y = min(y1, y2)
                line_max_y = max(y1, y2)
                
                # Determine if this line is angled (not horizontal)
                is_angled = abs(y2 - y1) > 1.0  # Has significant vertical component
                
                # Determine if this line is the current line or connected to it
                line_id = id(line)
                is_current_line = (self.current_line_id == line_id)
                is_connected = line_id in connected_line_ids
                
                # Calculate extended bounds based on line type and movement direction
                # Base extension
                base_extension = 15
                # Much more extension for angled lines (they need more tolerance)
                if is_angled:
                    base_extension = 35  # Angled lines need more X extension
                # More extension for current line (to keep player on it)
                if is_current_line:
                    base_extension = max(base_extension, 40)  # Even more for current angled line
                # More extension for connected lines (for smooth transitions)
                elif is_connected:
                    base_extension = max(base_extension, 35)
                
                # Directional extension: extend more in the direction of movement
                # This helps detect the next line when approaching a connection point
                extension_left = base_extension
                extension_right = base_extension
                
                # If moving right, extend more to the right to catch the next line early
                if self.moving_right:
                    extension_right = base_extension + 25  # Extra extension on right when moving right
                # If moving left, extend more to the left
                elif self.moving_left:
                    extension_left = base_extension + 25  # Extra extension on left when moving left
                
                # For connected lines, always extend more in both directions for smooth transitions
                if is_connected:
                    extension_left = max(extension_left, 40)
                    extension_right = max(extension_right, 40)
                
                # Check if foot_x is within extended bounds
                extended_min = line_min_x - extension_left
                extended_max = line_max_x + extension_right
                within_bounds = extended_min <= foot_x <= extended_max
                
                # STRICT CHECK: Is it within the ACTUAL line bounds?
                strictly_within = line_min_x <= foot_x <= line_max_x
                
                # Also check if we're at an endpoint (with tolerance)
                # For angled lines, use larger tolerance
                endpoint_tolerance = 12.0 if is_angled else 8.0
                at_start = abs(foot_x - line_min_x) < endpoint_tolerance
                at_end = abs(foot_x - line_max_x) < endpoint_tolerance
                
                # Check if we're near a connection point where this line is involved
                at_connection = False
                connection_y = None
                connection_point = None
                for endpoint, line_ids in endpoint_to_line_ids.items():
                    if line_id in line_ids:
                        # Check if this endpoint is near our probe point
                        # For angled lines, be more generous
                        conn_tolerance = endpoint_tolerance * 1.5 if is_angled else endpoint_tolerance
                        
                        # When moving right, extend tolerance to the right to catch connections early
                        # When moving left, extend tolerance to the left
                        if self.moving_right:
                            # Extend tolerance to the right (looking ahead)
                            if foot_x >= endpoint[0] - conn_tolerance and foot_x <= endpoint[0] + conn_tolerance * 2:
                                at_connection = True
                                connection_y = endpoint[1]
                                connection_point = endpoint
                                break
                        elif self.moving_left:
                            # Extend tolerance to the left (looking ahead)
                            if foot_x >= endpoint[0] - conn_tolerance * 2 and foot_x <= endpoint[0] + conn_tolerance:
                                at_connection = True
                                connection_y = endpoint[1]
                                connection_point = endpoint
                                break
                        else:
                            # Not moving - use symmetric tolerance
                            if abs(foot_x - endpoint[0]) < conn_tolerance:
                                at_connection = True
                                connection_y = endpoint[1]
                                connection_point = endpoint
                                break
                
                # Proactive detection: if we're on a line ending at a connection and moving toward it,
                # check if this line starts at that connection point
                if not (within_bounds or at_start or at_end or at_connection):
                    # Check if we're approaching a connection point from the current line
                    if self.current_line_id is not None and current_line:
                        cx1, cy1 = current_line["x1"], current_line["y1"]
                        cx2, cy2 = current_line["x2"], current_line["y2"]
                        current_min_x = min(cx1, cx2)
                        current_max_x = max(cx1, cx2)
                        
                        # Check if current line ends at a connection point we're approaching
                        for endpoint, line_ids in endpoint_to_line_ids.items():
                            endpoint_x, endpoint_y = endpoint
                            
                            # If moving right, check if current line ends at connection and we're approaching it
                            if self.moving_right:
                                # Current line ends at connection on the right
                                if abs(current_max_x - endpoint_x) < 5.0 and abs(cy2 if cx2 > cx1 else cy1 - endpoint_y) < 5.0:
                                    # This line starts at that connection point
                                    if line_id in line_ids:
                                        # Check if we're approaching from the left
                                        if foot_x >= endpoint_x - 30 and foot_x <= endpoint_x + 15:
                                            at_connection = True
                                            connection_y = endpoint_y
                                            connection_point = endpoint
                                            within_bounds = True  # Treat as within bounds
                                            break
                            
                            # If moving left, check if current line ends at connection and we're approaching it
                            elif self.moving_left:
                                # Current line ends at connection on the left
                                if abs(current_min_x - endpoint_x) < 5.0 and abs(cy1 if cx1 < cx2 else cy2 - endpoint_y) < 5.0:
                                    # This line starts at that connection point
                                    if line_id in line_ids:
                                        # Check if we're approaching from the right
                                        if foot_x >= endpoint_x - 15 and foot_x <= endpoint_x + 30:
                                            at_connection = True
                                            connection_y = endpoint_y
                                            connection_point = endpoint
                                            within_bounds = True  # Treat as within bounds
                                            break
                
                # For angled lines, also check if we're within Y range even if X is slightly outside
                # This helps when player is moving horizontally on a slope
                within_y_range = False
                if is_angled and not (within_bounds or at_start or at_end or at_connection):
                    # Calculate Y at this X
                    if abs(x2 - x1) > 0.001:
                        m = (y2 - y1) / (x2 - x1)
                        b = y1 - m * x1
                        test_y = m * foot_x + b
                        # If Y is within line range, we might still be on the line
                        if line_min_y - 30 <= test_y <= line_max_y + 30:
                            # Check if player's Y is close to this line's Y
                            player_y = self.rect.bottom
                            if abs(test_y - player_y) < 30:  # Within 30 pixels vertically
                                within_y_range = True
                
                if not (within_bounds or at_start or at_end or at_connection or within_y_range):
                    continue
                
                # Calculate Y position on line for this X
                if abs(x2 - x1) > 0.001:
                    m = (y2 - y1) / (x2 - x1)
                    b = y1 - m * x1
                    # Clamp foot_x to actual line bounds to prevent extrapolation
                    effective_x = max(line_min_x, min(line_max_x, foot_x))
                    surface_y = m * effective_x + b
                else:
                    # Horizontal line (Y constant)
                    surface_y = y1
                
                # At connection points, use the connection Y for consistency
                if at_connection and connection_y is not None and connection_point is not None:
                    # Blend between line Y and connection Y based on distance
                    dist_to_connection = abs(foot_x - connection_point[0])
                    if dist_to_connection < endpoint_tolerance:
                        # Calculate line Y at connection point
                        if abs(x2 - x1) > 0.001:
                            line_y_at_conn = m * connection_point[0] + b
                        else:
                            line_y_at_conn = y1
                        
                        # If lines are aligned, use connection Y; otherwise blend
                        if abs(line_y_at_conn - connection_y) < 5.0:  # Increased tolerance
                            surface_y = connection_y
                        else:
                            blend = max(0, 1.0 - dist_to_connection / endpoint_tolerance)
                            surface_y = surface_y * (1 - blend) + connection_y * blend
                
                # Check if player is on or above the line
                vertical_gap = surface_y - self.rect.bottom
                
                # Determine tolerance and max step based on line type
                tolerance_bottom = -2
                max_step = self.max_slope_step_down
                
                # CRITICAL: Much more generous for angled lines
                if is_angled:
                    tolerance_bottom = -35  # Very generous for angled lines (increased from -25)
                    max_step = self.max_slope_step_up + 15
                
                # More generous for current line
                if is_current_line:
                    tolerance_bottom = max(tolerance_bottom, -20)  # At least -20
                    max_step = max(max_step, self.max_slope_step_up)
                # Very generous for connected lines (smooth transitions)
                elif is_connected:
                    tolerance_bottom = max(tolerance_bottom, -25)
                    max_step = max(max_step, self.max_slope_step_up + 10)
                # Generous at connection points and endpoints
                elif at_connection or at_start or at_end:
                    tolerance_bottom = max(tolerance_bottom, -15)
                    max_step = max(max_step, self.max_slope_step_up)
                
                # Check if valid surface
                if tolerance_bottom <= vertical_gap <= max_step:
                    gap_abs = abs(vertical_gap)
                    
                    # NEW SCORING SYSTEM:
                    # Base priority
                    priority = 0
                    
                    # 1. Current line bonus
                    if is_current_line:
                        if strictly_within:
                            priority += 1000
                        else:
                            priority += 300 # Reduced bonus for extended segments
                    
                    # 2. Connected line bonus (high)
                    if is_connected:
                        priority += 500
                    
                    # 3. STRICTLY WITHIN BOUNDS bonus (Critical for preventing premature snaps)
                    if strictly_within:
                        priority += 200
                    
                    # 4. Angled line bonus (small, just to prefer slopes over flat if ambiguous)
                    if is_angled:
                        priority += 50
                    
                    valid_surfaces.append((surface_y, line, foot_x, gap_abs, priority, not strictly_within))
        
        # NEW MECHANISM: Select best line based on priority and coverage
        if not valid_surfaces:
            self.current_line_id = None
            return
        
        # Group surfaces by line
        line_surface_map = {}  # line_id -> list of (surface_y, foot_x, gap_abs, priority, is_extended)
        for surface_y, line, foot_x, gap_abs, priority, is_extended in valid_surfaces:
            line_id = id(line)
            if line_id not in line_surface_map:
                line_surface_map[line_id] = []
            line_surface_map[line_id].append((surface_y, foot_x, gap_abs, priority, is_extended))
        
        # Find the best line based on priority and coverage
        best_line_id = None
        best_score = -1
        best_line_obj = None
        
        for line_id, surfaces in line_surface_map.items():
            # Calculate score: priority (from surfaces) + coverage (number of probe points)
            # Priority is already in the surfaces, use the max priority
            max_priority = max(s[3] for s in surfaces)
            coverage = len(surfaces)
            
            # Bonus for having "strictly within" hits
            strict_hits = sum(1 for s in surfaces if not s[4]) # s[4] is is_extended
            
            score = max_priority + coverage * 10 + strict_hits * 20
            
            # Get the actual line object
            line_obj = None
            for line in self.collision_lines:
                if id(line) == line_id:
                    line_obj = line
                    break
            
            # Select line with highest score
            if score > best_score:
                best_score = score
                best_line_id = line_id
                best_line_obj = line_obj
            elif score == best_score and line_obj:
                # If same score, prefer current line if it exists
                if best_line_id == self.current_line_id:
                    # Keep current line
                    pass
                elif line_id == self.current_line_id:
                    # Switch to current line
                    best_line_id = line_id
                    best_line_obj = line_obj
        
        # Calculate the actual Y position on the best line at the player's center X
        if best_line_obj is not None:
            x1, y1 = best_line_obj["x1"], best_line_obj["y1"]
            x2, y2 = best_line_obj["x2"], best_line_obj["y2"]
            center_x = self.rect.centerx
            
            # Verify the player's X is within the line's bounds (with tolerance)
            line_min_x = min(x1, x2)
            line_max_x = max(x1, x2)
            line_min_y = min(y1, y2)
            line_max_y = max(y1, y2)
            
            # Extended bounds check - make sure we're actually on or near this line
            extended_min = line_min_x - 40
            extended_max = line_max_x + 40
            
            # Track if we're using connection Y (to prevent teleportation)
            use_connection_y = False
            
            if extended_min <= center_x <= extended_max:
                # Calculate Y using the line equation at the player's center X
                if abs(x2 - x1) > 0.001:
                    m = (y2 - y1) / (x2 - x1)
                    b = y1 - m * x1
                    # Clamp center_x to actual line bounds to prevent extrapolation
                    effective_center_x = max(line_min_x, min(line_max_x, center_x))
                    best_center_y = m * effective_center_x + b
                else:
                    # Horizontal line
                    best_center_y = y1
                
                # Check if we're at a connection point - but ONLY use connection Y if it's close to line Y
                for endpoint, line_ids in endpoint_to_line_ids.items():
                    if best_line_id in line_ids:
                        # Check if player is near this connection point
                        # INCREASED BLEND RANGE for smoother transitions
                        blend_range = 30.0 # Increased from 25.0
                        
                        if abs(center_x - endpoint[0]) < blend_range:
                            # Calculate line Y at connection point
                            if abs(x2 - x1) > 0.001:
                                line_y_at_conn = m * endpoint[0] + b
                            else:
                                line_y_at_conn = y1
                            
                            # Only use connection Y if it's very close to the line's Y at that point
                            # This prevents teleporting to positions where no line exists
                            if abs(line_y_at_conn - endpoint[1]) < 5.0:  # Increased tolerance
                                best_center_y = endpoint[1]
                                use_connection_y = True
                            elif abs(line_y_at_conn - endpoint[1]) < 20.0:  # Increased blend range
                                dist = abs(center_x - endpoint[0])
                                blend = max(0, 1.0 - dist / blend_range)
                                best_center_y = best_center_y * (1 - blend) + endpoint[1] * blend
                                use_connection_y = True
                            # If lines are not aligned, use the line's actual Y (don't teleport)
                            break
            else:
                # Player is outside line bounds - this shouldn't happen, but calculate Y anyway
                if abs(x2 - x1) > 0.001:
                    m = (y2 - y1) / (x2 - x1)
                    b = y1 - m * x1
                    effective_center_x = max(line_min_x, min(line_max_x, center_x))
                    best_center_y = m * effective_center_x + b
                else:
                    best_center_y = y1
            
            # Apply the best surface
            # For angled lines, allow smooth Y changes to follow the slope
            current_bottom = self.rect.bottom
            y_change = best_center_y - current_bottom
            
            # For angled lines, be more generous with Y changes to allow slope following
            is_angled = abs(y2 - y1) > 1.0 if abs(x2 - x1) > 0.001 else False
            is_current = (best_line_id == self.current_line_id)
            
            # If we're on the current line and it's angled, allow smooth Y changes
            # Calculate expected Y change based on horizontal movement
            if is_current and is_angled and abs(x2 - x1) > 0.001:
                # Calculate slope
                slope = (y2 - y1) / (x2 - x1)
                # Expected Y change based on player speed (max 3 pixels horizontal movement)
                expected_y_change = abs(slope) * self.speed
                # Allow reasonable Y changes for slope following (up to 2x expected)
                max_y_change = max(60, expected_y_change * 2 + 10)
            else:
                max_y_change = 50
            
            # Prevent teleportation: if Y change is too large and we're not smoothly transitioning
            # on the current line, it might be a glitch
            if abs(y_change) > max_y_change:
                if is_current and is_angled:
                    # On current angled line - allow the change (slope following)
                    pass
                elif use_connection_y:
                    # Using connection Y - verify it's reasonable
                    # If change is extremely large, it might be wrong
                    if abs(y_change) > 100:
                        # Too large even for connection - use line Y instead
                        if abs(x2 - x1) > 0.001:
                            m = (y2 - y1) / (x2 - x1)
                            b = y1 - m * x1
                            effective_center_x = max(line_min_x, min(line_max_x, center_x))
                            best_center_y = m * effective_center_x + b
                        else:
                            best_center_y = y1
                else:
                    # Not on current line and not at connection - clamp to prevent teleportation
                    best_center_y = current_bottom + (max_y_change if y_change > 0 else -max_y_change)
            
            self.rect.bottom = best_center_y
            self.vel_y = 0
            self.in_air = False
            # Track which line we're on for next frame
            self.current_line_id = best_line_id
        else:
            # Fallback: use the surface with highest priority, then smallest gap
            valid_surfaces.sort(key=lambda s: (-s[4], s[3], s[0]))  # Sort by priority (desc), gap, then Y
            if valid_surfaces:
                surface_y = valid_surfaces[0][0]
                # Clamp Y change
                current_bottom = self.rect.bottom
                y_change = surface_y - current_bottom
                max_y_change = 50
                if abs(y_change) > max_y_change:
                    surface_y = current_bottom + (max_y_change if y_change > 0 else -max_y_change)
                
                self.rect.bottom = surface_y
                self.vel_y = 0
                self.in_air = False
                # Track which line we're on
                self.current_line_id = id(valid_surfaces[0][1])
            else:
                # Not on any line
                self.current_line_id = None


    def shoot(self, projectile, isRotate, damage, hit_count):
        projectile_img = Projectile(self.rect.centerx + (0.6 * self.rect.size[0] * self.direction), self.rect.centery, self.direction, 300, isRotate, projectile, damage, hit_count)
        self.projectiles_group.add(projectile_img)
        self.play_sound("player", "attack")

    def handle_skill(self, skill):
        big_star_skill = Skill(self.rect.centerx + (0.6 * self.rect.size[0] * (self.direction * - 1)), self.rect.centery, self.direction, skill)
        self.skills_group.add(big_star_skill)




    def update_animation(self):
        #update animation
        # case of player idle
        if self.action == 0:
            animation_cooldown = 800
        # case of player jumps
        elif self.action == 1:
            animation_cooldown = 170
        # case of player walks
        elif self.action == 2:
            animation_cooldown = 50
        # case of big star skill
        elif self.action == 6:
            self.moving_left = False
            self.moving_right = False
            self.jump = False
            self.attack = False
            if not self.skill:
                self.handle_skill("big_star")
                self.play_sound("skills","big_star")
                self.skill = True
            # change to last frame to lower animation cooldown
            if self.frame_index == len(self.animation_list[self.action])-1:
                animation_cooldown = 100
            else:
                animation_cooldown = 700
            # case of player hit
        elif self.action == 7:
            animation_cooldown = 100
        # case of attacking while on ground
        elif self.action >= 3 and self.action <= 5 and not self.in_air:
            # case of player nearby mobs
            # if pygame.sprite.spritecollide(self, self.mobs, False):
            #     self.action = 8
            self.moving_left = False
            self.moving_right = False
            animation_cooldown = 150
        # case of attacking in air
        elif self.action >= 3 and self.action <= 5:
            animation_cooldown = 130
        #update image depending on current frame
        self.image = self.animation_list[self.action][self.frame_index]
        #check if enough time has passed since the last update
        if pygame.time.get_ticks() - self.update_time > animation_cooldown:
            self.update_time = pygame.time.get_ticks()
            self.frame_index += 1
            animation_cooldown = self.handle_attacks(len(self.animation_list[self.action]), self.frame_index)
        #if the animation has run out the reset back to the start
        if self.frame_index >= len(self.animation_list[self.action]):
            self.frame_index = 0

    def handle_attacks(self, frame_len, frame_index):
        if frame_index == frame_len-1:
            if self.attack:
                self.shoot("throwing_star", False, 25, 1)
            if self.skill_big_star:
                self.shoot("big_star", True, 25, 3)
        if frame_index == frame_len:
                self.skill = False
                self.skill_big_star = False
        if frame_index == frame_len and self.attack:
                self.attack = False
                self.next_attack = random.randint(3, 5) # To get a random attack (1-3)
                self.action = self.next_attack


            

    def update_action(self, new_action):
        #check if the new action is different to the previous one
        if new_action != self.action:
            self.action = new_action
            #update the animation settings
            self.frame_index = 0
            self.update_time = pygame.time.get_ticks()

    def hit(self, damage):
        if self.hit_cooldown <= 0:
            self.is_hit = True
            # self.update_action(7)
            self.health -= damage
            print(f"Player health: {self.health}")
            
    
    def check_alive(self):
        if self.health <= 0:
            self.health = 0
            self.alive = False
            self.update_action(4)


    def play_sound(self, dir_name, sound):
        soundObj = pygame.mixer.Sound(f'sprites/sounds/{dir_name}/{sound}.mp3')
        soundObj.play()
        
        
    def handle_cooldown(self):
        if self.flash_jump_cooldown > 0:
            self.flash_jump_cooldown -= 1
        if self.is_hit:
            if self.hit_cooldown >= 100:
                self.hit_cooldown = 0
                self.is_hit = False
            else:
                self.hit_cooldown += 1

    def draw(self, camera_x=0, camera_y=0):
        # Calculate screen position relative to camera
        screen_x = self.rect.x - camera_x
        screen_y = self.rect.y - camera_y
        if self.is_hit:
            if self.hit_cooldown%5:
                copy_of_image = self.image.copy()
                copy_of_image.fill((115, 115, 115, 240), special_flags=pygame.BLEND_RGBA_MULT)
                self.screen.blit(pygame.transform.flip(copy_of_image, self.flip, False), (screen_x, screen_y))
        else:
                self.screen.blit(pygame.transform.flip(self.image, self.flip, False), (screen_x, screen_y))