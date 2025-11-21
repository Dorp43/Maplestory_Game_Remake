import pygame
from Player import Player
from mobs.Mob import Mob
from maps.Map import Map
from screens.MainMenu import MainMenu
from screens.MultiplayerMenu import MultiplayerMenu
from enum import Enum
from Network import Network
import uuid

class GameState(Enum):
    MENU = 0
    MULTIPLAYER_MENU = 1
    GAME = 2


class Game:
    def __init__(self, width=0, height=0, fps=60, map_id=1):
        pygame.init()
        self.run = True
        self.state = GameState.MENU
        self.map_id = map_id
        self.map = None
        self.players = pygame.sprite.Group()
        self.remote_players = {} # id -> Player
        self.player_id = str(uuid.uuid4())
        self.username = ""
        self.network = None
        self.mobs = pygame.sprite.Group()
        self.gravity = 0.75
        self.fps = fps
        
        # Virtual resolution settings
        self.VIRTUAL_WIDTH = 1366
        self.VIRTUAL_HEIGHT = 768
        
        # Display resolution (actual window size)
        self.display_width = width
        self.display_height = height
        
        # Camera offset (world position of top-left corner of screen)
        self.camera_x = 0
        self.camera_y = 0
        self.initialize_game()
        self.initialize_game()
        
        # Initialize Menus
        self.main_menu = MainMenu(self.VIRTUAL_WIDTH, self.VIRTUAL_HEIGHT, 
                                  self.start_singleplayer, self.open_multiplayer, self.quit_game)
        self.multiplayer_menu = MultiplayerMenu(self.VIRTUAL_WIDTH, self.VIRTUAL_HEIGHT, 
                                                self.connect_multiplayer, self.back_to_main)
        
        self.load_map(map_id)
        self.game_loop()

    def start_singleplayer(self):
        self.state = GameState.GAME
        
    def open_multiplayer(self):
        self.state = GameState.MULTIPLAYER_MENU
        
    def quit_game(self):
        self.run = False
        
    def connect_multiplayer(self, username, ip):
        print(f"Connecting to {ip} as {username}")
        self.username = username
        self.network = Network(ip)
        self.state = GameState.GAME
        
    def back_to_main(self):
        self.state = GameState.MENU

    def initialize_game(self):
        """ Initializes general settings """
        display_info = pygame.display.Info()
        # If width/height were not provided, use current display resolution.
        if self.display_width <= 0 or self.display_height <= 0:
            self.display_width = display_info.current_w
            self.display_height = display_info.current_h

        # Create the actual display window
        self.display_surface = pygame.display.set_mode(
            (self.display_width, self.display_height), pygame.FULLSCREEN)
            
        # Create the virtual screen surface (what we draw to)
        self.screen = pygame.Surface((self.VIRTUAL_WIDTH, self.VIRTUAL_HEIGHT)).convert()
        
        self.clock = pygame.time.Clock()
        pygame.mouse.set_visible(False)  # hide the cursor
        self.cursor = pygame.image.load(
            'sprites/entities/UI/cursor.png').convert_alpha()
        pygame.display.set_caption('Maplestory')

    def update_camera(self, player):
        """Update camera to follow player, keeping player centered on screen, clamped to map boundaries"""
        if not self.map:
            return
            
        # Center camera on player (using virtual dimensions)
        target_x = player.rect.centerx - self.VIRTUAL_WIDTH // 2
        target_y = player.rect.centery - self.VIRTUAL_HEIGHT // 2
        
        # Get map boundaries
        map_min_x, map_max_x, map_min_y, map_max_y = self.map.get_map_bounds()
        
        # Calculate camera limits (camera position is top-left of screen)
        # Horizontal: clamp both sides (don't show void on left or right)
        camera_min_x = map_min_x
        camera_max_x = map_max_x - self.VIRTUAL_WIDTH
        
        # Vertical: only clamp bottom (don't show void below), but allow void above
        # Don't set camera_min_y - allow camera to go above map_min_y to show void at top
        camera_max_y = map_max_y - self.VIRTUAL_HEIGHT
        
        # If global background bounds are set, clamp camera to them
        if self.map.global_bg_start_y is not None:
            # Ensure camera doesn't go above the top background bound
            camera_min_y = self.map.global_bg_start_y
        else:
            # Default behavior: allow going above map top (no min y)
            camera_min_y = float('-inf')
            
        if self.map.global_bg_end_y is not None:
            # Ensure camera doesn't go below the bottom background bound
            # The bottom of the screen should not exceed global_bg_end_y
            # So camera_y + screen_height <= global_bg_end_y
            # camera_y <= global_bg_end_y - screen_height
            camera_max_y = min(camera_max_y, self.map.global_bg_end_y - self.VIRTUAL_HEIGHT)
        
        # Handle case where map is smaller than screen horizontally
        if camera_max_x < camera_min_x:
            camera_max_x = camera_min_x
        
        # Clamp camera horizontally (both sides)
        self.camera_x = max(camera_min_x, min(camera_max_x, target_x))
        
        # Clamp camera vertically
        self.camera_y = max(camera_min_y, min(camera_max_y, target_y))

    def game_loop(self):
        """ Game loop main method """
        while self.run:
            dt = self.clock.tick(self.fps)
            # Scale mouse position for UI
            mouse_x, mouse_y = pygame.mouse.get_pos()
            virtual_mouse_x = int(mouse_x * (self.VIRTUAL_WIDTH / self.display_width))
            virtual_mouse_y = int(mouse_y * (self.VIRTUAL_HEIGHT / self.display_height))
            virtual_mouse_pos = (virtual_mouse_x, virtual_mouse_y)

            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    self.run = False

            if self.state == GameState.MENU:
                self.screen.fill((0, 0, 0))
                self.main_menu.update(virtual_mouse_pos, events)
                self.main_menu.draw(self.screen)
            
            elif self.state == GameState.MULTIPLAYER_MENU:
                self.screen.fill((0, 0, 0))
                self.multiplayer_menu.update(virtual_mouse_pos, events)
                self.multiplayer_menu.draw(self.screen)

            elif self.state == GameState.GAME:
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

                    self.handle_controls(player, events)
                    
                    # --- Networking ---
                    if self.network:
                        # Prepare data to send
                        data = {
                            'id': self.player_id,
                            'username': self.username,
                            'x': player.rect.x,
                            'y': player.rect.y,
                            'action': player.action,
                            'frame_index': player.frame_index,
                            'flip': player.flip,
                            'char_type': player.char_type,
                            'hp': player.health,
                            'max_hp': player.max_health
                        }
                        
                        # Send and receive
                        all_players_data = self.network.send(data)
                        
                        # Process received data
                        if all_players_data:
                            current_remote_ids = set()
                            
                            for addr, p_data in all_players_data.items():
                                if not p_data: continue
                                pid = p_data.get('id')
                                
                                # Skip ourselves
                                if pid == self.player_id:
                                    continue
                                    
                                current_remote_ids.add(pid)
                                
                                # Update or Create remote player
                                if pid in self.remote_players:
                                    remote_p = self.remote_players[pid]
                                    remote_p.rect.x = p_data['x']
                                    remote_p.rect.y = p_data['y']
                                    remote_p.action = p_data['action']
                                    remote_p.frame_index = p_data['frame_index']
                                    remote_p.flip = p_data['flip']
                                    remote_p.health = p_data['hp']
                                    # Update animation manually since we don't call update()
                                    remote_p.image = remote_p.animation_list[remote_p.action][remote_p.frame_index]
                                    
                                else:
                                    # Create new remote player
                                    new_p = Player(
                                        self.screen,
                                        p_data['char_type'],
                                        p_data['x'],
                                        p_data['y'],
                                        1, # scale
                                        3, # speed (irrelevant)
                                        p_data['max_hp'],
                                        None, # mobs
                                        None, # tiles
                                    )
                                    self.remote_players[pid] = new_p
                                    
                            # Remove disconnected players
                            disconnected_ids = set(self.remote_players.keys()) - current_remote_ids
                            for pid in disconnected_ids:
                                del self.remote_players[pid]
                                
                            # Draw remote players
                            for pid, remote_p in self.remote_players.items():
                                remote_p.draw(self.camera_x, self.camera_y)
                                # Draw username
                                # Find the username from the data (we need to find the data again or store it)
                                # Optimization: Store username in remote_p or look it up
                                # Let's just look it up from all_players_data for now, it's inefficient but fine for small player count
                                p_name = "Unknown"
                                for p_data in all_players_data.values():
                                    if p_data and p_data.get('id') == pid:
                                        p_name = p_data.get('username', 'Unknown')
                                        break
                                
                                font = pygame.font.SysFont("Arial", 14)
                                name_surf = font.render(p_name, True, (255, 255, 255))
                                name_rect = name_surf.get_rect(center=(remote_p.rect.centerx - self.camera_x, remote_p.rect.top - 10 - self.camera_y))
                                self.screen.blit(name_surf, name_rect)

            # draws cursor
            # Scale mouse position from display coordinates to virtual coordinates
            # mouse_x, mouse_y = pygame.mouse.get_pos() # Already got this above
            # virtual_mouse_x = int(mouse_x * (self.VIRTUAL_WIDTH / self.display_width))
            # virtual_mouse_y = int(mouse_y * (self.VIRTUAL_HEIGHT / self.display_height))
            self.screen.blit(self.cursor, (virtual_mouse_x, virtual_mouse_y))
            self.screen.blit(self.cursor, (virtual_mouse_x, virtual_mouse_y))

            # Scale virtual screen to display size and blit
            scaled_screen = pygame.transform.scale(self.screen, (self.display_width, self.display_height))
            self.display_surface.blit(scaled_screen, (0, 0))

            pygame.display.update()

        pygame.quit()

    def handle_controls(self, player, events):
        """ Handles game controlls """
        for event in events:
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
        self.camera_x = player.rect.centerx - self.VIRTUAL_WIDTH // 2
        self.camera_y = player.rect.centery - self.VIRTUAL_HEIGHT // 2

    def draw_bg(self):
        self.screen.fill((255, 255, 255))
        if self.map:
            self.map.draw(self.screen, self.camera_x, self.camera_y)


if __name__ == "__main__":
    game = Game()
