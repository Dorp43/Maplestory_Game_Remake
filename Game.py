import pygame
from Player import Player
from mobs.Mob import Mob
from maps.Map import Map


class Game:
    def __init__(self, width=0, height=0, fps=60, map_id=1):
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
        # Camera offset (world position of top-left corner of screen)
        self.camera_x = 0
        self.camera_y = 0
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

    def update_camera(self, player):
        """Update camera to follow player, keeping player centered on screen, clamped to map boundaries"""
        if not self.map:
            return
            
        # Center camera on player
        target_x = player.rect.centerx - self.screen_width // 2
        target_y = player.rect.centery - self.screen_height // 2
        
        # Get map boundaries
        map_min_x, map_max_x, map_min_y, map_max_y = self.map.get_map_bounds()
        
        # Calculate camera limits (camera position is top-left of screen)
        # Horizontal: clamp both sides (don't show void on left or right)
        camera_min_x = map_min_x
        camera_max_x = map_max_x - self.screen_width
        
        # Vertical: only clamp bottom (don't show void below), but allow void above
        # Don't set camera_min_y - allow camera to go above map_min_y to show void at top
        camera_max_y = map_max_y - self.screen_height
        
        # Handle case where map is smaller than screen horizontally
        if camera_max_x < camera_min_x:
            camera_max_x = camera_min_x
        
        # Clamp camera horizontally (both sides)
        self.camera_x = max(camera_min_x, min(camera_max_x, target_x))
        
        # Clamp camera vertically (only bottom, allow going above map top)
        # Don't clamp to map_min_y - we want to allow showing void above
        self.camera_y = min(camera_max_y, target_y)

    def game_loop(self):
        """ Game loop main method """
        while self.run:
            dt = self.clock.tick(self.fps)
            # Update animation time for backgrounds
            if self.map:
                self.map.animation_time += dt / 1000.0  # Convert to seconds
            self.draw_bg()

            for mob in self.mobs:
                mob.update(self.camera_x, self.camera_y)
                mob.draw(self.camera_x, self.camera_y)
            for player in self.players:
                # Update camera to follow player (before updating player so health bar uses correct camera)
                self.update_camera(player)
                player.update(self.camera_x, self.camera_y)
                player.draw(self.camera_x, self.camera_y)
                player.projectiles_group.update(self.mobs, player)
                # Draw projectiles with camera offset
                for projectile in player.projectiles_group:
                    screen_x = projectile.rect.x - self.camera_x
                    screen_y = projectile.rect.y - self.camera_y
                    self.screen.blit(projectile.image, (screen_x, screen_y))
                player.skills_group.update(player)
                # Draw skills with camera offset
                for skill in player.skills_group:
                    screen_x = skill.rect.x - self.camera_x
                    screen_y = skill.rect.y - self.camera_y
                    self.screen.blit(skill.image, (screen_x, screen_y))

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
        # Get map boundaries to pass to player
        map_bounds = self.map.get_map_bounds()
        # Get spawn point from map
        spawn_x, spawn_y = self.map.get_spawn_point()
        # Spawn Player (Would move to Map class on next update)
        player = Player(
            self.screen,
            'player',
            spawn_x,
            spawn_y,
            1,
            3,
            200,
            self.mobs,
            self.map.tiles,
            self.map.slope_tiles,
            lines=self.map.lines,
            map_bounds=map_bounds,
        )
        self.players.add(player)
        # Initialize camera to player's starting position
        self.camera_x = player.rect.centerx - self.screen_width // 2
        self.camera_y = player.rect.centery - self.screen_height // 2

    def draw_bg(self):
        self.screen.fill((255, 255, 255))
        if self.map:
            self.map.draw(self.screen, self.camera_x, self.camera_y)


game = Game()
