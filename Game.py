import pygame
import os
import simpleaudio as sa
from Player import Player
from Mob import Mob
from HealthBar import HealthBar


pygame.init()


SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600

# , pygame.FULLSCREEN
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption('Maplestory')
#set framerate
clock = pygame.time.Clock()
FPS = 60

#define game variables
GRAVITY = 0.75

pygame.mouse.set_visible(False)  # hide the cursor
MANUAL_CURSOR = pygame.image.load('sprites/entities/UI/cursor.png').convert_alpha()


#define colours
BG = pygame.image.load("sprites\maps\map0.png")

def draw_bg():
    screen.blit(BG, (0, 0))

players = pygame.sprite.Group()
mobs = pygame.sprite.Group()
player = Player(screen, 'player', 400, 200, 1, 3, 200,mobs)
players.add(player)
mushroom1 = Mob(screen, 'mushroom', 300, 400, 1, 1, 100, players)
mushroom2 = Mob(screen, 'mushroom', 450, 400, 1, 1, 100, players)
mushroom3 = Mob(screen, 'mushroom', 600, 400, 1, 1, 100, players)
stump1 = Mob(screen, 'stump', 150, 400, 1, 1, 150, players)
slime1 = Mob(screen, 'slime', 700, 400, 1, 1, 150, players)

mobs.add(mushroom1, mushroom2, mushroom3, stump1, slime1)



run = True
while run:

    

    clock.tick(FPS)


    draw_bg()
    

    for mob in mobs:
        mob.update()
        mob.draw()
    for player in players:
        player.update()
        player.draw()
    player.projectiles_group.update(mobs, player)
    player.projectiles_group.draw(screen)
    player.skills_group.update(player)
    player.skills_group.draw(screen)


    #update player actions
    if player.alive:
        if player.attack:
            player.update_action(player.next_attack)
        elif player.in_air:
            player.update_action(2)#2: jump
        elif player.moving_left or player.moving_right:
            player.update_action(1)#1: run
        elif player.skill_big_star:
            player.update_action(6)
        else:
            player.update_action(0)#0: idle
        player.move(GRAVITY)


    for event in pygame.event.get():
        #quit game
        if event.type == pygame.QUIT:
            run = False
        #keyboard presses
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_a:
                player.moving_left = True
            if event.key == pygame.K_d:
                player.moving_right = True
            if event.key == pygame.K_SPACE:
                if player.in_air and not player.flash_jump and player.flash_jump_cooldown == 0:
                    player.flash_jump = True
                if not player.in_air:
                    player.jump = True
            if event.key == pygame.K_LCTRL and player.alive:
                player.attack = True
            if event.key == pygame.K_q and not player.attack and not player.in_air:
                player.skill_big_star = True
                player.moving_left = False
                player.moving_right = False
                player.jump = False
                player.attack = False
            if event.key == pygame.K_ESCAPE:
                run = False
            if event.key == pygame.K_TAB:
                print(f"Player \nx: {player.rect.x} \ny: {player.rect.y} \nMob \nx: {mushroom1.rect.x} \ny: {mushroom1.rect.y}")
            


        #keyboard button released
        if event.type == pygame.KEYUP:
            if event.key == pygame.K_a:
                player.moving_left = False
            if event.key == pygame.K_d:
                player.moving_right = False
            if event.key == pygame.K_LCTRL:
                player.attack == False

    screen.blit( MANUAL_CURSOR, ( pygame.mouse.get_pos() ) ) # draws cursor


    pygame.display.update()

pygame.quit()