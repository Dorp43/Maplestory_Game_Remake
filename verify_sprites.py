import unittest
from unittest.mock import MagicMock, patch
import sys
import os
import importlib

# Mock pygame
sys.modules['pygame'] = MagicMock()
import pygame

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

class TestSpriteLoading(unittest.TestCase):
    def test_player_loading(self):
        # Configure the global pygame mock
        mock_surface = MagicMock()
        pygame.image.load.return_value = mock_surface
        
        # Instantiate Player
        screen = MagicMock()
        mobs = MagicMock()
        tiles = []
        
        # Use explicit patch on the os module object
        with patch.object(os, 'listdir', return_value=['0.png']) as mock_listdir:
            import Player
            # We don't need reload if we patch the os module object itself, 
            # as Player.py's 'os' reference points to the same module object.
            
            Player.Player(screen, 'char', 0, 0, 1, 1, 100, mobs, tiles)
            
            # Verify convert_alpha was called
            sys.stderr.write(f"Player listdir called: {mock_listdir.called}\n")
            sys.stderr.write(f"Player class: {Player.Player}\n")
            self.assertTrue(mock_surface.convert_alpha.called, "Player images should be converted with convert_alpha()")

    def test_mob_loading(self):
        # Configure the global pygame mock
        mock_surface = MagicMock()
        pygame.image.load.return_value = mock_surface
        
        screen = MagicMock()
        players = MagicMock()
        tiles = []
        
        with patch.object(os, 'listdir', return_value=['0.png']) as mock_listdir, \
             patch.object(os.path, 'exists', return_value=True) as mock_exists:
            
            import mobs.Mob
            mobs.Mob.Mob(screen, players, tiles, mob_name="snail")
            
            # Verify convert_alpha was called
            print(f"Mob listdir called: {mock_listdir.called}")
            self.assertTrue(mock_surface.convert_alpha.called, "Mob images should be converted with convert_alpha()")

    def test_skill_loading(self):
        # Configure the global pygame mock
        mock_surface = MagicMock()
        pygame.image.load.return_value = mock_surface
        
        with patch.object(os, 'listdir', return_value=['0.png']) as mock_listdir:
            import skills.Skill
            skills.Skill.Skill(0, 0, 1, "test_skill")
            
            # Verify convert_alpha was called
            print(f"Skill listdir called: {mock_listdir.called}")
            self.assertTrue(mock_surface.convert_alpha.called, "Skill images should be converted with convert_alpha()")

if __name__ == '__main__':
    unittest.main()
