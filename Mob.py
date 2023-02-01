import pygame
import os
import random
from HealthBar import HealthBar


FLOOR = 465

class Mob(pygame.sprite.Sprite):
    def __init__(self,screen, char_type, x, y, scale, speed, health, players):
        pygame.sprite.Sprite.__init__(self)
        self.screen = screen
        self.alive = True
        self.char_type = char_type
        self.speed = speed
        self.players = players
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
            #reset temporary list of images
            temp_list = []
            #count number of files in the folder
            num_of_frames = len(os.listdir(f'sprites/mobs/{self.char_type}/{animation}'))
            for i in range(num_of_frames):
                img = pygame.image.load(f'sprites/mobs/{self.char_type}/{animation}/{i}.png')
                img = pygame.transform.scale(img, (int(img.get_width() * scale), int(img.get_height() * scale)))
                temp_list.append(img)
            self.animation_list.append(temp_list)

        self.image = self.animation_list[self.action][self.frame_index]
        self.rect = self.image.get_rect()
        self.rect.center = (x, y)
        self.health_bar = HealthBar(self, screen, "red")



    def update(self):
        self.health_bar.update()
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

        #check collision with floor
        if self.rect.bottom + dy > FLOOR:
            dy = FLOOR - self.rect.bottom
            self.in_air = False

        #update rectangle position
        self.rect.x += dx
        self.rect.y += dy


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


    def draw(self):
        self.screen.blit(pygame.transform.flip(self.image, self.flip, False), self.rect)


    def play_sound(self, dir_name, sound):
        soundObj = pygame.mixer.Sound(f'sprites/sounds/{dir_name}/{sound}.mp3')
        soundObj.play()
