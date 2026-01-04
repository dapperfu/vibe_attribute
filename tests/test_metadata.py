"""Tests for metadata operations using pytest fixtures."""

from pathlib import Path

import pytest

from attribute.metadata import (
    MetadataError,
    UnsupportedFormatError,
    is_supported_format,
    read_metadata,
    write_metadata,
)
from attribute.models import ImageMetadata


@pytest.mark.parametrize(
    "filename,expected",
    [
        ("test.png", True),
        ("test.PNG", True),
        ("test.jpg", True),
        ("test.jpeg", True),
        ("test.webp", True),
        ("test.txt", False),
        ("test.gif", False),
        ("test.bmp", False),
        ("image", False),
    ],
)
def test_is_supported_format(filename: str, expected: bool) -> None:
    """Test format detection with parametrization.

    Parameters
    ----------
    filename : str
        Filename to test.
    expected : bool
        Expected result.
    """
    assert is_supported_format(filename) == expected


@pytest.mark.parametrize(
    "image_fixture,format_name",
    [
        ("png_image", "PNG"),
        ("jpeg_image", "JPEG"),
        ("webp_image", "WebP"),
    ],
)
def test_read_write_metadata_formats(
    image_fixture: str,
    format_name: str,
    request: pytest.FixtureRequest,
    sample_metadata: ImageMetadata,
) -> None:
    """Test reading and writing metadata for different formats.

    Parameters
    ----------
    image_fixture : str
        Name of image fixture to use.
    format_name : str
        Format name for display.
    request : pytest.FixtureRequest
        Pytest fixture request.
    sample_metadata : ImageMetadata
        Metadata to write.
    """
    image_path: Path = request.getfixturevalue(image_fixture)

    # Write metadata
    write_metadata(image_path, sample_metadata)

    # Read metadata
    read_meta = read_metadata(image_path)

    assert read_meta.prompt == sample_metadata.prompt
    assert read_meta.model == sample_metadata.model
    assert read_meta.date == sample_metadata.date
    assert read_meta.description == sample_metadata.description
    assert read_meta.tags == sample_metadata.tags
    assert read_meta.copyright == sample_metadata.copyright
    assert read_meta.artist == sample_metadata.artist


def test_read_write_metadata_png(
    png_image: Path,
    sample_metadata: ImageMetadata,
) -> None:
    """Test reading and writing metadata for PNG.

    Parameters
    ----------
    png_image : Path
        Path to PNG test image.
    sample_metadata : ImageMetadata
        Sample metadata to write.
    """
    # Write metadata
    write_metadata(png_image, sample_metadata)

    # Read metadata
    read_meta = read_metadata(png_image)

    assert read_meta.prompt == "A beautiful sunset over mountains"
    assert read_meta.model == "ChatGPT-5.2 Thinking"
    assert read_meta.date == "2024-01-15"
    assert read_meta.description == "AI-generated landscape image"
    assert read_meta.tags == ["sunset", "mountains", "landscape"]
    assert read_meta.copyright == "© 2024"
    assert read_meta.artist == "AI Artist"


def test_read_write_metadata_jpeg(
    jpeg_image: Path,
    minimal_metadata: ImageMetadata,
) -> None:
    """Test reading and writing metadata for JPEG.

    Parameters
    ----------
    jpeg_image : Path
        Path to JPEG test image.
    minimal_metadata : ImageMetadata
        Minimal metadata to write.
    """
    # Write metadata
    write_metadata(jpeg_image, minimal_metadata)

    # Read metadata
    read_meta = read_metadata(jpeg_image)

    assert read_meta.prompt == "Test prompt"
    assert read_meta.model == "Test Model"


def test_metadata_preservation(
    png_image: Path,
    sample_metadata: ImageMetadata,
    minimal_metadata: ImageMetadata,
) -> None:
    """Test that existing metadata is preserved when writing new metadata.

    Parameters
    ----------
    png_image : Path
        Path to PNG test image.
    sample_metadata : ImageMetadata
        Initial metadata to write.
    minimal_metadata : ImageMetadata
        New metadata to write (should preserve existing fields).
    """
    # Write initial metadata
    write_metadata(png_image, sample_metadata)

    # Write new metadata (only prompt and model)
    write_metadata(png_image, minimal_metadata)

    # Read metadata - description should be preserved
    read_meta = read_metadata(png_image)
    assert read_meta.prompt == "Test prompt"  # New value
    assert read_meta.model == "Test Model"  # New value
    # Other fields should be preserved
    assert read_meta.description == "AI-generated landscape image"
    assert read_meta.tags == ["sunset", "mountains", "landscape"]


def test_metadata_merge_custom_fields(
    png_image: Path,
    sample_metadata: ImageMetadata,
) -> None:
    """Test that custom fields are properly merged.

    Parameters
    ----------
    png_image : Path
        Path to PNG test image.
    sample_metadata : ImageMetadata
        Metadata with custom fields.
    """
    # Write initial metadata with custom fields
    write_metadata(png_image, sample_metadata)

    # Write new metadata with additional custom fields
    new_metadata = ImageMetadata(
        prompt="New prompt",
        model="New Model",
        custom_fields={"new_field": "new_value"},
    )
    write_metadata(png_image, new_metadata)

    # Read metadata - both old and new custom fields should exist
    read_meta = read_metadata(png_image)
    assert "style" in read_meta.custom_fields
    assert "seed" in read_meta.custom_fields
    assert "new_field" in read_meta.custom_fields
    assert read_meta.custom_fields["new_field"] == "new_value"


def test_read_existing_metadata(
    image_with_metadata: Path,
    sample_metadata: ImageMetadata,
) -> None:
    """Test reading existing metadata from image.

    Parameters
    ----------
    image_with_metadata : Path
        Path to image with pre-written metadata.
    sample_metadata : ImageMetadata
        Expected metadata.
    """
    read_meta = read_metadata(image_with_metadata)

    assert read_meta.prompt == sample_metadata.prompt
    assert read_meta.model == sample_metadata.model
    assert read_meta.date == sample_metadata.date


@pytest.mark.parametrize(
    "error_type,file_path,expected_message",
    [
        (MetadataError, Path("nonexistent.png"), "Image file not found"),
        (UnsupportedFormatError, Path("test.txt"), "Unsupported format"),
    ],
)
def test_read_metadata_errors(
    error_type: type[Exception],
    file_path: Path,
    expected_message: str,
) -> None:
    """Test error handling for reading metadata.

    Parameters
    ----------
    error_type : type[Exception]
        Expected exception type.
    file_path : Path
        Path to file that should cause error.
    expected_message : str
        Expected error message substring.
    """
    if error_type == UnsupportedFormatError:
        # Create a text file for unsupported format test
        file_path.write_text("not an image")

    with pytest.raises(error_type, match=expected_message):
        read_metadata(file_path)

    # Cleanup
    if file_path.exists() and file_path.suffix == ".txt":
        file_path.unlink()


def test_write_nonexistent_file(minimal_metadata: ImageMetadata) -> None:
    """Test writing to nonexistent file raises error.

    Parameters
    ----------
    minimal_metadata : ImageMetadata
        Metadata to write.
    """
    with pytest.raises(MetadataError, match="Image file not found"):
        write_metadata(Path("nonexistent.png"), minimal_metadata)


def test_write_unsupported_format(minimal_metadata: ImageMetadata) -> None:
    """Test writing to unsupported format raises error.

    Parameters
    ----------
    minimal_metadata : ImageMetadata
        Metadata to write.
    """
    test_file = Path("test.txt")
    test_file.write_text("not an image")

    try:
        with pytest.raises(UnsupportedFormatError, match="Unsupported format"):
            write_metadata(test_file, minimal_metadata)
    finally:
        if test_file.exists():
            test_file.unlink()


@pytest.mark.parametrize(
    "prompt,model,should_raise",
    [
        ("", "Model", False),  # Empty prompt is now allowed
        ("Prompt", "", True),  # Empty model still required
        ("", "", True),  # Empty model still required
        ("Valid prompt", "Valid model", False),
    ],
)
def test_metadata_validation(
    prompt: str,
    model: str,
    should_raise: bool,
) -> None:
    """Test metadata validation with parametrization.

    Parameters
    ----------
    prompt : str
        Prompt value to test.
    model : str
        Model value to test.
    should_raise : bool
        Whether validation should raise an error.
    """
    if should_raise:
        with pytest.raises(ValueError, match="required"):
            ImageMetadata(prompt=prompt, model=model)
    else:
        metadata = ImageMetadata(prompt=prompt, model=model)
        assert metadata.prompt == prompt
        assert metadata.model == model
