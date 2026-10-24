"""Run the complete pipeline in Docker, including from Windows OneDrive paths.

BuildKit may reject OneDrive placeholder/reparse metadata. Copy only the source
allowlist into a short ASCII temporary build context. Data stays bind-mounted.
"""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.local_config import load_local_env


def main():
    load_local_env(ROOT)
    temp_root = Path(tempfile.gettempdir()).resolve()
    with tempfile.TemporaryDirectory(prefix='sparkify-build-', dir=temp_root) as stage_name:
        stage = Path(stage_name).resolve()
        if not stage.is_relative_to(temp_root) or stage.parent != temp_root:
            raise ValueError('Build context must be inside the OS temporary directory')
        for name in ['Dockerfile', 'requirements.txt']:
            shutil.copyfile(ROOT / name, stage / name)
        for name in ['scripts', 'dbt']:
            shutil.copytree(ROOT / name, stage / name,
                ignore=shutil.ignore_patterns('__pycache__', '*.pyc', 'target', 'logs', 'dbt_packages', '.user.yml'))
        env = os.environ.copy()
        env['SPARKIFY_BUILD_CONTEXT'] = stage.as_posix()
        print('Building from a temporary source-only context; original ZIP files remain in place.', flush=True)
        subprocess.run(['docker', 'compose', '--profile', 'run', 'run', '--build', '--rm', 'pipeline'],
                       cwd=ROOT, env=env, check=True)


if __name__ == '__main__':
    main()
