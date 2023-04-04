import pygame
from mobs.Mob import Mob
from maps import map0


class Map:
    def __init__(self,screen, players, map_id=0):
        self.screen = screen
        self.players = players
        self.mobs = pygame.sprite.Group()
        self.set_map(map_id)
        
    def set_map(self, map_id):
        """ Sets the map to the requested map """
        self.map_id = map_id
        if map_id == 0:
            self.set_mobs(map0.mobs_list)
        
    def set_mobs(self, mobs_list):
        """ Spawn the mobs on map """
        for mob in mobs_list:
            self.mobs.add(Mob(self.screen, self.players, **mob))
    
    def get_mobs(self):
        """ Returns mobs list """
        return self.mobs

            

        
        