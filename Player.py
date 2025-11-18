import pygame
import random
import os
from skills.Skill import Skill
from skills.Projectile import Projectile
from entities.HealthBar import HealthBar


class Player(pygame.sprite.Sprite):
    def __init__(self, screen, char_type, x, y, scale, speed, health, mobs, tiles, map_bounds=None):
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
        # list of pygame.Rect for solid tiles / platforms
        self.tiles = tiles
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
 


