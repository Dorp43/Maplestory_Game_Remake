import pygame
from UI.UIElements import Button, TextInput, Label

class MultiplayerMenu:
    def __init__(self, screen_width, screen_height, on_connect, on_back):
        self.width = screen_width
        self.height = screen_height
        self.on_connect = on_connect
        self.on_back = on_back
        
        self.font = pygame.font.SysFont("Arial", 24)
        self.title_font = pygame.font.SysFont("Arial", 40, bold=True)
        
        self.ui_elements = []
        self.username_input = None
        self.ip_input = None
        
        self.setup_ui()

    def setup_ui(self):
        center_x = self.width // 2
        start_y = self.height // 3
        
        # Labels and Inputs
        self.ui_elements.append(Label(center_x - 150, start_y, "Username:", self.font))
        self.username_input = TextInput(center_x - 150, start_y + 30, 300, 40, self.font, placeholder="Enter Username")
        self.ui_elements.append(self.username_input)
        
        self.ui_elements.append(Label(center_x - 150, start_y + 90, "Server IP:", self.font))
        self.ip_input = TextInput(center_x - 150, start_y + 120, 300, 40, self.font, placeholder="Enter Server IP")
        self.ui_elements.append(self.ip_input)
        
        # Buttons
        btn_width = 140
        btn_height = 50
        spacing = 20
        
        self.ui_elements.append(Button(center_x - btn_width - spacing // 2, start_y + 200, btn_width, btn_height, "Back", self.font, action=self.on_back, bg_color=(200, 50, 50), hover_color=(230, 70, 70)))
        self.ui_elements.append(Button(center_x + spacing // 2, start_y + 200, btn_width, btn_height, "Connect", self.font, action=self.handle_connect, bg_color=(50, 200, 50), hover_color=(70, 230, 70)))

    def handle_connect(self):
        username = self.username_input.text
        ip = self.ip_input.text
        # Basic validation could go here
        if username and ip:
            self.on_connect(username, ip)

    def update(self, virtual_mouse_pos, events):
        for element in self.ui_elements:
            if hasattr(element, 'update_with_mouse'):
                element.update_with_mouse(virtual_mouse_pos, events)

    def draw(self, screen):
        screen.fill((230, 240, 255))
        
        title_surf = self.title_font.render("Multiplayer Connection", True, (0, 0, 0))
        title_rect = title_surf.get_rect(center=(self.width // 2, self.height // 6))
        screen.blit(title_surf, title_rect)
        
        for element in self.ui_elements:
            element.draw(screen)
