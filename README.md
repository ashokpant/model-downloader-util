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
from modeldownloaderutil import download_model, cache_dir

path = download_model("s3://my-bucket/models/weights.onnx")
path = download_model("https://example.com/model.onnx", force_download=True)
```

## Supported sources

| Scheme | Example |
|--------|---------|
| Local | `/path/to/model.onnx`, `~/models/x.onnx` |
| HTTP(S) | `https://host/path/model.onnx` |
| S3 | `s3://bucket/key` |
| MinIO | `minio://bucket/key` (`MINIO_ENDPOINT`) |
| RustFS | `rustfs://bucket/key` (`RUSTFS_ENDPOINT`) |
| GCS | `gs://bucket/object` |
| Git LFS | `git+https://github.com/org/repo.git#path/in/repo.onnx` |

## Cache

Default: `~/.cache/model-downloader` (override with `MODEL_CACHE_DIR`).

```
~/.cache/model-downloader/
  s3/<bucket>/<key>
  gs/<bucket>/<object>
  url/<host>/<path>
  git/<repo_slug>/<file_path>
```

## Environment

Copy `.env.example` to `.env` in the project root (loaded automatically on `download_model`).

| Variable | Purpose |
|----------|---------|
| `MODEL_CACHE_DIR` | Download cache root (`cache_dir()`) |
| `RUSTFS_ENDPOINT` | Required for `rustfs://` URLs |
| `MINIO_ENDPOINT` | Required for `minio://` URLs |
| `MODEL_ACCESS_KEY` / `MODEL_SECRET_KEY` | S3-compatible credentials |

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

Dry run on TestPyPI first:

```bash
export UV_PUBLISH_TOKEN=pypi-xxxxxxxx
make publish-test
pip install --index-url https://test.pypi.org/simple/ modeldownloaderutil
```
