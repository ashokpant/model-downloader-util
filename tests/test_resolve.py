from pathlib import Path
from zipfile import ZipFile

import pytest

from modeldownloaderutil import extract_archive, find_file, resolve_model


def test_find_file_returns_file(tmp_path: Path) -> None:
    f = tmp_path / "a.onnx"
    f.write_bytes(b"x")
    assert find_file(f) == f


def test_find_file_picks_shallowest(tmp_path: Path) -> None:
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "deep.onnx").write_bytes(b"d")
    top = tmp_path / "top.onnx"
    top.write_bytes(b"t")
    assert find_file(tmp_path) == top


def test_find_file_custom_suffix(tmp_path: Path) -> None:
    (tmp_path / "a.onnx").write_bytes(b"o")
    wanted = tmp_path / "b.custom"
    wanted.write_bytes(b"c")
    assert find_file(tmp_path, suffixes=[".custom"]) == wanted


def test_find_file_missing(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="No model file"):
        find_file(tmp_path)


def test_extract_archive_unzip(tmp_path: Path) -> None:
    onnx = tmp_path / "model.onnx"
    onnx.write_bytes(b"weights")
    zpath = tmp_path / "model.zip"
    with ZipFile(zpath, "w") as zf:
        zf.write(onnx, "model.onnx")
    dest = extract_archive(zpath)
    assert dest.is_dir()
    assert (dest / "model.onnx").read_bytes() == b"weights"
    assert extract_archive(zpath) == dest


def test_extract_archive_non_zip(tmp_path: Path) -> None:
    f = tmp_path / "a.onnx"
    f.write_bytes(b"x")
    assert extract_archive(f) == f


def test_resolve_model_unzip_and_find(monkeypatch, tmp_path: Path) -> None:
    onnx_name = "weights.onnx"
    zip_path = tmp_path / "bundle.zip"
    with ZipFile(zip_path, "w") as zf:
        zf.writestr(f"inner/{onnx_name}", b"ok")

    monkeypatch.setattr(
        "modeldownloaderutil.downloader.download_model",
        lambda source, force_download=False: zip_path,
    )
    path = resolve_model("s3://bucket/bundle.zip")
    assert path.name == onnx_name
    assert path.read_bytes() == b"ok"
