import pygame
from Player import Player
from mobs.Mob import Mob
from maps.Map import Map


class Game:
    def __init__(self, width=0, height=0, fps=60, map_id=0):
        pygame.init()
        self.run = True
        self.map_id = map_id
        self.map = None
        self.players = pygame.sprite.Group()
        self.mobs = pygame.sprite.Group()
        self.gravity = 0.75
        self.fps = fps
        self.screen_width = width
        self.screen_height = height
        self.initialize_game()
        self.load_map(map_id)
        self.game_loop()

    def initialize_game(self):
        """ Initializes general settings """
        display_info = pygame.display.Info()
        # If width/height were not provided, use current display resolution.
        if self.screen_width <= 0 or self.screen_height <= 0:
            self.screen_width = display_info.current_w
            self.screen_height = display_info.current_h

        self.screen = pygame.display.set_mode(
            (self.screen_width, self.screen_height), pygame.FULLSCREEN)
        self.clock = pygame.time.Clock()
        pygame.mouse.set_visible(False)  # hide the cursor
        self.cursor = pygame.image.load(
            'sprites/entities/UI/cursor.png').convert_alpha()
        pygame.display.set_caption('Maplestory')

    def game_loop(self):
        """ Game loop main method """
        while self.run:
            self.clock.tick(self.fps)
            self.draw_bg()

            for mob in self.mobs:
                mob.update()
                mob.draw()
            for player in self.players:
                player.update()
                player.draw()
                player.projectiles_group.update(self.mobs, player)
                player.projectiles_group.draw(self.screen)
                player.skills_group.update(player)
                player.skills_group.draw(self.screen)

                # update player actions
                if player.alive:
                    if player.attack:
                        player.update_action(player.next_attack)
                    elif player.in_air:
                        player.update_action(2)  # 2: jump
                    elif player.moving_left or player.moving_right:
                        player.update_action(1)  # 1: run
                    elif player.skill_big_star:
                        player.update_action(6)
                    else:
                        player.update_action(0)  # 0: idle
                    player.move(self.gravity)

                self.handle_controls(player)

            # draws cursor
            self.screen.blit(self.cursor, (pygame.mouse.get_pos()))

            pygame.display.update()

        pygame.quit()

    def handle_controls(self, player):
        """ Handles game controlls """
        for event in pygame.event.get():
            # quit game
            if event.type == pygame.QUIT:
                self.run = False
            # keyboard presses
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
                    self.run = False
                if event.key == pygame.K_TAB:
                    print(
                        f"Player \nx: {player.rect.x} \ny: {player.rect.y}")

            # keyboard button released
            if event.type == pygame.KEYUP:
                if event.key == pygame.K_a:
                    player.moving_left = False
                if event.key == pygame.K_d:
                    player.moving_right = False
                if event.key == pygame.K_LCTRL:
                    player.attack == False


    def load_map(self, map_id: int):
        """ Sets bg variable to the current map """
        self.map = Map(self.screen, self.players, self.map_id)
        self.mobs = self.map.get_mobs()
        # Spawn Player (Would move to Map class on next update)
        self.players.add(
            Player(
                self.screen,
                'player',
                400,
                200,
                1,
                3,
                200,
                self.mobs,
                self.map.tiles,
            )
        )

    def draw_bg(self):
        self.screen.fill((255, 255, 255))
        if self.map:
            self.map.draw(self.screen)


game = Game()
