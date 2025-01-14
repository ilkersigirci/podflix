"""Utility functions for working with ChainLit data layer.

This module provides utility functions for configuring and working with ChainLit's data layer,
including S3 storage integration and SQLAlchemy database connections.
"""

import os

import boto3
import chainlit as cl
import chainlit.socket
from chainlit.data import get_data_layer
from chainlit.data.sql_alchemy import SQLAlchemyDataLayer
from chainlit.data.storage_clients.s3 import S3StorageClient
from chainlit.element import ElementDict
from loguru import logger

from podflix.db.db_factory import DBInterfaceFactory
from podflix.env_settings import env_settings


def get_s3_storage_client() -> S3StorageClient:
    """Get the S3 storage client configured with environment credentials.

    Examples:
        >>> client = get_s3_storage_client()
        >>> isinstance(client, S3StorageClient)
        True

    Returns:
        S3StorageClient: An initialized S3 storage client instance.

    Raises:
        ValueError: If required AWS S3 credentials are not set in environment variables.
    """
    BUCKET_NAME = os.getenv("BUCKET_NAME", None)
    APP_AWS_ACCESS_KEY = os.getenv("APP_AWS_ACCESS_KEY", None)
    APP_AWS_SECRET_KEY = os.getenv("APP_AWS_SECRET_KEY", None)
    APP_AWS_REGION = os.getenv("APP_AWS_REGION", None)
    DEV_AWS_ENDPOINT = os.getenv("DEV_AWS_ENDPOINT", None)

    if not all(
        [
            BUCKET_NAME,
            APP_AWS_ACCESS_KEY,
            APP_AWS_SECRET_KEY,
            APP_AWS_REGION,
            DEV_AWS_ENDPOINT,
        ]
    ):
        raise ValueError("AWS S3 credentials not set in environment variables.")

    return S3StorageClient(
        bucket=BUCKET_NAME,
        region_name=APP_AWS_REGION,
        aws_access_key_id=APP_AWS_ACCESS_KEY,
        aws_secret_access_key=APP_AWS_SECRET_KEY,
        endpoint_url=DEV_AWS_ENDPOINT,
    )


def check_s3_credentials(boto_client: boto3.client) -> None:
    """Check if the AWS S3 credentials are valid by attempting to list buckets.

    Examples:
        >>> s3_client = get_s3_storage_client()
        >>> check_s3_credentials(s3_client.client)  # No error if credentials are valid

    Args:
        boto_client: A boto3 client instance configured for AWS S3.

    Returns:
        None

    Raises:
        Exception: If connection to AWS S3 fails using provided credentials.
    """
    try:
        boto_client.list_buckets()
        logger.debug("AWS S3 Auth Check Passed")
    except Exception as e:
        logger.error(f"AWS S3 Auth Check Error: {e}")
        raise e


def get_custom_sqlalchemy_data_layer(
    show_logger: bool = False, enable_s3_storage_provider: bool = False
) -> SQLAlchemyDataLayer:
    """Create and configure a custom SQLAlchemy data layer instance.

    This function sets up a SQLAlchemy data layer with optional S3 storage integration
    and logging capabilities.

    Examples:
        >>> data_layer = get_custom_sqlalchemy_data_layer()
        >>> isinstance(data_layer, SQLAlchemyDataLayer)
        True
        >>> data_layer_with_s3 = get_custom_sqlalchemy_data_layer(enable_s3_storage_provider=True)
        >>> data_layer_with_logging = get_custom_sqlalchemy_data_layer(show_logger=True)

    Args:
        show_logger: Whether to enable SQL query logging. Defaults to False.
        enable_s3_storage_provider: Whether to enable S3 storage integration. Defaults to False.

    Returns:
        SQLAlchemyDataLayer: A configured data layer instance.

    Raises:
        ValueError: If S3 storage is enabled but credentials are invalid.
    """
    if enable_s3_storage_provider is True:
        storage_client = get_s3_storage_client()

        check_s3_credentials(boto_client=storage_client.client)
    else:
        storage_client = None

    return SQLAlchemyDataLayer(
        DBInterfaceFactory.create().async_connection(),
        ssl_require=False,
        show_logger=show_logger,
        storage_provider=storage_client,
    )


async def get_element_url(
    data_layer: SQLAlchemyDataLayer, thread_id: str, element_id: str
) -> str | None:
    """Retrieve the URL for accessing an element's file content.

    Examples:
        >>> data_layer = get_custom_sqlalchemy_data_layer()
        >>> url = await get_element_url(data_layer, "thread123", "element456")
        >>> print(url)  # None if not found, URL string if exists

    Args:
        data_layer: The SQLAlchemy data layer instance to use for retrieval.
        thread_id: The unique identifier of the thread containing the element.
        element_id: The unique identifier of the element to retrieve.

    Returns:
        str | None: The URL string if the element exists, None otherwise.
    """
    logger.debug(
        f"SQLAlchemy: get_element_url, thread_id={thread_id}, element_id={element_id}"
    )

    element_dict: ElementDict = data_layer.get_element(
        thread_id=thread_id, element_id=element_id
    )

    if element_dict is None:
        return None

    return element_dict.url


async def get_read_url_of_file(thread_id: str, file_name: str) -> str:
    """Retrieve the URL for accessing an file in a thread.

    Examples:
        >>> data_layer = ChainlitDataLayer()
        >>> url = await get_read_url_of_file(data_layer, "thread123", "audio.mp3")
        >>> print(url)  # URL string

    Args:
        thread_id: The unique identifier of the thread containing the file.
        file_name: The full name of the the file to retrieve, included the file extension.

    Returns:
        str: The S3 URL string of the file.

    Raises:
        ValueError: If S3 storage client is not configured in the data layer.
    """
    cl_data_layer = get_data_layer()

    if cl_data_layer.storage_client is None:
        raise ValueError("S3 storage client not set in data layer.")

    object_key = f"threads/{thread_id}/files/{file_name}"

    return await cl_data_layer.storage_client.get_read_url(object_key=object_key)


def apply_sqlite_data_layer_fixes():
    """Apply necessary fixes for SQLite data layer configuration.

    This function applies patches and configurations specific to SQLite data layer
    when it is enabled in the environment settings.

    Examples:
        >>> apply_sqlite_data_layer_fixes()  # Applies fixes if SQLite is enabled

    Returns:
        None
    """
    if env_settings.enable_sqlite_data_layer is False:
        return

    from podflix.utils.chainlit_utils.patch_chainlit import custom_resume_thread

    chainlit.socket.resume_thread = custom_resume_thread

    @cl.data_layer
    def data_layer():
        return get_custom_sqlalchemy_data_layer(show_logger=True)
