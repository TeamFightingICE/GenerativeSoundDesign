from __future__ import annotations

import argparse
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

AUDIO_EXTS = {".wav", ".mp3", ".ogg", ".flac", ".m4a", ".aac", ".wma", ".aiff", ".aif", ".opus"}


def norm_name(s: str) -> str:
    """
    Normalization used to match names despite capitalization / separators:
    - lowercase
    - remove extension if present
    - convert non-alnum to underscore
    - collapse underscores
    """
    s = Path(s).stem  # drop extension if any
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s


def is_audio_file(p: Path) -> bool:
    return p.is_file() and p.suffix.lower() in AUDIO_EXTS


def ensure_ffmpeg_available(ffmpeg: str = "ffmpeg") -> None:
    if shutil.which(ffmpeg) is None:
        raise RuntimeError(
            f"FFmpeg not found ('{ffmpeg}'). Install it first.\n"
            f"Conda:  conda install -c conda-forge ffmpeg\n"
            f"Ubuntu: sudo apt-get update && sudo apt-get install -y ffmpeg\n"
            f"Windows: install ffmpeg and ensure it's on PATH."
        )


def ffmpeg_convert_to_wav_mono(
    *,
    ffmpeg: str,
    src: Path,
    dst: Path,
    sample_rate: Optional[int] = None,
) -> None:
    """
    High-quality conversion to WAV mono. Uses PCM 16-bit by default (broadly compatible).
    If you need PCM 24-bit instead, change pcm_s16le -> pcm_s24le.
    """
    dst.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        ffmpeg,
        "-y",                 # overwrite output
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(src),
        "-ac",
        "1",                 # mono
        "-c:a",
        "pcm_s16le",         # WAV PCM 16-bit
    ]
    if sample_rate is not None:
        cmd += ["-ar", str(sample_rate)]
    cmd += [str(dst)]

    subprocess.run(cmd, check=True)


@dataclass(frozen=True)
class MappingRule:
    source_key: str
    output_names: List[str]


def build_rules() -> List[MappingRule]:
    """
    Output names here must match the example folder naming (robust to case/underscores via norm_name()).
    """
    return [
        # A: Light Punch -> crouch/stand/air variants + air special
        MappingRule("A", ["CROUCH_A", "STAND_A", "AIR_A", "AIR_DA", "AIR_F_D_DFA"]),

        # B: Light Kick -> crouch/stand/air variants + air special
        MappingRule("B", ["CROUCH_B", "STAND_B", "AIR_B", "AIR_DB", "AIR_F_D_DFB"]),

        # FA: Heavy Punch
        MappingRule("FA", ["CROUCH_FA", "STAND_FA", "AIR_FA", "AIR_UA", "AIR_D_DB_BA"]),

        # FB: Heavy Kick
        MappingRule("FB", ["CROUCH_FB", "STAND_FB", "AIR_FB", "AIR_UB", "AIR_D_DB_BB"]),

        # Throws (example folder uses THROW_W_A / THROW_W_B)
        MappingRule("Throw_A", ["THROW_A"]),
        MappingRule("Throw_B", ["THROW_B"]),

        # Getting hit + throw-specific hit/suffer
        MappingRule("Hit_A", ["HitA", "THROW_HIT"]),
        MappingRule("Hit_B", ["HitB", "THROW_SUFFER"]),

        # Movement
        MappingRule("Walk", ["FORWARD_WALK", "BACK_STEP"]),
        MappingRule("Dash", ["DASH"]),
        MappingRule("Crouch", ["CROUCH"]),
        MappingRule("Jump", ["FOR_JUMP", "BACK_JUMP", "JUMP"]),

        # Guards
        MappingRule("Guard", ["AIR_GUARD", "CROUCH_GUARD", "STAND_GUARD", "WeakGuard"]),

        # Specials
        MappingRule("Light_Uppercut", ["STAND_F_D_DFA"]),
        MappingRule("Hard_Uppercut", ["STAND_F_D_DFB"]),
        MappingRule("Dashkick", ["STAND_D_DB_BB"]),
        MappingRule("Jump_Strike", ["STAND_D_DB_BA"]),

        # Fireballs
        MappingRule("Light_Fireball", ["AIR_D_DF_FA", "STAND_D_DF_FA"]),
        MappingRule("Heavy_Fireball", ["AIR_D_DF_FB", "STAND_D_DF_FB"]),
        MappingRule("Special_Fireball", ["STAND_D_DF_FC"]),

        # Misc
        MappingRule("Landing", ["LANDING"]),
        MappingRule("EnergyChange", ["Energy_Charge", "EnergyCharge", "EnergyChange"]),
        MappingRule("Heartbeat", ["Heartbeat"]),
        MappingRule("BorderAlert", ["BorderAlert"]),
        MappingRule("BGM0", ["BGM0"]),
    ]



def build_output_to_sourcekey_map(example_files: List[Path]) -> Dict[str, str]:
    """
    Returns: { exact_example_stem (case preserved) -> source_key }
    by matching normalized stems to normalized rule outputs.
    """
    rules = build_rules()

    # normalized rule output -> source_key
    rule_out_norm_to_key: Dict[str, str] = {}
    for r in rules:
        for out_name in r.output_names:
            rule_out_norm_to_key[norm_name(out_name)] = r.source_key

    out: Dict[str, str] = {}
    for ef in example_files:
        stem = ef.stem  # keep EXACT stem as in example folder
        nstem = norm_name(stem)
        if nstem in rule_out_norm_to_key:
            out[stem] = rule_out_norm_to_key[nstem]

    return out


def find_source_files_for_keys(subfolder: Path) -> Dict[str, Path]:
    """
    Finds the 25 input sounds inside one subfolder and maps them to the 25 source keys.

    Matching is by filename stem with normalization, so capitalization / separators are robust.

    If your 25 input files use different naming, add aliases below.
    """
    files = [p for p in subfolder.iterdir() if is_audio_file(p)]
    if len(files) < 25:
        raise RuntimeError(f"{subfolder}: found {len(files)} audio files (<25).")

    # Aliases for matching the 25 source keys.
    # Add more aliases here if your 25-file naming differs.
    key_aliases: Dict[str, List[str]] = {
        # Based on your 25-file folder names
        "A": ["A", "light_punch", "lightpunch", "LightPunch", "Light_Punch", "LP"],
        "B": ["B", "light_kick", "lightkick", "LightKick", "Light_Kick", "LK"],
        "FA": ["FA", "heavy_punch", "heavypunch", "HeavyPunch", "Heavy_Punch", "HP"],
        "FB": ["FB", "heavy_kick", "heavykick", "HeavyKick", "Heavy_Kick", "HK"],

        "Throw_A": ["Throw_A", "throw_light", "throwlight", "ThrowLight", "Throw_Light"],
        "Throw_B": ["Throw_B", "throw_heavy", "throwheavy", "ThrowHeavy", "Throw_Heavy"],

        "Hit_A": ["Hit_A", "getting_hit_light", "gettinghitlight", "Getting_Hit_Light", "getting_hit_lit", "HitLight"],
        "Hit_B": ["Hit_B", "getting_hit_heavy", "gettinghitheavy", "Getting_Hit_Heavy", "HitHeavy"],

        "Walk": ["Walk", "walk", "forward_walk", "forwardwalk", "Forward_Walk"],
        "Dash": ["Dash", "dash", "DASH"],
        "Crouch": ["Crouch", "crouch", "CROUCH"],
        "Jump": ["Jump", "jump", "JUMP"],
        "Guard": ["Guard", "guard", "GUARD"],

        "Light_Uppercut": ["Light_Uppercut", "light_uppercut", "lightuppercut"],
        "Hard_Uppercut": ["Hard_Uppercut", "hard_uppercut", "harduppercut"],
        "Dashkick": ["Dashkick", "dashkick", "Dash_kick"],
        "Jump_Strike": ["Jump_Strike", "jump_strike", "jumpstrike"],

        "Light_Fireball": ["Light_Fireball", "light_fireball", "lightfireball"],
        "Heavy_Fireball": ["Heavy_Fireball", "heavy_fireball", "heavyfireball"],
        "Special_Fireball": ["Special_Fireball", "special_fireball", "specialfireball"],

        "Landing": ["Landing", "landing"],
        "EnergyChange": ["EnergyChange", "energychange", "Energy_Change", "energy_change"],
        "Heartbeat": ["Heartbeat", "heartbeat"],
        "BorderAlert": ["BorderAlert", "borderalert", "Border_Alert", "border_alert"],
        "BGM0": ["BGM0", "bgm0", "BGM", "bgm"],
    }


    # Pre-index all audio files by normalized stem
    by_norm: Dict[str, Path] = {}
    for f in files:
        by_norm[norm_name(f.stem)] = f

    found: Dict[str, Path] = {}
    missing: List[str] = []

    for key, aliases in key_aliases.items():
        match: Optional[Path] = None
        for a in aliases:
            na = norm_name(a)
            if na in by_norm:
                match = by_norm[na]
                break
        if match is None:
            missing.append(key)
        else:
            found[key] = match

    if missing:
        # Give the user actionable diagnostics.
        available = sorted({p.stem for p in files})
        raise RuntimeError(
            f"{subfolder}: could not match these required source keys: {missing}\n"
            f"Available stems (for debugging): {available}\n"
            f"Fix: rename files OR extend key_aliases in the script."
        )

    return found


def generate_full_folder(
    *,
    subfolder: Path,
    example_files: List[Path],
    out_to_key: Dict[str, str],
    ffmpeg: str,
    sample_rate: Optional[int],
    overwrite: bool,
) -> None:
    out_dir = subfolder.parent / f"{subfolder.name}-full"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Map 25 sources
    key_to_src = find_source_files_for_keys(subfolder)

    # Convert each of the 25 sources once to cached mono wav, then duplicate by copy
    cache_dir = out_dir / "_cache_converted_25"
    if overwrite and cache_dir.exists():
        shutil.rmtree(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)

    key_to_converted: Dict[str, Path] = {}
    for key, src in key_to_src.items():
        converted = cache_dir / f"{key}.wav"
        if overwrite or not converted.exists():
            ffmpeg_convert_to_wav_mono(
                ffmpeg=ffmpeg,
                src=src,
                dst=converted,
                sample_rate=sample_rate,
            )
        key_to_converted[key] = converted

    # Now create the 51 outputs using *exact* example stems, but output .wav
    unmapped: List[str] = []
    for ef in example_files:
        stem_exact = ef.stem  # keep as-is from example folder
        if stem_exact not in out_to_key:
            # This example file wasn't matched to any rule output (likely naming mismatch)
            unmapped.append(stem_exact)
            continue

        key = out_to_key[stem_exact]
        src_wav = key_to_converted[key]

        out_path = out_dir / f"{stem_exact}.wav"
        if out_path.exists() and not overwrite:
            continue
        shutil.copyfile(src_wav, out_path)

    if unmapped:
        # Not fatal by default; you may want strict behavior.
        # If you want strict, change this to: raise RuntimeError(...)
        print(
            f"[WARN] {subfolder.name}: {len(unmapped)} example filenames were not mapped by rules.\n"
            f"       Unmapped example stems (first 25 shown): {unmapped[:25]}\n"
            f"       Fix: adjust build_rules() output names to match example folder stems."
        )


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Create '-full' SFX folders: expand 25 inputs into 51 outputs using example folder naming."
    )
    ap.add_argument("--input_root", type=Path, required=True, help="Root folder containing subfolders (each with 25 audio files).")
    ap.add_argument("--example_dir", type=Path, required=True, help="Folder containing the 51 example SFX files (names define targets).")
    ap.add_argument("--overwrite", action="store_true", help="Overwrite existing outputs and reconvert.")
    ap.add_argument("--ffmpeg", type=str, default="ffmpeg", help="FFmpeg executable name/path.")
    ap.add_argument("--sample_rate", type=int, default=44100, help="Output sample rate (Hz). Set to 0 to preserve input rate.")
    args = ap.parse_args()

    ensure_ffmpeg_available(args.ffmpeg)

    input_root: Path = args.input_root
    example_dir: Path = args.example_dir
    overwrite: bool = args.overwrite
    ffmpeg: str = args.ffmpeg
    sample_rate: Optional[int] = None if args.sample_rate == 0 else int(args.sample_rate)

    if not input_root.exists():
        raise SystemExit(f"input_root not found: {input_root}")
    if not example_dir.exists():
        raise SystemExit(f"example_dir not found: {example_dir}")

    example_files = [p for p in example_dir.iterdir() if is_audio_file(p)]
    if len(example_files) == 0:
        raise SystemExit(f"No audio files found in example_dir: {example_dir}")

    # Map example stems -> source_key using normalized matching
    out_to_key = build_output_to_sourcekey_map(example_files)

    # Basic sanity: user expects 51.
    if len(example_files) != 51:
        print(f"[WARN] example_dir contains {len(example_files)} audio files (expected 51). Continuing anyway.")

    # Iterate subfolders
    subfolders = [p for p in input_root.iterdir() if p.is_dir() and not p.name.endswith("-full")]
    if not subfolders:
        raise SystemExit(f"No subfolders found under input_root: {input_root}")

    for sf in sorted(subfolders):
        try:
            generate_full_folder(
                subfolder=sf,
                example_files=sorted(example_files),
                out_to_key=out_to_key,
                ffmpeg=ffmpeg,
                sample_rate=sample_rate,
                overwrite=overwrite,
            )
            print(f"[OK] Generated: {sf.parent / (sf.name + '-full')}")
        except Exception as e:
            print(f"[ERROR] {sf}: {e}")


if __name__ == "__main__":
    main()
