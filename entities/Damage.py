import pygame

class Damage(pygame.sprite.Sprite):
    def __init__(self, object, screen):
        pygame.sprite.Sprite.__init__(self)
        self.object = object
        self.screen = screen

    def inflict_damage(self):
        """ Displays damage """
        