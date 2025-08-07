import os
from pygame import mixer

# Qubitrix - Sound Effects Module
# This module provides functionality to load and play sound effects in a game.
# It decouples the game logic from the mechanism used to play sounds, 
# allowing for easy replacement or modification of sound playback methods 
# without changing the game code.

"""
Design patterns used in this module:
===================================

1. Singleton Pattern: The Effects class is a singleton, meaning only one instance exists throughout the application.
   This is useful for managing sound effects globally because you don't have to keep track of instance variables.
2. Factory Pattern: The `Effects` class acts as a factory for creating `Effect` objects 
   using the _load_sound method, which initializes Effect instances if there is a .wav file found in the local directory.
   The rest of the code doesn't have to know about the details of how Effect objects are created, or where the .wav files are 
   stored.  This means later on we can change effects to be loaded from a database or a different source without changing the 
   game code.  The is called `decoupling`, where the game code is not tightly coupled to the sound loading mechanism, and you 
   can change either independently. 
3. Proxy Pattern: The `Effect` class acts as a proxy for the actual pygame.mixer.Sound object, encapsulating the details of 
   how the sound is played.  The game code interacts with the `Effect` class to play sounds, without needing to know
   the specifics of how the sound is loaded or played.  
4. Facade Pattern: The Effects class provides a simple interface to access sound effects by name or as attributes,
   hiding the complexity of managing sound files and their playback. This allows the game code to interact
   with sound effects in a straightforward way, without needing to understand the underlying details of how sounds
   are loaded and played.

Finally we use a lazy loading design idiom, where sound effects are loaded only when they are first accessed.
This improves performance by avoiding unnecessary loading of sounds that may never be used.  We also have the ability to 
call load_all_sounds to preload all sound effects at once, which can be useful for performance in some cases.

These patterns help make the sound management system flexible, maintainable, and easy to use within the game code.   
"""

DEFAULT_MAXTIME = 100
class Effect:
    """Represents a sound effect that knows how to play itself"""
    def __init__(self, sound_file: str, loops:int= 0, maxtime:int= DEFAULT_MAXTIME, fade_ms:int = 0):
        """
            Initialize the sound effect.
            Args:
                sound_file : Path to the sound file.
                loops (Optional): Number of times to loop the sound. Default is 0 (no looping).
                maxtime (Optional): Maximum time in milliseconds to play the sound. Default is 100ms.
                fade_ms (Optional): Fade in/out time in milliseconds. Default is 0ms.
        """
        self.name = sound_file.split('/')[-1].split('.')[0] # Extract name from file path
        self.sound = mixer.Sound(sound_file)
        self.loops = loops
        self.maxtime = maxtime
        self.fade_ms = fade_ms
    
    def play(self, loops=None, maxtime=None, fade_ms = None):
        """
            Play the sound effect using pygame.mixer.
            Args:
                loops (int): Number of times to loop the sound. Default is 0 (no looping).
                maxtime (int): Maximum time in milliseconds to play the sound. Default is 100ms.
                fade_ms (int): Fade in/out time in milliseconds. Default is 0ms.
        """
        mixer.Sound.play(self.sound, 
                         loops if loops is not None else self.loops, 
                         maxtime if maxtime is not None else self.maxtime, 
                         fade_ms if fade_ms is not None else self.fade_ms)
    
class Effects:
    """
    Singleton class to manage sound effects
    The Effects class loads all sound effects from the current directory and provides
    a way to access them by name or as attributes.

    What is a Singleton?
    --------------------
    A singleton is a design pattern that makes sure only one instance of a class can ever exist.
    This is useful when you want to have a single, shared resource (like a sound manager) that
    is used everywhere in your program. If you try to create another Effects object, you will
    always get the same one that was created first.  

    In this code, we use the __new__ method to check if an instance already exists.
    `__new__(cls)` is a special method in Python that is called when you create a new object, 
    If _instance already exists, we return it. If not, we call the __new__ of the base object class (super().__new__(cls))
    to actually create the instance and we store it in the _instance class variable.
    This way, there is always only ever one Effects object.

    We still need to guard the __init__ method to ensure that it only initializes the instance once.
    This is done by checking if the sounds attribute doesn't exist, which means the instance has not been initialized yet.
    """
    _instance = None # Singleton instance of Effects, the underbar _instance is a convention to indicate it's a private variable
    def __new__(cls): # Singleton pattern to ensure only one instance of Effects exists
        if cls._instance is None: # if we have never created an instance of Effects before
            cls._instance = super().__new__(cls) # create a new instance of Effects and store it in the _instance variable
        return cls._instance
    
    def __init__(self):
        if 'sounds' in self.__dict__:
            return  # Already initialized
        self.sounds = {}
        self.sounds_dir = os.path.dirname(__file__)

    def load_all_sounds(self):
        """
        Loads all .wav files in the directory into the cache.
        """
        for fname in os.listdir(self.sounds_dir):
            if fname.lower().endswith('.wav'):
                name = fname.rsplit('.', 1)[0]
                if name not in self.sounds:
                    path = os.path.join(self.sounds_dir, fname)
                    self.sounds[name] = Effect(path)

    def _load_sound(self, name):
        """
        Loads a single sound by name if not already loaded.
        """
        fname = f'{name}.wav'
        path = os.path.join(self.sounds_dir, fname)
        if os.path.isfile(path):
            self.sounds[name] = Effect(path)
            return self.sounds[name]
        raise AttributeError(f"No sound effect named '{name}' found.")


    def __getitem__(self, key):  # Allows access to sound effects by name eg: Effects["my_named_effect"].play() - this has to be used with file names that start with a number.
        return self._load_sound(key) if key not in self.sounds else self.sounds[key] # lazy load the sound if it is not already loaded
    
    def __getattr__(self, name): # Allows access to sound effects as attributes eg: Effects.my_named_effect.play()
        try:
            return self.sounds[name]
        except KeyError:
            raise AttributeError(f"'Effects' object has no attribute '{name}'")
