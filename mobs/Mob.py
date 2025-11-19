import pygame
import os
import random
from entities.HealthBar import HealthBar

FLOOR = 465


class Mob(pygame.sprite.Sprite):
    def __init__(self, screen, players, tiles, slope_tiles=None, collision_lines=None, mob_name=None, x=0, y=0, scale=1, speed=1, health=150, map_bounds=None):
        pygame.sprite.Sprite.__init__(self)
        self.screen = screen
        self.alive = True
        self.mob_name = mob_name
        self.speed = speed
        self.players = players
        # list of pygame.Rect for solid tiles / platforms (legacy, may be empty if using lines)
        self.tiles = tiles
        self.slope_tiles = slope_tiles or []
        self.collision_lines = collision_lines or []
        self.max_slope_step_up = 60
        self.max_slope_step_down = 25
        self.current_line_id = None  # Track which line the mob is currently on for smooth transitions
        # Map boundaries: (min_x, max_x, min_y, max_y) - None means no boundaries
        self.map_bounds = map_bounds
        self.direction = -1
        self.max_health = health
        self.health = health
        self.radius = 125
        self.vel_y = 0
        self.GRAVITY = 7.5
        self.vel_x = 0
        self.attacker = ""
        self.alpha = 255
        # Booleans
        self.is_idle = False
        self.has_attacker = False
        self.is_hit = False
        self.jump = False
        self.in_air = True
        self.flip = False
        self.fade = False
        # Movement
        self.moving_left = True
        self.moving_right = False
        self.randomMovement = True
        self.spawn_x = x
        # Patrol radius (how far left/right from spawn the mob is allowed to wander)
        self.patrol_radius = 150
        self.moveRange = random.randint(100, 500)
        # Cool downs
        self.idle_cooldown = 0
        # Animation
        self.animation_list = []
        self.next_attack = 3
        self.frame_index = 0
        self.action = 0
        self.update_time = pygame.time.get_ticks()
        
        #load all images for the players
        animation_types = ['stand', 'walk', 'jump', 'hit', 'die']

        for animation in animation_types:
            temp_list = []
            anim_path = f'sprites/mobs/{self.mob_name}/{animation}'

            # If the folder doesn't exist, use the first animation (stand) as fallback
            if not os.path.exists(anim_path):
                print(f"[WARNING] Missing animation '{animation}' for mob '{self.mob_name}'. Using fallback.")
                temp_list = self.animation_list[0] if self.animation_list else []
                self.animation_list.append(temp_list)
                continue

            num_of_frames = len(os.listdir(anim_path))
            for i in range(num_of_frames):
                img = pygame.image.load(f'{anim_path}/{i}.png')
                img = pygame.transform.scale(img, (int(img.get_width() * scale), int(img.get_height() * scale)))
                temp_list.append(img)

            self.animation_list.append(temp_list)

        self.image = self.animation_list[self.action][self.frame_index]
        self.rect = self.image.get_rect()
        self.rect.center = (x, y)
        self.health_bar = HealthBar(self, screen, "red")



    def update(self, camera_x=0, camera_y=0):
        self.health_bar.update(camera_x, camera_y)
        self.update_animation()
        self.check_alive()
        self.handle_movement()
    
    def handle_movement(self):
        if self.alive and not self.is_hit and not self.has_attacker:
            self.move(self.GRAVITY)
            if self.randomMovement:
                if self.moveRange <= 0:

                    # 40% for mob to be idle after finishing its 
                    if random.random() < 0.4 and not self.has_attacker:
                        self.is_idle = True
                        self.update_action(0)
                        self.moving_left = False
                        self.moving_right = False
                        if self.is_idle and self.idle_cooldown <= 200:
                            self.idle_cooldown += 1
                        elif self.idle_cooldown >= 200:
                            self.idle_cooldown = 0
                            self.is_idle = False


                    # If mob is not idle calculate a new route
                    if not self.is_idle:
                        self.moveRange = random.randint(100, 500)
                        if self.moving_left:
                            self.moving_left = False
                            self.moving_right = True
                        elif self.moving_right:
                            self.moving_right = False
                            self.moving_left = True
                        else:
                            # If there is no direction defined than define one.
                            if random.random() < 0.5:
                                self.moving_left = True
                            else:
                                self.moving_right = True
                        self.update_action(1)
                        # If range is not 0 keep sub from the range
                else:
                    self.update_action(1)
                    self.moveRange -= 1
            # Checks if a player gets nearby in radius of 125 so it can chase him
            for player in self.players:
                #Radius set to 125   
                if pygame.sprite.collide_circle(self, player):
                    self.follow_player(player)
                else: 
                    self.randomMovement = True
        elif self.has_attacker and not self.is_hit and self.alive:
            self.move(self.GRAVITY)
            self.follow_player(self.attacker)


    def follow_player(self, player):
        self.attack()
        self.randomMovement = False
        #If player in the right
        if player.rect.x >= self.rect.x:
            self.update_action(1)
            self.moving_right = True
            self.moving_left = False
        #If player in the left
        elif player.rect.x <= self.rect.x:
            self.update_action(1)
            self.moving_left = True
            self.moving_right = False
        


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



        #jump
        if self.jump == True and self.in_air == False:
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
            
            # Clamp horizontal position within patrol radius
            min_x = self.spawn_x - self.patrol_radius
            max_x = self.spawn_x + self.patrol_radius
            if self.rect.centerx < min_x:
                self.rect.centerx = min_x
                self.moving_left = False
                self.moving_right = True
            elif self.rect.centerx > max_x:
                self.rect.centerx = max_x
                self.moving_right = False
                self.moving_left = True
            
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

            # Clamp horizontal position within patrol radius
            min_x = self.spawn_x - self.patrol_radius
            max_x = self.spawn_x + self.patrol_radius
            if self.rect.centerx < min_x:
                self.rect.centerx = min_x
                self.moving_left = False
                self.moving_right = True
            elif self.rect.centerx > max_x:
                self.rect.centerx = max_x
                self.moving_right = False
                self.moving_left = True

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

        if self.slope_tiles:
            self._handle_slope_collision()

        # Clamp mob to map boundaries if provided
        if self.map_bounds:
            map_min_x, map_max_x, map_min_y, map_max_y = self.map_bounds
            # Horizontal boundaries
            if self.rect.left < map_min_x:
                self.rect.left = map_min_x
                self.moving_left = False
                self.moving_right = True
            if self.rect.right > map_max_x:
                self.rect.right = map_max_x
                self.moving_right = False
                self.moving_left = True
            # Vertical boundaries (only clamp bottom, allow going above map top)
            if self.rect.bottom > map_max_y:
                self.rect.bottom = map_max_y
                self.vel_y = 0
                self.in_air = False

    def _handle_slope_collision(self):
        padding = min(12, max(2, self.rect.width // 6))
        probe_points = (
            self.rect.left + padding,
            self.rect.centerx,
            self.rect.right - padding,
        )
        candidate_y = None
        smallest_gap = None

        for foot_x in probe_points:
            for slope in self.slope_tiles:
                rect = slope['rect']
                if foot_x < rect.left or foot_x >= rect.right:
                    continue
                if self.rect.bottom < rect.top - self.max_slope_step_up:
                    continue
                if self.rect.top > rect.bottom:
                    continue

                surface_y = self._get_slope_surface_y(slope, foot_x)
                if surface_y is None:
                    continue

                vertical_gap = surface_y - self.rect.bottom
                if -self.max_slope_step_up <= vertical_gap <= self.max_slope_step_down:
                    gap_abs = abs(vertical_gap)
                    if (
                        smallest_gap is None
                        or gap_abs < smallest_gap
                        or (gap_abs == smallest_gap and surface_y < candidate_y)
                    ):
                        candidate_y = surface_y
                        smallest_gap = gap_abs

        if candidate_y is not None:
            self.rect.bottom = candidate_y
            self.vel_y = 0
            self.in_air = False

    def _get_slope_surface_y(self, slope, world_x):
        rect = slope['rect']
        local_x = int(world_x - rect.left)
        columns = slope.get('column_tops')
        if not columns or local_x < 0 or local_x >= len(columns):
            return None

        if columns[local_x] is not None:
            return columns[local_x]

        max_offset = len(columns)
        for offset in range(1, max_offset):
            left_idx = local_x - offset
            right_idx = local_x + offset
            if left_idx >= 0 and columns[left_idx] is not None:
                return columns[left_idx]
            if right_idx < len(columns) and columns[right_idx] is not None:
                return columns[right_idx]
        return None

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
            
            # Check if line is in mob's horizontal range
            if line_max_x < self.rect.left or line_min_x > self.rect.right:
                continue
            
            # For vertical lines, check direct collision
            if abs(x2 - x1) < 1:  # Essentially vertical
                line_x = x1
                # Only block if line is actually in the mob's vertical range
                if line_max_y >= self.rect.top and line_min_y <= self.rect.bottom:
                    if dx > 0 and self.rect.right >= line_x and self.rect.right - dx < line_x:
                        self.rect.right = line_x
                    elif dx < 0 and self.rect.left <= line_x and self.rect.left - dx > line_x:
                        self.rect.left = line_x
            else:
                # Diagonal line - only treat as barrier if mob is NOT standing on it
                # Check if mob's feet are on this line (if so, it's walkable, not a barrier)
                if abs(x2 - x1) > 0.001:
                    m = (y2 - y1) / (x2 - x1)
                    b = y1 - m * x1
                    
                    # Check if mob is standing on this line
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
                            # Check if mob's feet are on or very close to the line
                            if abs(surface_y - self.rect.bottom) <= self.max_slope_step_down + 5:
                                is_standing_on = True
                                break
                    
                    # If mob is standing on this line, skip it (it's a walkable surface)
                    if is_standing_on:
                        continue
                    
                    # Otherwise, treat as barrier - check if mob would intersect with it
                    # Check if line is in mob's vertical range
                    if line_max_y < self.rect.top or line_min_y > self.rect.bottom:
                        continue
                    
                    # Check if mob's left/right edge would cross the line
                    if dx > 0:  # Moving right
                        test_x = self.rect.right
                        test_y = m * test_x + b
                        if line_min_x <= test_x <= line_max_x and line_min_y <= test_y <= line_max_y:
                            if self.rect.top <= test_y <= self.rect.bottom:
                                if abs(m) > 0.001:
                                    y_at_top = self.rect.top
                                    x_at_top = (y_at_top - b) / m
                                    y_at_bottom = self.rect.bottom
                                    x_at_bottom = (y_at_bottom - b) / m
                                    
                                    if line_min_x <= x_at_top <= line_max_x or line_min_x <= x_at_bottom <= line_max_x:
                                        self.rect.right = min(x_at_top, x_at_bottom) if m > 0 else max(x_at_top, x_at_bottom)
                    elif dx < 0:  # Moving left
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
        # This prevents the mob from being snapped back to the ground when jumping on slopes
        if self.vel_y < 0 or dy < 0:  # Moving upward (jumping) - check both velocity and movement
            # Clear current line tracking when jumping
            self.current_line_id = None
            return
        
        # Check if mob's feet are on a line
        padding = min(12, max(2, self.rect.width // 6))
        probe_points = [
            self.rect.left + padding,
            self.rect.centerx,
            self.rect.right - padding,
        ]
        
        # Collect all valid surface positions for each probe point
        valid_surfaces = []  # List of (surface_y, line, foot_x, gap_abs)
        
        for foot_x in probe_points:
            for line in self.collision_lines:
                x1, y1 = line["x1"], line["y1"]
                x2, y2 = line["x2"], line["y2"]
                
                # Skip vertical lines (they're barriers, not walkable)
                if abs(x2 - x1) < 1:
                    continue
                
                # Check if foot_x is within line's x range
                line_min_x = min(x1, x2)
                line_max_x = max(x1, x2)
                
                # For connected lines, allow checking at exact endpoints with small tolerance
                # This ensures smooth transitions at connection points
                tolerance = 0.1  # Small tolerance for floating point precision
                if foot_x < line_min_x - tolerance or foot_x > line_max_x + tolerance:
                    continue
                
                # Clamp foot_x to line bounds to handle endpoints correctly
                clamped_x = max(line_min_x, min(line_max_x, foot_x))
                
                # Calculate Y position on line for this X
                if abs(x2 - x1) > 0.001:
                    m = (y2 - y1) / (x2 - x1)
                    b = y1 - m * x1
                    surface_y = m * clamped_x + b
                else:
                    # Horizontal line
                    surface_y = y1
                
                # Check if mob is on or above the line
                vertical_gap = surface_y - self.rect.bottom
                # Allow collision if:
                # 1. Mob is above the line (gap > 0) and within step-down range (falling onto it)
                # 2. Mob is on or slightly below the line (gap <= small threshold) to prevent falling through
                # This prevents teleporting upward when touching lines from below, but allows staying on lines
                if -2 <= vertical_gap <= self.max_slope_step_down:
                    gap_abs = abs(vertical_gap)
                    valid_surfaces.append((surface_y, line, foot_x, gap_abs))
        
        if not valid_surfaces:
            return
        
        # Group surfaces by line to find which line covers the most probe points
        line_surface_map = {}  # line_id -> list of (surface_y, foot_x, gap_abs)
        for surface_y, line, foot_x, gap_abs in valid_surfaces:
            line_id = id(line)
            if line_id not in line_surface_map:
                line_surface_map[line_id] = []
            line_surface_map[line_id].append((surface_y, foot_x, gap_abs))
        
        # Find line that covers the most probe points (most stable for connected lines)
        # Also track which line the mob is currently on to ensure smooth transitions
        best_line_id = None
        max_coverage = 0
        best_center_y = None
        best_avg_gap = None
        
        # Try to find the line the mob is currently on (for smooth transitions)
        current_line_id = self.current_line_id
        if not self.in_air:
            # Check which line the mob's center is on
            center_x = self.rect.centerx
            for surface_y, line, foot_x, gap_abs in valid_surfaces:
                if abs(foot_x - center_x) < 5:  # Close to center
                    x1, y1 = line["x1"], line["y1"]
                    x2, y2 = line["x2"], line["y2"]
                    line_min_x = min(x1, x2)
                    line_max_x = max(x1, x2)
                    if line_min_x <= center_x <= line_max_x:
                        if abs(surface_y - self.rect.bottom) < 5:  # Very close to mob's feet
                            current_line_id = id(line)
                            break
        
        for line_id, surfaces in line_surface_map.items():
            coverage = len(surfaces)
            # Find the surface Y for the center probe point
            center_y = None
            avg_gap = sum(s[2] for s in surfaces) / len(surfaces)
            
            for surface_y, foot_x, gap_abs in surfaces:
                if abs(foot_x - self.rect.centerx) < 1:
                    center_y = surface_y
                    break
            
            # If no center match, use average
            if center_y is None:
                center_y = sum(s[0] for s in surfaces) / len(surfaces)
            
            # Prefer the line the mob is currently on (for smooth transitions)
            is_current_line = (line_id == current_line_id)
            
            # Prefer lines that cover more probe points (more stable)
            if coverage > max_coverage:
                max_coverage = coverage
                best_line_id = line_id
                best_center_y = center_y
                best_avg_gap = avg_gap
            elif coverage == max_coverage:
                # If same coverage, prefer current line first, then smaller gap
                if is_current_line and best_line_id != current_line_id:
                    # Switch to current line for smooth transition
                    best_line_id = line_id
                    best_center_y = center_y
                    best_avg_gap = avg_gap
                elif best_avg_gap is None or avg_gap < best_avg_gap or (abs(avg_gap - best_avg_gap) < 0.1 and center_y < best_center_y):
                    if not (best_line_id == current_line_id and not is_current_line):
                        # Don't switch away from current line unless new line is clearly better
                        best_line_id = line_id
                        best_center_y = center_y
                        best_avg_gap = avg_gap
        
        # Use the best line's center Y position for smooth transitions
        if best_center_y is not None:
            self.rect.bottom = best_center_y
            self.vel_y = 0
            self.in_air = False
            # Track which line we're on for next frame
            self.current_line_id = best_line_id
        else:
            # Fallback: use the surface with smallest gap
            valid_surfaces.sort(key=lambda s: (s[3], s[0]))  # Sort by gap, then by Y
            if valid_surfaces:
                self.rect.bottom = valid_surfaces[0][0]
                self.vel_y = 0
                self.in_air = False
                # Track which line we're on
                self.current_line_id = id(valid_surfaces[0][1])
            else:
                # Not on any line
                self.current_line_id = None


    def update_animation(self):
        #update animation
        # case of mob idle
        if self.action == 0:
            animation_cooldown = 300
        # case of mob walk
        elif self.action == 1:
            animation_cooldown = 170
        # case of mob jump
        elif self.action == 2:
            animation_cooldown = 50
        # case of mob hit
        elif self.action == 3:
            self.is_hit = True
            self.moving_right = False
            self.moving_left = False
            animation_cooldown = 800
        # case of mob die
        elif self.action == 4:
            if self.fade:
                animation_cooldown = 10
            else:
                animation_cooldown = 150
        # case of attacking while on ground
        self.image = self.animation_list[self.action][self.frame_index]
        #check if enough time has passed since the last update
        if pygame.time.get_ticks() - self.update_time > animation_cooldown:
            self.update_time = pygame.time.get_ticks()
            self.frame_index += 1
        #if the animation has run out the reset back to the start
        if self.frame_index >= len(self.animation_list[self.action]):
            if self.action == 3:
                self.is_hit = False
            if self.action == 4:  
                self.fade = True
                self.frame_index = (int)(len(self.animation_list[self.action])) - 1
                self.alpha = max(0, self.alpha-5)  # alpha should never be < 0.
                self.image.fill((255, 255, 255, self.alpha), special_flags=pygame.BLEND_RGBA_MULT)
                if self.alpha <= 0:  # Kill the sprite when the alpha is <= 0.
                    self.kill()
            else:
                self.frame_index = 0

    
    def check_alive(self):
        if self.health <= 0:
            self.health = 0
            self.alive = False
            self.update_action(4)



    def hit(self, damage, player):
        self.has_attacker = True
        self.health -= damage
        self.attacker = player
        self.play_sound("mob","hit")
        self.update_action(3)

    
    def attack(self):
        for player in self.players:  
            if pygame.sprite.collide_mask(self, player):
                    player.hit(5)
                    


    def update_action(self, new_action):
        #check if the new action is different to the previous one
        if new_action != self.action:
            self.action = new_action
            #update the animation settings
            self.frame_index = 0
            self.update_time = pygame.time.get_ticks()


    def draw(self, camera_x=0, camera_y=0):
        # Calculate screen position relative to camera
        screen_x = self.rect.x - camera_x
        screen_y = self.rect.y - camera_y
        self.screen.blit(pygame.transform.flip(self.image, self.flip, False), (screen_x, screen_y))


    def play_sound(self, dir_name, sound):
        soundObj = pygame.mixer.Sound(f'sprites/sounds/{dir_name}/{sound}.mp3')
        soundObj.play()
