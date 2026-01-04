"""Tests for data models using pytest fixtures."""

from typing import Optional

import pytest

from attribute.models import ImageMetadata


@pytest.fixture
def full_metadata_dict() -> dict:
    """Create a full metadata dictionary for testing.

    Returns
    -------
    dict
        Dictionary with all metadata fields.
    """
    return {
        "prompt": "Test prompt",
        "model": "Test Model",
        "date": "2024-01-15",
        "description": "Test description",
        "tags": ["tag1", "tag2"],
        "copyright": "© 2024",
        "artist": "Test Artist",
        "custom_field1": "value1",
        "custom_field2": "value2",
    }


@pytest.fixture
def minimal_metadata_dict() -> dict:
    """Create a minimal metadata dictionary.

    Returns
    -------
    dict
        Dictionary with only required fields.
    """
    return {
        "prompt": "Test prompt",
        "model": "Test Model",
    }


def test_image_metadata_creation(minimal_metadata: ImageMetadata) -> None:
    """Test creating ImageMetadata.

    Parameters
    ----------
    minimal_metadata : ImageMetadata
        Minimal metadata fixture.
    """
    assert minimal_metadata.prompt == "Test prompt"
    assert minimal_metadata.model == "Test Model"
    assert minimal_metadata.tags == []
    assert minimal_metadata.custom_fields == {}


def test_image_metadata_full_creation(sample_metadata: ImageMetadata) -> None:
    """Test creating ImageMetadata with all fields.

    Parameters
    ----------
    sample_metadata : ImageMetadata
        Sample metadata fixture.
    """
    assert sample_metadata.prompt == "A beautiful sunset over mountains"
    assert sample_metadata.model == "ChatGPT-5.2 Thinking"
    assert sample_metadata.date == "2024-01-15"
    assert sample_metadata.description == "AI-generated landscape image"
    assert sample_metadata.tags == ["sunset", "mountains", "landscape"]
    assert sample_metadata.copyright == "© 2024"
    assert sample_metadata.artist == "AI Artist"
    assert "style" in sample_metadata.custom_fields
    assert "seed" in sample_metadata.custom_fields


@pytest.mark.parametrize(
    "prompt,model,expected_error",
    [
        ("Prompt", "", "Model is required"),
        ("Prompt", "   ", "Model is required"),  # Whitespace only
        ("", "Model", None),  # Empty prompt is now allowed
        ("   ", "Model", None),  # Whitespace-only prompt is now allowed
    ],
)
def test_image_metadata_validation(
    prompt: str,
    model: str,
    expected_error: Optional[str],
) -> None:
    """Test metadata validation with parametrization.

    Parameters
    ----------
    prompt : str
        Prompt value to test.
    model : str
        Model value to test.
    expected_error : Optional[str]
        Expected error message, or None if no error expected.
    """
    if expected_error:
        with pytest.raises(ValueError, match=expected_error):
            ImageMetadata(prompt=prompt, model=model)
    else:
        # Should not raise an error
        metadata = ImageMetadata(prompt=prompt, model=model)
        assert metadata.prompt == prompt
        assert metadata.model == model


@pytest.mark.parametrize(
    "date,should_raise",
    [
        ("2024-01-15", False),
        ("2024-12-31", False),
        ("invalid-date", True),
        ("2024/01/15", True),
        ("01-15-2024", True),
        ("", False),  # Empty is allowed (None)
    ],
)
def test_image_metadata_date_validation(
    date: str,
    should_raise: bool,
) -> None:
    """Test date format validation.

    Parameters
    ----------
    date : str
        Date string to test.
    should_raise : bool
        Whether validation should raise an error.
    """
    if should_raise:
        with pytest.raises(ValueError, match="Date must be in ISO format"):
            ImageMetadata(prompt="Test", model="Test", date=date)
    else:
        metadata = ImageMetadata(
            prompt="Test",
            model="Test",
            date=date if date else None,
        )
        assert metadata.date == (date if date else None)


def test_image_metadata_to_dict(sample_metadata: ImageMetadata) -> None:
    """Test converting metadata to dictionary.

    Parameters
    ----------
    sample_metadata : ImageMetadata
        Sample metadata fixture.
    """
    result = sample_metadata.to_dict()
    assert result["prompt"] == "A beautiful sunset over mountains"
    assert result["model"] == "ChatGPT-5.2 Thinking"
    assert isinstance(result["tags"], str)  # CSV format (comma-separated)


def test_image_metadata_to_json_dict(sample_metadata: ImageMetadata) -> None:
    """Test converting metadata to JSON dictionary.

    Parameters
    ----------
    sample_metadata : ImageMetadata
        Sample metadata fixture.
    """
    result = sample_metadata.to_json_dict()
    assert result["prompt"] == "A beautiful sunset over mountains"
    assert result["model"] == "ChatGPT-5.2 Thinking"
    assert isinstance(result["tags"], list)  # JSON format (list)


@pytest.mark.parametrize(
    "tags_input,expected",
    [
        ("tag1, tag2, tag3", ["tag1", "tag2", "tag3"]),
        ("tag1,tag2,tag3", ["tag1", "tag2", "tag3"]),
        (["tag1", "tag2"], ["tag1", "tag2"]),
        ("", []),
        ([], []),
    ],
)
def test_image_metadata_from_dict_tags(
    tags_input: str | list,
    expected: list,
) -> None:
    """Test parsing tags from dictionary.

    Parameters
    ----------
    tags_input : str | list
        Tags input (string or list).
    expected : list
        Expected parsed tags.
    """
    data = {
        "prompt": "Test",
        "model": "Test",
        "tags": tags_input,
    }
    metadata = ImageMetadata.from_dict(data)
    assert metadata.tags == expected


def test_image_metadata_from_dict(full_metadata_dict: dict) -> None:
    """Test creating metadata from dictionary.

    Parameters
    ----------
    full_metadata_dict : dict
        Full metadata dictionary fixture.
    """
    metadata = ImageMetadata.from_dict(full_metadata_dict)
    assert metadata.prompt == "Test prompt"
    assert metadata.model == "Test Model"
    assert metadata.date == "2024-01-15"
    assert metadata.description == "Test description"
    assert metadata.copyright == "© 2024"
    assert metadata.artist == "Test Artist"
    # Custom fields should be extracted
    assert "custom_field1" in metadata.custom_fields
    assert metadata.custom_fields["custom_field1"] == "value1"


def test_image_metadata_from_json_dict() -> None:
    """Test creating metadata from JSON dictionary."""
    data = {
        "prompt": "Test prompt",
        "model": "Test Model",
        "tags": ["tag1", "tag2"],  # List format (from JSON)
    }
    metadata = ImageMetadata.from_json_dict(data)
    assert metadata.prompt == "Test prompt"
    assert metadata.model == "Test Model"
    assert metadata.tags == ["tag1", "tag2"]


def test_image_metadata_custom_fields(sample_metadata: ImageMetadata) -> None:
    """Test custom fields handling.

    Parameters
    ----------
    sample_metadata : ImageMetadata
        Sample metadata fixture with custom fields.
    """
    assert "style" in sample_metadata.custom_fields
    assert sample_metadata.custom_fields["style"] == "photorealistic"
    assert "seed" in sample_metadata.custom_fields
    assert sample_metadata.custom_fields["seed"] == "12345"


def test_image_metadata_custom_fields_merge() -> None:
    """Test that custom fields can be added and merged."""
    metadata1 = ImageMetadata(
        prompt="Test",
        model="Test",
        custom_fields={"field1": "value1"},
    )
    metadata2 = ImageMetadata(
        prompt="Test",
        model="Test",
        custom_fields={"field2": "value2"},
    )

    # Both should have their custom fields
    assert "field1" in metadata1.custom_fields
    assert "field2" in metadata2.custom_fields
    assert "field1" not in metadata2.custom_fields
    assert "field2" not in metadata1.custom_fields


def test_image_metadata_multiline_prompt() -> None:
    """Test that multiline prompts are preserved."""
    multiline_prompt = "First line of prompt\nSecond line of prompt\nThird line"
    metadata = ImageMetadata(prompt=multiline_prompt, model="Test Model")
    assert metadata.prompt == multiline_prompt
    assert "\n" in metadata.prompt
    assert metadata.prompt.count("\n") == 2


def test_image_metadata_empty_prompt() -> None:
    """Test that empty prompts are allowed."""
    metadata = ImageMetadata(prompt="", model="Test Model")
    assert metadata.prompt == ""
    assert metadata.model == "Test Model"
