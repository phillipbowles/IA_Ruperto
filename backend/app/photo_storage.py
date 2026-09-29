"""Almacenamiento de JPEG en Railway Buckets (S3) o disco local en desarrollo."""

import io
import os
from pathlib import Path

import boto3
from botocore.config import Config


def _env(*names: str, default: str | None = None) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return default


class PhotoStorage:
    def __init__(self) -> None:
        # Acepta tanto los nombres de `railway bucket credentials` como los
        # nombres nativos que ofrece la inyeccion automatica de Railway.
        self.bucket = _env("AWS_S3_BUCKET_NAME", "BUCKET")
        self.endpoint = _env("AWS_ENDPOINT_URL", "ENDPOINT")
        self.access_key = _env("AWS_ACCESS_KEY_ID", "ACCESS_KEY_ID")
        self.secret_key = _env("AWS_SECRET_ACCESS_KEY", "SECRET_ACCESS_KEY")
        self.region = _env("AWS_DEFAULT_REGION", "REGION", default="auto")
        self.url_style = _env("AWS_S3_URL_STYLE", default="virtual")
        self.local_dir = Path(os.getenv("PHOTO_STORAGE_DIR", "/tmp/plantaia-fotos"))
        self.required = os.getenv("PHOTO_STORAGE_REQUIRED", "false").lower() == "true"
        self._client = None

    @property
    def uses_s3(self) -> bool:
        return bool(self.bucket and self.endpoint and self.access_key and self.secret_key)

    def _ensure_available(self) -> None:
        if self.required and not self.uses_s3:
            raise RuntimeError("Faltan las credenciales del Railway Bucket")

    def _s3_client(self):
        if self._client is None:
            self._client = boto3.client(
                "s3",
                endpoint_url=self.endpoint,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                region_name=self.region,
                config=Config(
                    signature_version="s3v4",
                    s3={"addressing_style": self.url_style},
                ),
            )
        return self._client

    def put(self, key: str, data: bytes, content_type: str) -> None:
        self._ensure_available()
        if self.uses_s3:
            self._s3_client().put_object(
                Bucket=self.bucket,
                Key=key,
                Body=data,
                ContentType=content_type,
            )
            return

        path = self.local_dir / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def get(self, key: str) -> tuple[io.BytesIO, str]:
        self._ensure_available()
        if self.uses_s3:
            response = self._s3_client().get_object(Bucket=self.bucket, Key=key)
            return io.BytesIO(response["Body"].read()), response.get("ContentType", "image/jpeg")

        return io.BytesIO((self.local_dir / key).read_bytes()), "image/jpeg"

    def delete(self, key: str) -> None:
        self._ensure_available()
        if self.uses_s3:
            self._s3_client().delete_object(Bucket=self.bucket, Key=key)
            return
        (self.local_dir / key).unlink(missing_ok=True)


photo_storage = PhotoStorage()
