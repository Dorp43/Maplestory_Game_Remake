import pygame
import os
import random
from entities.HealthBar import HealthBar

FLOOR = 465


class Mob(pygame.sprite.Sprite):
    def __init__(self, screen, players, tiles, slope_tiles=None, lines=None, mob_name=None, x=0, y=0, scale=1, speed=1, health=150, map_bounds=None):
        pygame.sprite.Sprite.__init__(self)
        self.screen = screen
        self.alive = True
        self.mob_name = mob_name
        self.speed = speed
        self.players = players
        # list of pygame.Rect for solid tiles / platforms
        self.tiles = tiles
        self.slope_tiles = slope_tiles or []
        self.lines = lines or []
        self.current_floor = None
        self.max_slope_step_up = 60
        self.max_slope_step_down = 25
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
                img = pygame.image.load(f'{anim_path}/{i}.png').convert_alpha()
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
                        self.moving_right = False
                        self.moving_left = True
                    elif dx < 0: # Moving left
                        self.rect.left = line_max_x
                        self.moving_left = False
                        self.moving_right = True

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

        # Vertical movement
        self.rect.y += dy
        self.in_air = True
        self.current_floor = None
        
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
                            line_y = min(p1[1], p2[1]) 
                            
                        # Check if we crossed it or are near it
                        # Tolerance for snapping
                        if foot_y >= line_y - 5 and foot_y <= line_y + max(10, self.vel_y + 5):
                            if ground_y is None or line_y < ground_y:
                                ground_y = line_y
                                self.current_floor = line

        if ground_y is not None:
            self.rect.bottom = ground_y
            self.vel_y = 0
            self.in_air = False
            
        # Fallback to old tile collision if no lines
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

        max_offset = len(columns)
        for offset in range(1, max_offset):
            left_idx = local_x - offset
            right_idx = local_x + offset
            if left_idx >= 0 and columns[left_idx] is not None:
                return columns[left_idx]
            if right_idx < len(columns) and columns[right_idx] is not None:
                return columns[right_idx]
        return None


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
