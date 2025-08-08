import pytest
from Qubitrix.sounds import Effects

def test_singleton():
    e1 = Effects()
    e2 = Effects()
    assert e1 is e2

def test_lazy_loading():
    effects = Effects()
    # This assumes you have a sound file named "sonic_drop.wav" in the sounds folder - this may fail currently due to the effect's name giving the entire file path from the drive
    effect = effects._load_sound("sonic_drop")
    assert effect.name == "sonic_drop"
