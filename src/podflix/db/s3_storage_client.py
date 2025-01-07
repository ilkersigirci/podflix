"""Module to interact with Amazon S3 compatible storage provider."""

from typing import Any, Dict, Union

import boto3
from botocore.client import Config
from chainlit.data.storage_clients.base import BaseStorageClient
from loguru import logger

from podflix.env_settings import env_settings


def get_boto_client():
    """Create and return a boto3 S3 client with configured credentials.

    Examples:
        >>> client = get_boto_client()
        >>> client.list_buckets()
        {'Buckets': [...], 'Owner': {...}}

    Returns:
        A configured boto3 S3 client instance with the specified endpoint and credentials.

    Raises:
        botocore.exceptions.ClientError: If there are issues with credentials or configuration.
    """
    return boto3.client(
        "s3",
        endpoint_url=env_settings.aws_s3_endpoint_url,
        aws_access_key_id=env_settings.aws_access_key_id,
        aws_secret_access_key=env_settings.aws_secret_access_key,
        region_name=env_settings.aws_region_name,
        config=Config(signature_version="s3v4"),
        verify=True,  # Set False to skip SSL verification for local development
    )


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
            self.client = get_boto_client()
            # Check if bucket exists, if not create it
            try:
                self.client.head_bucket(Bucket=self.bucket)
            except self.client.exceptions.ClientError:
                logger.info(f"Creating bucket: {self.bucket}")
                self.client.create_bucket(
                    Bucket=self.bucket,
                    CreateBucketConfiguration={"LocationConstraint": "eu-central-1"},
                )

            logger.debug("S3CompatibleStorageClient initialized")
        except Exception as e:
            logger.error(f"S3CompatibleStorageClient initialization error: {e}")

    async def get_read_url(self, object_key: str) -> str:
        """Compute and return the full URL for an object in S3 storage.

        Examples:
            >>> url = await storage_client.get_read_url("test.txt")
            >>> print(url)
            'https://s3.example.com/my-bucket/test.txt'

        Args:
            object_key: A string representing the key (path) of the object in the bucket.

        Returns:
            A string representing the full URL to access the object.
        """
        return f"{env_settings.aws_s3_endpoint_url}/{self.bucket}/{object_key}"

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
            object_key: A string representing the key (path) where the object will be stored.
            data: The file content to upload (can be bytes or string).
            mime: A string representing the MIME type of the file.
            overwrite: A boolean indicating whether to overwrite existing files.

        Returns:
            A dictionary containing the object_key and url of the uploaded file.
            Returns empty dict if upload fails.

        Raises:
            Exception: If the upload operation fails.
        """
        try:
            self.client.put_object(
                Bucket=self.bucket, Key=object_key, Body=data, ContentType=mime
            )
            url = await self.get_read_url(object_key)
            return {"object_key": object_key, "url": url}
        except Exception as e:
            logger.error(f"S3CompatibleStorageClient, upload_file error: {e}")
            return {}

    async def read_file(self, object_key: str) -> Union[str, None]:
        """Read a file from the S3 compatible storage.

        Examples:
            >>> content = await storage_client.read_file("test.txt")
            >>> print(content)
            'Hello World'

        Args:
            object_key: A string representing the key (path) of the object in the bucket.

        Returns:
            The content of the file as a string, or None if the operation fails.

        Raises:
            Exception: If the read operation fails.
        """
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=object_key)
            return response["Body"].read().decode("utf-8")
        except Exception as e:
            logger.error(f"S3CompatibleStorageClient, read_file error: {e}")
            return None
