# model-downloader-util

Download or resolve model files from local paths, HTTP(S), S3-compatible storage (S3, MinIO, RustFS), Google Cloud Storage, and Git LFS.

## Install

```bash
pip install modeldownloaderutil
```

From source:

```bash
uv sync
```

## Usage

```python
from modeldownloaderutil import download_model, cache_dir, storage_key

path = download_model("s3://my-bucket/models/weights.onnx")
path = download_model("https://example.com/model.onnx", force_download=True)
path = download_model(
    "git+https://github.com/treeleaftech/biometricslib.git#biometricslib/models/model_4_kps.onnx.zip"
)
```

Git+ sources resolve **cache → RustFS → git**. The object key is the same everywhere:

```
treeleaftech/biometricslib/biometricslib/models/model_4_kps.onnx.zip
```

so you do not change model URLs when switching storage.

## Supported sources

| Scheme | Example |
|--------|---------|
| Local | `/path/to/model.onnx`, `~/models/x.onnx` |
| HTTP(S) | `https://host/path/model.onnx` |
| S3 | `s3://bucket/key` |
| MinIO | `minio://bucket/key` (`MINIO_ENDPOINT`) |
| RustFS | `rustfs://bucket/key` (`RUSTFS_MODEL_ENDPOINT`) |
| GCS | `gs://bucket/object` |
| Git LFS | `git+https://github.com/org/repo.git#path/in/repo.onnx` |

## Cache

Default: platformdirs cache for `model_registry` (override with `MODEL_CACHE_DIR`).

```
<cache>/
  s3/<bucket>/<key>
  gs/<bucket>/<object>
  url/<host>/<path>
  git/<repo_slug>/<file_path>
  git/<repo_slug>.lock
```

## Progress

HTTP(S), S3/MinIO/RustFS, GCS, and Git LFS show tqdm byte bars. Disable with `MODEL_DOWNLOAD_PROGRESS=0` (or `TQDM_DISABLE=1`).

## Environment

Copy `.env.example` to `.env` in the project root (loaded automatically on `download_model`).

| Variable | Purpose |
|----------|---------|
| `MODEL_CACHE_DIR` | Download cache root (`cache_dir()`) |
| `MODEL_DOWNLOAD_PROGRESS` | Set to `0`/`false` to disable tqdm progress bars |
| `RUSTFS_MODEL_ENDPOINT` | RustFS API URL. Default `https://s3.treeleaf.ai`. Optional path is `/{bucket}/{prefix}`. |
| `RUSTFS_MODEL_ACCESS_KEY` / `RUSTFS_MODEL_SECRET_KEY` | Credentials for model objects (required to use RustFS) |
| `MINIO_ENDPOINT` | Required for `minio://` URLs |
| `MODEL_ACCESS_KEY` / `MODEL_SECRET_KEY` | Fallback credentials for `s3://` / `minio://` |

## Development

```bash
make test
make build
```

## Publish to PyPI

Create an API token at [pypi.org](https://pypi.org/manage/account/token/) (scope: project `modeldownloaderutil` or entire account).

```bash
export UV_PUBLISH_TOKEN=pypi-xxxxxxxx
make publish
```
