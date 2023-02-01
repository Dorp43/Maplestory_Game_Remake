import pygame

class Projectile(pygame.sprite.Sprite):
    def __init__(self, x, y, direction, range, isRotate, projectile, damage):
        pygame.sprite.Sprite.__init__(self)
        self.range = range
        self.projectile = projectile
        self.speed = 12
        self.hit_count = 0
        self.damage = damage
        self.isRotate = isRotate
        if direction == 1:
            self.flip = True
        else:
            self.flip = False
        self.image = pygame.image.load(f'sprites/projectiles/{projectile}/0.png').convert_alpha()
        self.image = pygame.transform.flip(self.image, self.flip, False)
        self.rect = self.image.get_rect()
        self.rect.center = (x, y)
        self.direction = direction
        self.angle = 0

    def update(self, mobs, player):
        #move projectile
        self.rect.x += (self.direction * self.speed)
        if self.isRotate:
            self.rotate()
        for mob in mobs:
            if pygame.sprite.spritecollide(mob, player.projectiles_group, False):
                if mob.alive and self.hit_count != 1:
                    mob.play_sound("mob","hit")
                    mob.health -= 25
                    mob.update_action(3)
                    if self.projectile != 'big_star':
                        self.kill()
                    self.hit_count += 1
        #check if projectile has gone off range
        if self.rect.x > (player.rect.x + self.range) or self.rect.x < (player.rect.x - self.range):
            self.kill()

    def rotate(self):
        self.image = pygame.transform.rotozoom(self.image, self.angle, 1)
        self.rect = self.image.get_rect(center=self.rect.center)
        self.angle += 1
 