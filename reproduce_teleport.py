
import sys
import os
import pygame
from unittest.mock import MagicMock

# Mock pygame setup
pygame.init = MagicMock()
pygame.display = MagicMock()
pygame.sprite = MagicMock()
pygame.image = MagicMock()
pygame.transform = MagicMock()
pygame.time = MagicMock()
pygame.font = MagicMock()
pygame.mixer = MagicMock()

# Mock Sprite class
class MockSprite:
    def __init__(self):
        self.groups = MagicMock()
    def add(self, *groups):
        pass
    def kill(self):
        pass

pygame.sprite.Sprite = MockSprite
pygame.sprite.Group = MagicMock

# Mock Rect
class MockRect:
    def __init__(self, x, y, w, h):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
    
    @property
    def left(self): return self.x
    @left.setter
    def left(self, val): self.x = val
    
    @property
    def right(self): return self.x + self.w
    @right.setter
    def right(self, val): self.x = val - self.w
    
    @property
    def top(self): return self.y
    @top.setter
    def top(self, val): self.y = val
    
    @property
    def bottom(self): return self.y + self.h
    @bottom.setter
    def bottom(self, val): self.y = val - self.h
    
    @property
    def centerx(self): return self.x + self.w / 2
    @centerx.setter
    def centerx(self, val): self.x = val - self.w / 2
    
    @property
    def centery(self): return self.y + self.h / 2
    @centery.setter
    def centery(self, val): self.y = val - self.h / 2
    
    @property
    def width(self): return self.w
    
    @property
    def height(self): return self.h
    
    @property
    def size(self): return (self.w, self.h)

    def colliderect(self, other):
        return (self.x < other.x + other.w and
                self.x + self.w > other.x and
                self.y < other.y + other.h and
                self.y + self.h > other.y)
    
    def copy(self):
        return MockRect(self.x, self.y, self.w, self.h)

pygame.Rect = MockRect

# Mock dependencies
sys.modules['skills.Skill'] = MagicMock()
sys.modules['skills.Projectile'] = MagicMock()
sys.modules['entities.HealthBar'] = MagicMock()

# Mock os.listdir
original_listdir = os.listdir
def mock_listdir(path):
    if "sprites" in path:
        return ["0.png"]
    return original_listdir(path)
os.listdir = mock_listdir

sys.path.append(os.getcwd())

# Mock image loading
pygame.image.load = MagicMock(return_value=MagicMock())
pygame.transform.scale = MagicMock(return_value=MagicMock())
pygame.transform.scale.return_value.get_rect = MagicMock(return_value=MockRect(0, 0, 50, 80))

from Player import Player

def test_teleportation():
    print("Starting teleportation test...")
    
    # Setup lines: Line 1 (0, 500) -> (100, 500) connected to Line 2 (100, 500) -> (200, 400)
    # A flat line connected to a STEEP upward slope (45 degrees)
    lines = [
        {"x1": 0, "y1": 500, "x2": 100, "y2": 500},
        {"x1": 100, "y1": 500, "x2": 200, "y2": 400}
    ]
    
    screen = MagicMock()
    player = Player(screen, "char_type", 50, 400, 1, 5, 100, [], [], lines, None)
    
    # Manually set rect
    player.rect = MockRect(50, 420, 50, 80) # 50 wide, 80 tall. Bottom at 500.
    player.rect.bottom = 500
    
    GRAVITY = 1
    player.moving_right = True
    
    prev_x = player.rect.x
    prev_y = player.rect.bottom
    
    failed = False
    for i in range(30):
        player.move(GRAVITY)
        curr_x = player.rect.x
        curr_y = player.rect.bottom
        
        print(f"Frame {i}: Pos ({curr_x}, {curr_y}) LineID: {player.current_line_id}")
        
        # Check for teleportation (large jump in X or Y)
        # Normal movement is speed=5.
        if abs(curr_x - prev_x) > 10:
            print(f"FAILURE: Teleported X! Jumped from {prev_x} to {curr_x}")
            failed = True
        
        # Check for premature slope snapping
        # If we are well before the connection point (x=100), Y should be 500
        # Center X is x + 25. Connection is at 100.
        # If Center X < 95, we should definitely be on the flat line (Y=500)
        center_x = curr_x + 25
        if center_x < 95:
            if abs(curr_y - 500) > 1:
                print(f"FAILURE: Premature slope snap! At center_x={center_x}, Y={curr_y} (Expected 500)")
                failed = True
        
        # Y change should be reasonable. On 45 deg slope, dy = dx = 5.
        if abs(curr_y - prev_y) > 20:
             print(f"FAILURE: Teleported Y! Jumped from {prev_y} to {curr_y}")
             failed = True
             
        prev_x = curr_x
        prev_y = curr_y
        
        if failed:
            break

    if not failed:
        print("SUCCESS: No teleportation detected.")

if __name__ == "__main__":
    test_teleportation()
