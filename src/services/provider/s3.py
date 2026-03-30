import os
from tempfile import SpooledTemporaryFile
from typing import Any, BinaryIO, Optional, cast

import aioboto3  # type: ignore[import-untyped]
import aiofiles  # type: ignore[import-untyped]

# this not to be changed because it's required by the s3 compatibility
os.environ["AWS_REQUEST_CHECKSUM_CALCULATION"] = "when_required"
os.environ["AWS_RESPONSE_CHECKSUM_VALIDATION"] = "when_required"


class S3Provider:
    def __init__(
        self,
        access_key_id: str,
        secret_access_key: str,
        region_name: str,
        endpoint_url: str,
        bucket_name: str | None = None,
    ) -> None:
        self._access_key_id = access_key_id
        self._secret_access_key = secret_access_key
        self._region_name = region_name
        self._session: Optional[aioboto3.Session] = None
        self.endpoint_url = endpoint_url
        self.bucket_name = bucket_name

    def create_session(self) -> aioboto3.Session:
        if self._session is None:
            self._session = aioboto3.Session(
                aws_access_key_id=self._access_key_id,
                aws_secret_access_key=self._secret_access_key,
                region_name=self._region_name,
            )

        return self._session

    async def upload_file(
        self,
        key: str,
        file_object: BinaryIO
        | aiofiles.threadpool.binary.AsyncBufferedReader
        | SpooledTemporaryFile[bytes]
        | None = None,
        bucket_name: str | None = None,
        file_path: str | None = None,
        content_type: str = "image/png",
        extra_args: Optional[dict[str, Any]] = None,
    ) -> str:
        if not self.bucket_name and not bucket_name:
            raise ValueError("Provide bucket_name or set it in the provider")

        async with self.create_session().client(
            service_name="s3", endpoint_url=self.endpoint_url
        ) as s3:
            if file_path:
                async with aiofiles.open(file_path, "rb") as file_obj:
                    await s3.upload_fileobj(
                        Fileobj=file_obj,
                        Key=key,
                        Bucket=bucket_name or self.bucket_name,
                        ExtraArgs={"ContentType": content_type, **(extra_args or {})},
                    )
                    return key

            if file_object is None:
                raise ValueError("Provide file_object or file_path")

            await s3.upload_fileobj(
                Fileobj=file_object,
                Key=key,
                Bucket=bucket_name or self.bucket_name,
                ExtraArgs={"ContentType": content_type, **(extra_args or {})},
            )

            return key

    async def delete_file(
        self,
        key: str,
        bucket_name: str | None = None,
        version_id: str | None = None,
    ) -> dict[str, Any]:
        async with self.create_session().client(
            service_name="s3", endpoint_url=self.endpoint_url
        ) as s3:
            if not self.bucket_name and not bucket_name:
                raise ValueError("Provide bucket_name or set it in the provider")

            delete_kwargs = {
                "Bucket": bucket_name or self.bucket_name,
                "Key": key,
            }
            if version_id:
                delete_kwargs["VersionId"] = version_id

            response = await s3.delete_object(**delete_kwargs)
            return cast(dict[str, Any], response)
