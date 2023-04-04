import pygame
import os

class Skill(pygame.sprite.Sprite):
    def __init__(self, x, y, direction, skill):
        pygame.sprite.Sprite.__init__(self)
        self.skill = skill
        self.frame_index = 0
        self.x = x
        self.animation_list = []
        # Used to flip the sprites by direction
        if direction == 1:
            self.flip = True
        else:
            self.flip = False


        num_of_frames = len(os.listdir(f'sprites/skills/{skill}'))
        for i in range(num_of_frames):
                img = pygame.image.load(f'sprites/skills/{skill}/{i}.png')
                img = pygame.transform.scale(img, (int(img.get_width()), int(img.get_height())))
                img = pygame.transform.flip(img, self.flip, False)
                self.animation_list.append(img)
        self.image = self.animation_list[self.frame_index]
        self.rect = self.image.get_rect()
        self.rect.center = (x, y)
        self.direction = direction
        self.update_time = pygame.time.get_ticks()


    def update(self, player):
        # self.rect.x = player.rect.x + (self.direction * -25)
        self.update_animation()

    def update_animation(self):
        #update animation
        animation_cooldown = 50
        #update image depending on current frame
        self.image = self.animation_list[self.frame_index]
        #check if enough time has passed since the last update
        if pygame.time.get_ticks() - self.update_time > animation_cooldown:
            self.update_time = pygame.time.get_ticks()
            self.frame_index += 1
        #if the animation has run out the reset back to the start
        if self.frame_index >= len(self.animation_list):
            # if action is attack stop it from attacking again
            self.kill()
