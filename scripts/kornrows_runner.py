"""Single-image JSON worker for the pinned Kornrows fork (isolated interpreter)."""
import hashlib
import json
import os
from pathlib import Path
import sys


def main():
    request = json.load(sys.stdin)
    weights = Path(request['weights']).resolve(strict=True)
    if weights.suffix.lower() != '.pt':
        raise ValueError('Kornrows requires its trained PyTorch .pt checkpoint')
    with weights.open('rb') as file:
        if file.read(80).startswith(b'version https://git-lfs.github.com/spec/'):
            raise ValueError('Git LFS pointer is not a checkpoint')
    repo = Path(request['repo']).resolve(strict=True)
    sys.path.insert(0, str(repo))  # Only this subprocess sees models and utils.
    # Upstream Annotator downloads Arial at import for RANK -1/0. We do not
    # use it (Django draws overlays); disable that import-time side effect.
    # No distributed/training code is run in this single-image worker.
    os.environ['RANK'] = '1'
    import torch
    import numpy as np
    from PIL import Image
    from models import experimental
    from models.yolo import Detect
    from utils.augmentations import letterbox
    from utils.general import check_img_size, non_max_suppression, scale_coords
    from utils.torch_utils import select_device

    # Disallow the upstream fallback downloader even if the file disappears.
    def local_checkpoint(path):
        return str(Path(path).resolve(strict=True))
    experimental.attempt_download = local_checkpoint
    device = select_device(request['device'])
    model = experimental.attempt_load(str(weights), map_location=device)
    names = model.names
    if isinstance(names, dict):
        if set(names) != {0}:
            raise ValueError('Expected exactly class 0 (cc), refusing other models')
        names = [names[0]]
    if list(names) != ['cc'] or not isinstance(model.model[-1], Detect) or model.model[-1].nc != 1:
        raise ValueError('Expected the Kornrows cc detector, not COCO or leaf disease weights')
    stride = int(model.stride.max())
    size = check_img_size(request['image_size'], s=stride)
    with Image.open(request['image']) as source:
        original = np.asarray(source.convert('RGB'))
    resized = letterbox(original, new_shape=size, stride=stride, auto=True)[0]
    tensor = torch.from_numpy(np.ascontiguousarray(resized.transpose(2, 0, 1))).to(device).float() / 255
    with torch.inference_mode():
        predictions = model(tensor.unsqueeze(0))[0]
        boxes = non_max_suppression(predictions, request['confidence'], 0.45, max_det=1000)[0]
        if len(boxes):
            boxes[:, :4] = scale_coords(tensor.shape[1:], boxes[:, :4], original.shape).round()
    detections = [{'xyxy': row[:4], 'confidence': row[4], 'class_id': int(row[5])}
                  for row in boxes.cpu().tolist() if row[2] > row[0] and row[3] > row[1]]
    result = {'names': list(names), 'detections': detections,
              'weights_sha256': hashlib.sha256(weights.read_bytes()).hexdigest()}
    Path(request['output']).write_text(json.dumps(result, allow_nan=False), encoding='utf-8')


if __name__ == '__main__':
    main()
