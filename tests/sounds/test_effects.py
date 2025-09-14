import pytest
from Qubitrix.sounds import Effects # This gives a "missing import" warning in VSCode, but still works for some reason

def test_singleton():
    e1 = Effects()
    e2 = Effects()
    assert e1 is e2

def test_lazy_loading():
    effects = Effects()
    # This assumes you have a sound file named "sonic_drop.wav" in the sounds folder
    effect = effects._load_sound("sonic_drop")
    assert effect.name == "sonic_drop"
