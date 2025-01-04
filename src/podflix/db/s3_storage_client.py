"""Module to interact with Amazon S3 compatible storage provider."""

from typing import Any, Dict, Union

import boto3
from botocore.client import Config
from chainlit.data.storage_clients.base import BaseStorageClient
from chainlit.logger import logger

from podflix.env_settings import env_settings


class S3CompatibleStorageClient(BaseStorageClient):
    """Class to enable Amazon S3 compatible storage provider.

    This class provides functionality to interact with Amazon S3 compatible storage services.
    It handles bucket creation, file uploads, and basic S3 operations.

    Examples:
        >>> storage_client = S3CompatibleStorageClient("my-bucket")
        >>> await storage_client.upload_file("test.txt", "Hello World", "text/plain")
        {'object_key': 'test.txt', 'url': 'https://s3.example.com/my-bucket/test.txt'}

    Attributes:
        bucket (str): The name of the S3 bucket to use
        client: The boto3 S3 client instance
    """

    def __init__(self, bucket: str | None = None):
        """Initialize the S3 compatible storage client.

        Args:
            bucket: Name of the S3 bucket. If None, uses the value from env_settings.

        Raises:
            Exception: If initialization of the S3 client fails
        """
        try:
            if bucket is None:
                bucket = env_settings.aws_s3_bucket_name

            self.bucket = bucket
            self.client = boto3.client(
                "s3",
                endpoint_url=env_settings.aws_s3_endpoint_url,
                aws_access_key_id="test",
                aws_secret_access_key="test",
                region_name="us-east-1",
                config=Config(signature_version="s3v4"),
                verify=True,  # Set False to skip SSL verification for local development
            )

            # Check if bucket exists, if not create it
            try:
                self.client.head_bucket(Bucket=self.bucket)
            except self.client.exceptions.ClientError:
                logger.info(f"Creating bucket: {self.bucket}")
                self.client.create_bucket(Bucket=self.bucket)

            logger.debug("S3CompatibleStorageClient initialized")
        except Exception as e:
            logger.error(f"S3CompatibleStorageClient initialization error: {e}")

    async def upload_file(
        self,
        object_key: str,
        data: Union[bytes, str],
        mime: str = "application/octet-stream",
        overwrite: bool = True,
    ) -> Dict[str, Any]:
        """Upload a file to the S3 compatible storage.

        Examples:
            >>> result = await storage_client.upload_file(
            ...     "test.txt",
            ...     "Hello World",
            ...     "text/plain"
            ... )
            >>> print(result)
            {'object_key': 'test.txt', 'url': 'https://s3.example.com/bucket/test.txt'}

        Args:
            object_key: The key (path) where the object will be stored in the bucket
            data: The file content to upload (can be bytes or string)
            mime: The MIME type of the file (default: application/octet-stream)
            overwrite: Whether to overwrite existing files (default: True)

        Returns:
            A dictionary containing the object_key and url of the uploaded file.
            Returns empty dict if upload fails.

        Raises:
            Exception: If the upload operation fails
        """
        try:
            self.client.put_object(
                Bucket=self.bucket, Key=object_key, Body=data, ContentType=mime
            )
            url = f"{env_settings.aws_s3_endpoint_url}/{self.bucket}/{object_key}"
            return {"object_key": object_key, "url": url}
        except Exception as e:
            logger.error(f"S3CompatibleStorageClient, upload_file error: {e}")
            return {}

    async def read_file(self, object_key: str) -> Union[str, None]:
        """Read a file from the S3 compatible storage.

        Args:
            object_key: The key (path) of the object in the bucket

        Returns:
            The content of the file as a string, or None if the operation fails
        """
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=object_key)
            return response["Body"].read().decode("utf-8")
        except Exception as e:
            logger.error(f"S3CompatibleStorageClient, read_file error: {e}")
            return None
