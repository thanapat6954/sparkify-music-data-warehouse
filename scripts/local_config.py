"""Read project-local settings without overriding exported environment variables."""
import os
from pathlib import Path


def load_local_env(root: Path):
    path = root / '.env'
    if path.exists():
        for line in path.read_text(encoding='utf-8-sig').splitlines():
            if line.strip() and not line.lstrip().startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def save_local_setting(root: Path, key: str, value: str):
    path = root / '.env'
    lines = path.read_text(encoding='utf-8').splitlines() if path.exists() else []
    lines = [line for line in lines if not line.startswith(key + '=')]
    lines.append(key + '=' + value)
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    os.environ[key] = value
