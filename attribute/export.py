"""Export and import metadata functionality."""

import csv
import json
from pathlib import Path
from typing import Dict, List, Any

from attribute.metadata import read_metadata, write_metadata, MetadataError
from attribute.models import ImageMetadata


def export_metadata(
    metadata_dict: Dict[str, ImageMetadata],
    output_path: Path,
    format: str,
) -> None:
    """Export metadata to JSON or CSV file.

    Parameters
    ----------
    metadata_dict : Dict[str, ImageMetadata]
        Dictionary mapping image paths to metadata.
    output_path : Path
        Output file path.
    format : str
        Export format ("json" or "csv").

    Raises
    ------
    ValueError
        If format is not supported.
    """
    if format.lower() == "json":
        _export_json(metadata_dict, output_path)
    elif format.lower() == "csv":
        _export_csv(metadata_dict, output_path)
    else:
        raise ValueError(f"Unsupported format: {format}. Use 'json' or 'csv'.")


def _export_json(
    metadata_dict: Dict[str, ImageMetadata],
    output_path: Path,
) -> None:
    """Export metadata to JSON file.

    Parameters
    ----------
    metadata_dict : Dict[str, ImageMetadata]
        Dictionary mapping image paths to metadata.
    output_path : Path
        Output JSON file path.
    """
    json_dict: Dict[str, Any] = {}
    for image_path, metadata in metadata_dict.items():
        json_dict[image_path] = metadata.to_json_dict()

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(json_dict, f, indent=2, ensure_ascii=False)


def _export_csv(
    metadata_dict: Dict[str, ImageMetadata],
    output_path: Path,
) -> None:
    """Export metadata to CSV file.

    Parameters
    ----------
    metadata_dict : Dict[str, ImageMetadata]
        Dictionary mapping image paths to metadata.
    output_path : Path
        Output CSV file path.
    """
    if not metadata_dict:
        # Create empty CSV with headers
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "image_path",
                    "prompt",
                    "model",
                    "date",
                    "description",
                    "tags",
                    "copyright",
                    "artist",
                ],
            )
            writer.writeheader()
        return

    # Get all field names (including custom fields)
    all_fields = set()
    for metadata in metadata_dict.values():
        all_fields.update(metadata.custom_fields.keys())

    fieldnames = [
        "image_path",
        "prompt",
        "model",
        "date",
        "description",
        "tags",
        "copyright",
        "artist",
    ] + sorted(all_fields)

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for image_path, metadata in metadata_dict.items():
            row = {
                "image_path": image_path,
                "prompt": metadata.prompt,
                "model": metadata.model,
                "date": metadata.date or "",
                "description": metadata.description or "",
                "tags": ", ".join(metadata.tags) if metadata.tags else "",
                "copyright": metadata.copyright or "",
                "artist": metadata.artist or "",
            }

            # Add custom fields
            for key in all_fields:
                row[key] = metadata.custom_fields.get(key, "")

            writer.writerow(row)


def import_metadata(metadata_file: Path) -> List[str]:
    """Import metadata from JSON or CSV file and apply to images.

    Parameters
    ----------
    metadata_file : Path
        Path to JSON or CSV metadata file.

    Returns
    -------
    List[str]
        List of image paths that were successfully updated.

    Raises
    ------
    ValueError
        If file format is not supported.
    MetadataError
        If metadata cannot be read or written.
    """
    ext = metadata_file.suffix.lower()

    if ext == ".json":
        return _import_json(metadata_file)
    elif ext == ".csv":
        return _import_csv(metadata_file)
    else:
        raise ValueError(
            f"Unsupported file format: {ext}. Use .json or .csv files."
        )


def _import_json(metadata_file: Path) -> List[str]:
    """Import metadata from JSON file.

    Parameters
    ----------
    metadata_file : Path
        Path to JSON metadata file.

    Returns
    -------
    List[str]
        List of image paths that were successfully updated.
    """
    with open(metadata_file, "r", encoding="utf-8") as f:
        json_dict = json.load(f)

    updated_files: List[str] = []

    for image_path_str, metadata_dict in json_dict.items():
        image_path = Path(image_path_str)

        # Resolve relative paths relative to metadata file
        if not image_path.is_absolute():
            image_path = metadata_file.parent / image_path

        if not image_path.exists():
            continue

        try:
            metadata = ImageMetadata.from_json_dict(metadata_dict)
            write_metadata(image_path, metadata)
            updated_files.append(str(image_path))
        except Exception:
            # Skip files that fail
            continue

    return updated_files


def _import_csv(metadata_file: Path) -> List[str]:
    """Import metadata from CSV file.

    Parameters
    ----------
    metadata_file : Path
        Path to CSV metadata file.

    Returns
    -------
    List[str]
        List of image paths that were successfully updated.
    """
    updated_files: List[str] = []

    with open(metadata_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        if "image_path" not in reader.fieldnames:
            raise ValueError("CSV file must have 'image_path' column")

        for row in reader:
            image_path_str = row["image_path"]
            image_path = Path(image_path_str)

            # Resolve relative paths relative to metadata file
            if not image_path.is_absolute():
                image_path = metadata_file.parent / image_path

            if not image_path.exists():
                continue

            try:
                # Extract standard fields
                metadata_dict: Dict[str, Any] = {
                    "prompt": row.get("prompt", ""),
                    "model": row.get("model", ""),
                    "date": row.get("date") or None,
                    "description": row.get("description") or None,
                    "tags": row.get("tags", ""),
                    "copyright": row.get("copyright") or None,
                    "artist": row.get("artist") or None,
                }

                # Extract custom fields (all other columns)
                standard_fields = {
                    "image_path",
                    "prompt",
                    "model",
                    "date",
                    "description",
                    "tags",
                    "copyright",
                    "artist",
                }
                custom_fields = {
                    k: v for k, v in row.items() if k not in standard_fields and v
                }
                if custom_fields:
                    metadata_dict["custom_fields"] = custom_fields

                metadata = ImageMetadata.from_dict(metadata_dict)
                write_metadata(image_path, metadata)
                updated_files.append(str(image_path))
            except Exception:
                # Skip files that fail
                continue

    return updated_files

