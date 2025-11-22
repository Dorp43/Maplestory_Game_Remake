import pygame

class UIElement:
    def __init__(self, x, y, width, height):
        self.rect = pygame.Rect(x, y, width, height)
        self.active = True

    def update(self, events):
        pass

    def draw(self, screen):
        pass

class Button(UIElement):
    def __init__(self, x, y, width, height, text, font, action=None, bg_color=(255, 165, 0), hover_color=(255, 200, 0), text_color=(255, 255, 255), border_color=(200, 100, 0)):
        super().__init__(x, y, width, height)
        self.text = text
        self.font = font
        self.action = action
        self.bg_color = bg_color
        self.hover_color = hover_color
        self.text_color = text_color
        self.border_color = border_color
        self.is_hovered = False

    def update(self, events):
        pass

    def update_with_mouse(self, virtual_mouse_pos, events):
        self.is_hovered = self.rect.collidepoint(virtual_mouse_pos)
        
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.is_hovered and self.action:
                    self.action()

    def draw(self, screen):
        color = self.hover_color if self.is_hovered else self.bg_color
        # Draw shadow
        shadow_rect = self.rect.copy()
        shadow_rect.y += 4
        pygame.draw.rect(screen, (50, 50, 50, 100), shadow_rect, border_radius=10)
        
        # Draw button body
        pygame.draw.rect(screen, color, self.rect, border_radius=10)
        pygame.draw.rect(screen, self.border_color, self.rect, width=3, border_radius=10) # Border
        
        # Draw text with shadow
        text_surf = self.font.render(self.text, True, self.text_color)
        text_shadow = self.font.render(self.text, True, (0, 0, 0))
        
        text_rect = text_surf.get_rect(center=self.rect.center)
        screen.blit(text_shadow, (text_rect.x + 2, text_rect.y + 2))
        screen.blit(text_surf, text_rect)

class TextInput(UIElement):
    def __init__(self, x, y, width, height, font, placeholder="", text="", text_color=(0, 0, 0), bg_color=(255, 255, 255)):
        super().__init__(x, y, width, height)
        self.font = font
        self.text = text
        self.placeholder = placeholder
        self.text_color = text_color
        self.bg_color = bg_color
        self.is_focused = False
        self.cursor_visible = True
        self.cursor_timer = 0

    def update_with_mouse(self, virtual_mouse_pos, events):
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.rect.collidepoint(virtual_mouse_pos):
                    self.is_focused = True
                else:
                    self.is_focused = False
            
            if event.type == pygame.KEYDOWN and self.is_focused:
                if event.key == pygame.K_BACKSPACE:
                    self.text = self.text[:-1]
                else:
                    # Filter for printable characters
                    if len(event.unicode) > 0 and event.unicode.isprintable():
                        self.text += event.unicode

    def draw(self, screen):
        pygame.draw.rect(screen, self.bg_color, self.rect, border_radius=5)
        border_color = (0, 120, 215) if self.is_focused else (100, 100, 100)
        pygame.draw.rect(screen, border_color, self.rect, width=2, border_radius=5)
        
        display_text = self.text if self.text else self.placeholder
        color = self.text_color if self.text else (150, 150, 150)
        
        text_surf = self.font.render(display_text, True, color)
        # Clip text if it's too long
        screen.set_clip(self.rect.inflate(-10, -10))
        screen.blit(text_surf, (self.rect.x + 5, self.rect.centery - text_surf.get_height() // 2))
        screen.set_clip(None)

class Label(UIElement):
    def __init__(self, x, y, text, font, color=(0, 0, 0)):
        # Width and height are dynamic based on text
        super().__init__(x, y, 0, 0)
        self.text = text
        self.font = font
        self.color = color

    def draw(self, screen):
        text_surf = self.font.render(self.text, True, self.color)
        screen.blit(text_surf, (self.rect.x, self.rect.y))
