import pytest
from Qubitrix.sounds import Effects

def test_singleton():
    e1 = Effects()
    e2 = Effects()
    assert e1 is e2

def test_lazy_loading():
    import pygame
    pygame.mixer.init()
    
    effects = Effects()
    # This assumes you have a sound file named "sonic_drop.wav" in the sounds folder
    effect = effects._load_sound("sonic_drop")
    assert effect.name == "sonic_drop"