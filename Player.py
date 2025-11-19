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
                                    if line_min_x <= x_at_top <= line_max_x or line_min_x <= x_at_bottom <= line_max_x:
                                        self.rect.right = min(x_at_top, x_at_bottom) if m > 0 else max(x_at_top, x_at_bottom)
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
                                    
                                    if line_min_x <= x_at_top <= line_max_x or line_min_x <= x_at_bottom <= line_max_x:
                                        self.rect.left = max(x_at_top, x_at_bottom) if m > 0 else min(x_at_top, x_at_bottom)

    def _handle_line_vertical_collision(self, dy):
        """Handle vertical collision with lines (walkable surfaces)."""
        # Skip collision entirely when moving upward (jumping) - allow natural jump movement
        # Check both vel_y and dy to catch all jumping cases
        # This prevents the player from being snapped back to the ground when jumping on slopes
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
        
        # Collect all valid surface positions for each probe point
        valid_surfaces = []  # List of (surface_y, line, foot_x, gap_abs)
        
        # Build a map of connection points (endpoints that are shared by multiple lines)
        # Use a tolerance to group nearby endpoints together
        CONNECTION_TOLERANCE = 2.0  # Pixels - endpoints within this distance are considered the same point
        connection_groups = []  # List of (x, y, lines) where lines share this connection point
        
        # First, find all unique connection points by grouping nearby endpoints
        endpoint_lines = {}  # (rounded_x, rounded_y) -> list of (line, is_start)
        for line in self.collision_lines:
            x1, y1 = line["x1"], line["y1"]
            x2, y2 = line["x2"], line["y2"]
            if abs(x2 - x1) < 1:  # Skip vertical lines
                continue
            
            # Round endpoints to reduce floating point issues
            p1 = (round(x1), round(y1))
            p2 = (round(x2), round(y2))
            
            if p1 not in endpoint_lines:
                endpoint_lines[p1] = []
            if p2 not in endpoint_lines:
                endpoint_lines[p2] = []
            
            endpoint_lines[p1].append((line, True))  # True = is start point
            endpoint_lines[p2].append((line, False))  # False = is end point
        
        # Group nearby endpoints together
        processed_points = set()
        for (px, py), lines_list in endpoint_lines.items():
            if (px, py) in processed_points:
                continue
            
            # Find all nearby points and merge them
            group_lines = []
            group_x = px
            group_y = py
            group_points = [(px, py)]
            
            for (qx, qy), other_lines in endpoint_lines.items():
                if (qx, qy) in processed_points:
                    continue
                dist = ((qx - px)**2 + (qy - py)**2)**0.5
                if dist <= CONNECTION_TOLERANCE:
                    group_points.append((qx, qy))
                    group_lines.extend(other_lines)
                    # Use average position for the connection point
                    group_x = (group_x + qx) / 2
                    group_y = (group_y + qy) / 2
            
            # Only add if multiple lines share this point (it's a connection)
            if len(group_lines) > 1:
                unique_lines = []
                seen_line_ids = set()
                for line, _ in group_lines:
                    line_id = id(line)
                    if line_id not in seen_line_ids:
                        unique_lines.append(line)
                        seen_line_ids.add(line_id)
                if len(unique_lines) > 1:
                    connection_groups.append((group_x, group_y, unique_lines))
            
            for pt in group_points:
                processed_points.add(pt)
        
        for foot_x in probe_points:
            # Check ALL lines
            for line in self.collision_lines:
                x1, y1 = line["x1"], line["y1"]
                x2, y2 = line["x2"], line["y2"]
                
                # Skip vertical lines (they're barriers, not walkable)
                if abs(x2 - x1) < 1:
                    continue
                
                line_min_x = min(x1, x2)
                line_max_x = max(x1, x2)
                
                # Check if we're at a connection point
                at_connection = False
                connection_y = None
                connection_x = None
                tolerance = 5.0  # Increased tolerance for connection detection
                
                # Check if foot_x is near any connection point
                for cx, cy, lines in connection_groups:
                    if line in lines and abs(foot_x - cx) < tolerance:
                        # We're at a connection point
                        at_connection = True
                        # Always use the connection point's Y for consistency across all connected lines
                        # This prevents teleportation when transitioning between connected lines
                        connection_y = cy
                        connection_x = cx
                        break
                
                # Check if foot_x is within line bounds or at endpoints
                # For connected lines, be more generous with bounds to handle angled connections
                within_bounds = line_min_x <= foot_x <= line_max_x
                at_start = abs(foot_x - line_min_x) < tolerance
                at_end = abs(foot_x - line_max_x) < tolerance
                
                # If at a connection point, extend bounds significantly to catch the transition
                if at_connection:
                    # Extend bounds much more at connection points to handle angled connections
                    extended_min = line_min_x - 20
                    extended_max = line_max_x + 20
                    within_bounds = extended_min <= foot_x <= extended_max
                    # Also increase tolerance at endpoints when at connection
                    at_start = abs(foot_x - line_min_x) < tolerance + 20
                    at_end = abs(foot_x - line_max_x) < tolerance + 20
                
                # If player is already on this line, be VERY generous to keep them on diagonal lines
                is_current_line = (self.current_line_id == id(line))
                if is_current_line:
                    # Extend bounds significantly to keep player on the line
                    # This is critical for diagonal lines where player moves horizontally
                    extended_min = line_min_x - 20
                    extended_max = line_max_x + 20
                    within_bounds = extended_min <= foot_x <= extended_max
                    # Also increase tolerance at endpoints when on current line
                    at_start = abs(foot_x - line_min_x) < tolerance + 20
                    at_end = abs(foot_x - line_max_x) < tolerance + 20
                
                # Also check if this line is connected to the current line - extend bounds for smooth transition
                if self.current_line_id is not None:
                    current_line = None
                    for l in self.collision_lines:
                        if id(l) == self.current_line_id:
                            current_line = l
                            break
                    if current_line:
                        cx1, cy1 = current_line["x1"], current_line["y1"]
                        cx2, cy2 = current_line["x2"], current_line["y2"]
                        # Check if lines share an endpoint (with tolerance)
                        endpoint_tolerance = 3.0
                        is_connected = (abs(x1 - cx1) < endpoint_tolerance and abs(y1 - cy1) < endpoint_tolerance) or \
                                      (abs(x1 - cx2) < endpoint_tolerance and abs(y1 - cy2) < endpoint_tolerance) or \
                                      (abs(x2 - cx1) < endpoint_tolerance and abs(y2 - cy1) < endpoint_tolerance) or \
                                      (abs(x2 - cx2) < endpoint_tolerance and abs(y2 - cy2) < endpoint_tolerance)
                        if is_connected:
                            # Extend bounds for connected lines to ensure smooth transition
                            extended_min = line_min_x - 25
                            extended_max = line_max_x + 25
                            within_bounds = extended_min <= foot_x <= extended_max
                            at_start = abs(foot_x - line_min_x) < tolerance + 25
                            at_end = abs(foot_x - line_max_x) < tolerance + 25
                
                if not (within_bounds or at_start or at_end or at_connection):
                    continue
                
                # Calculate Y position on line for this X
                # Always calculate the line's Y first
                if abs(x2 - x1) > 0.001:
                    m = (y2 - y1) / (x2 - x1)
                    b = y1 - m * x1
                    surface_y = m * foot_x + b
                else:
                    # Horizontal line
                    surface_y = y1
                
                # At a connection point, we need to handle angled connections carefully
                if at_connection and connection_y is not None and connection_x is not None:
                    # Calculate what the line's Y would be at the connection point
                    if abs(x2 - x1) > 0.001:
                        m = (y2 - y1) / (x2 - x1)
                        b = y1 - m * x1
                        line_y_at_connection = m * connection_x + b
                    else:
                        line_y_at_connection = y1
                    
                    # If we're very close to the connection point X, use connection point Y
                    # This ensures smooth transitions between connected lines
                    if abs(foot_x - connection_x) < 5.0:
                        # Check if the line's Y at connection is close to the connection point Y
                        # If they're aligned (within 3 pixels), use connection point Y for consistency
                        if abs(line_y_at_connection - connection_y) < 3.0:
                            surface_y = connection_y
                        # Otherwise, use the line's calculated Y (for angled connections)
                        # But blend towards connection point Y to prevent gaps
                        else:
                            # Blend between line Y and connection Y based on distance from connection point
                            blend_factor = max(0, 1.0 - abs(foot_x - connection_x) / 5.0)
                            surface_y = surface_y * (1 - blend_factor) + connection_y * blend_factor
                    # If we're further from connection point, use the line's normal Y
                    # (surface_y already calculated above)
                
                # Check if player is on or above the line
                vertical_gap = surface_y - self.rect.bottom
                
                # Determine max step range and tolerance
                # Start with defaults
                max_step = self.max_slope_step_down
                tolerance_bottom = -2
                
                # Check if connected to current line
                is_connected_to_current = False
                if self.current_line_id is not None:
                    current_line = None
                    for l in self.collision_lines:
                        if id(l) == self.current_line_id:
                            current_line = l
                            break
                    if current_line:
                        cx1, cy1 = current_line["x1"], current_line["y1"]
                        cx2, cy2 = current_line["x2"], current_line["y2"]
                        endpoint_tolerance = 3.0
                        is_connected_to_current = (abs(x1 - cx1) < endpoint_tolerance and abs(y1 - cy1) < endpoint_tolerance) or \
                                                  (abs(x1 - cx2) < endpoint_tolerance and abs(y1 - cy2) < endpoint_tolerance) or \
                                                  (abs(x2 - cx1) < endpoint_tolerance and abs(y2 - cy1) < endpoint_tolerance) or \
                                                  (abs(x2 - cx2) < endpoint_tolerance and abs(y2 - cy2) < endpoint_tolerance)
                
                # Be generous at connection points and endpoints
                if at_connection or at_start or at_end:
                    max_step = self.max_slope_step_up
                    tolerance_bottom = -15  # Very generous for connection points
                
                # Be even more generous for connected lines (angled connections)
                if is_connected_to_current or at_connection:
                    max_step = max(max_step, self.max_slope_step_up + 10)
                    tolerance_bottom = -15
                
                # If already on a line, allow much larger range to stay on it
                if self.current_line_id is not None:
                    tolerance_bottom = -10
                    if is_current_line:
                        max_step = max(max_step, self.max_slope_step_up)
                        tolerance_bottom = -15
                
                if tolerance_bottom <= vertical_gap <= max_step:
                    gap_abs = abs(vertical_gap)
                    valid_surfaces.append((surface_y, line, foot_x, gap_abs))
        
        # Final safety check: if no surfaces found, check if player is near any connection point
        # and force-check all lines at that connection point
        if not valid_surfaces:
            center_x = self.rect.centerx
            # Find all connection points near the player
            for cx, cy, lines in connection_groups:
                # Be more generous with connection point detection
                if abs(center_x - cx) < 25:  # Player is near this connection point
                    # Check ALL lines at this connection point
                    for line in lines:
                        x1, y1 = line["x1"], line["y1"]
                        x2, y2 = line["x2"], line["y2"]
                        if abs(x2 - x1) < 1:  # Skip vertical
                            continue
                        
                        line_min_x = min(x1, x2)
                        line_max_x = max(x1, x2)
                        
                        # Extend bounds significantly for connection point check
                        extended_min = line_min_x - 30
                        extended_max = line_max_x + 30
                        
                        # Check if any probe point is within extended bounds
                        for foot_x in probe_points:
                            if extended_min <= foot_x <= extended_max or abs(foot_x - cx) < 25:
                                # Calculate Y on the line at this probe point
                                if abs(x2 - x1) > 0.001:
                                    m = (y2 - y1) / (x2 - x1)
                                    b = y1 - m * x1
                                    surface_y = m * foot_x + b
                                else:
                                    surface_y = y1
                                
                                # At connection point, use connection Y if close
                                if abs(foot_x - cx) < 10:
                                    # Blend connection Y with line Y
                                    if abs(x2 - x1) > 0.001:
                                        m = (y2 - y1) / (x2 - x1)
                                        b = y1 - m * x1
                                        line_y_at_conn = m * cx + b
                                    else:
                                        line_y_at_conn = y1
                                    
                                    if abs(line_y_at_conn - cy) < 5.0:
                                        surface_y = cy
                                    else:
                                        # Blend for angled connections
                                        blend = max(0, 1.0 - abs(foot_x - cx) / 10.0)
                                        surface_y = surface_y * (1 - blend) + cy * blend
                                
                                vertical_gap = surface_y - self.rect.bottom
                                # Very generous range at connection points
                                if -10 <= vertical_gap <= self.max_slope_step_up:
                                    gap_abs = abs(vertical_gap)
                                    valid_surfaces.append((surface_y, line, foot_x, gap_abs))
                    break  # Found connection point, no need to check others
        
        if not valid_surfaces:
            self.current_line_id = None
            return
        
        # Group surfaces by line to find which line covers the most probe points
        line_surface_map = {}  # line_id -> list of (surface_y, foot_x, gap_abs)
        for surface_y, line, foot_x, gap_abs in valid_surfaces:
            line_id = id(line)
            if line_id not in line_surface_map:
                line_surface_map[line_id] = []
            line_surface_map[line_id].append((surface_y, foot_x, gap_abs))
        
        # Find line that covers the most probe points (most stable for connected lines)
        # Also track which line the player is currently on to ensure smooth transitions
        best_line_id = None
        max_coverage = 0
        max_effective_coverage = 0
        best_center_y = None
        best_avg_gap = None
        
        # Try to find the line the player is currently on (for smooth transitions)
        current_line_id = self.current_line_id
        if not self.in_air and current_line_id is not None:
            # Check which line the player's center is on
            center_x = self.rect.centerx
            for surface_y, line, foot_x, gap_abs in valid_surfaces:
                if id(line) == current_line_id:
                    x1, y1 = line["x1"], line["y1"]
                    x2, y2 = line["x2"], line["y2"]
                    line_min_x = min(x1, x2)
                    line_max_x = max(x1, x2)
                    if line_min_x - 10 <= center_x <= line_max_x + 10:
                        if abs(surface_y - self.rect.bottom) < 10:  # Close to player's feet
                            current_line_id = id(line)
                            break
        
        for line_id, surfaces in line_surface_map.items():
            coverage = len(surfaces)
            # Find the surface Y for the center probe point
            center_y = None
            avg_gap = sum(s[2] for s in surfaces) / len(surfaces)
            
            # Get the line object for this line_id
            current_check_line = None
            for l in self.collision_lines:
                if id(l) == line_id:
                    current_check_line = l
                    break
            
            for surface_y, foot_x, gap_abs in surfaces:
                if abs(foot_x - self.rect.centerx) < 2:
                    center_y = surface_y
                    break
            
            # If no center match, use average
            if center_y is None:
                center_y = sum(s[0] for s in surfaces) / len(surfaces)
            
            # Prefer the line the player is currently on (for smooth transitions)
            is_current_line = (line_id == current_line_id)
            
            # Check if this line is connected to current line
            is_connected_to_current = False
            if current_line_id is not None and current_check_line:
                current_line = None
                for l in self.collision_lines:
                    if id(l) == current_line_id:
                        current_line = l
                        break
                if current_line:
                    cx1, cy1 = current_line["x1"], current_line["y1"]
                    cx2, cy2 = current_line["x2"], current_line["y2"]
                    lx1, ly1 = current_check_line["x1"], current_check_line["y1"]
                    lx2, ly2 = current_check_line["x2"], current_check_line["y2"]
                    # Check if lines share an endpoint (with tolerance)
                    endpoint_tolerance = 2.0
                    if (abs(lx1 - cx1) < endpoint_tolerance and abs(ly1 - cy1) < endpoint_tolerance) or \
                       (abs(lx1 - cx2) < endpoint_tolerance and abs(ly1 - cy2) < endpoint_tolerance) or \
                       (abs(lx2 - cx1) < endpoint_tolerance and abs(ly2 - cy1) < endpoint_tolerance) or \
                       (abs(lx2 - cx2) < endpoint_tolerance and abs(ly2 - cy2) < endpoint_tolerance):
                        is_connected_to_current = True
            
            # Prefer lines that cover more probe points (more stable)
            # But prioritize current line and connected lines MUCH more strongly
            priority = 0
            if is_current_line:
                priority = 10000  # Very high priority - stay on current line to prevent teleportation
            elif is_connected_to_current:
                priority = 1000   # High priority - connected lines
            
            # Use priority + coverage for comparison
            effective_coverage = coverage + priority
            
            if effective_coverage > max_effective_coverage:
                max_effective_coverage = effective_coverage
                max_coverage = coverage  # Track actual coverage too
                best_line_id = line_id
                best_center_y = center_y
                best_avg_gap = avg_gap
            elif effective_coverage == max_effective_coverage:
                # If same effective coverage, prefer current line, then smaller gap
                if is_current_line:
                    best_line_id = line_id
                    best_center_y = center_y
                    best_avg_gap = avg_gap
                elif best_avg_gap is None or avg_gap < best_avg_gap or (abs(avg_gap - best_avg_gap) < 0.1 and center_y < best_center_y):
                    best_line_id = line_id
                    best_center_y = center_y
                    best_avg_gap = avg_gap
        
        # Use the best line's center Y position for smooth transitions
        if best_center_y is not None:
            # Clamp the Y change to prevent large teleportations
            current_bottom = self.rect.bottom
            y_change = best_center_y - current_bottom
            max_y_change = 30  # Maximum allowed Y change per frame to prevent teleportation
            if abs(y_change) > max_y_change:
                # If change is too large, it might be a glitch - use a smaller change
                best_center_y = current_bottom + (max_y_change if y_change > 0 else -max_y_change)
            
            self.rect.bottom = best_center_y
            self.vel_y = 0
            self.in_air = False
            # Track which line we're on for next frame
            self.current_line_id = best_line_id
        else:
            # Fallback: use the surface with smallest gap
            valid_surfaces.sort(key=lambda s: (s[3], s[0]))  # Sort by gap, then by Y
            if valid_surfaces:
                surface_y = valid_surfaces[0][0]
                # Clamp Y change here too
                current_bottom = self.rect.bottom
                y_change = surface_y - current_bottom
                max_y_change = 30
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
 


