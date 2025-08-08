# Qubitrix
A 3D falling block puzzle game primarily inspired by Tetris.

Note: The only controller supported at the moment is the PlayStation 4 controller (as it is the only one I have been able to test so far). Using other controllers may yield unexpected results.

You can install this game using pip:
```bash
pip install qubitrix
```
If you use UV to manage your Python environment, then you should prepend uv to any pip command to ensure that the package is installed in the correct environment:

```bash
uv pip install qubitrix
```

## Developers: 

Developers may install Qubitrix in editable mode as follows, so as you change the source, the changes are reflected immediately without needing to reinstall the package:

```bash
pip install -e .
```

## Running tests:

To install the tests, you can install using the `test` extra:
```bash
pip install -e ."[test]"
```

To run the tests you can use the `pytest` command from the command line:

```bash
pytest
```

## Coverage analysis:

To see which parts of the code are covered by tests and which are not, you need to run a coverage analysis.  
You need to have `pytest-cov` installed. 
If you installed the package with the `test` extra, it should already be installed. 
If not, you can install it separately:

```bash
pip install pytest-cov
```

To run tests with coverage, you can use the `--cov` option. This will generate a coverage report in the terminal:

```bash
pytest --cov=Qubitrix --cov-report=html
```

## Gameplay Controls:

WASD, D-pad or left analog stick - move the piece horizontally, select level

K/L, Square/Circle or right analog stick - rotate the view of the grid

Space, Cross or R1 - lower the piece, start game

Holding Shift or L1 with the horizontal movement or rotation buttons will rotate the piece in any of 6 directions.

Semicolon (;), Triangle or L2 - hold the current piece

Esc or touch pad click - pause/unpause the game, quit game on pause menu alongside Shift/L1

On the Game Over screen, holding Shift/L1 will show the final grid, which you can still rotate your view of.
