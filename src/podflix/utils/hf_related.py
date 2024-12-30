"""Hugginface related utilities."""

from huggingface_hub import hf_hub_download, snapshot_download
from loguru import logger

from podflix.env_settings import env_settings


def download_model_snapshot_hf(
    repo_id: str = "Qwen/Qwen2.5-0.5B-Instruct",
    revision: str = "main",
    ignore_patterns: list[str] | None = None,
) -> None:
    """Download a complete model snapshot from Hugging Face hub.

    Examples:
        >>> download_model_snapshot_hf("Qwen/Qwen2.5-0.5B-Instruct")
        >>> download_model_snapshot_hf("Qwen/Qwen2.5-0.5B-Instruct", ignore_patterns=["*.pt"])

    Args:
        repo_id: A string representing the Hugging Face repository ID.
        revision: A string representing the specific model version to use.
        ignore_patterns: A list of patterns to ignore during download.

    Returns:
        None
    """
    local_dir_name = repo_id.split("/")[1]

    if ignore_patterns is None:
        ignore_patterns = ["*.pt"]

    snapshot_download(
        repo_id=repo_id,
        revision=revision,
        local_dir=f"{env_settings.library_base_path}/deployment/models/{local_dir_name}",
        ignore_patterns=ignore_patterns,
        token=env_settings.hf_token,
    )


def download_gguf_hf(
    repo_id: str,
    filename: str,
    revision: str = "main",
) -> str:
    """Download a specific GGUF file from Hugging Face hub.

    Examples:
        >>> download_gguf_hf("Qwen/Qwen2-0.5B-Instruct-GGUF", "qwen2-0_5b-instruct-fp16.gguf")
        '/path/to/downloaded/file.gguf'

    Args:
        repo_id: A string representing the Hugging Face repository ID.
        filename: A string representing the name of the GGUF file to download.
        revision: A string representing the specific model version to use.

    Returns:
        str: Local path to the downloaded file.
    """
    return hf_hub_download(
        repo_id=repo_id,
        filename=filename,
        revision=revision,
        local_dir=f"{env_settings.library_base_path}/deployment/models/GGUF",
        token=env_settings.hf_token,
    )


if __name__ == "__main__":
    # Example snapshot download
    # repo_id = "Qwen/Qwen2.5-0.5B-Instruct"
    # revision = "main"
    # ignore_patterns = ["*.pt", "*.bin", "*.onnx", "*.onnx_data"]

    # download_model_snapshot_hf(
    #     repo_id=repo_id, revision=revision, ignore_patterns=ignore_patterns
    # )

    # Example GGUF download
    repo_id = "Qwen/Qwen2-0.5B-Instruct-GGUF"
    filename = "qwen2-0_5b-instruct-fp16.gguf"
    revision = "main"

    gguf_path = download_gguf_hf(
        repo_id=repo_id,
        filename=filename,
        revision=revision,
    )
    logger.info(f"Downloaded GGUF file to: {gguf_path}")
