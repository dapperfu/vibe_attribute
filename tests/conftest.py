"""Pytest configuration and shared fixtures."""

import shutil
import tempfile
from pathlib import Path
from typing import Generator

import pytest
from PIL import Image

from attribute.models import ImageMetadata


@pytest.fixture
def test_images_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test images.

    Yields
    ------
    Path
        Path to temporary test images directory.
    """
    test_dir = Path(tempfile.mkdtemp(prefix="test_images_"))
    yield test_dir
    # Cleanup
    if test_dir.exists():
        shutil.rmtree(test_dir)


@pytest.fixture
def sample_metadata() -> ImageMetadata:
    """Create sample metadata for testing.

    Returns
    -------
    ImageMetadata
        Sample metadata instance.
    """
    return ImageMetadata(
        prompt="A beautiful sunset over mountains",
        model="ChatGPT-5.2 Thinking",
        date="2024-01-15",
        description="AI-generated landscape image",
        tags=["sunset", "mountains", "landscape"],
        copyright="© 2024",
        artist="AI Artist",
        custom_fields={"style": "photorealistic", "seed": "12345"},
    )


@pytest.fixture
def minimal_metadata() -> ImageMetadata:
    """Create minimal metadata (only required fields).

    Returns
    -------
    ImageMetadata
        Minimal metadata instance.
    """
    return ImageMetadata(
        prompt="Test prompt",
        model="Test Model",
    )


@pytest.fixture
def empty_metadata() -> ImageMetadata:
    """Create empty metadata (for testing defaults).

    Returns
    -------
    ImageMetadata
        Empty metadata instance with empty strings.
    """
    return ImageMetadata(prompt="", model="")


@pytest.fixture
def png_image(test_images_dir: Path) -> Path:
    """Create a PNG test image.

    Parameters
    ----------
    test_images_dir : Path
        Directory for test images.

    Returns
    -------
    Path
        Path to created PNG image.
    """
    image_path = test_images_dir / "test.png"
    img = Image.new("RGB", (100, 100), color="red")
    img.save(image_path)
    return image_path


@pytest.fixture
def jpeg_image(test_images_dir: Path) -> Path:
    """Create a JPEG test image.

    Parameters
    ----------
    test_images_dir : Path
        Directory for test images.

    Returns
    -------
    Path
        Path to created JPEG image.
    """
    image_path = test_images_dir / "test.jpg"
    img = Image.new("RGB", (100, 100), color="blue")
    img.save(image_path)
    return image_path


@pytest.fixture
def webp_image(test_images_dir: Path) -> Path:
    """Create a WebP test image.

    Parameters
    ----------
    test_images_dir : Path
        Directory for test images.

    Returns
    -------
    Path
        Path to created WebP image.
    """
    image_path = test_images_dir / "test.webp"
    img = Image.new("RGB", (100, 100), color="green")
    img.save(image_path)
    return image_path


@pytest.fixture
def image_with_metadata(
    png_image: Path,
    sample_metadata: ImageMetadata,
) -> Path:
    """Create a PNG image with pre-written metadata.

    Parameters
    ----------
    png_image : Path
        Path to PNG image.
    sample_metadata : ImageMetadata
        Metadata to write.

    Returns
    -------
    Path
        Path to image with metadata.
    """
    from attribute.metadata import write_metadata

    # Write metadata directly without reading first to avoid validation issues
    try:
        write_metadata(png_image, sample_metadata)
    except ValueError:
        # If it fails due to empty metadata, write directly
        from attribute.metadata import _write_png_metadata
        _write_png_metadata(png_image, sample_metadata)
    return png_image

