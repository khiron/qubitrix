import pygame
from controllers.abstract_controller import AbstractController, GameEvent # This also gives a "missing import" warning in VSCode, but still works for some reason

class KeyboardController(AbstractController):
    MODIFIER_KEY_ID = 0 # Set to KMOD_LSHIFT. This current implementation only allows for detecting if keys such as Shift/Ctrl/Alt are pressed, and is thus subject to change.
    KEY_MAP = {
        pygame.K_d: GameEvent.MOVE_PIECE_RIGHT,
        pygame.K_w: GameEvent.MOVE_PIECE_FORWARD,
        pygame.K_a: GameEvent.MOVE_PIECE_LEFT,
        pygame.K_s: GameEvent.MOVE_PIECE_BACKWARD,
        pygame.K_k: GameEvent.ROTATE_GRID_CLOCKWISE,
        pygame.K_l: GameEvent.ROTATE_GRID_COUNTERCLOCKWISE,
        pygame.K_SPACE: GameEvent.LOWER_PIECE,
        pygame.K_ESCAPE: GameEvent.PAUSE_GAME,
        pygame.K_SEMICOLON: GameEvent.HOLD_PIECE
    }
    SHIFT_KEY_MAP = {
        pygame.K_d: GameEvent.ROTATE_PIECE_RIGHT,
        pygame.K_w: GameEvent.ROTATE_PIECE_FORWARD,
        pygame.K_a: GameEvent.ROTATE_PIECE_LEFT,
        pygame.K_s: GameEvent.ROTATE_PIECE_BACKWARD,
        pygame.K_k: GameEvent.ROTATE_PIECE_CLOCKWISE,
        pygame.K_l: GameEvent.ROTATE_PIECE_COUNTERCLOCKWISE,
        pygame.K_SPACE: GameEvent.SONIC_DROP_PIECE,
        pygame.K_ESCAPE: GameEvent.QUIT_GAME, # This should only pause the game if it is currently playing, and it should only quit the game on the pause or home screens.
        pygame.K_SEMICOLON: GameEvent.HOLD_PIECE # This is unchanged upon holding Shift.
    }

    def process_events(self):
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                # Whether the modifier key is held or not is determined through a bitwise AND function between pygame.key.get_mods() and whichever bit MODIFIER_KEY_ID is set to.
                action = self.KEY_MAP.get(event.key) if not bool(pygame.key.get_mods() & 2**self.MODIFIER_KEY_ID) else self.SHIFT_KEY_MAP.get(event.key)
                if action:
                    self.notify(action)
