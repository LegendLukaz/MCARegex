# MCARegex
Utility for subsituting values in Minecraft .mca files (tested on Anvil Format ONLY)

***Backup your files before modifying your world***

## Installation
1. git clone or download the files
2. If you haven't installed `pipenv` yet, install it
```
# pip install pipenv
```
3. Go to the directory with the cloned repo
4. Run `pipenv install` to create and install the required virtualenv
5. Modify `main.py` according to [Usage](#usage) and `pipenv run main.py`

## Usage
There are multiple variables/function being definied at the start of the main section. Modify them accordingly:
- worldPath: `str` relative/absolute path to the world folder, i.e. the folder where `level.dat` is located
- tagType: `str` name of tag to be searched inside the `Level` tag in each chunk
- id: `str` id of the tag to be searched (will be changed to dict later to allow customisation)
- key: `str`
- searchStr: `str` regex string for substitution
- subfunc: custom function for modifying the matched string
