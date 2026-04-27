
# SFX Mapper

A Python tool that takes a core set of 25 sound effects and automatically duplicates, converts, and renames them into a full set of 51 properly named files based on an example template folder. 

This is particularly useful for game development or modding when you need to quickly map a small batch of base sounds (like light punch, heavy kick, jump) into a larger, specific folder structure required by a game engine.

## Prerequisites

Before running the script, ensure you have the following installed:

* **Python 3.7+**
* **FFmpeg**: The script uses FFmpeg to convert all sounds to high-quality mono WAV files.
  * **Windows:** Download [FFmpeg](https://ffmpeg.org/download.html), extract it, and add the `bin` folder to your system's PATH. 
  * **macOS:** `brew install ffmpeg`
  * **Linux (Ubuntu/Debian):** `sudo apt-get update && sudo apt-get install -y ffmpeg`

## Folder Structure

You need to arrange your audio files into two main areas: an **Example Folder** and an **Input Root Folder**.

* **Example Folder:** Contains your 51 target audio files (from this [link](https://github.com/TeamFightingICE/Generative-Sound-AI/tree/main/data/sounds). The script strictly uses the *filenames* here as a template for your final output; the actual audio inside them is ignored.
* **Input Root Folder:** A master folder containing one or more subfolders (e.g., characters or soundpacks). Each subfolder must contain your 25 base sound effects.

### Example Directory Layout

```text
my_project/
│
├── sdmaker.py
│
├── example_sounds/          <-- Your 51 template files
│   ├── CROUCH_A.wav
│   ├── STAND_FA.wav
│   └── ... 
│
└── input_sounds/            <-- Your input root folder
    ├── Character_One/       <-- Put your 25 base sounds here
    │   ├── light_punch.wav
    │   ├── heavy_kick.mp3
    │   └── ... 
    │
    └── Character_Two/       <-- The script processes multiple folders at once
        ├── A.wav
        ├── B.wav
        └── ...
```

## File Naming

The script is highly forgiving with how you name your 25 input files. It ignores capitalization, symbols, and file extensions (`.mp3`, `.wav`, `.ogg`, etc.). 

It uses an internal alias list to recognize your files. For example, for the "Light Punch" input, you can name your file `A.wav`, `light_punch.mp3`, `LightPunch.ogg`, or `LP.wav`. If you have a custom naming convention, you can open `sfx_mapper.py` and add your custom filenames to the `key_aliases` dictionary inside the `find_source_files_for_keys` function.

## Usage

Run the script from your terminal or command prompt, pointing it to your input and example folders:

```bash
python sfx_mapper.py --input_root ./input_sounds --example_dir ./example_sounds
```

The script will convert your 25 source files to standard 16-bit mono WAVs, map them to the 51 template names, and output a brand new folder named `./input_sounds/Character_One-full/`.

### Command-Line Arguments

| Argument | Requirement | Description |
| :--- | :--- | :--- |
| `--input_root` | **Required** | Path to the folder containing your subfolders of 25 sounds. |
| `--example_dir` | **Required** | Path to the folder containing the 51 example files. |
| `--overwrite` | Optional | Overwrite an existing `-full` folder and force reconversion. |
| `--ffmpeg` | Optional | Specific path to the FFmpeg executable (if not on your PATH). |
| `--sample_rate` | Optional | Output sample rate in Hz (default: `44100`). Set to `0` to keep the original rate. |

## Troubleshooting

* **`RuntimeError: FFmpeg not found`** Your computer doesn't know where FFmpeg is. Ensure it is installed and added to your system's PATH, or use the `--ffmpeg` argument to point directly to the executable.
* **`RuntimeError: found X audio files (<25)`** One of your input subfolders has fewer than 25 audio files. The script requires all 25 base sounds to be present to map everything correctly.
* **`could not match these required source keys`** The script couldn't figure out which of your files was supposed to be a specific move (like a Fireball or a Guard). Look at the "Available stems" printed in the error message, and rename your missing file to match one of the expected aliases.
```
