import pygame
import random
import os
from skills.Skill import Skill
from skills.Projectile import Projectile
from entities.HealthBar import HealthBar


class Player(pygame.sprite.Sprite):
    def __init__(self, screen, char_type, x, y, scale, speed, health, mobs=None, tiles=None, slope_tiles=None, lines=None, map_bounds=None):
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
        self.mobs = mobs or pygame.sprite.Group()
        # list of pygame.Rect for solid tiles / platforms
        self.tiles = tiles or []
        self.slope_tiles = slope_tiles or []
        self.lines = lines or []
        self.current_floor = None
        self.max_slope_step_up = 60
        self.max_slope_step_down = 25
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
        print(f"DEBUG: os.listdir is {os.listdir}")
        animation_types = ['stand', 'walk', 'jump', 'attack1', 'attack2', 'attack3', 'attack_big_star', 'hit', 'stab']
        for animation in animation_types:
            #reset temporary list of images
            temp_list = []
            #count number of files in the folder
            num_of_frames = len(os.listdir(f'sprites/{self.char_type}/Thief/{animation}'))
            for i in range(num_of_frames):
                img = pygame.image.load(f'sprites/{self.char_type}/Thief/{animation}/{i}.png').convert_alpha()
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

        # --- Line Collision Logic ---
        
        # Horizontal movement
        self.rect.x += dx
        
        # Check wall collisions
        for line in self.lines:
            if line.get('type') == 'wall':
                # Check if this wall is a "cliff" connected to a floor at our height
                if self._should_ignore_wall(line, dx):
                    continue

                p1 = line['p1']
                p2 = line['p2']
                # Simple AABB check first
                line_min_x = min(p1[0], p2[0])
                line_max_x = max(p1[0], p2[0])
                line_min_y = min(p1[1], p2[1])
                line_max_y = max(p1[1], p2[1])
                
                if self.rect.right > line_min_x and self.rect.left < line_max_x and \
                   self.rect.bottom > line_min_y and self.rect.top < line_max_y:
                    
                    # Determine side
                    if dx > 0: # Moving right
                        self.rect.right = line_min_x
                    elif dx < 0: # Moving left
                        self.rect.left = line_max_x

        # Vertical movement
        self.rect.y += dy
        self.in_air = True
        self.current_floor = None # Reset, will be set if we find ground
        
        # Check floor collisions
        ground_y = None
        
        # We only check for ground if we are falling or on ground
        if self.vel_y >= 0:
            foot_x = self.rect.centerx
            foot_y = self.rect.bottom
            
            # Find the highest floor line that we are currently above or crossing
            for line in self.lines:
                if line.get('type') == 'floor':
                    p1 = line['p1']
                    p2 = line['p2']
                    
                    # Check if x is within line segment
                    if min(p1[0], p2[0]) <= foot_x <= max(p1[0], p2[0]):
                        # Calculate line y at foot_x
                        if p2[0] != p1[0]:
                            slope = (p2[1] - p1[1]) / (p2[0] - p1[0])
                            line_y = p1[1] + slope * (foot_x - p1[0])
                        else:
                            line_y = min(p1[1], p2[1]) # Vertical floor? Should not happen but handle it
                            
                        # Check if we crossed it or are near it
                        # We allow snapping if we are slightly above it or just crossed it
                        # dy is the amount we moved down this frame
                        # previous_bottom = foot_y - dy
                        
                        # Tolerance for snapping
                        if foot_y >= line_y - 5 and foot_y <= line_y + max(10, self.vel_y + 5):
                            if ground_y is None or line_y < ground_y:
                                ground_y = line_y
                                self.current_floor = line

        if ground_y is not None:
            self.rect.bottom = ground_y
            self.vel_y = 0
            self.in_air = False
            
        # Fallback to old tile collision if no lines (optional, but good for backward compat)
        if not self.lines:
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

    def _should_ignore_wall(self, wall, dx):
        """
        Check if we should ignore this wall collision based on direction.
        Logic:
        - If we are moving RIGHT (dx > 0), we ignore the wall if there is a floor connected to its top extending to the LEFT.
          (This means we are walking off a cliff edge to the right)
        - If we are moving LEFT (dx < 0), we ignore the wall if there is a floor connected to its top extending to the RIGHT.
          (This means we are walking off a cliff edge to the left)
        """
        # 1. Find top of wall
        p1 = wall['p1']
        p2 = wall['p2']
        # Y is down, so min Y is the top
        top_y = min(p1[1], p2[1])
        top_point = p1 if p1[1] == top_y else p2
        
        # 2. Find connected floor
        connected_floor = None
        for line in self.lines:
            if line.get('type') == 'floor':
                fp1 = line['p1']
                fp2 = line['p2']
                if fp1 == top_point or fp2 == top_point:
                    connected_floor = line
                    break
        
        if not connected_floor:
            return False

        # 3. Check direction of floor relative to wall top
        fp1 = connected_floor['p1']
        fp2 = connected_floor['p2']
        
        # Find the "other" point of the floor (not the shared top_point)
        other_point = fp1 if fp2 == top_point else fp2
        
        # Check relative X position
        # If other_point.x < top_point.x, floor is to the LEFT
        # If other_point.x > top_point.x, floor is to the RIGHT
        
        is_floor_left = other_point[0] < top_point[0]
        is_floor_right = other_point[0] > top_point[0]
        
        # If moving RIGHT (dx > 0), we want the floor to be on the LEFT (behind us/under us)
        if dx > 0 and is_floor_left:
            return True
            
        # If moving LEFT (dx < 0), we want the floor to be on the RIGHT (behind us/under us)
        if dx < 0 and is_floor_right:
            return True
            
        return False

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

        # search nearby columns to smooth out sparse data from the sprite mask
        max_offset = len(columns)
        for offset in range(1, max_offset):
            left_idx = local_x - offset
            right_idx = local_x + offset
            if left_idx >= 0 and columns[left_idx] is not None:
                return columns[left_idx]
            if right_idx < len(columns) and columns[right_idx] is not None:
                return columns[right_idx]
        return None


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
 


    def draw_remote_projectiles(self, screen, camera_x, camera_y):
        # Draw projectiles
        if hasattr(self, 'remote_projectiles'):
            if not hasattr(self, 'projectile_cache'):
                self.projectile_cache = {}
                
            for p_data in self.remote_projectiles:
                p_name = p_data['image_name']
                
                # Load image if not cached
                if p_name not in self.projectile_cache:
                    try:
                        # Projectiles are stored in sprites/projectiles/{name}/0.png
                        img = pygame.image.load(f'sprites/projectiles/{p_name}/0.png').convert_alpha()
                        self.projectile_cache[p_name] = img
                    except Exception as e:
                        print(f"Error loading projectile {p_name}: {e}")
                        continue
                
                img = self.projectile_cache[p_name]
                
                # Rotate if needed
                if p_data.get('angle', 0) != 0:
                    img = pygame.transform.rotate(img, p_data['angle'])
                elif p_data.get('direction', 1) == -1:
                    img = pygame.transform.flip(img, True, False)
                    
                screen_x = p_data['x'] - camera_x
                screen_y = p_data['y'] - camera_y
                screen.blit(img, (screen_x, screen_y))

        # Draw skills
        if hasattr(self, 'remote_skills'):
            if not hasattr(self, 'skill_cache'):
                self.skill_cache = {} # format: {skill_name: [img0, img1, ...]}
                
            for s_data in self.remote_skills:
                s_name = s_data['skill_name']
                frame_idx = s_data.get('frame_index', 0)
                
                # Load animation frames if not cached
                if s_name not in self.skill_cache:
                    try:
                        self.skill_cache[s_name] = []
                        path = f'sprites/skills/{s_name}'
                        if os.path.exists(path):
                            num_frames = len([f for f in os.listdir(path) if f.endswith('.png')])
                            for i in range(num_frames):
                                img = pygame.image.load(f'{path}/{i}.png').convert_alpha()
                                self.skill_cache[s_name].append(img)
                    except Exception as e:
                        print(f"Error loading skill {s_name}: {e}")
                        continue
                
                # Draw current frame
                if s_name in self.skill_cache and self.skill_cache[s_name]:
                    frames = self.skill_cache[s_name]
                    # Wrap index if out of bounds (just in case)
                    img = frames[frame_idx % len(frames)]
                    
                    if s_data.get('direction', 1) == 1:
                        img = pygame.transform.flip(img, True, False)
                        
                    screen_x = s_data['x'] - camera_x
                    screen_y = s_data['y'] - camera_y
                    screen.blit(img, (screen_x, screen_y))
