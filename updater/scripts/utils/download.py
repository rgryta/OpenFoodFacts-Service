"""
Utility functions for downloading OpenFoodFacts data
"""
import logging
import httpx
from pathlib import Path

logger = logging.getLogger(__name__)


async def download_file(url: str, destination: Path, timeout: int = 3600) -> bool:
    """
    Download a file from URL to destination path.

    Args:
        url: Source URL
        destination: Local file path
        timeout: Download timeout in seconds (default 1 hour)

    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info(f"Downloading {url} to {destination}")

        # Create parent directory if needed
        destination.parent.mkdir(parents=True, exist_ok=True)

        # Stream download to handle large files
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            async with client.stream("GET", url) as response:
                response.raise_for_status()

                total_size = int(response.headers.get("content-length", 0))
                downloaded = 0

                with open(destination, "wb") as f:
                    async for chunk in response.aiter_bytes(chunk_size=8192):
                        f.write(chunk)
                        downloaded += len(chunk)

                        # Log progress every 100MB
                        if total_size > 0 and downloaded % (100 * 1024 * 1024) < 8192:
                            progress = (downloaded / total_size) * 100
                            logger.info(f"Download progress: {progress:.1f}% ({downloaded / (1024**3):.2f} GB)")

        logger.info(f"Download complete: {destination} ({downloaded / (1024**3):.2f} GB)")
        return True

    except Exception as e:
        logger.exception(f"Download failed: {e}")
        # Clean up partial download
        if destination.exists():
            destination.unlink()
        return False
