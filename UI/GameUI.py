import pygame

class GameUI:
    def __init__(self, screen):
        self.screen = screen
        self.font = pygame.font.SysFont("Arial", 14, bold=True)
        self.level_font = pygame.font.SysFont("Arial", 20, bold=True)
        self.level_num_font = pygame.font.SysFont("Arial", 22, bold=True)

    def draw_bar(self, x, y, width, height, current, max_val, color_start, color_end, bg_color):
        # Draw background
        pygame.draw.rect(self.screen, bg_color, (x, y, width, height), border_radius=5)
        
        if max_val > 0:
            ratio = max(0, min(1, current / max_val))
            fill_width = int(width * ratio)
            if fill_width > 0:
                # Draw gradient fill (simulated)
                rect_fill = pygame.Rect(x, y, fill_width, height)
                pygame.draw.rect(self.screen, color_end, rect_fill, border_radius=5)
                
                # Glossy Highlight (Top half, lighter)
                highlight_rect = pygame.Rect(x, y, fill_width, height // 2)
                # Use a transparent surface for highlight to blend better
                s = pygame.Surface((fill_width, height // 2), pygame.SRCALPHA)
                s.fill((255, 255, 255, 50)) # White with alpha
                self.screen.blit(s, (x, y))
                
        # Border (Draw last to cover edges)
        pygame.draw.rect(self.screen, (180, 180, 180), (x, y, width, height), 1, border_radius=5)

    def draw(self, player):
        screen_width = self.screen.get_width()
        screen_height = self.screen.get_height()
        
        # Draw the bar background at the bottom
        bar_height = 60 # Reduced height as bars are horizontal
        
        # Draw semi-transparent background (Dark Grey / Metallic)
        s = pygame.Surface((screen_width, bar_height))
        s.set_alpha(230)
        s.fill((30, 30, 30))
        self.screen.blit(s, (0, screen_height - bar_height))
        
        # Draw top border (Gold/Metallic)
        pygame.draw.line(self.screen, (150, 150, 150), (0, screen_height - bar_height), (screen_width, screen_height - bar_height), 2)
        
        # Layout Constants
        padding = 10
        current_x = padding
        bar_y = screen_height - 40
        bar_height_inner = 25
        
        # --- Level & Name Section ---
        # [LV. XX] [Name]
        # Level Box
        level_box_width = 60
        level_box_height = 30
        level_y = screen_height - 45
        
        # "LV." text
        lv_label = self.level_font.render("LV.", True, (255, 255, 255))
        self.screen.blit(lv_label, (current_x, level_y + 2))
        current_x += lv_label.get_width() + 5
        
        # Level Number Box (Orange)
        box_width = 40
        box_height = 30
        pygame.draw.rect(self.screen, (200, 100, 0), (current_x, level_y - 2, box_width, box_height), border_radius=5)
        pygame.draw.rect(self.screen, (255, 150, 0), (current_x, level_y - 2, box_width, box_height // 2), border_radius=5) # Highlight
        
        level_text = self.level_num_font.render(str(player.level), True, (255, 255, 255))
        self.screen.blit(level_text, (current_x + box_width//2 - level_text.get_width()//2, level_y - 2 + box_height//2 - level_text.get_height()//2))
        current_x += box_width + 15
        
        # --- Bars Section ---
        # Calculate remaining width for bars
        # We have 3 bars: HP, MP, EXP
        # Let's give them equal width or specific ratios
        # Available width
        remaining_width = screen_width - current_x - padding
        # Let's say HP: 30%, MP: 30%, EXP: 40% (or similar)
        # Or fixed widths if screen is wide enough
        
        bar_width = (remaining_width - 40) // 3 # 3 bars with gaps
        
        # HP Bar
        self.draw_bar(current_x, bar_y, bar_width, bar_height_inner, player.health, player.max_health, (255, 100, 100), (200, 0, 0), (50, 0, 0))
        # Text above
        hp_label = self.font.render(f"HP [{player.health}/{player.max_health}]", True, (255, 255, 255))
        self.screen.blit(hp_label, (current_x, bar_y - 15))
        current_x += bar_width + 20
        
        # MP Bar
        self.draw_bar(current_x, bar_y, bar_width, bar_height_inner, player.mana, player.max_mana, (100, 100, 255), (0, 0, 200), (0, 0, 50))
        # Text above
        mp_label = self.font.render(f"MP [{player.mana}/{player.max_mana}]", True, (255, 255, 255))
        self.screen.blit(mp_label, (current_x, bar_y - 15))
        current_x += bar_width + 20
        
        # EXP Bar
        exp_ratio = player.exp / player.max_exp if player.max_exp > 0 else 0
        exp_percent = int(exp_ratio * 10000) / 100 # 2 decimal places
        self.draw_bar(current_x, bar_y, bar_width, bar_height_inner, player.exp, player.max_exp, (255, 255, 100), (200, 200, 0), (50, 50, 0))
        # Text above
        exp_label = self.font.render(f"EXP {player.exp}[{exp_percent}%]", True, (255, 255, 255))
        self.screen.blit(exp_label, (current_x, bar_y - 15))
        
        # Draw segments for EXP
        for i in range(1, 10):
            seg_x = current_x + (bar_width * (i / 10))
            pygame.draw.line(self.screen, (50, 50, 50), (seg_x, bar_y), (seg_x, bar_y + bar_height_inner), 1)
