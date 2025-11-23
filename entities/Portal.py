import pygame
import os


class Portal(pygame.sprite.Sprite):
    """
    Portal entity that allows players to transition between maps.
    Displays an animated portal sprite and detects player collision.
    """

    def __init__(self, x, y, target_map_id, base_dir=None):
        """
        Initialize a portal.
        
        Args:
            x: World X position
            y: World Y position
            target_map_id: The map ID to transition to when portal is used
            base_dir: Base directory for loading sprites (optional)
        """
        super().__init__()
        self.x = x
        self.y = y
        self.target_map_id = target_map_id
        
        # Animation settings
        self.animation_frames = []
        self.current_frame = 0
        self.animation_speed = 10  # FPS for animation
        self.animation_timer = 0
        
        # Load portal sprites
        if base_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        portal_dir = os.path.join(base_dir, "sprites", "entities", "portal")
        
        # Load all 8 portal frames (pv_0.png through pv_7.png)
        for i in range(8):
            frame_path = os.path.join(portal_dir, f"pv_{i}.png")
            if os.path.exists(frame_path):
                try:
                    frame = pygame.image.load(frame_path).convert_alpha()
                    self.animation_frames.append(frame)
                except pygame.error as e:
                    print(f"[Portal] Error loading frame {i}: {e}")
        
        if not self.animation_frames:
            # Create a fallback surface if no frames loaded
            fallback = pygame.Surface((60, 80))
            fallback.fill((100, 100, 255))
            self.animation_frames.append(fallback)
            print("[Portal] Warning: No portal frames loaded, using fallback")
        
        # Set initial image and rect
        self.image = self.animation_frames[0]
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y
        
        # Collision rect (slightly smaller for better feel)
        self.collision_rect = pygame.Rect(
            x + self.rect.width // 4,
            y + self.rect.height // 4,
            self.rect.width // 2,
            self.rect.height // 2
        )
    
    def update(self, dt):
        """
        Update portal animation.
        
        Args:
            dt: Delta time in milliseconds
        """
        if len(self.animation_frames) <= 1:
            return
        
        # Update animation timer
        self.animation_timer += dt / 1000.0  # Convert to seconds
        
        # Calculate frame based on animation speed
        frame_duration = 1.0 / self.animation_speed
        if self.animation_timer >= frame_duration:
            self.animation_timer = 0
            self.current_frame = (self.current_frame + 1) % len(self.animation_frames)
            self.image = self.animation_frames[self.current_frame]
    
    def draw(self, surface, camera_x=0, camera_y=0):
        """
        Draw the portal on the given surface with camera offset.
        
        Args:
            surface: Pygame surface to draw on
            camera_x: Camera X offset
            camera_y: Camera Y offset
        """
        screen_x = self.x - camera_x
        screen_y = self.y - camera_y
        surface.blit(self.image, (screen_x, screen_y))
    
    def check_collision(self, player_rect):
        """
        Check if player is colliding with this portal.
        
        Args:
            player_rect: Player's pygame.Rect
            
        Returns:
            True if colliding, False otherwise
        """
        return self.collision_rect.colliderect(player_rect)
    
    def get_target_map_id(self):
        """Get the target map ID for this portal."""
        return self.target_map_id
    
    def set_target_map_id(self, map_id):
        """Set the target map ID for this portal."""
        self.target_map_id = map_id
    
    def get_position(self):
        """Get portal position as (x, y) tuple."""
        return (self.x, self.y)
