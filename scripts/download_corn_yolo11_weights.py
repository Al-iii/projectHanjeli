"""Fetch the official Git LFS binary at a pinned commit and verify its digest."""
import hashlib
from pathlib import Path
from urllib.request import urlopen

COMMIT = 'a662066aa41977c0eb1efd1b278a49a87c300fbe'
URL = f'https://media.githubusercontent.com/media/wjxn13/corn-leaf-disease-detector/{COMMIT}/best.pt'
SHA256 = 'c60b9bf7c9e85270fbc4656adc976f07a2cb082607366f373717003d42c47686'
SIZE = 19175123
DESTINATION = Path(__file__).resolve().parents[1] / 'weights/corn_leaf_yolo11/best.pt'


def main():
    with urlopen(URL, timeout=120) as response:
        data = response.read()
    if data.startswith(b'version https://git-lfs.github.com/spec/'):
        raise RuntimeError('Unduhan adalah pointer Git LFS, bukan bobot.')
    if len(data) != SIZE or hashlib.sha256(data).hexdigest() != SHA256:
        raise RuntimeError('Ukuran atau SHA-256 bobot berbeda; file tidak dipasang.')
    DESTINATION.parent.mkdir(parents=True, exist_ok=True)
    DESTINATION.write_bytes(data)
    print(f'{DESTINATION}\nBytes: {SIZE}\nSHA-256: {SHA256}')


if __name__ == '__main__':
    main()
