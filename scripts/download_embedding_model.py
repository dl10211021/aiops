from __future__ import annotations

import argparse
import sys
from pathlib import Path

from huggingface_hub import snapshot_download

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.local_embedding import (
    DEFAULT_LOCAL_EMBEDDING_PATH,
    DEFAULT_LOCAL_EMBEDDING_REPO_ID,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Download the default OpsCore local embedding model.")
    parser.add_argument("--repo-id", default=DEFAULT_LOCAL_EMBEDDING_REPO_ID)
    parser.add_argument("--local-dir", default=str(DEFAULT_LOCAL_EMBEDDING_PATH))
    args = parser.parse_args()

    target = Path(args.local_dir)
    target.mkdir(parents=True, exist_ok=True)
    snapshot_download(
        repo_id=args.repo_id,
        local_dir=str(target),
        ignore_patterns=["*.h5", "*.msgpack", "*.onnx", "*.ot", "*.tflite"],
    )
    print(f"Embedding model downloaded: {args.repo_id} -> {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
