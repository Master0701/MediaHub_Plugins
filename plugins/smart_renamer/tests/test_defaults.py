from pathlib import Path
def test_defaults_exist():
 root=Path(__file__).resolve().parents[1]; assert (root/"defaults/renamer/Settings.ini").is_file(); assert (root/"defaults/renamer/Presets").is_dir()
