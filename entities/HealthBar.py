import pygame

class HealthBar(pygame.sprite.Sprite):
    def __init__(self, object, screen, color):
        pygame.sprite.Sprite.__init__(self)
        self.object = object
        self.screen = screen
        self.bar_pos = (self.object.rect.x, self.object.rect.top - 20)
        self.progress = self.object.health / self.object.max_health
        self.bar_size = (70, 10)
        self.border_color = (0, 0, 0)
        self.background_color = (0, 0, 0)
        if color == "red":
            self.bar_color = (204, 0, 0)
        elif color == "green":
            self.bar_color = (0, 204, 0)
        

    def update(self, camera_x=0, camera_y=0):
        sum = (self.object.rect.center[0] - self.object.rect.x)
        world_x = self.object.rect.x - sum/2
        world_y = self.object.rect.top - 20
        # Convert to screen coordinates
        self.bar_pos = (world_x - camera_x, world_y - camera_y)
        self.progress = self.object.health / self.object.max_health
        self.draw()


    def draw(self):
        pygame.draw.rect(self.screen, self.border_color, (*self.bar_pos, * self.bar_size), 1)
        pygame.draw.rect(self.screen, self.background_color, (*self.bar_pos, * self.bar_size))
        innerPos  = (self.bar_pos[0]+3, self.bar_pos[1]+3)
        innerSize = ((self.bar_size[0]-6) * self.progress, self.bar_size[1]-6)
        pygame.draw.rect(self.screen, self.bar_color, (*innerPos, *innerSize))
        
