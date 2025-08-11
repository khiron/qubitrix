import pygame
import sys
import random
import math
from copy import deepcopy
from pygame.locals import QUIT, KEYDOWN, KEYUP

from fonts import get_large_font, get_small_font
from sounds import Effects
from controllers.abstract_controller import AbstractController
from controllers.keyboard_controller import KeyboardController

WINDOW_WIDTH, WINDOW_HEIGHT = 960, 720
ASPECT_RATIO = WINDOW_WIDTH/WINDOW_HEIGHT
FPS = 60
WIDTH, DEPTH, HEIGHT = 4, 4, 12
DEPTH_LEVEL = 0.6 * max(WIDTH, DEPTH) # lower value makes depth stronger
PIECES = [ # tetracubes, float (half) values will have to be converted to int.
    {"centers": [[1,1,-4], [2,1,-4]], "cubes": [[0,1,-4],[1,1,-4],[2,1,-4],[3,1,-4]], "id": 1}, # I piece
    {"centers": [[1.5,1.5,-3.5],[1.5,1.5,-4.5]], "cubes": [[1,1,-4],[1,2,-4],[2,1,-4],[2,2,-4]], "id": 2}, # O piece
    {"centers": [[1,1,-4]], "cubes": [[1,1,-3],[1,1,-4],[1,1,-5],[2,1,-5]], "id": 3}, # L piece
    {"centers": [[1,1,-4],[2,1,-4]], "cubes": [[1,1,-3],[1,1,-4],[2,1,-4],[2,1,-5]], "id": 4}, # Z piece
    {"centers": [[1,1,-4]], "cubes": [[1,1,-3],[1,1,-4],[2,1,-4],[1,1,-5]], "id": 5}, # T piece
    {"centers": [[1.5,1.5,-3.5]], "cubes": [[1,1,-3],[1,2,-3],[1,2,-4],[2,2,-3]], "id": 6}, # Y piece
    {"centers": [[1.5,1.5,-3.5]], "cubes": [[2,1,-3],[1,2,-3],[1,2,-4],[2,2,-3]], "id": 7}, # Chiral piece A
    {"centers": [[1.5,1.5,-3.5]], "cubes": [[1,1,-3],[1,2,-3],[2,2,-4],[2,2,-3]], "id": 8} # Chiral piece B
]
COLORS = [(0, 0, 0), (200, 40, 20), (220, 120, 40), (220, 240, 60), (60, 220, 40), (20, 180, 220), (40, 80, 240), (100, 40, 220), (180, 20, 240), (120, 120, 120), (255, 160, 140), (10, 20, 30), (255, 255, 255), (255, 240, 180), (0, 0, 0)]
NEXT_PIECE_COUNT = 5
Y_CAMERA_DISTANCE = HEIGHT*DEPTH_LEVEL*ASPECT_RATIO*1.55
BACKGROUND_COLORS = [tuple(COLORS[n][m]*0.35+40 for m in range(3)) for n in range(10)]
UI_COLORS = [tuple(COLORS[n][m]*0.2+20 for m in range(3)) for n in (0, 2, 1, 4, 3, 6, 5, 8, 7, 9)] # swap nearby colors
CUBE_VERTEX_OFFSET = 0.46 # the size of the cube divided by 2
GHOST_BORDER_WIDTH = int(WINDOW_HEIGHT/360)
RENDER_CUBES = True
VISUAL_GRID_ROT_EASING = 12/FPS
GAME_OVER_SCREEN_ANIM_TIME = 0.5 # in seconds
ANALOG_DEADZONE_WIDTH = 0.55 # setting this above 0.7 will make diagonals impossible
MULT_BUFFER_DRAIN_COEFFICIENT = 0.014
MULT_DRAIN_COEFFICIENT = 1.8
MULT_BUFFER_SIZE = 0.4
RENDER_CENTERS = False
PLANE_CLEAR_SCORE_BONUSES = (0, 100, 250, 500, 1000)
SPIN_CLEAR_SCORE_FACTOR = 3
PLANE_CLEAR_MULT_BONUSES = (0, 0.15, 0.32, 0.5, 0.7)
SPIN_CLEAR_MULT_FACTOR = 2

hotkeys = [7, 26, 4, 22, 14, 15, 44, 225, 51, 41] # d,w,a,s,k,l,space,lshift,semicolon,esc by default. to do: add settings for this
controller_bindings = [14, 11, 13, 12, 2, 1, 0, 9, 3, 15, 10] # see above, but index 10 is for an alternate lower button

class Game:
    def __init__(self):
        self.mode = "Home"
        self.rotate_modifier = False
        self.key_hold_times = [0, 0, 0, 0, 0, 0, 0] # for each movement hotkey
        self.initial_level = 1
        self.init_sounds()
    def init_game(self):
        self.grid = [[[0 for _ in range(HEIGHT)] for _ in range(DEPTH)] for _ in range(WIDTH)] # indexing: [x][y][z] where z is height
        self.mode = "Playing"
        self.score = 0
        self.total_planes_cleared = 0
        self.plane_clear_level_progress = math.ceil((self.initial_level-1)*(3.5+0.125*(self.initial_level-1)))
        self.total_plane_clear_types = [0, 0, 0, 0]
        self.total_spin_clear_types = [0, 0, 0]
        self.total_spins = 0
        self.secluded_spaces = 0
        self.check_for_level_increase()
        self.score_multiplier = 1.0
        self.highest_score_multiplier = 1.0
        self.score_mult_buffer = 0.0
        self.score_mult_cap = 1.0 + self.level/5
        self.repeat_input_delay = FPS/7.5
        self.next_pieces = []
        self.get_new_piece()
        self.held_piece = {}
        self.grid_rotation = 0
        self.visual_grid_rotation = 0.0
        self.game_over_screen_time = 0
    def init_sounds(self):
        Effects().load_all_sounds() # preload all wav files into the Effects manager
        # wav files loaded but not used 
        # '1_plane_clear.wav'
        # '2_plane_clear.wav'
        # '3_plane_clear.wav'
        # '4_plane_clear.wav'
        # '1_spin_clear.wav'
        # '2_spin_clear.wav'
        # '3_spin_clear.wav'
    def change_initial_level(self, amount):
        self.initial_level += amount
        if self.initial_level < 1:
            self.initial_level = 1
        elif self.initial_level > 40:
            self.initial_level = 40
    def increase_score(self, points):
        self.score += points * self.score_multiplier
    def check_for_level_increase(self):
        self.level = math.floor((8*self.plane_clear_level_progress+196)**0.5) - 13 # level scaling. to do: reintroduce constants
        self.score_mult_cap = 1.0 + self.level/5
        self.refresh_tickspeed()
    def score_mult_bonus(self, amount):
        self.score_mult_buffer += amount
        if self.score_mult_buffer > MULT_BUFFER_SIZE:
            self.score_multiplier += self.score_mult_buffer - MULT_BUFFER_SIZE
            self.score_mult_buffer = MULT_BUFFER_SIZE
            if self.score_multiplier > self.score_mult_cap:
                self.score_multiplier = self.score_mult_cap
        if self.highest_score_multiplier < self.score_multiplier:
            self.highest_score_multiplier = self.score_multiplier
    def refresh_tickspeed(self):
        self.tick_duration = FPS/(1.5*((2+self.level)/3)**1.25)*(1+self.secluded_spaces/25) # show mercy when there is a large number of secluded spaces to fill
        self.placement_leniency = FPS/(1.5*((2+self.level)/3)**1.25) * self.level**0.75
        self.repeat_input_times = [ # faster for soft dropping and slower for other inputs
            *[min(FPS/7.5, self.placement_leniency/4)]*6, # d,w,a,s,k,l
            min(FPS/20, self.tick_duration/2) # space
        ]
    def load_upcoming_pieces(self):
        while len(self.next_pieces) <= NEXT_PIECE_COUNT:
            piece_bag = PIECES + [PIECES[random.randrange(0, 7)]] # adds a "bag" of a set of pieces with an extra random piece to come next
            random.shuffle(piece_bag)
            self.next_pieces.extend(piece_bag)
    def reset_piece_state(self):
        self.tick_time = 0
        self.place_time = 0
        self.in_hard_drop = False
        self.lowest_center_elevation = self.current_piece["centers"][0][2]
        self.lowest_spin_elevation = self.current_piece["centers"][0][2]
        self.piece_spin_on_last_movement = False
        self.get_ghost_piece()
    def get_new_piece(self):
        self.load_upcoming_pieces()
        self.current_piece = deepcopy(self.next_pieces.pop(0)) # get the first piece in the queue
        self.hold_piece_used = False
        self.get_secluded_spaces()
        self.reset_piece_state()
    def hold_piece(self):
        if not self.hold_piece_used: # only if it is not already used this turn
            self.hold_piece_used = True
            current_piece_index = self.current_piece["id"] - 1 # for indexing in the PIECES list
            self.current_piece = self.held_piece
            self.held_piece = deepcopy(PIECES[current_piece_index])
            if not self.current_piece: # empty dict
                self.load_upcoming_pieces()
                self.current_piece = deepcopy(self.next_pieces.pop(0)) # get the first piece in the queue
            self.reset_piece_state()
            Effects().hold_piece.play(maxtime=300) # play the sound effect for holding the piece
    def clear_planes(self):
        planes_cleared = 0
        for z in range(HEIGHT): # for each horizontal plane
            cubes = 0
            for y in range(DEPTH):
                for x in range(WIDTH):
                    if self.grid[x][y][z] > 0:
                        cubes += 1 # count the number of cubes in that plane
            if cubes == DEPTH*WIDTH: # if the plane is full
                planes_cleared += 1
                for y in range(DEPTH):
                    for x in range(WIDTH):
                        self.grid[x][y].pop(z) # remove the plane
                        self.grid[x][y].insert(0, 0) # insert an empty plane at the top
        self.increase_score(PLANE_CLEAR_SCORE_BONUSES[min(planes_cleared, 4)] * (SPIN_CLEAR_SCORE_FACTOR if self.piece_spin_on_last_movement else 1))
        self.total_planes_cleared += planes_cleared
        self.plane_clear_level_progress += planes_cleared
        self.check_for_level_increase()
        self.score_mult_bonus(PLANE_CLEAR_MULT_BONUSES[min(planes_cleared, 4)] * (SPIN_CLEAR_MULT_FACTOR if self.piece_spin_on_last_movement else 1))
        if (planes_cleared > 0) and (type(planes_cleared) == int): # ensure that only integers may be used in the eval() functions
            if not self.piece_spin_on_last_movement:
                eval(f"Effects()['{min(planes_cleared, 4)}_plane_clear'].play(maxtime=1000)")
                self.total_plane_clear_types[min(planes_cleared, 4)-1] += 1
            else:
                eval(f"Effects()['{min(planes_cleared, 3)}_spin_clear'].play(maxtime=1000)")
                self.total_spin_clear_types[min(planes_cleared, 3)-1] += 1
        return planes_cleared
    def get_secluded_spaces(self):
        self.secluded_spaces = 0 # this could just be a returned variable, perhaps modify?
        visible_depths = [[[0 for _ in range(DEPTH if rot%2 else WIDTH)] for _ in range(HEIGHT)] for rot in range(4)] # Indexing: [Face rotation (in the order below)][z][x or y, depending on face - this is "a" in the below code]
        # The below function provides how deep empty spaces go in each row from 4 perspectives relative to the default grid rotation:
        # Front face, left face (but flipped horizontally for later code to easily index cells), back face (also flipped), right face
        for rot in range(4):
            for z in range(HEIGHT):
                for a in range(DEPTH if rot%2 else WIDTH): # Swaps indexing of X and Y axes if rotation is odd
                    depth = 0
                    for b in range(WIDTH if rot%2 else DEPTH): # b's indexing is inverted if rot >= 2
                        if self.grid[(a, b, a, WIDTH-b-1)[rot]][(b, a, DEPTH-b-1, a)[rot]][z] <= 0: # Index based on the order of faces listed above
                            depth += 1
                        else:
                            break
                    visible_depths[rot][z][a] = depth
            for z in range(HEIGHT-1): # excluding topmost layer, done from bottom to top
                for a in range(DEPTH if rot%2 else WIDTH):
                    if visible_depths[rot][HEIGHT-z-1][a] < visible_depths[rot][HEIGHT-z-2][a]: # If the lower row has a lesser depth than the upper row...
                        visible_depths[rot][HEIGHT-z-1][a] = visible_depths[rot][HEIGHT-z-2][a] - 1 # set the lower row to the upper row's value minus one, as it is visible that far from the top.
        for z in range(HEIGHT-1): # topmost plane (z=0) cannot be secluded, thus z+1 will be used
            for y in range(DEPTH):
                for x in range(WIDTH):
                    if self.grid[x][y][z+1] <= 0: # For every empty cube in the grid
                        secluded_directions = 0
                        for dir in range(4): # for each of the 4 directions - while this may be a lot of checks, for typical board sizes this takes less than 1ms on a typical system. Even on lower-end systems, this should not cause considerable lag compared to that of rendering.
                            if visible_depths[dir][z+1][y if dir%2 else x] < (y, x, DEPTH-y-1, WIDTH-x-1)[dir]:
                                secluded_directions += 1 # If the visible depth is less than the depth of the cube in a given direction, it is secluded in that direction.
                        if secluded_directions >= 3:
                            self.grid[x][y][z+1] = -1
                            self.secluded_spaces += 1
    def check_piece_elevation(self):
        if self.current_piece["centers"][0][2] > self.lowest_center_elevation:
            self.lowest_center_elevation = self.current_piece["centers"][0][2]
            self.place_time = 0 # reset the time to place the piece if its center gets lowered beyond any previous depths
    def lower_piece(self, piece, tick_modification=True, manual=False):
        self.piece_spin_on_last_movement = False
        for n in range(len(piece["cubes"])):
            piece["cubes"][n][2] += 1 # lower the piece
        for n in range(len(piece["centers"])):
            piece["centers"][n][2] += 1 # lower the rotation center
        if tick_modification:
            if self.tick_time < self.tick_duration*0.75:
                if self.current_piece["centers"][0][2] > self.lowest_center_elevation:
                    self.increase_score(1) # increase score for manual lowering if enough time is saved (and it was not a previously reached depth this turn)
            self.tick_time -= self.tick_duration
            if self.tick_time < 0:
                self.tick_time = 0
        if manual:
            Effects().lower_piece.play(maxtime=100) # play the sound effect for manually lowering the piece
        self.check_piece_elevation()
    def place_piece(self, hard=False):
        planes_cleared = 0
        for n in range(len(self.current_piece["cubes"])):
            cube = sorted(self.current_piece["cubes"], key = lambda cube: -cube[2])[n] # checks the bottom-most cubes first
            if cube[2] >= 0:
                self.grid[cube[0]][cube[1]][cube[2]] = self.current_piece["id"]
            elif cube[2] >= -1:
                planes_cleared += self.clear_planes()
                for _ in range(planes_cleared):
                    self.lower_piece(self.current_piece)
                    cube = sorted(self.current_piece["cubes"], key = lambda cube: -cube[2])[n]
                    self.grid[cube[0]][cube[1]][cube[2]] = self.current_piece["id"] # place the lowered piece
                if planes_cleared == 0:
                    self.mode = "Finished" # game over
                    self.rotate_modifier = False # to initially show the game over screen animation
            else:
                self.mode = "Finished" # game over
                self.rotate_modifier = False
        self.clear_planes()
        self.get_new_piece()
        self.refresh_tickspeed()
        if hard:
            Effects().place_hard.play(maxtime=300) # play the sound effect for hard dropping the piece
        else:
            Effects().place_soft.play(maxtime=200) 
    def score_multiplier_tick(self):
        self.score_mult_buffer -= self.score_multiplier * MULT_BUFFER_DRAIN_COEFFICIENT / FPS
        if self.score_mult_buffer < 0:
            self.score_multiplier += self.score_mult_buffer * MULT_DRAIN_COEFFICIENT * self.score_multiplier
            self.score_mult_buffer = 0
            if self.score_multiplier < 1:
                self.score_multiplier = 1
    def tick(self):
        for n in range(len(self.key_hold_times)):
            if self.key_hold_times[n] > 0:
                self.key_hold_times[n] += 1
            if self.key_hold_times[n] >= self.repeat_input_times[n]+self.repeat_input_delay:
                self.key_hold_times[n] = int(self.key_hold_times[n] - self.repeat_input_times[n])
                if not self.rotate_modifier:
                    self.basic_input(n, repeat=True)
                elif n != 6: # excludes holding down hard drop
                    self.modified_input(n)
        self.score_multiplier_tick()
        if not self.piece_grounded(self.current_piece):
            self.tick_time += 1
        else:
            self.place_time += 1
        while (self.tick_time >= self.tick_duration) and not self.piece_grounded(self.current_piece):
            self.lower_piece(self.current_piece)
        if (self.place_time >= self.tick_duration + self.placement_leniency) and self.piece_grounded(self.current_piece):
            self.place_piece()
        if self.in_hard_drop == True:
            self.drop_piece()
        self.ease_grid_rotation()
    def ease_grid_rotation(self):
        visual_grid_rot_offset = (self.visual_grid_rotation - self.grid_rotation + 2) % 4 - 2
        if visual_grid_rot_offset >= 0:
            visual_grid_rot_offset = max(((visual_grid_rot_offset**0.5)-VISUAL_GRID_ROT_EASING), 0)**2 # visual easing for grid rotation
            self.visual_grid_rotation = self.grid_rotation + visual_grid_rot_offset
        else:
            visual_grid_rot_offset = max((((-visual_grid_rot_offset)**0.5)-VISUAL_GRID_ROT_EASING), 0)**2
            self.visual_grid_rotation = self.grid_rotation - visual_grid_rot_offset
    def game_over_screen_tick(self):
        self.game_over_screen_time += 1/FPS
    def check_for_collision(self, cube, x, y, z):
        if (0 <= cube[0]+x <= WIDTH-1) and (0 <= cube[1]+y <= DEPTH-1) and (0 <= cube[2]+z <= HEIGHT-1):
            return (self.grid[cube[0]+x][cube[1]+y][cube[2]+z] > 0)  # if colliding with a tile within the confines of the grid (preventing Python list wrap-around shenanigans)
        else:
            return not ((0 <= cube[0]+x <= WIDTH-1) and (0 <= cube[1]+y <= DEPTH-1) and (cube[2]+z <= HEIGHT-1)) # allowing the piece to be above the grid without being flagged as colliding
    def piece_grounded(self, piece):
        for n in range(len(piece["cubes"])):
            cube = piece["cubes"][n]
            if cube[2] >= HEIGHT-1: # bottom of grid (or lower as a failsafe)
                return True
            if self.check_for_collision(cube, 0, 0, 1): # above another piece, second check to prevent Python interpreting negative values as being from the end of the list
                return True
        return False
    def piece_fully_grounded(self, piece):
        grounded_cubes = 0
        for n in range(len(piece["cubes"])):
            cube = piece["cubes"][n]
            if (cube[2] >= HEIGHT-1) or self.check_for_collision(cube, 0, 0, 1) or [piece["cubes"][n][0], piece["cubes"][n][1], piece["cubes"][n][2]+1] in piece["cubes"]: # additional case for there being a cube in the ghost piece above another
                grounded_cubes += 1
        return len(piece["cubes"]) == grounded_cubes
    def piece_held_by_overhang(self, piece):
        for n in range(len(piece["cubes"])):
            cube = piece["cubes"][n]
            if self.check_for_collision(cube, 0, 0, -1): # below another piece
                return True
        return False
    def move_piece(self, piece, rot):
        self.piece_spin_on_last_movement = False
        x = [1, 0, -1, 0][(rot+self.grid_rotation)%4]
        y = [0, 1, 0, -1][(rot+self.grid_rotation)%4] # get the movement in each axis based on the input and current grid rotation
        # x_modified = int(round(x*math.cos(self.grid_rotation*math.pi/2)-y*math.sin(self.grid_rotation*math.pi/2)))
        # y_modified = int(round(y*math.cos(self.grid_rotation*math.pi/2)+x*math.sin(self.grid_rotation*math.pi/2))) # modify x and y movements with grid rotation. also the + and - here have to be swapped, or movement inverts itself for odd rotations I guess
        for n in range(len(piece["cubes"])):
            cube = piece["cubes"][n]
            if not (0 <= cube[0]+x <= WIDTH-1) or not (0 <= cube[1]+y <= DEPTH-1) or not (cube[2] <= HEIGHT-1): # if outside at least one of the boundaries
                return False
            if self.check_for_collision(cube, x, y, 0): # collisions with tiles in-bounds
                return False
        for n in range(len(piece["cubes"])):
            piece["cubes"][n][0] += x
            piece["cubes"][n][1] += y # move the piece
        for n in range(len(piece["centers"])):
            piece["centers"][n][0] += x
            piece["centers"][n][1] += y # move the rotation center
        self.get_ghost_piece()
        if self.piece_fully_grounded(self.ghost_piece):
            Effects().move_piece_gold.play(maxtime=300) # play the sound effect for moving the piece if it is fully grounded
        else:
            Effects().move_piece.play(maxtime=200) # play the sound effect for moving the piece
        return True
    def force_move_piece(self, piece, x, y, z): # absolute positioning, no collision checking 
        for n in range(len(piece["cubes"])):
            piece["cubes"][n][0] += x
            piece["cubes"][n][1] += y # move the piece
            piece["cubes"][n][2] += z
        for n in range(len(piece["centers"])):
            piece["centers"][n][0] += x
            piece["centers"][n][1] += y # move all of the possible rotation centers
            piece["centers"][n][2] += z
        self.check_piece_elevation()
    def drop_piece(self, instant_placement=False):
        while True:
            if not self.piece_grounded(self.current_piece):
                self.lower_piece(self.current_piece)
            else:
                if instant_placement:
                    self.place_piece(hard=True)
                return
    def raise_piece_to_initial_center(self, modified_piece):
        for n in range(int(max(modified_piece["centers"][0][2]-self.current_piece["centers"][0][2], 0))): # how much the center of the modified piece has moved down compared to the original, if any
            cube_placements_found = 0
            for n in range(len(modified_piece["cubes"])):
                cube = modified_piece["cubes"][n]
                if (not self.check_for_collision(cube, 0, 0, -1)) and not (not (0 <= cube[0] <= WIDTH-1) or not (0 <= cube[1] <= DEPTH-1) or not (cube[2]-1 <= HEIGHT-1)): # if the cube is able to be placed and is within bounds after moving upwards
                    cube_placements_found += 1
            if cube_placements_found == len(modified_piece["cubes"]):
                self.force_move_piece(modified_piece, 0, 0, -1)
            else:
                return # no further checks given
    def detect_spin(self, modified_piece, axis): # where axis refers to the pole which the piece is rotated around
        spin_check_displacements = [(0, 0, -1)] # upward check
        if axis != 0: # left/right or cw/ccw rotations
            spin_check_displacements.extend([(0, 1, 0), (0, -1, 0)]) # check for the piece being movable in the forward/backward directions
        if axis != 1: # forward/backward or cw/ccw rotations
            spin_check_displacements.extend([(1, 0, 0), (-1, 0, 0)]) # check for the piece being movable in the left/right directions
        for relative_x, relative_y, relative_z in spin_check_displacements:
            cube_placements_found = 0
            for n in range(len(modified_piece["cubes"])):
                cube = modified_piece["cubes"][n]
                if (not self.check_for_collision(cube, relative_x, relative_y, relative_z)) and not (not (0 <= cube[0]+relative_x <= WIDTH-1) or not (0 <= cube[1]+relative_y <= DEPTH-1) or not (cube[2]+relative_z <= HEIGHT-1)): # if the cube is able to be placed and is within bounds after moving
                    cube_placements_found += 1
            if cube_placements_found == len(modified_piece["cubes"]):
                return # the piece should not be movable in any of the given directions - otherwise, it is not considered a spin
        if self.current_piece["centers"][0][2] > self.lowest_spin_elevation: # only if the spin as at a lower point than the last spin this turn (prevents repeated point gain)
            self.lowest_spin_elevation = self.current_piece["centers"][0][2]
            final_spin_displacement = abs(self.current_piece["centers"][0][0]-modified_piece["centers"][0][0])+abs(self.current_piece["centers"][0][1]-modified_piece["centers"][0][1])+abs(self.current_piece["centers"][0][2]-modified_piece["centers"][0][2])
            self.increase_score(20+10*final_spin_displacement)
            self.score_mult_bonus(0.14+0.07*final_spin_displacement)
            self.piece_spin_on_last_movement = True
            Effects().piece_spin.play(maxtime=300) # play the sound effect for spinning the piece
            self.total_spins += 1
    def get_ghost_piece(self):
        self.ghost_piece = deepcopy(self.current_piece)
        while True:
            if not self.piece_grounded(self.ghost_piece):
                self.lower_piece(self.ghost_piece, tick_modification=False)
            else:
                return
    def rotate_piece(self, input):
        self.piece_spin_on_last_movement = False
        if input < 4:
            input = (input + self.grid_rotation) % 4 # setting input to be relative to the grid's current rotation
        axis, rot = [(1,-1),(0,-1),(1,1),(0,1),(2,1),(2,-1)][input] # axes of rotation and directions for each input
        movable_axes = [0, 1, 2]
        movable_axes.remove(axis)
        if len(self.current_piece["centers"]) > 1: # for deciding which center a piece with an ambiguous center should rotate around
            if self.current_piece["centers"][0][2] != self.current_piece["centers"][1][2]: # first priority check: whichever center point is lower
                self.current_piece["centers"] = sorted(self.current_piece["centers"], key=lambda position: -position[2])
            elif (input < 4): # second priority check: whichever center point is closest to the movement direction
                self.current_piece["centers"] = sorted(self.current_piece["centers"], key=lambda position: position[input%2] * (-1 if input < 2 else 1))
        rotated_piece = deepcopy(self.current_piece)
        for n in range(len(rotated_piece["cubes"])):
            rotated_piece["cubes"][n][movable_axes[0]] -= rotated_piece["centers"][0][movable_axes[0]]
            rotated_piece["cubes"][n][movable_axes[1]] -= rotated_piece["centers"][0][movable_axes[1]] # make the cubes' relative centers (0,0) on the two movable axes
            a = rotated_piece["cubes"][n][movable_axes[0]]
            b = rotated_piece["cubes"][n][movable_axes[1]]
            rotated_piece["cubes"][n][movable_axes[0]] = a*math.cos(rot*math.pi/2)+b*math.sin(rot*math.pi/2)
            rotated_piece["cubes"][n][movable_axes[1]] = b*math.cos(rot*math.pi/2)-a*math.sin(rot*math.pi/2) # rotate the cubes relative to the axis
            rotated_piece["cubes"][n][movable_axes[0]] = int(round(rotated_piece["cubes"][n][movable_axes[0]] + rotated_piece["centers"][0][movable_axes[0]]))
            rotated_piece["cubes"][n][movable_axes[1]] = int(round(rotated_piece["cubes"][n][movable_axes[1]] + rotated_piece["centers"][0][movable_axes[1]])) # move the cubes back to the axis's position, convert float to int
        for n in range(len(rotated_piece["centers"])-1):
            n = n+1 # start indexing for the alternate center (index 1)
            rotated_piece["centers"][n][movable_axes[0]] -= rotated_piece["centers"][0][movable_axes[0]]
            rotated_piece["centers"][n][movable_axes[1]] -= rotated_piece["centers"][0][movable_axes[1]] # make the alternate center's relative centers (0,0) on the two movable axes
            a = rotated_piece["centers"][n][movable_axes[0]]
            b = rotated_piece["centers"][n][movable_axes[1]]
            rotated_piece["centers"][n][movable_axes[0]] = a*math.cos(rot*math.pi/2)+b*math.sin(rot*math.pi/2)
            rotated_piece["centers"][n][movable_axes[1]] = b*math.cos(rot*math.pi/2)-a*math.sin(rot*math.pi/2) # rotate the center relative to the axis
            rotated_piece["centers"][n][movable_axes[0]] = rotated_piece["centers"][n][movable_axes[0]] + rotated_piece["centers"][0][movable_axes[0]]
            rotated_piece["centers"][n][movable_axes[1]] = rotated_piece["centers"][n][movable_axes[1]] + rotated_piece["centers"][0][movable_axes[1]] # move the alternate center back to the axis's position, convert float to int
        rotation_success = False
        coordinate_ranges = []
        for n in range(3): # get how wide, deep, and tall the rotated piece is
            axis_positions = []
            for m in range(len(rotated_piece["cubes"])):
                axis_positions.append(rotated_piece["cubes"][m][n])
            coordinate_ranges.append(axis_positions)
        for n in range(len(coordinate_ranges)):
            coordinate_ranges[n] = max(coordinate_ranges[n])-min(coordinate_ranges[n])+1 # actual range for each coordinate
        for comparison, push_axis, movement in [(">= 0", 0, [1,0,0]), (">= 0", 1, [0,1,0]), ("<= WIDTH-1", 0, [-1,0,0]), ("<= DEPTH-1", 1, [0,-1,0])]: # evaluate the given code (pushing the piece out of the border) for each of the 4 conditions
            exec(f"""
while True:
    for n in range(len(rotated_piece['cubes'])):
        pushed = False
        cube = rotated_piece['cubes'][n]
        if not (cube[{push_axis}] {comparison}):
            pushed = True
            self.force_move_piece(rotated_piece, *{movement})
    if not pushed:
        break
            """)
        if not self.piece_held_by_overhang(self.current_piece): # special case for things such as t-spin triples
            for relative_z in (0, 1, -1): # correct downward first if initial position fails, then upward.
                cube_placements_found = 0
                initial_horiz_displacements = [[0, 0]]
                if (input < 4) and (relative_z > 0): # another special case for spinning pieces into the ground with a displacement parallel to the rotation direction
                    initial_horiz_displacements = [[0, 0], [0, 0], [0, 0]]
                    initial_horiz_displacements[1][movable_axes[0]] = -rot
                    initial_horiz_displacements[2][movable_axes[0]] = rot
                for relative_x, relative_y in initial_horiz_displacements:
                    cube_placements_found = 0
                    if rotated_piece["centers"][0][0]%1 == 0: # if the piece's last used center is at an integer location
                        for n in range(3):
                            rotated_piece["centers"][0][n] = int(round(rotated_piece["centers"][0][n])) # to not make them randomly floats
                        upwards_special_case = 0 if self.check_for_collision(rotated_piece["centers"][0], 0, 0, 1) else -1 # 1 for true, -1 for false and disabled for this piece check
                    else:
                        upwards_special_case = -1
                    for n in range(len(rotated_piece["cubes"])):
                        cube = rotated_piece["cubes"][n]
                        if (not self.check_for_collision(cube, relative_x, relative_y, relative_z)) and not (not (0 <= cube[0]+relative_x <= WIDTH-1) or not (0 <= cube[1]+relative_y <= DEPTH-1) or not (cube[2]+relative_z <= HEIGHT-1)): # if the cube is able to be placed and is within bounds after moving
                            cube_placements_found += 1
                        elif relative_z == -1:
                            if (abs(cube[0]-rotated_piece["centers"][0][0])+abs(cube[1]-rotated_piece["centers"][0][1])+(cube[2]-rotated_piece["centers"][0][2]) >= 2) and upwards_special_case >= 0: # special case for long/tall pieces pushing up against something. last coordinate is intentionally not an absolute value
                                upwards_special_case = 1
                            else:
                                upwards_special_case = -1
                    if cube_placements_found == len(rotated_piece["cubes"]):
                        self.force_move_piece(rotated_piece, relative_x, relative_y, relative_z)
                        self.raise_piece_to_initial_center(rotated_piece)
                        self.detect_spin(rotated_piece, axis)
                        self.current_piece = rotated_piece
                        rotation_success = True
                        self.get_ghost_piece()
                        if self.piece_fully_grounded(self.ghost_piece):
                            Effects().rotate_piece_gold.play(maxtime=300) # play the sound effect for rotating the piece if it is fully grounded
                        else:
                            Effects().rotate_piece.play(maxtime=200)
                        return
                    elif upwards_special_case == 1:
                        cube_placements_found = 0
                        for n in range(len(rotated_piece["cubes"])):
                            cube = rotated_piece["cubes"][n]
                            if (not self.check_for_collision(cube, relative_x, relative_y, relative_z-1)) and not (not (0 <= cube[0]+relative_x <= WIDTH-1) or not (0 <= cube[1]+relative_y <= DEPTH-1) or not (cube[2]+relative_z-1 <= HEIGHT-1)): # if the cube is able to be placed and is within bounds after moving
                                cube_placements_found += 1
                        if cube_placements_found == len(rotated_piece["cubes"]):
                            self.force_move_piece(rotated_piece, relative_x, relative_y, relative_z-1)
                            self.raise_piece_to_initial_center(rotated_piece)
                            self.detect_spin(rotated_piece, axis)
                            self.current_piece = rotated_piece
                            rotation_success = True
                            self.get_ghost_piece()
                            if self.piece_fully_grounded(self.ghost_piece):
                                Effects().rotate_piece_gold.play(maxtime=300) # play the sound effect for rotating the piece if it is fully grounded
                            else:
                                Effects().rotate_piece.play(maxtime=200)
                            return
        if not rotation_success: # if the piece needs to be moved (to do: this rotation_success variable does nothing. maybe remove/rework it?)
            horizontal_displacements = []
            for y in range(-coordinate_ranges[1], coordinate_ranges[1]+1):
                for x in range(-coordinate_ranges[0], coordinate_ranges[0]+1):
                    horizontal_displacements.append([x, y])
            preferred_displacement = [[0.001,-0.0001],[0.0001,0.001],[-0.001,0.0001],[-0.0001,-0.001]][input if input < 4 else (self.grid_rotation+1)%4] # displacements are checked for first in these positions based on the input given... (0.001 values are to prioritize [0,0] displacement forst, then in that direction; 0.0001 for a clockwise check thereafter) [and is set to to always correct backwards relative to the camera for cw/ccw rotations]
            horizontal_displacements = sorted(horizontal_displacements, key=lambda displacement: ((displacement[0]-preferred_displacement[0])**2+(displacement[1]-preferred_displacement[1])**2)) # then by Euclidean distance between those positions
            for z in range(-coordinate_ranges[2], coordinate_ranges[2]+1)[::-1]: # every value from the negative to the positive end of that value. Z axis (bottom to top) is done first            
                for x, y in horizontal_displacements:
                    cube_placements_found = 0
                    for n in range(len(rotated_piece["cubes"])):
                        cube = rotated_piece["cubes"][n]
                        if (not self.check_for_collision(cube, x, y, z)) and not (not (0 <= cube[0]+x <= WIDTH-1) or not (0 <= cube[1]+y <= DEPTH-1) or not (cube[2]+z <= HEIGHT-1)): # if the cube is able to be placed and is within bounds after moving
                            cube_placements_found += 1
                    if cube_placements_found == len(rotated_piece["cubes"]):
                        original_cubes_touched = [] # made into all cubes the unrotated piece has touched
                        for n in range(len(self.current_piece["cubes"])):
                            for dx, dy, dz in [(0,0,0), (1,0,0), (0,1,0), (0,0,1), (-1,0,0), (0,-1,0), (0,0,-1)]: # the cube and its adjacent neighbors
                                original_cubes_touched.append([self.current_piece["cubes"][n][0]+dx, self.current_piece["cubes"][n][1]+dy, self.current_piece["cubes"][n][2]+dz])
                        translated_piece = deepcopy(rotated_piece)
                        self.force_move_piece(translated_piece, x, y, z)
                        for m in range(len(rotated_piece["cubes"])):
                            if translated_piece["cubes"][m] in original_cubes_touched: # if the current piece is in contact with the rotated and translated piece
                                self.raise_piece_to_initial_center(translated_piece)
                                self.detect_spin(translated_piece, axis)
                                self.current_piece = translated_piece
                                rotation_success = True
                                self.get_ghost_piece()
                                if self.piece_fully_grounded(self.ghost_piece):
                                    Effects().rotate_piece_gold.play(maxtime=300) # play the sound effect for rotating the piece if it is fully grounded
                                else:
                                    Effects().rotate_piece.play(maxtime=200) # play the sound effect for rotating the piece
                                return
        Effects().rotation_blocked.play(maxtime=400) # return statement cancels this
    def basic_input(self, input, repeat=False):
        match input:
            case 0: # right
                self.move_piece(self.current_piece, input)
                self.key_hold_times[2] = 0 # prevent opposite directions from both being held
            case 1: # up
                self.move_piece(self.current_piece, input)
                self.key_hold_times[3] = 0
            case 2: # left
                self.move_piece(self.current_piece, input)
                self.key_hold_times[0] = 0
            case 3: # down
                self.move_piece(self.current_piece, input)
                self.key_hold_times[1] = 0
            case 4: # grid clockwise
                self.grid_rotation = (self.grid_rotation+1)%4
                self.key_hold_times[5] = 0
            case 5: # grid counterclockwise
                self.grid_rotation = (self.grid_rotation-1)%4
                self.key_hold_times[4] = 0
            case 6: # lower
                if not self.piece_grounded(self.current_piece):
                    self.lower_piece(self.current_piece, manual=True)
                else:
                    self.place_piece()
        if (input < 7) and (repeat == False):
            self.key_hold_times[input] = 1
    def modified_input(self, input):
        match input:
            case 0: # rotate right
                self.rotate_piece(input)
                self.key_hold_times[2] = 0 # prevent opposite directions from both being held
            case 1: # rotate up
                self.rotate_piece(input)
                self.key_hold_times[3] = 0
            case 2: # rotate left
                self.rotate_piece(input)
                self.key_hold_times[0] = 0
            case 3: # rotate down
                self.rotate_piece(input)
                self.key_hold_times[1] = 0
            case 4: # rotate clockwise
                self.rotate_piece(input)
                self.key_hold_times[5] = 0
            case 5: # rotate counterclockwise
                self.rotate_piece(input)
                self.key_hold_times[4] = 0
            case 6: # drop
                if not self.piece_grounded(self.current_piece):
                    self.drop_piece()
                    self.in_hard_drop = True
                    Effects().sonic_drop.play(maxtime=300) # play the sound effect for hard dropping the piece
                else:
                    self.place_piece(hard=True)
        self.key_hold_times[input] = 1

def draw_home_ui(screen, game, font_small, font_large):
    title_text = font_large.render(("QUBITRIX"), False, COLORS[-3])
    screen.blit(title_text, title_text.get_rect(center=(WINDOW_WIDTH/2, WINDOW_HEIGHT*0.2)))
    start_text = font_small.render((f"Start at level < {game.initial_level} >"), False, COLORS[-3])
    screen.blit(start_text, start_text.get_rect(center=(WINDOW_WIDTH/2, WINDOW_HEIGHT*0.6)))


def screen_coordinates(x, y, z):
    return WINDOW_WIDTH/2+DEPTH_LEVEL*x*WINDOW_WIDTH/y, DEPTH_LEVEL*z*WINDOW_WIDTH/y

def draw_game_ui(screen, game, font_small, font_large, ui_color_id):
    z_a = -0.5+(HEIGHT-1)/1.8
    z_b = HEIGHT-0.5+(HEIGHT-1)/1.8
    for border in (True, False): # draw border first, then solid polygons above it
        floor_coordinates = []
        for n in range(4):
            rot = n + game.visual_grid_rotation
            x_a = (WIDTH, DEPTH)[n%2]/2*math.cos(rot*math.pi/2) + (DEPTH, WIDTH)[n%2]/2*math.sin(rot*math.pi/2)
            y_a = (DEPTH, WIDTH)[n%2]/2*math.cos(rot*math.pi/2) - (WIDTH, DEPTH)[n%2]/2*math.sin(rot*math.pi/2)+Y_CAMERA_DISTANCE
            rot += 1
            x_b = (DEPTH, WIDTH)[n%2]/2*math.cos(rot*math.pi/2) + (WIDTH, DEPTH)[n%2]/2*math.sin(rot*math.pi/2)
            y_b = (WIDTH, DEPTH)[n%2]/2*math.cos(rot*math.pi/2) - (DEPTH, WIDTH)[n%2]/2*math.sin(rot*math.pi/2)+Y_CAMERA_DISTANCE
            if (screen_coordinates(x_a, y_a, z_a)[0] < screen_coordinates(x_b, y_b, z_a)[0]) or border: # only draw inner faces
                pygame.draw.polygon(screen, get_color(ui_color_id, n%2, 0 if (0 < n < 3) else 7, game.visual_grid_rotation, ui=True) if not border else COLORS[0], [ # bounding box, shading is inverted from the inside
                    screen_coordinates(x_a, y_a, z_a), screen_coordinates(x_b, y_b, z_a),  screen_coordinates(x_b, y_b, z_b), screen_coordinates(x_a, y_a, z_b)], width = GHOST_BORDER_WIDTH*4 if border else 0)
            floor_coordinates.append((x_a, y_a, z_b))
        pygame.draw.polygon(screen, get_color(ui_color_id, 2, 0, game.visual_grid_rotation, ui=True) if not border else COLORS[0], # render floor - closest vertex is irrelevant
            [screen_coordinates(*floor_coordinates[0]), screen_coordinates(*floor_coordinates[1]), screen_coordinates(*floor_coordinates[2]), screen_coordinates(*floor_coordinates[3])], width = GHOST_BORDER_WIDTH*4 if border else 0)
    # to do: fix the missing corners of the game grid's border
    for border in (False, True): # border rendering for rects is on the inside for some reason
        pygame.draw.rect(screen, COLORS[0] if border else UI_COLORS[ui_color_id], (WINDOW_WIDTH/2+max(WIDTH, DEPTH)*WINDOW_HEIGHT/HEIGHT/2+WINDOW_HEIGHT*0.04, WINDOW_HEIGHT*0.04, WINDOW_HEIGHT*0.285, WINDOW_HEIGHT*0.92), width = GHOST_BORDER_WIDTH*2 if border else 0)
        pygame.draw.rect(screen, COLORS[0] if border else UI_COLORS[ui_color_id], (WINDOW_WIDTH/2-max(WIDTH, DEPTH)*WINDOW_HEIGHT/HEIGHT/2-WINDOW_HEIGHT*0.325, WINDOW_HEIGHT*0.04, WINDOW_HEIGHT*0.285, WINDOW_HEIGHT*0.92), width = GHOST_BORDER_WIDTH*2 if border else 0)

    pygame.draw.rect(screen, COLORS[9], (WINDOW_WIDTH/2+max(WIDTH, DEPTH)*WINDOW_HEIGHT/HEIGHT/2+WINDOW_HEIGHT/5, WINDOW_HEIGHT*2/25, WINDOW_HEIGHT/36, WINDOW_HEIGHT*0.58)) # level progress bar
    level_progress = (game.plane_clear_level_progress-math.ceil((game.level-1)*(3.5+0.125*(game.level-1))))/(math.ceil((game.level)*(3.5+0.125*(game.level)))-math.ceil((game.level-1)*(3.5+0.125*(game.level-1)))) # proportion of plane clears gained towards the next level
    pygame.draw.rect(screen, COLORS[-3], (WINDOW_WIDTH/2+max(WIDTH, DEPTH)*WINDOW_HEIGHT/HEIGHT/2+WINDOW_HEIGHT/5, WINDOW_HEIGHT*2/25, WINDOW_HEIGHT/36, level_progress*WINDOW_HEIGHT*0.58))
    pygame.draw.rect(screen, COLORS[9], (WINDOW_WIDTH/2+max(WIDTH, DEPTH)*WINDOW_HEIGHT/HEIGHT/2+WINDOW_HEIGHT/16, WINDOW_HEIGHT*0.77, WINDOW_HEIGHT*0.178, WINDOW_HEIGHT/36)) # score multiplier bar
    pygame.draw.rect(screen, COLORS[-3], (WINDOW_WIDTH/2+max(WIDTH, DEPTH)*WINDOW_HEIGHT/HEIGHT/2+WINDOW_HEIGHT/16, WINDOW_HEIGHT*0.77, WINDOW_HEIGHT*0.178*game.score_mult_buffer/MULT_BUFFER_SIZE, WINDOW_HEIGHT/36))
    score_text = font_large.render(f"{math.floor(game.score):06d}", False, COLORS[-3])
    screen.blit(score_text, (WINDOW_WIDTH/2+max(WIDTH, DEPTH)*WINDOW_HEIGHT/HEIGHT/2+WINDOW_HEIGHT/16, WINDOW_HEIGHT*0.82))
    level_text = font_small.render("Level " + str(game.level), False, COLORS[-3])
    screen.blit(level_text, (WINDOW_WIDTH/2+max(WIDTH, DEPTH)*WINDOW_HEIGHT/HEIGHT/2+WINDOW_HEIGHT/16, WINDOW_HEIGHT*0.9))
    mult_text = font_small.render(f"x{game.score_multiplier:.3f}", False, COLORS[-2 if game.score_multiplier >= game.score_mult_cap else (-3 if (game.score_mult_buffer > 0) or (game.score_multiplier == 1.0) else -5)])
    screen.blit(mult_text, (WINDOW_WIDTH/2+max(WIDTH, DEPTH)*WINDOW_HEIGHT/HEIGHT/2+WINDOW_HEIGHT/16, WINDOW_HEIGHT*0.72))
    for position, (category, stat) in list(enumerate((("Single clears:", str(game.total_plane_clear_types[0])), ("Double clears:", str(game.total_plane_clear_types[1])), ("Triple clears:", str(game.total_plane_clear_types[2])), ("Quad clears:", str(game.total_plane_clear_types[3])), 
                                     ("Piece spins:", str(game.total_spins)), ("Spin singles:", str(game.total_spin_clear_types[0])), ("Spin doubles:", str(game.total_spin_clear_types[1])), ("Spin triples:", str(game.total_spin_clear_types[2]))))):
        category_text = font_small.render(category, False, COLORS[-3])
        category_text_rect = category_text.get_rect()
        category_text_rect.topright = (WINDOW_WIDTH/2-max(WIDTH, DEPTH)*WINDOW_HEIGHT/HEIGHT/2-WINDOW_HEIGHT/22, WINDOW_HEIGHT*(0.235+0.09*position))
        screen.blit(category_text, category_text_rect)
        stat_text = font_small.render(stat, False, COLORS[-2])
        stat_text_rect = stat_text.get_rect()
        stat_text_rect.topright = (WINDOW_WIDTH/2-max(WIDTH, DEPTH)*WINDOW_HEIGHT/HEIGHT/2-WINDOW_HEIGHT/22, WINDOW_HEIGHT*(0.285+0.09*position))
        screen.blit(stat_text, stat_text_rect)

def draw_pause_ui(screen, font_small):
    paused_text = font_small.render(("Paused"), False, COLORS[-3])
    screen.blit(paused_text, paused_text.get_rect(center=(WINDOW_WIDTH/2, WINDOW_HEIGHT/2)))

def draw_finish_ui(screen, game, font_small, font_large, ui_color_id):
    dropdown_depth = WINDOW_HEIGHT*(min((game.game_over_screen_time/GAME_OVER_SCREEN_ANIM_TIME)**2, 1)-1)
    pygame.draw.rect(screen, UI_COLORS[ui_color_id], (0, dropdown_depth, WINDOW_WIDTH, WINDOW_HEIGHT))
    game_over_text = font_large.render(("GAME OVER"), False, COLORS[-3])
    screen.blit(game_over_text, game_over_text.get_rect(center=(WINDOW_WIDTH/2, dropdown_depth+WINDOW_HEIGHT*0.125)))
    for position, (category, stat) in list(enumerate((("Final score:", str(int(game.score))), ("Final level:", str(game.level)), ("Planes cleared:", str(game.total_planes_cleared)), ("Best score mult.:", f"x{game.highest_score_multiplier:.3f}"),
                                     ("Single clears:", str(game.total_plane_clear_types[0])), ("Double clears:", str(game.total_plane_clear_types[1])), ("Triple clears:", str(game.total_plane_clear_types[2])), ("Quad clears:", str(game.total_plane_clear_types[3])), 
                                     ("Piece spins:", str(game.total_spins)), ("Spin singles:", str(game.total_spin_clear_types[0])), ("Spin doubles:", str(game.total_spin_clear_types[1])), ("Spin triples:", str(game.total_spin_clear_types[2]))))):
        stat_category_text = font_small.render(category, False, COLORS[-3])
        screen.blit(stat_category_text, (WINDOW_WIDTH*0.5-WINDOW_HEIGHT*0.5+(WINDOW_HEIGHT*0.5*(position%2)), dropdown_depth+WINDOW_HEIGHT*(0.21+0.05*(position//2))))
        stat_text = font_small.render(stat, False, COLORS[-3])
        screen.blit(stat_text, (WINDOW_WIDTH*0.5-WINDOW_HEIGHT*0.15+(WINDOW_HEIGHT*0.5*(position%2)), dropdown_depth+WINDOW_HEIGHT*(0.21+0.05*(position//2))))

def get_color(id, face, closest_vertex, rot, ui=False):
    if ui:
        r, g, b = UI_COLORS[id]
    else:
        r, g, b = COLORS[id]
    r, g, b = (r/255)**0.5, (g/255)**0.5, (b/255)**0.5 # convert to relative brightness
    match face:
        case 0:
            if closest_vertex in [4, 5, 6, 7]: # left face (before rotation)
                shade = (rot-1)%4-2
                r, g, b = r*(shade*0.6+1), g*(shade*0.4+1), b*(shade*0.2+1)
            elif closest_vertex in [0, 1, 2, 3]: # right face (before rotation)
                shade = (rot+1)%4-2
                r, g, b = r*(shade*0.6+1), g*(shade*0.4+1), b*(shade*0.2+1)
        case 1:
            if closest_vertex in [2, 3, 6, 7]: # front face (before rotation)
                shade = (rot-2)%4-2
                r, g, b = r*(shade*0.6+1), g*(shade*0.4+1), b*(shade*0.2+1)
            elif closest_vertex in [0, 1, 4, 5]: # back face (before rotation)
                shade = (rot)%4-2
                r, g, b = r*(shade*0.6+1), g*(shade*0.4+1), b*(shade*0.2+1)
        case 2:
            r, g, b = r*1.225, g*1.15, b*1.075
    r, g, b = r**2*255, g**2*255, b**2*255 # convert back to absolute brightness
    r, g, b = min(255, r), min(255, g), min(255, b) # cap the color values at 255
    return r, g, b

def render_cubes(screen, cubes_to_render, rot, next_pos=0, hold_position=False):
    for n in range(len(cubes_to_render)):
        x, y = deepcopy(cubes_to_render[n][0]), deepcopy(cubes_to_render[n][1])
        cubes_to_render[n][0] = x*math.cos(rot*math.pi/2)+y*math.sin(rot*math.pi/2)
        cubes_to_render[n][1] = y*math.cos(rot*math.pi/2)-x*math.sin(rot*math.pi/2)+Y_CAMERA_DISTANCE
        if next_pos > 0: # renders the next pieces at a given displacement
            cubes_to_render[n][0] += (max(WIDTH, DEPTH)*DEPTH_LEVEL*0.21+8.7) * (1 if not hold_position else -1) # draw the held piece at the other side of the UI
            cubes_to_render[n][1] += 25*DEPTH_LEVEL*ASPECT_RATIO/4*3
            cubes_to_render[n][2] += 4.7*next_pos-2.5
    cubes_to_render = sorted(cubes_to_render, key=lambda cube: -(cube[0]**2+cube[1]**2+cube[2]**2)) # distance from the camera squared, those furthest away are rendered first
    for n in range(len(cubes_to_render)):
        x, y, z, id = cubes_to_render[n]
        cube_vertices = []
        vertex_distances = []
        vertex_id = 0
        vertex_offset = CUBE_VERTEX_OFFSET/2 if id == -1 else CUBE_VERTEX_OFFSET # secluded cubes appear smaller to make perspective more clear
        for a in (vertex_offset, -vertex_offset):
            for b in (vertex_offset, -vertex_offset):
                for c in (z+vertex_offset, z-vertex_offset): # to do: use itertools or something for this
                    x += a*math.cos(rot*math.pi/2)+b*math.sin(rot*math.pi/2)
                    y += b*math.cos(rot*math.pi/2)-a*math.sin(rot*math.pi/2)
                    cube_vertices.append((x, y, c))
                    vertex_distances.append(x**2+y**2+c**2) # squared distance
                    vertex_id += 1
                    x, y, z, id = cubes_to_render[n]
        closest_vertex = vertex_distances.index(min(vertex_distances))
        near_vertices = [closest_vertex^1, closest_vertex^2, closest_vertex^4] # XOR with 1, 2, 4 to get the nearby vertices
        far_vertices = [closest_vertex^6, closest_vertex^5, closest_vertex^3] # XOR with 6, 5, 3 to get the vertices further away (but not polar opposites)
        polygons_to_draw = [
            [screen_coordinates(*cube_vertices[closest_vertex]), screen_coordinates(*cube_vertices[near_vertices[0]]), screen_coordinates(*cube_vertices[far_vertices[2]]), screen_coordinates(*cube_vertices[near_vertices[1]])],
            [screen_coordinates(*cube_vertices[closest_vertex]), screen_coordinates(*cube_vertices[near_vertices[0]]), screen_coordinates(*cube_vertices[far_vertices[1]]), screen_coordinates(*cube_vertices[near_vertices[2]])],
            [screen_coordinates(*cube_vertices[closest_vertex]), screen_coordinates(*cube_vertices[near_vertices[1]]), screen_coordinates(*cube_vertices[far_vertices[0]]), screen_coordinates(*cube_vertices[near_vertices[2]])] # big and clunky, should probably be reworked
        ] # since there is no drawing priority here, sometimes **very** slight polygon clipping can occur, though it's practically unnoticeable so I can't be bothered to fix it - also the top always gets rendered last
        if not RENDER_CUBES:
            pygame.draw.circle(screen, COLORS[id], screen_coordinates(x, y, z), (x**2+y**2+z**2)**0.5/3, width=5) # in case drawing cubes gets unreasonably laggy
        if RENDER_CUBES:
            for face in range(3):
                border_width = GHOST_BORDER_WIDTH*2 if id == -2 else (GHOST_BORDER_WIDTH if id < 0 else 0) # fully grounded ghosts have thicker borders, draw filled polygon for non-ghosts
                pygame.draw.polygon(screen, get_color(id, face, closest_vertex, rot) if id >= 0 else COLORS[id], polygons_to_draw[face], width=border_width) # draw edges and ignore shading if it is a ghost/secluded piece with a negative ID

def draw_game_grid(screen, game):
    cubes_to_render = []
    for x in range(WIDTH):
        for y in range(DEPTH):
            for z in range(HEIGHT):
                if game.grid[x][y][z] > 0:
                    cubes_to_render.append([x-(WIDTH-1)/2, y-(DEPTH-1)/2, z+(HEIGHT-1)/1.8, game.grid[x][y][z]])
    for n in game.current_piece["cubes"]:
        x, y, z = n
        cubes_to_render.append([x-(WIDTH-1)/2, y-(DEPTH-1)/2, z+(HEIGHT-1)/1.8, game.current_piece["id"]])
    render_cubes(screen, cubes_to_render, game.visual_grid_rotation)

def draw_ghost_display(screen, game):
    if RENDER_CENTERS:
        for n in range(len(game.current_piece["centers"])):
            center_point = game.current_piece["centers"][n]
            center_point = [center_point[0]-(WIDTH-1)/2, center_point[1]-(DEPTH-1)/2, center_point[2]+(HEIGHT-1)/1.8] # make this a list for item assignment
            for axis in range(3):
                center_marker_start = deepcopy(center_point)
                center_marker_start[axis] -= CUBE_VERTEX_OFFSET/2
                center_marker_start = [center_marker_start[0]*math.cos(game.visual_grid_rotation*math.pi/2)+center_marker_start[1]*math.sin(game.visual_grid_rotation*math.pi/2),
                                    center_marker_start[1]*math.cos(game.visual_grid_rotation*math.pi/2)-center_marker_start[0]*math.sin(game.visual_grid_rotation*math.pi/2)+Y_CAMERA_DISTANCE,
                                    center_marker_start[2]] # rotate the marker's ends relative to the grid's rotation
                center_marker_end = deepcopy(center_point)
                center_marker_end[axis] += CUBE_VERTEX_OFFSET/2
                center_marker_end = [center_marker_end[0]*math.cos(game.visual_grid_rotation*math.pi/2)+center_marker_end[1]*math.sin(game.visual_grid_rotation*math.pi/2),
                                    center_marker_end[1]*math.cos(game.visual_grid_rotation*math.pi/2)-center_marker_end[0]*math.sin(game.visual_grid_rotation*math.pi/2)+Y_CAMERA_DISTANCE,
                                    center_marker_end[2]] # see above
                pygame.draw.line(screen, COLORS[-2-n], screen_coordinates(*center_marker_start), screen_coordinates(*center_marker_end), GHOST_BORDER_WIDTH)
    cubes_to_render = []
    for x in range(WIDTH):
        for y in range(DEPTH):
            for z in range(HEIGHT):
                if game.grid[x][y][z] < 0:
                    cubes_to_render.append([x-(WIDTH-1)/2, y-(DEPTH-1)/2, z+(HEIGHT-1)/1.8, game.grid[x][y][z]])
    render_cubes(screen, cubes_to_render, game.visual_grid_rotation) # render secluded space indicators first, then the ghost piece always in front of it
    cubes_to_render = []
    if game.mode == "Playing":
        for n in game.ghost_piece["cubes"]:
            x, y, z = n
            cubes_to_render.append([x-(WIDTH-1)/2, y-(DEPTH-1)/2, z+(HEIGHT-1)/1.8, -2 if game.piece_fully_grounded(game.ghost_piece) else -3])
        render_cubes(screen, cubes_to_render, game.visual_grid_rotation)

def draw_next_pieces(screen, game):
    for m in range(NEXT_PIECE_COUNT):
        cubes_to_render = []
        for n in game.next_pieces[m]["cubes"]:
            x, y, z = n
            cubes_to_render.append([x-(WIDTH-1)/2, y-(DEPTH-1)/2, z+(HEIGHT-1)/1.8, game.next_pieces[m]["id"]])
        render_cubes(screen, cubes_to_render, game.visual_grid_rotation, next_pos=m+1)
    cubes_to_render = []
    if game.held_piece:
        for n in game.held_piece["cubes"]:
            x, y, z = n
            cubes_to_render.append([x-(WIDTH-1)/2, y-(DEPTH-1)/2, z+(HEIGHT-1)/1.8, game.held_piece["id"]])
        render_cubes(screen, cubes_to_render, game.visual_grid_rotation, next_pos=1, hold_position=True)

def toggle_pause_game(game):
    match game.mode:
        case "Playing":
            game.mode = "Paused"
        case "Paused":
            if game.rotate_modifier == True:
                game.mode = "Home" # exit game
            else:
                game.mode = "Playing"
        case "Finished":
            game.mode = "Home" # exit game

def controller_input_check(controller, controller_button_states, controller_analog_states, game):
    for button_id in controller_bindings:
        input = controller_bindings.index(button_id)
        if not controller.get_button(button_id) and controller_button_states[controller_bindings.index(button_id)]: # button release when it is currently held
            match input:
                case 7:
                    game.rotate_modifier = False
                    if game.mode == "Playing":
                        if game.in_hard_drop: # only defined if the game has been initialized
                            game.drop_piece(instant_placement=True) # fully drop upon releasing the modifier key
                case 8:
                    ... # hold piece, only action is on button down
                case 9:
                    ... # pause game, only action is on button down
                case 10:
                    game.key_hold_times[6] = 0
                case _:
                    game.key_hold_times[input] = 0
            controller_button_states[input] = False
        elif ((game.mode == "Playing") or (input in (7, 9)) or ((game.mode == "Finished") and (input in (4, 5)) and game.rotate_modifier == True)) and controller.get_button(button_id) and (not controller_button_states[controller_bindings.index(button_id)]): # only if button is pressed and not currently held
            if game.rotate_modifier == False:
                match input:
                    case 7:
                        game.rotate_modifier = True
                    case 8:
                        game.hold_piece()
                    case 9:
                        toggle_pause_game(game)
                    case 10:
                        game.basic_input(6)
                    case _:
                        game.basic_input(input)
            else:
                match input:
                    case 7:
                        game.rotate_modifier = True
                    case 8:
                        game.hold_piece()
                    case 9:
                        toggle_pause_game(game)
                    case 10:
                        game.modified_input(6)
                    case _:
                        if not ((game.mode == "Finished") and (input in (4, 5))):
                            game.modified_input(input)
                        else:
                            game.basic_input(input) # for rotating the board when hiding the game over screen
            controller_button_states[input] = True
        if game.mode == "Home" and controller.get_button(button_id) and (not controller_button_states[controller_bindings.index(button_id)]): # home menu button presses
            match input:
                case 6:
                    game.init_game()
                case _:
                    if input < 4:
                        game.change_initial_level((1, 10, -1, -10)[input])
            controller_button_states[input] = True
    for input, axis, dir in (0, 0, 1), (1, 1, -1), (2, 0, -1), (3, 1, 1), (4, 2, -1), (5, 2, 1), (8, 4, 1): # to do: add other controller support here. analog controls only for the first 6 inputs and the hold input currently
        if controller.get_axis(axis) * dir < ANALOG_DEADZONE_WIDTH and controller_analog_states[input]: # button release when it is currently held
            if input < 6:
                game.key_hold_times[input] = 0
            controller_analog_states[input] = False
        elif ((game.mode == "Playing") or ((game.mode == "Finished") and (input in (4, 5)) and game.rotate_modifier == True)) and controller.get_axis(axis) * dir > ANALOG_DEADZONE_WIDTH and (not controller_analog_states[input]): # only if button is pressed and not currently held
            if input < 6:
                if game.rotate_modifier == False:
                    game.basic_input(input)
                else:
                    if not ((game.mode == "Finished") and (input in (4, 5))):
                        game.modified_input(input)
                    else:
                        game.basic_input(input) # for rotating the board when hiding the game over screen
            else:
                game.hold_piece()
            controller_analog_states[input] = True
        if game.mode == "Home" and controller.get_axis(axis) * dir > ANALOG_DEADZONE_WIDTH and (not controller_analog_states[input]): # home menu button presses
            match input:
                case 6:
                    game.init_game()
                case _:
                    if input < 4:
                        game.change_initial_level((1, 10, -1, -10)[input])
            controller_analog_states[input] = True

def keyboard_input_check(event, game):
    if event.type == KEYUP:
        try:
            input = hotkeys.index(event.dict["scancode"])
            match input:
                case 7:
                    game.rotate_modifier = False
                    if game.mode == "Playing":
                        if game.in_hard_drop: # only defined if the game has been initialized
                            game.drop_piece(instant_placement=True) # fully drop upon releasing the modifier key
                case 8: # hold piece, only action is on KEYDOWN
                    pass
                case 9: # pause game, only action is on KEYDOWN
                    pass
                case _:
                    game.key_hold_times[input] = 0
        except ValueError:
            pass
    if event.type == KEYDOWN:
        # print(event.dict["scancode"]) # debug for scancodes
        try:
            input = hotkeys.index(event.dict["scancode"])
            match input:
                case 7:
                    game.rotate_modifier = True
                case 8:
                    if game.mode == "Playing":
                        game.hold_piece()
                case 9:
                    toggle_pause_game(game)
                case _:
                    if game.mode == "Playing":
                        if game.rotate_modifier == False:
                            game.basic_input(input)
                        else:
                            game.modified_input(input)
                    elif (game.mode == "Finished") and (input in (4, 5)) and game.rotate_modifier == True: # for inspecting the grid upon pressing the modifier key on the game over screen
                        game.basic_input(input)
                    elif game.mode == "Home": # start game
                        match input:
                            case 6:
                                game.init_game()
                            case _:
                                if input < 4:
                                    game.change_initial_level((1, 10, -1, -10)[input])
        except ValueError:
            pass

def main():
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.Surface.convert_alpha(screen)
    pygame.display.set_caption("Qubitrix")
    clock = pygame.time.Clock()
    pygame.font.init()
    font_small = get_small_font(WINDOW_HEIGHT)
    font_large = get_large_font(WINDOW_HEIGHT)
    pygame.mixer.init()
    pygame.joystick.init()
    controller_connected = pygame.joystick.get_count() > 0
    if controller_connected:
        controller = pygame.joystick.Joystick(0)
        numbuttons = controller.get_numbuttons()
        controller_button_states = [False for _ in range(len(controller_bindings))]
        controller_analog_states = [False for _ in range(9)] # note that indexes 6 and 7 are unused
    game = Game()
    kb_controller = KeyboardController()

    while True:
        if game.mode == "Home":
            ui_color_id = min(math.ceil(game.initial_level/4), 9)
        else:
            ui_color_id = min(math.ceil(game.level/4), 9)
        screen.fill(tuple(int(c) for c in BACKGROUND_COLORS[ui_color_id]))

        if controller_connected:
            controller_input_check(controller, controller_button_states, controller_analog_states, game)

        # kb_controller.process_events() # This prevents Pygame from fetching any other keyboard inputs, so it is disabled for the time being.

        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                sys.exit()
            keyboard_input_check(event, game) # soon to be deprecated
        
        match game.mode:
            case "Playing":
                game.tick()
            case "Paused":
                game.ease_grid_rotation() # to prevent the grid from being stuck at an improper angle when paused
            case "Finished":
                game.ease_grid_rotation()
                game.game_over_screen_tick()

        match game.mode:
            case "Playing":
                draw_game_ui(screen, game, font_small, font_large, ui_color_id)
                draw_game_grid(screen, game)
                draw_next_pieces(screen, game)
                draw_ghost_display(screen, game)
            case "Paused":
                draw_game_ui(screen, game, font_small, font_large, ui_color_id)
                draw_pause_ui(screen, font_small)
            case "Finished":
                draw_game_ui(screen, game, font_small, font_large, ui_color_id)
                draw_game_grid(screen, game)
                draw_next_pieces(screen, game)
                draw_ghost_display(screen, game)
                if not game.rotate_modifier:
                    draw_finish_ui(screen, game, font_small, font_large, ui_color_id)
            case "Home":
                draw_home_ui(screen, game, font_small, font_large)
        
        pygame.display.update()
        if ((pygame.time.Clock.get_fps(clock) / FPS) < 0.98) and pygame.time.get_ticks() > 500:
            print("something's causing lag")
        clock.tick(FPS)

if __name__ == '__main__':
    main()
