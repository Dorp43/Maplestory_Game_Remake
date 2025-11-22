import pygame
from Player import Player
from mobs.Mob import Mob
from maps.Map import Map
from screens.MainMenu import MainMenu
from screens.MultiplayerMenu import MultiplayerMenu
from screens.SettingsMenu import SettingsMenu
from enum import Enum
from Network import Network
import uuid

class GameState(Enum):
    MENU = 0
    MULTIPLAYER_MENU = 1
    SETTINGS = 3
    GAME = 2


from utils.SettingsManager import SettingsManager

class Game:
    def __init__(self, width=0, height=0, fps=60, map_id=1):
        pygame.init()
        self.run = True
        self.state = GameState.MENU
        self.map_id = map_id
        self.map = None
        self.players = pygame.sprite.Group()
        self.all_players = pygame.sprite.Group() # Group containing local AND remote players for Mob AI
        self.remote_players = {} # id -> Player
        self.player_id = str(uuid.uuid4())
        self.username = ""
        self.network = None
        self.is_host = True
        self.mobs = pygame.sprite.Group()
        self.gravity = 0.75
        self.fps = fps
        
        # Initialize Settings
        self.settings_manager = SettingsManager()
        
        # Virtual resolution settings
        self.VIRTUAL_WIDTH = 1366
        self.VIRTUAL_HEIGHT = 768
        
        # Display resolution (actual window size)
        # Load from settings if not provided
        if width == 0 and height == 0:
            self.display_width = self.settings_manager.get_setting("window_width", 1024)
            self.display_height = self.settings_manager.get_setting("window_height", 576)
        else:
            self.display_width = width
            self.display_height = height
        
        # Camera offset (world position of top-left corner of screen)
        self.camera_x = 0
        self.camera_y = 0
        self.initialize_game()
        
        # Initialize Menus
        # Pass saved username/ip to MultiplayerMenu
        saved_username = self.settings_manager.get_setting("username", "")
        saved_ip = self.settings_manager.get_setting("last_ip", "127.0.0.1")
        
        self.main_menu = MainMenu(self.VIRTUAL_WIDTH, self.VIRTUAL_HEIGHT, 
                                  self.start_singleplayer, self.open_multiplayer, self.open_settings, self.quit_game)
        self.multiplayer_menu = MultiplayerMenu(self.VIRTUAL_WIDTH, self.VIRTUAL_HEIGHT, 
                                                self.connect_multiplayer, self.back_to_main, 
                                                default_username=saved_username, default_ip=saved_ip)
        self.settings_menu = SettingsMenu(self.VIRTUAL_WIDTH, self.VIRTUAL_HEIGHT,
                                          self.back_to_main, self.toggle_fullscreen, self.toggle_audio)
        
        self.load_map(map_id)
        self.game_loop()

    def start_singleplayer(self):
        self.state = GameState.GAME
        
    def open_multiplayer(self):
        self.state = GameState.MULTIPLAYER_MENU

    def open_settings(self):
        self.state = GameState.SETTINGS

    def toggle_fullscreen(self):
        is_fullscreen = self.display_surface.get_flags() & pygame.FULLSCREEN
        if is_fullscreen:
            # Switch to Windowed
            # Use saved window size or default
            w = self.settings_manager.get_setting("window_width", 1024)
            h = self.settings_manager.get_setting("window_height", 576)
            self.display_surface = pygame.display.set_mode((w, h))
            self.display_width = w
            self.display_height = h
            self.settings_manager.set_setting("fullscreen", False)
        else:
            # Switch to Fullscreen
            display_info = pygame.display.Info()
            self.display_width = display_info.current_w
            self.display_height = display_info.current_h
            self.display_surface = pygame.display.set_mode((self.display_width, self.display_height), pygame.FULLSCREEN)
            self.settings_manager.set_setting("fullscreen", True)
            
    def toggle_audio(self):
        if pygame.mixer.get_init():
            if pygame.mixer.get_num_channels() > 0:
                # Simple mute check - if volume is > 0, set to 0, else set to 1
                # But pygame mixer doesn't have a global mute easily without iterating channels or using music
                # Let's just toggle volume for now.
                # A better way is to set a flag and check it before playing sounds, but for now let's try to set volume.
                # Actually, we can just use a flag in Game and pass it to Player?
                # Or just hack it by setting num_channels to 0? No.
                # Let's just set volume of all channels to 0 or 1.
                pass
                # For now, let's just print "Toggled Audio" as placeholder or implement a simple global volume
                # But Player.py plays sounds directly.
                # We should probably add a sound_manager or just hack it here.
                # Let's try to just stop all playback for mute, but that doesn't prevent new sounds.
                # We'll leave it as a TODO or implement a simple global flag if user insists.
                # User asked for "mute option", so let's implement a global volume set.
                current_vol = pygame.mixer.Channel(0).get_volume() # Check one channel? No.
                # Let's assume unmuted.
                # We'll use a flag self.muted
                if not hasattr(self, 'muted'):
                    self.muted = False
                
                self.muted = not self.muted
                if self.muted:
                    pygame.mixer.set_num_channels(0) # This might stop all sounds
                else:
                    pygame.mixer.set_num_channels(8) # Default
                    
    def quit_game(self):
        self.run = False
        
    def connect_multiplayer(self, username, ip):
        print(f"Connecting to {ip} as {username}")
        self.username = username
        self.is_host = False # Assume client until server says otherwise
        
        # Save settings
        self.settings_manager.set_setting("username", username)
        self.settings_manager.set_setting("last_ip", ip)
        
        self.network = Network(ip)
        self.state = GameState.GAME
        
    def back_to_main(self):
        self.state = GameState.MENU

    def initialize_game(self):
        """ Initializes general settings """
        # Check fullscreen setting
        start_fullscreen = self.settings_manager.get_setting("fullscreen", False)
        
        if start_fullscreen:
            display_info = pygame.display.Info()
            self.display_width = display_info.current_w
            self.display_height = display_info.current_h
            flags = pygame.FULLSCREEN
        else:
            flags = 0

        # Create the actual display window
        self.display_surface = pygame.display.set_mode(
            (self.display_width, self.display_height), flags)
            
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

            elif self.state == GameState.SETTINGS:
                self.screen.fill((0, 0, 0))
                self.settings_menu.update(virtual_mouse_pos, events)
                self.settings_menu.draw(self.screen)

            elif self.state == GameState.GAME:
                # Update animation time for backgrounds
                if self.map:
                    self.map.animation_time += dt / 1000.0  # Convert to seconds
                self.draw_bg()

                # Mob Logic
                # Only Host updates mob physics/AI
                if self.is_host:
                    for mob in self.mobs:
                        mob.update(self.camera_x, self.camera_y)
                        mob.draw(self.camera_x, self.camera_y)
                else:
                    # Clients just draw mobs based on server data (updated in network block)
                    # But we still need to draw them
                    for mob in self.mobs:
                        # mob.update() # Don't run update logic on client
                        mob.client_update(self.camera_x, self.camera_y)
                        mob.draw(self.camera_x, self.camera_y)

                for player in self.players:
                    # Update camera to follow player (before updating player so health bar uses correct camera)
                    self.update_camera(player)
                    player.update(self.camera_x, self.camera_y)
                    player.draw(self.camera_x, self.camera_y)
                    
                    # Collect hits this frame
                    self.frame_hits = []
                    player.projectiles_group.update(self.mobs, player, self.frame_hits)
                    
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
                        # Prepare player data to send
                        # Include projectiles
                        projectiles_data = []
                        for p in player.projectiles_group:
                            projectiles_data.append({
                                'x': p.rect.x,
                                'y': p.rect.y,
                                'image_name': p.projectile_name, # We need to know what image to draw
                                'direction': p.direction,
                                'angle': p.angle
                            })
                            
                        # Include skills (big star)
                        skills_data = []
                        for s in player.skills_group:
                             skills_data.append({
                                'x': s.rect.x,
                                'y': s.rect.y,
                                'skill_name': s.skill_name,
                                'direction': s.direction,
                                'frame_index': s.frame_index # Send frame index for animation
                            })

                        player_data = {
                            'id': self.player_id,
                            'username': self.username,
                            'x': player.rect.x,
                            'y': player.rect.y,
                            'action': player.action,
                            'frame_index': player.frame_index,
                            'flip': player.flip,
                            'char_type': player.char_type,
                            'hp': player.health,
                            'max_hp': player.max_health,
                            'is_hit': player.is_hit,
                            'hit_cooldown': player.hit_cooldown,
                            'projectiles': projectiles_data,
                            'skills': skills_data
                        }
                        
                        # Prepare Mob Data (If Host)
                        mob_updates = {}
                        if self.is_host:
                            for mob in self.mobs:
                                if mob.alive: # Only send alive mobs? Or send dead state?
                                    mob_updates[mob.id] = {
                                        'x': mob.rect.x,
                                        'y': mob.rect.y,
                                        'action': mob.action,
                                        'frame_index': mob.frame_index,
                                        'flip': mob.flip,
                                        'hp': mob.health,
                                        'max_hp': mob.max_health
                                    }
                        
                        # Send and receive
                        
                        # Collect player hits (Host only)
                        player_hits = []
                        if self.is_host:
                            for p in self.all_players:
                                if hasattr(p, 'pending_damage') and p.pending_damage:
                                    # Find ID for this player
                                    # If it's local player
                                    if p == player:
                                        pid = self.player_id
                                    else:
                                        # Find remote player ID
                                        pid = None
                                        for r_id, r_p in self.remote_players.items():
                                            if r_p == p:
                                                pid = r_id
                                                break
                                    
                                    if pid:
                                        for dmg in p.pending_damage:
                                            player_hits.append((pid, dmg))
                                    
                                    p.pending_damage = [] # Clear
                        
                        packet = {
                            'player_data': player_data,
                            'mob_hits': self.frame_hits, # Send hits to server
                            'player_hits': player_hits # Host sends who got hit
                        }
                        if self.is_host:
                            packet['mob_updates'] = mob_updates
                            
                        server_reply = self.network.send(packet)
                        
                        # Process received data
                        if server_reply:
                            self.is_host = server_reply.get('is_host', False)
                            
                            # If Host, process remote hits
                            if self.is_host and 'remote_hits' in server_reply:
                                for mob_id, damage in server_reply['remote_hits']:
                                    # Find mob by ID
                                    for mob in self.mobs:
                                        if mob.id == mob_id and mob.alive:
                                            mob.hit(damage, None) # Apply damage
                                            break
                            
                            # Process Player Hits (Client side)
                            if 'player_hits' in server_reply:
                                for pid, damage in server_reply['player_hits']:
                                    if pid == self.player_id:
                                        # We got hit!
                                        # Apply damage locally
                                        # We use a special flag or just call hit() but ensure we don't loop
                                        # Player.hit() adds to pending_damage, but we are client, so we don't send player_hits.
                                        # So it's safe to call hit()
                                        player.hit(damage)
                            
                            # 1. Update Remote Players
                            all_players_data = server_reply.get('players', {})
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
                                    remote_p.is_hit = p_data.get('is_hit', False)
                                    remote_p.hit_cooldown = p_data.get('hit_cooldown', 0)
                                    # Update animation manually
                                    remote_p.image = remote_p.animation_list[remote_p.action][remote_p.frame_index]
                                    
                                    # Store projectile/skill data for drawing
                                    remote_p.remote_projectiles = p_data.get('projectiles', [])
                                    remote_p.remote_skills = p_data.get('skills', [])
                                    
                                else:
                                    # Create new remote player
                                    new_p = Player(
                                        self.screen,
                                        p_data['char_type'],
                                        p_data['x'],
                                        p_data['y'],
                                        1, # scale
                                        3, # speed
                                        p_data['max_hp'],
                                        None, # mobs
                                        None, # tiles
                                    )
                                    new_p.remote_projectiles = []
                                    new_p.remote_skills = []
                                    self.remote_players[pid] = new_p
                                    self.all_players.add(new_p) # Add to all_players for Mob AI
                                    
                            # Remove disconnected players
                            disconnected_ids = set(self.remote_players.keys()) - current_remote_ids
                            for pid in disconnected_ids:
                                if pid in self.remote_players:
                                    self.all_players.remove(self.remote_players[pid]) # Remove from all_players
                                del self.remote_players[pid]
                                
                            # Draw remote players and their skills
                            for pid, remote_p in self.remote_players.items():
                                remote_p.draw(self.camera_x, self.camera_y)
                                remote_p.draw_remote_projectiles(self.screen, self.camera_x, self.camera_y)
                                # Draw username
                                p_name = "Unknown"
                                for p_data in all_players_data.values():
                                    if p_data and p_data.get('id') == pid:
                                        p_name = p_data.get('username', 'Unknown')
                                        break
                                
                                font = pygame.font.SysFont("Arial", 14)
                                name_surf = font.render(p_name, True, (255, 255, 255))
                                name_rect = name_surf.get_rect(center=(remote_p.rect.centerx - self.camera_x, remote_p.rect.top - 10 - self.camera_y))
                                self.screen.blit(name_surf, name_rect)
                                
                                # Draw remote projectiles
                                # We need to load projectile images. 
                                # Optimization: Load them once or use Player's existing logic if possible.
                                # Since we don't have the objects, we just draw the images at the positions.
                                # We can use the local player's projectile loading logic or just load them here.
                                # Better: Add a method in Player to draw_remote_projectiles
                                remote_p.draw_remote_projectiles(self.screen, self.camera_x, self.camera_y)

                            # 2. Update Mobs (If Client)
                            if not self.is_host:
                                mob_states = server_reply.get('mobs', {})
                                for mob in self.mobs:
                                    if mob.id in mob_states:
                                        m_data = mob_states[mob.id]
                                        mob.rect.x = m_data['x']
                                        mob.rect.y = m_data['y']
                                        mob.action = m_data['action']
                                        mob.frame_index = m_data['frame_index']
                                        mob.flip = m_data['flip']
                                        mob.health = m_data['hp']
                                        # Update image
                                        if mob.action < len(mob.animation_list) and mob.frame_index < len(mob.animation_list[mob.action]):
                                            mob.image = mob.animation_list[mob.action][mob.frame_index]

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
        self.map = Map(self.screen, self.all_players, self.map_id)
        self.mobs = self.map.get_mobs()
        # Get map boundaries to pass to player
        map_bounds = self.map.get_map_bounds()
        # Get spawn point from map
        spawn_x, spawn_y = self.map.get_spawn_point()
        # Spawn Player (Would move to Map class on next update)
        player = Player(self.screen, "Thief", spawn_x, spawn_y, 1, 3, 150, self.mobs, self.map.tiles, self.map.slope_tiles, self.map.lines, map_bounds)
        self.players.add(player)
        self.all_players.add(player)
        # Initialize camera to player's starting position
        self.camera_x = player.rect.centerx - self.VIRTUAL_WIDTH // 2
        self.camera_y = player.rect.centery - self.VIRTUAL_HEIGHT // 2

    def draw_bg(self):
        self.screen.fill((255, 255, 255))
        if self.map:
            self.map.draw(self.screen, self.camera_x, self.camera_y)


if __name__ == "__main__":
    game = Game()
