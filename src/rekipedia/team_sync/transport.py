"""Transport layer for reki pull — download wiki bundles from remote URLs."""
import urllib.request
import zipfile
from pathlib import Path


def _download_https(url: str, dest: Path) -> None:
    """Download a file from an HTTPS URL to dest."""
    urllib.request.urlretrieve(url, dest)


def _download_s3(url: str, dest: Path) -> None:
    """Download from s3://bucket/key. Requires boto3."""
    try:
        import boto3
    except ImportError as e:
        raise ImportError(
            "S3 transport requires boto3: pip install rekipedia[aws]"
        ) from e
    # Parse s3://bucket/key
    path = url[len("s3://"):]
    bucket, _, key = path.partition("/")
    s3 = boto3.client("s3")
    s3.download_file(bucket, key, str(dest))


def _download_gcs(url: str, dest: Path) -> None:
    """Download from gs://bucket/blob. Requires google-cloud-storage."""
    try:
        from google.cloud import storage
    except ImportError as e:
        raise ImportError(
            "GCS transport requires google-cloud-storage: pip install rekipedia[gcs]"
        ) from e
    path = url[len("gs://"):]
    bucket_name, _, blob_name = path.partition("/")
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.download_to_filename(str(dest))


def download_bundle(url: str, dest_dir: Path) -> Path:
    """Download a wiki bundle zip from url into dest_dir. Returns path to the zip file."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    zip_path = dest_dir / "wiki-bundle.zip"
    if url.startswith("s3://"):
        _download_s3(url, zip_path)
    elif url.startswith("gs://"):
        _download_gcs(url, zip_path)
    elif url.startswith(("https://", "http://")):
        _download_https(url, zip_path)
    else:
        raise ValueError(f"Unsupported URL scheme: {url}")
    return zip_path


def extract_bundle(zip_path: Path, extract_dir: Path) -> Path:
    """Extract a bundle zip and return the bundle root dir."""
    extract_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(extract_dir)
    return extract_dir
