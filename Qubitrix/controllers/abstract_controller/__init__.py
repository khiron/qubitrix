from abc import ABC, abstractmethod
from typing import Callable
from enum import Enum

# Define the event alphabet as an Enum class
class GameEvent(Enum):
    MOVE_PIECE_RIGHT = 0
    MOVE_PIECE_FORWARD = 1
    MOVE_PIECE_LEFT = 2
    MOVE_PIECE_BACKWARD = 3
    ROTATE_GRID_CLOCKWISE = 4
    ROTATE_GRID_COUNTERCLOCKWISE = 5
    LOWER_PIECE = 6
    PAUSE_GAME = 7
    HOLD_PIECE = 8
    ROTATE_PIECE_RIGHT = 9
    ROTATE_PIECE_FORWARD = 10
    ROTATE_PIECE_LEFT = 11
    ROTATE_PIECE_BACKWARD = 12
    ROTATE_PIECE_CLOCKWISE = 13
    ROTATE_PIECE_COUNTERCLOCKWISE = 14
    SONIC_DROP_PIECE = 15
    QUIT_GAME = 16 # This should only pause the game if it is currently playing, and it should only quit the game on the pause or home screens.
    REVEAL_GRID = 17 # Only to be done on the Game Over screen. Currently is not able to be called.

class AbstractController(ABC):
    def __init__(self):
        self.subscribers = []

    def subscribe(self, callback: Callable[[GameEvent], None]): # this typing seems to not align with what I have to do?
        """Subscribe a callback to receive controller events."""
        self.subscribers.append(callback)

    def notify(self, event):
        """Notify all subscribers of an event."""
        for callback in self.subscribers:
            callback(event)

    @abstractmethod
    def process_events(event):
        """Processes input events and notify subscribers."""
        print(event)
        pass
