import pygame
from UI.UIElements import Button, Label

class SettingsMenu:
    def __init__(self, screen_width, screen_height, on_back, toggle_fullscreen, toggle_audio):
        self.width = screen_width
        self.height = screen_height
        self.on_back = on_back
        self.toggle_fullscreen = toggle_fullscreen
        self.toggle_audio = toggle_audio
        
        self.font = pygame.font.SysFont("Arial", 24)
        self.title_font = pygame.font.SysFont("Arial", 40, bold=True)
        
        self.ui_elements = []
        self.setup_ui()

    def setup_ui(self):
        center_x = self.width // 2
        start_y = self.height // 3
        
        # Title
        self.ui_elements.append(Label(center_x - 100, self.height // 6, "Settings", self.title_font))
        
        # Buttons
        btn_width = 200
        btn_height = 50
        spacing = 30
        
        # Display Mode Toggle
        self.ui_elements.append(Button(center_x - btn_width // 2, start_y, btn_width, btn_height, "Toggle Window/Full", self.font, action=self.toggle_fullscreen))
        
        # Audio Toggle
        self.ui_elements.append(Button(center_x - btn_width // 2, start_y + btn_height + spacing, btn_width, btn_height, "Toggle Audio", self.font, action=self.toggle_audio))
        
        # Back Button
        self.ui_elements.append(Button(center_x - btn_width // 2, start_y + (btn_height + spacing) * 2, btn_width, btn_height, "Back", self.font, action=self.on_back, bg_color=(200, 50, 50), hover_color=(230, 70, 70)))

    def update(self, virtual_mouse_pos, events):
        for element in self.ui_elements:
            if hasattr(element, 'update_with_mouse'):
                element.update_with_mouse(virtual_mouse_pos, events)

    def draw(self, screen):
        screen.fill((230, 240, 255))
        
        title_surf = self.title_font.render("Settings", True, (0, 0, 0))
        title_rect = title_surf.get_rect(center=(self.width // 2, self.height // 6))
        screen.blit(title_surf, title_rect)
        
        for element in self.ui_elements:
            element.draw(screen)
