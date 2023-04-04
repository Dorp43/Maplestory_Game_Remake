import pygame
import os

class Sprite(pygame.sprite.Sprite):
    def __init__(self, sprite_name, x, y, scale, speed):
        pygame.sprite.Sprite.__init__(self)
        self.alive = True
        self.sprite_name = sprite_name
        self.speed = speed
        self.direction = -1
        self.flip = False
        self.animation_list = []
        self.frame_index = 0
        self.action = 0
        self.update_time = pygame.time.get_ticks()

        # Get animations
        animation_types = ['stand', 'walk', 'jump', 'attack1', 'attack2', 'attack3']
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