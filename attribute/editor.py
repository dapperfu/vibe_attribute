"""Editor mode for metadata editing (git commit style)."""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

from attribute.metadata import read_metadata, write_metadata, MetadataError
from attribute.models import ImageMetadata


def _get_editor() -> str:
    """Get the system editor command.

    Returns
    -------
    str
        Editor command to use.
    """
    editor = os.environ.get("EDITOR")
    if editor:
        return editor

    # Fallback to common editors
    for cmd in ["nano", "vim", "vi", "code", "gedit"]:
        if _command_exists(cmd):
            return cmd

    return "nano"  # Default fallback


def _command_exists(cmd: str) -> bool:
    """Check if a command exists in PATH.

    Parameters
    ----------
    cmd : str
        Command name.

    Returns
    -------
    bool
        True if command exists, False otherwise.
    """
    try:
        subprocess.run(
            ["which", cmd],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def _create_template(metadata: ImageMetadata) -> str:
    """Create template text for metadata editing.

    Parameters
    ----------
    metadata : ImageMetadata
        Existing metadata to populate template.

    Returns
    -------
    str
        Template text.
    """
    template = """# Image Metadata
# Lines starting with # are ignored
# Leave fields empty to keep existing values

prompt: {prompt}
model: {model}
date: {date}
description: {description}
tags: {tags}
copyright: {copyright}
artist: {artist}

# Custom fields (key: value format, one per line)
""".format(
        prompt=metadata.prompt or "",
        model=metadata.model or "",
        date=metadata.date or "",
        description=metadata.description or "",
        tags=", ".join(metadata.tags) if metadata.tags else "",
        copyright=metadata.copyright or "",
        artist=metadata.artist or "",
    )

    # Add custom fields
    if metadata.custom_fields:
        template += "\n# Existing custom fields:\n"
        for key, value in metadata.custom_fields.items():
            template += f"# {key}: {value}\n"

    template += "\n# Add new custom fields below (key: value)\n"

    return template


def _parse_template(content: str) -> ImageMetadata:
    """Parse template content into ImageMetadata.

    Parameters
    ----------
    content : str
        Template content.

    Returns
    -------
    ImageMetadata
        Parsed metadata.

    Raises
    ------
    ValueError
        If required fields are missing or invalid.
    """
    lines = content.split("\n")
    metadata_dict: Dict[str, Any] = {
        "prompt": "",
        "model": "",
        "tags": [],
        "custom_fields": {},
    }

    for line in lines:
        # Skip comments and empty lines
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        # Parse key: value pairs
        if ":" in line:
            key, value = line.split(":", 1)
            key = key.strip().lower()
            value = value.strip()

            if key == "prompt":
                metadata_dict["prompt"] = value
            elif key == "model":
                metadata_dict["model"] = value
            elif key == "date":
                metadata_dict["date"] = value if value else None
            elif key == "description":
                metadata_dict["description"] = value if value else None
            elif key == "tags":
                if value:
                    metadata_dict["tags"] = [
                        tag.strip() for tag in value.split(",") if tag.strip()
                    ]
            elif key == "copyright":
                metadata_dict["copyright"] = value if value else None
            elif key == "artist":
                metadata_dict["artist"] = value if value else None
            else:
                # Custom field
                metadata_dict["custom_fields"][key] = value

    return ImageMetadata.from_dict(metadata_dict)


def edit_metadata_editor(image_path: Path) -> None:
    """Edit metadata using system editor.

    Parameters
    ----------
    image_path : Path
        Path to image file.

    Raises
    ------
    MetadataError
        If metadata cannot be read or written.
    """
    # Read existing metadata
    try:
        existing_metadata = read_metadata(image_path)
    except MetadataError:
        # Start with empty metadata if reading fails
        existing_metadata = ImageMetadata(prompt="", model="")

    # Create template
    template = _create_template(existing_metadata)

    # Create temporary file
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False
    ) as tmp_file:
        tmp_path = Path(tmp_file.name)
        tmp_file.write(template)

    try:
        # Open editor
        editor = _get_editor()
        editor_cmd = editor.split()

        # Handle special cases
        if editor == "code":
            # VS Code needs --wait flag
            subprocess.run([editor, "--wait", str(tmp_path)], check=True)
        else:
            subprocess.run([*editor_cmd, str(tmp_path)], check=True)

        # Read edited content
        with open(tmp_path, "r") as f:
            edited_content = f.read()

        # Parse and validate
        try:
            new_metadata = _parse_template(edited_content)
        except ValueError as e:
            print(f"Error parsing metadata: {e}")
            print("Metadata not saved.")
            return

        # Write metadata
        write_metadata(image_path, new_metadata)
        print(f"Metadata saved to {image_path}")

    except subprocess.CalledProcessError as e:
        raise MetadataError(f"Editor failed: {e}") from e
    except KeyboardInterrupt:
        print("\nCancelled by user.")
    finally:
        # Clean up temp file
        try:
            tmp_path.unlink()
        except Exception:
            pass

