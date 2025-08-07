# This code is subject to refactoring and cleanup.
# we will probably move this to a more appropriate location later, 
# along with a class for managing the game screen.

import os
import pygame

font_dir = os.path.dirname(__file__) 
font_path = os.path.join(font_dir, "qubitrix-font.ttf")

def get_small_font(WINDOW_HEIGHT):
    """
    Returns a small font based on the window height.
    The font size is set to 1/24th of the window height.
    """
    return pygame.font.Font(font_path, int(WINDOW_HEIGHT / 24))

def get_large_font(WINDOW_HEIGHT):
    """
    Returns a large font based on the window height.
    The font size is set to 1/12th of the window height.
    """
    return pygame.font.Font(font_path, int(WINDOW_HEIGHT / 12))
