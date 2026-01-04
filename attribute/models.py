"""Data models for image metadata."""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class ImageMetadata:
    """Metadata model for AI-generated images.

    Attributes
    ----------
    prompt : str
        The AI prompt used to generate the image.
    model : str
        The AI model used (e.g., "ChatGPT-5.2 Thinking").
    date : Optional[str]
        Creation date in ISO format (YYYY-MM-DD).
    description : Optional[str]
        Additional description of the image.
    tags : List[str]
        List of tags associated with the image.
    copyright : Optional[str]
        Copyright information.
    artist : Optional[str]
        Artist/creator name.
    custom_fields : Dict[str, str]
        Custom key-value pairs for additional metadata.
    """

    prompt: str
    model: str
    date: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    copyright: Optional[str] = None
    artist: Optional[str] = None
    custom_fields: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate metadata fields after initialization."""
        # Allow single space " " as placeholder for internal use when reading empty metadata
        # Prompt is optional and can be empty
        # Model is required and must be non-empty, non-whitespace-only
        model_valid = self.model and (self.model.strip() or self.model == " ")
        
        if not model_valid:
            raise ValueError("Model is required and cannot be empty")

        # Validate date format if provided
        if self.date:
            try:
                datetime.fromisoformat(self.date)
            except ValueError:
                raise ValueError(
                    f"Date must be in ISO format (YYYY-MM-DD), got: {self.date}"
                )

    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary.

        Returns
        -------
        Dict[str, Any]
            Dictionary representation of metadata.
        """
        result = asdict(self)
        # Convert tags list to comma-separated string for CSV compatibility
        if result["tags"]:
            result["tags"] = ", ".join(result["tags"])
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ImageMetadata":
        """Create ImageMetadata from dictionary.

        Parameters
        ----------
        data : Dict[str, Any]
            Dictionary containing metadata fields.

        Returns
        -------
        ImageMetadata
            ImageMetadata instance.
        """
        # Handle tags as string or list
        tags = data.get("tags", [])
        if isinstance(tags, str):
            tags = [tag.strip() for tag in tags.split(",") if tag.strip()]
        elif not isinstance(tags, list):
            tags = []

        # Extract custom fields
        standard_fields = {
            "prompt",
            "model",
            "date",
            "description",
            "tags",
            "copyright",
            "artist",
            "custom_fields",  # Exclude custom_fields from being treated as a custom field
        }
        
        # Start with custom_fields if provided as a dict
        if "custom_fields" in data and isinstance(data["custom_fields"], dict):
            custom_fields = data["custom_fields"].copy()
        else:
            custom_fields = {}
        
        # Extract other custom fields (keys starting with custom_ or not in standard_fields)
        for k, v in data.items():
            if k not in standard_fields:
                if k.startswith("custom_"):
                    # Extract key after "custom_" prefix
                    extracted_key = k[7:]
                    if extracted_key != "custom_fields":  # Avoid nesting
                        custom_fields[extracted_key] = str(v)
                else:
                    # Other non-standard fields
                    custom_fields[k] = str(v)

        return cls(
            prompt=data.get("prompt", ""),
            model=data.get("model", ""),
            date=data.get("date"),
            description=data.get("description"),
            tags=tags,
            copyright=data.get("copyright"),
            artist=data.get("artist"),
            custom_fields=custom_fields,
        )

    def to_json_dict(self) -> Dict[str, Any]:
        """Convert metadata to JSON-serializable dictionary.

        Returns
        -------
        Dict[str, Any]
            JSON-serializable dictionary.
        """
        result = asdict(self)
        # Keep tags as list for JSON
        return result

    @classmethod
    def from_json_dict(cls, data: Dict[str, Any]) -> "ImageMetadata":
        """Create ImageMetadata from JSON dictionary.

        Parameters
        ----------
        data : Dict[str, Any]
            JSON dictionary containing metadata fields.

        Returns
        -------
        ImageMetadata
            ImageMetadata instance.
        """
        # Handle tags as list (from JSON)
        tags = data.get("tags", [])
        if isinstance(tags, str):
            tags = [tag.strip() for tag in tags.split(",") if tag.strip()]

        # Extract custom fields
        standard_fields = {
            "prompt",
            "model",
            "date",
            "description",
            "tags",
            "copyright",
            "artist",
            "custom_fields",  # Exclude custom_fields from being treated as a custom field
        }
        
        # Start with custom_fields if provided as a dict
        if "custom_fields" in data and isinstance(data["custom_fields"], dict):
            custom_fields = data["custom_fields"].copy()
        else:
            custom_fields = {}
        
        # Extract other custom fields (keys not in standard_fields)
        for k, v in data.items():
            if k not in standard_fields:
                custom_fields[k] = str(v)

        return cls(
            prompt=data.get("prompt", ""),
            model=data.get("model", ""),
            date=data.get("date"),
            description=data.get("description"),
            tags=tags if isinstance(tags, list) else [],
            copyright=data.get("copyright"),
            artist=data.get("artist"),
            custom_fields=custom_fields,
        )

