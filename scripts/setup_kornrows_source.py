"""Fetch the reviewed source once; never overwrite an existing checkout."""
from pathlib import Path
import subprocess

COMMIT = 'b0c4c857233e3bf76d56df81b83d16fabb3929f2'
REPOSITORY = 'https://github.com/andre-kotze/kornrows.git'
DESTINATION = Path(__file__).resolve().parents[1] / 'vendor/kornrows'


def main():
    if not DESTINATION.exists():
        subprocess.run(['git', 'clone', '--branch', 'master', '--single-branch', REPOSITORY, str(DESTINATION)], check=True)
        subprocess.run(['git', '-C', str(DESTINATION), 'checkout', '--detach', COMMIT], check=True)
    revision = subprocess.check_output(['git', '-C', str(DESTINATION), 'rev-parse', 'HEAD'], text=True).strip()
    changes = subprocess.check_output(['git', '-C', str(DESTINATION), 'status', '--porcelain'], text=True)
    if revision != COMMIT or changes:
        raise RuntimeError('Existing Kornrows checkout differs from reviewed commit; left untouched.')
    print(f'Kornrows source ready: {revision}. Corn checkpoint must be supplied separately.')


if __name__ == '__main__':
    main()
