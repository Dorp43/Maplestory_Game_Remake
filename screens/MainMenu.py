import pygame
from UI.UIElements import Button, Label

class MainMenu:
    def __init__(self, screen_width, screen_height, on_singleplayer, on_multiplayer, on_settings, on_quit):
        self.width = screen_width
        self.height = screen_height
        self.on_singleplayer = on_singleplayer
        self.on_multiplayer = on_multiplayer
        self.on_settings = on_settings
        self.on_quit = on_quit
        
        self.font = pygame.font.SysFont("Arial", 30, bold=True)
        self.title_font = pygame.font.SysFont("Arial", 60, bold=True)
        
        self.buttons = []
        self.setup_ui()

    def setup_ui(self):
        # Center buttons
        btn_width = 250
        btn_height = 60
        spacing = 20
        start_y = self.height // 2 - (btn_height * 3 + spacing * 2) // 2 + 50
        center_x = self.width // 2 - btn_width // 2
        
        self.buttons.append(Button(center_x, start_y, btn_width, btn_height, "Singleplayer", self.font, action=self.on_singleplayer))
        self.buttons.append(Button(center_x, start_y + btn_height + spacing, btn_width, btn_height, "Multiplayer", self.font, action=self.on_multiplayer))
        self.buttons.append(Button(center_x, start_y + (btn_height + spacing) * 2, btn_width, btn_height, "Settings", self.font, action=self.on_settings))
        self.buttons.append(Button(center_x, start_y + (btn_height + spacing) * 3, btn_width, btn_height, "Quit Game", self.font, action=self.on_quit))

    def update(self, virtual_mouse_pos, events):
        for btn in self.buttons:
            btn.update_with_mouse(virtual_mouse_pos, events)

    def draw(self, screen):
        # Draw background (could be an image later, for now a gradient or solid color)
        screen.fill((240, 248, 255)) # AliceBlue
        
        # Draw Title
        title_surf = self.title_font.render("Maplestory Remake", True, (255, 140, 0))
        title_rect = title_surf.get_rect(center=(self.width // 2, self.height // 4))
        screen.blit(title_surf, title_rect)
        
        # Draw Buttons
        for btn in self.buttons:
            btn.draw(screen)
