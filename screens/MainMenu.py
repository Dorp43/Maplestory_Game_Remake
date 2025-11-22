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
        start_y = self.height // 2 - (btn_height * 3 + spacing * 2) // 2 + 80
        center_x = self.width // 2 - btn_width // 2
        
        # Maplestory Orange Buttons
        btn_bg = (255, 165, 0)
        btn_hover = (255, 200, 0)
        btn_border = (200, 100, 0)
        
        self.buttons.append(Button(center_x, start_y, btn_width, btn_height, "Singleplayer", self.font, action=self.on_singleplayer, bg_color=btn_bg, hover_color=btn_hover, border_color=btn_border))
        self.buttons.append(Button(center_x, start_y + btn_height + spacing, btn_width, btn_height, "Multiplayer", self.font, action=self.on_multiplayer, bg_color=btn_bg, hover_color=btn_hover, border_color=btn_border))
        self.buttons.append(Button(center_x, start_y + (btn_height + spacing) * 2, btn_width, btn_height, "Settings", self.font, action=self.on_settings, bg_color=btn_bg, hover_color=btn_hover, border_color=btn_border))
        self.buttons.append(Button(center_x, start_y + (btn_height + spacing) * 3, btn_width, btn_height, "Quit Game", self.font, action=self.on_quit, bg_color=(200, 50, 50), hover_color=(230, 70, 70), border_color=(150, 30, 30)))

    def update(self, virtual_mouse_pos, events):
        for btn in self.buttons:
            btn.update_with_mouse(virtual_mouse_pos, events)

    def draw(self, screen):
        # Draw background
        try:
            bg_img = pygame.image.load('sprites/backgrounds/menu_bg.png').convert()
            bg_img = pygame.transform.scale(bg_img, (self.width, self.height))
            screen.blit(bg_img, (0, 0))
        except Exception as e:
            print(f"Error loading background: {e}")
            screen.fill((240, 248, 255)) # Fallback
        
        # Draw Title Shadow
        title_text = "Maplestory Remake"
        title_shadow = self.title_font.render(title_text, True, (0, 0, 0))
        title_surf = self.title_font.render(title_text, True, (255, 140, 0))
        
        title_rect = title_surf.get_rect(center=(self.width // 2, self.height // 4))
        screen.blit(title_shadow, (title_rect.x + 4, title_rect.y + 4))
        screen.blit(title_surf, title_rect)
        
        # Draw Buttons
        for btn in self.buttons:
            btn.draw(screen)
