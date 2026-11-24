"""Download the pinned upstream model and verify its SHA-256 before installation."""
import hashlib
from pathlib import Path
from urllib.request import urlopen

COMMIT = 'fe0ef7bce7dbb2890b3374836e9970c841b17219'
URL = f'https://raw.githubusercontent.com/HassanCodesIt/corn-leaf-disease-detection/{COMMIT}/corn_Leaf_model.pt'
SHA256 = 'bdab3208322293a16fd80610d3cff160983e9bb6b4e0c04eb0a0f9ba57c18b8c'
DESTINATION = Path(__file__).resolve().parents[1] / 'weights/corn/corn_Leaf_model.pt'


def main():
    with urlopen(URL, timeout=120) as response:
        data = response.read()
    if data.startswith(b'version https://git-lfs.github.com/spec/'):
        raise RuntimeError('Unduhan merupakan pointer Git LFS, bukan bobot model.')
    digest = hashlib.sha256(data).hexdigest()
    if digest != SHA256:
        raise RuntimeError(f'SHA-256 berbeda: {digest}; bobot tidak dipasang.')
    DESTINATION.parent.mkdir(parents=True, exist_ok=True)
    DESTINATION.write_bytes(data)
    print(f'{DESTINATION}\nSHA-256: {digest}\nBytes: {len(data)}')


if __name__ == '__main__':
    main()
