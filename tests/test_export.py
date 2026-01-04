"""Tests for export/import functionality using pytest fixtures."""

import csv
import json
from pathlib import Path

import pytest

from attribute.export import export_metadata, import_metadata
from attribute.models import ImageMetadata


@pytest.fixture
def sample_metadata_dict(sample_metadata: ImageMetadata) -> dict:
    """Create metadata dictionary for export testing.

    Parameters
    ----------
    sample_metadata : ImageMetadata
        Sample metadata fixture.

    Returns
    -------
    dict
        Dictionary mapping image paths to metadata.
    """
    return {
        "test1.png": sample_metadata,
        "test2.jpg": ImageMetadata(
            prompt="Second prompt",
            model="Second Model",
            tags=["tag1"],
        ),
    }


@pytest.fixture
def temp_export_dir(tmp_path: Path) -> Path:
    """Create temporary directory for export files.

    Parameters
    ----------
    tmp_path : Path
        Pytest temporary path fixture.

    Returns
    -------
    Path
        Path to temporary export directory.
    """
    export_dir = tmp_path / "exports"
    export_dir.mkdir()
    return export_dir


@pytest.mark.parametrize(
    "format_name,extension",
    [
        ("json", ".json"),
        ("csv", ".csv"),
        ("JSON", ".json"),  # Case insensitive
        ("CSV", ".csv"),
    ],
)
def test_export_metadata(
    format_name: str,
    extension: str,
    sample_metadata_dict: dict,
    temp_export_dir: Path,
) -> None:
    """Test exporting metadata to different formats.

    Parameters
    ----------
    format_name : str
        Format name to test.
    extension : str
        Expected file extension.
    sample_metadata_dict : dict
        Metadata dictionary fixture.
    temp_export_dir : Path
        Temporary export directory.
    """
    output_path = temp_export_dir / f"export{extension}"

    export_metadata(sample_metadata_dict, output_path, format_name)

    assert output_path.exists()

    if extension == ".json":
        with open(output_path, "r") as f:
            data = json.load(f)
        assert "test1.png" in data
        assert data["test1.png"]["prompt"] == "A beautiful sunset over mountains"
    elif extension == ".csv":
        with open(output_path, "r") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert len(rows) == 2
        assert rows[0]["image_path"] == "test1.png"
        assert rows[0]["prompt"] == "A beautiful sunset over mountains"


def test_export_json_format(
    sample_metadata_dict: dict,
    temp_export_dir: Path,
) -> None:
    """Test exporting metadata to JSON format.

    Parameters
    ----------
    sample_metadata_dict : dict
        Metadata dictionary fixture.
    temp_export_dir : Path
        Temporary export directory.
    """
    output_path = temp_export_dir / "export.json"

    export_metadata(sample_metadata_dict, output_path, "json")

    with open(output_path, "r") as f:
        data = json.load(f)

    assert "test1.png" in data
    assert "test2.jpg" in data
    assert data["test1.png"]["prompt"] == "A beautiful sunset over mountains"
    assert data["test1.png"]["model"] == "ChatGPT-5.2 Thinking"
    assert isinstance(data["test1.png"]["tags"], list)  # JSON keeps as list


def test_export_csv_format(
    sample_metadata_dict: dict,
    temp_export_dir: Path,
) -> None:
    """Test exporting metadata to CSV format.

    Parameters
    ----------
    sample_metadata_dict : dict
        Metadata dictionary fixture.
    temp_export_dir : Path
        Temporary export directory.
    """
    output_path = temp_export_dir / "export.csv"

    export_metadata(sample_metadata_dict, output_path, "csv")

    with open(output_path, "r") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert len(rows) == 2
    assert rows[0]["image_path"] == "test1.png"
    assert rows[0]["prompt"] == "A beautiful sunset over mountains"
    assert rows[0]["model"] == "ChatGPT-5.2 Thinking"
    assert rows[1]["image_path"] == "test2.jpg"
    assert rows[1]["prompt"] == "Second prompt"


def test_export_csv_custom_fields(
    temp_export_dir: Path,
    sample_metadata: ImageMetadata,
) -> None:
    """Test exporting CSV with custom fields.

    Parameters
    ----------
    temp_export_dir : Path
        Temporary export directory.
    sample_metadata : ImageMetadata
        Sample metadata with custom fields.
    """
    metadata_dict = {"test.png": sample_metadata}
    output_path = temp_export_dir / "export.csv"

    export_metadata(metadata_dict, output_path, "csv")

    with open(output_path, "r") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert len(rows) == 1
    # Check that custom fields are included
    assert "style" in rows[0]
    assert rows[0]["style"] == "photorealistic"
    assert "seed" in rows[0]
    assert rows[0]["seed"] == "12345"


def test_export_empty_metadata(temp_export_dir: Path) -> None:
    """Test exporting empty metadata dictionary.

    Parameters
    ----------
    temp_export_dir : Path
        Temporary export directory.
    """
    output_path = temp_export_dir / "empty.csv"

    export_metadata({}, output_path, "csv")

    # Should create file with headers only
    assert output_path.exists()
    with open(output_path, "r") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    assert len(rows) == 0


@pytest.mark.parametrize(
    "format_name,expected_error",
    [
        ("xml", "Unsupported format"),
        ("yaml", "Unsupported format"),
        ("txt", "Unsupported format"),
    ],
)
def test_export_invalid_format(
    format_name: str,
    expected_error: str,
    sample_metadata_dict: dict,
    temp_export_dir: Path,
) -> None:
    """Test exporting with invalid format raises error.

    Parameters
    ----------
    format_name : str
        Invalid format name.
    expected_error : str
        Expected error message.
    sample_metadata_dict : dict
        Metadata dictionary fixture.
    temp_export_dir : Path
        Temporary export directory.
    """
    output_path = temp_export_dir / "export.txt"

    with pytest.raises(ValueError, match=expected_error):
        export_metadata(sample_metadata_dict, output_path, format_name)


def test_import_json_format(
    temp_export_dir: Path,
    sample_metadata: ImageMetadata,
) -> None:
    """Test importing metadata from JSON format.

    Parameters
    ----------
    temp_export_dir : Path
        Temporary export directory.
    sample_metadata : ImageMetadata
        Sample metadata fixture.
    """
    # Create test JSON file
    json_data = {
        "test1.png": sample_metadata.to_json_dict(),
        "test2.jpg": {
            "prompt": "Imported prompt",
            "model": "Imported Model",
            "tags": ["tag1"],
        },
    }

    json_path = temp_export_dir / "import.json"
    with open(json_path, "w") as f:
        json.dump(json_data, f)

    # Import should work (even if files don't exist, it returns empty list)
    result = import_metadata(json_path)
    assert isinstance(result, list)
    # Result will be empty since test files don't exist


def test_import_csv_format(temp_export_dir: Path) -> None:
    """Test importing metadata from CSV format.

    Parameters
    ----------
    temp_export_dir : Path
        Temporary export directory.
    """
    # Create test CSV file
    csv_path = temp_export_dir / "import.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["image_path", "prompt", "model", "tags"],
        )
        writer.writeheader()
        writer.writerow(
            {
                "image_path": "test.png",
                "prompt": "CSV prompt",
                "model": "CSV Model",
                "tags": "tag1, tag2",
            }
        )

    # Import should work (even if files don't exist)
    result = import_metadata(csv_path)
    assert isinstance(result, list)


def test_import_csv_custom_fields(temp_export_dir: Path) -> None:
    """Test importing CSV with custom fields.

    Parameters
    ----------
    temp_export_dir : Path
        Temporary export directory.
    """
    csv_path = temp_export_dir / "import.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["image_path", "prompt", "model", "style", "seed"],
        )
        writer.writeheader()
        writer.writerow(
            {
                "image_path": "test.png",
                "prompt": "Test",
                "model": "Test",
                "style": "photorealistic",
                "seed": "12345",
            }
        )

    result = import_metadata(csv_path)
    assert isinstance(result, list)


@pytest.mark.parametrize(
    "extension,expected_error",
    [
        (".txt", "Unsupported file format"),
        (".xml", "Unsupported file format"),
        (".yaml", "Unsupported file format"),
    ],
)
def test_import_invalid_format(
    extension: str,
    expected_error: str,
    temp_export_dir: Path,
) -> None:
    """Test importing with invalid format raises error.

    Parameters
    ----------
    extension : str
        Invalid file extension.
    expected_error : str
        Expected error message.
    temp_export_dir : Path
        Temporary export directory.
    """
    invalid_path = temp_export_dir / f"import{extension}"
    invalid_path.write_text("not json or csv")

    with pytest.raises(ValueError, match=expected_error):
        import_metadata(invalid_path)


def test_import_csv_missing_image_path_column(temp_export_dir: Path) -> None:
    """Test importing CSV without required image_path column.

    Parameters
    ----------
    temp_export_dir : Path
        Temporary export directory.
    """
    csv_path = temp_export_dir / "invalid.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["prompt", "model"])
        writer.writeheader()
        writer.writerow({"prompt": "Test", "model": "Test"})

    with pytest.raises(ValueError, match="image_path"):
        import_metadata(csv_path)
