import pygame
from Player import Player

# Mock pygame
pygame.init()
pygame.display.set_mode((100, 100))

# Mock screen
screen = pygame.Surface((800, 600))

# Create Player
p = Player(screen, "Thief", 0, 0, 1, 1, 100)

print(f"Initial Level: {p.level}")
print(f"Initial HP: {p.health}/{p.max_health}")
print(f"Initial MP: {p.mana}/{p.max_mana}")
print(f"Initial EXP: {p.exp}/{p.max_exp}")

# Test Gain EXP
print("\nGaining 50 EXP...")
p.gain_exp(50)
print(f"EXP: {p.exp}/{p.max_exp}")
print(f"Level: {p.level}")

# Test Level Up
print("\nGaining 60 EXP (should level up)...")
p.gain_exp(60)
print(f"EXP: {p.exp}/{p.max_exp}")
print(f"Level: {p.level}")
print(f"HP: {p.health}/{p.max_health}")
print(f"MP: {p.mana}/{p.max_mana}")

# Test Mana Consumption
print("\nConsuming 20 Mana...")
success = p.consume_mana(20)
print(f"Success: {success}")
print(f"MP: {p.mana}/{p.max_mana}")

print("\nConsuming 200 Mana (should fail)...")
success = p.consume_mana(200)
print(f"Success: {success}")
print(f"MP: {p.mana}/{p.max_mana}")

pygame.quit()
