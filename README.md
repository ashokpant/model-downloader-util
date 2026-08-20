# model-downloader-util

Download model files from local paths, HTTP(S), S3 / MinIO / RustFS, GCS, or Git LFS.

## Install

```bash
pip install modeldownloaderutil
```

## Usage

```python
from modeldownloaderutil import download_model, sources

path = download_model("s3://bucket/models/weights.onnx")
path = download_model("https://example.com/model.onnx")
path = download_model("git+https://github.com/org/repo.git#weights/a.onnx")

# Try sources in order (first success wins):
path = download_model(sources(
    "rustfs://bucket/org/repo/weights/a.onnx",
    "git+https://github.com/org/repo.git#weights/a.onnx",
))
# same as:
path = download_model(
    "rustfs://bucket/org/repo/weights/a.onnx,git+https://github.com/org/repo.git#weights/a.onnx"
)
```

## Schemes

| Scheme | Example | Notes |
|--------|---------|--------|
| Local | `/path/to/model.onnx` | |
| HTTP(S) | `https://host/model.onnx` | |
| S3 | `s3://bucket/key` | `MODEL_ACCESS_KEY` / `MODEL_SECRET_KEY` |
| MinIO | `minio://bucket/key` | `MINIO_ENDPOINT` |
| RustFS | `rustfs://bucket/key` | `RUSTFS_MODEL_ENDPOINT` + access/secret |
| GCS | `gs://bucket/object` | |
| Git LFS | `git+https://host/org/repo.git#path` | |

## Environment

| Variable | Purpose |
|----------|---------|
| `MODEL_CACHE_DIR` | Cache root |
| `MODEL_DOWNLOAD_PROGRESS` | `0` to disable progress bars |
| `RUSTFS_MODEL_ENDPOINT` | Required for `rustfs://` |
| `RUSTFS_MODEL_ACCESS_KEY` / `RUSTFS_MODEL_SECRET_KEY` | Or `MODEL_ACCESS_KEY` / `MODEL_SECRET_KEY` |
| `MINIO_ENDPOINT` | Required for `minio://` |

## Develop

```bash
make test
make build
```
