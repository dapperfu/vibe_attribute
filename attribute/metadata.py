"""Core metadata handling for images with EXIF and XMP support."""

import json
from pathlib import Path
from typing import Dict, Optional, Any

try:
    from PIL import Image
    from PIL.ExifTags import TAGS
except ImportError:
    raise ImportError("Pillow is required. Install with: pip install Pillow")

try:
    import piexif
except ImportError:
    piexif = None

try:
    from libxmp import XMPFiles
    from libxmp import consts
except ImportError:
    XMPFiles = None
    consts = None

from attribute.models import ImageMetadata

# Supported image formats
SUPPORTED_FORMATS = {".png", ".jpg", ".jpeg", ".webp"}

# EXIF tag mappings
EXIF_IMAGE_DESCRIPTION = 270
EXIF_ARTIST = 315
EXIF_COPYRIGHT = 33432
EXIF_DATETIME_ORIGINAL = 36867

# XMP namespace URIs
XMP_NS_DC = "http://purl.org/dc/elements/1.1/"
XMP_NS_CUSTOM = "http://ns.example.com/vibe/1.0/"


class MetadataError(Exception):
    """Base exception for metadata operations."""

    pass


class UnsupportedFormatError(MetadataError):
    """Raised when image format is not supported."""

    pass


def is_supported_format(file_path: str | Path) -> bool:
    """Check if file format is supported.

    Parameters
    ----------
    file_path : str | Path
        Path to image file.

    Returns
    -------
    bool
        True if format is supported, False otherwise.
    """
    ext = Path(file_path).suffix.lower()
    return ext in SUPPORTED_FORMATS


def _read_png_metadata(img: Image.Image) -> Dict[str, Any]:
    """Read metadata from PNG image.

    Parameters
    ----------
    img : Image.Image
        PIL Image object.

    Returns
    -------
    Dict[str, Any]
        Dictionary of metadata fields.
    """
    metadata: Dict[str, Any] = {}
    if hasattr(img, "text") and img.text:
        # PNG text chunks
        for key, value in img.text.items():
            if key == "prompt":
                metadata["prompt"] = value
            elif key == "model":
                metadata["model"] = value
            elif key == "description":
                metadata["description"] = value
            elif key == "copyright":
                metadata["copyright"] = value
            elif key == "artist":
                metadata["artist"] = value
            elif key == "date":
                metadata["date"] = value
            elif key == "tags":
                metadata["tags"] = [t.strip() for t in value.split(",") if t.strip()]
            elif key.startswith("custom_"):
                if "custom_fields" not in metadata:
                    metadata["custom_fields"] = {}
                # Skip if the extracted key is "custom_fields" to avoid nesting
                extracted_key = key[7:]
                if extracted_key != "custom_fields":
                    metadata["custom_fields"][extracted_key] = value
    return metadata


def _read_exif_metadata(img: Image.Image, image_path: Path | None = None) -> Dict[str, Any]:
    """Read EXIF metadata from image.

    Parameters
    ----------
    img : Image.Image
        PIL Image object.
    image_path : Path | None
        Optional path to image file for piexif reading.

    Returns
    -------
    Dict[str, Any]
        Dictionary of metadata fields.
    """
    metadata: Dict[str, Any] = {}
    
    # Try piexif first if available and path provided
    if piexif is not None and image_path is not None:
        try:
            exif_dict = piexif.load(str(image_path))
            if exif_dict:
                # Read from 0th IFD
                if "0th" in exif_dict and EXIF_IMAGE_DESCRIPTION in exif_dict["0th"]:
                    value = exif_dict["0th"][EXIF_IMAGE_DESCRIPTION]
                    if value:
                        if isinstance(value, bytes):
                            value = value.decode('utf-8', errors='ignore')
                        metadata["description"] = str(value)
                        if "prompt" not in metadata:
                            metadata["prompt"] = str(value)
                if "0th" in exif_dict and EXIF_ARTIST in exif_dict["0th"]:
                    value = exif_dict["0th"][EXIF_ARTIST]
                    if value:
                        if isinstance(value, bytes):
                            value = value.decode('utf-8', errors='ignore')
                        metadata["artist"] = str(value)
                        if "model" not in metadata:
                            metadata["model"] = str(value)
                if "0th" in exif_dict and EXIF_COPYRIGHT in exif_dict["0th"]:
                    value = exif_dict["0th"][EXIF_COPYRIGHT]
                    if value:
                        if isinstance(value, bytes):
                            value = value.decode('utf-8', errors='ignore')
                        metadata["copyright"] = str(value)
                # Read date from Exif IFD
                if "Exif" in exif_dict and EXIF_DATETIME_ORIGINAL in exif_dict["Exif"]:
                    value = exif_dict["Exif"][EXIF_DATETIME_ORIGINAL]
                    if value:
                        # Handle bytes
                        if isinstance(value, bytes):
                            date_str = value.decode('utf-8', errors='ignore')
                        else:
                            date_str = str(value)
                        if ":" in date_str:
                            # Extract date part (YYYY:MM:DD) and convert to ISO format
                            date_part = date_str.split()[0] if " " in date_str else date_str
                            date_str = date_part.replace(":", "-")
                        metadata["date"] = date_str
        except Exception:
            pass
    
    # Fallback to PIL getexif if piexif didn't work or isn't available
    if not metadata.get("date") and "date" not in metadata:
        try:
            exif_data = img.getexif()
            if exif_data:
                if EXIF_IMAGE_DESCRIPTION in exif_data and "prompt" not in metadata:
                    value = exif_data[EXIF_IMAGE_DESCRIPTION]
                    if value:
                        metadata["description"] = str(value)
                        metadata["prompt"] = str(value)
                if EXIF_ARTIST in exif_data and "model" not in metadata:
                    value = exif_data[EXIF_ARTIST]
                    if value:
                        metadata["artist"] = str(value)
                        metadata["model"] = str(value)
                if EXIF_COPYRIGHT in exif_data:
                    value = exif_data[EXIF_COPYRIGHT]
                    if value:
                        metadata["copyright"] = str(value)
                if EXIF_DATETIME_ORIGINAL in exif_data and "date" not in metadata:
                    value = exif_data[EXIF_DATETIME_ORIGINAL]
                    if value:
                        # Handle both bytes and string
                        if isinstance(value, bytes):
                            date_str = value.decode('utf-8', errors='ignore')
                        else:
                            date_str = str(value)
                        if ":" in date_str:
                            # Extract date part (YYYY:MM:DD) and convert to ISO format
                            date_part = date_str.split()[0] if " " in date_str else date_str
                            date_str = date_part.replace(":", "-")
                        metadata["date"] = date_str
        except Exception:
            pass
    return metadata


def _read_xmp_metadata(image_path: Path) -> Dict[str, Any]:
    """Read XMP metadata from image file.

    Parameters
    ----------
    image_path : Path
        Path to image file.

    Returns
    -------
    Dict[str, Any]
        Dictionary of metadata fields.
    """
    metadata: Dict[str, Any] = {}
    if XMPFiles is None:
        return metadata

    try:
        xmp_file = XMPFiles(file_path=str(image_path), open_forupdate=False)
        xmp = xmp_file.get_xmp()

        if xmp:
            # Read DC namespace
            try:
                dc_desc = xmp.get_property(XMP_NS_DC, "description")
                if dc_desc:
                    metadata["description"] = dc_desc
                    if "prompt" not in metadata:
                        metadata["prompt"] = dc_desc
            except Exception:
                pass

            # Read tags/subjects
            try:
                count = xmp.count_array_items(XMP_NS_DC, "subject")
                if count > 0:
                    tags = []
                    for i in range(1, count + 1):
                        tag = xmp.get_property_array_item(XMP_NS_DC, "subject", i)
                        if tag:
                            tags.append(tag)
                    if tags:
                        metadata["tags"] = tags
            except Exception:
                pass

            # Read custom namespace
            try:
                custom_prompt = xmp.get_property(XMP_NS_CUSTOM, "prompt")
                if custom_prompt:
                    metadata["prompt"] = custom_prompt
            except Exception:
                pass

            try:
                custom_model = xmp.get_property(XMP_NS_CUSTOM, "model")
                if custom_model:
                    metadata["model"] = custom_model
            except Exception:
                pass

        xmp_file.close_file()
    except Exception:
        pass

    return metadata


def read_metadata(image_path: str | Path) -> ImageMetadata:
    """Read metadata from image file.

    Parameters
    ----------
    image_path : str | Path
        Path to image file.

    Returns
    -------
    ImageMetadata
        ImageMetadata instance with read values.

    Raises
    ------
    UnsupportedFormatError
        If image format is not supported.
    MetadataError
        If metadata cannot be read.
    """
    image_path = Path(image_path)
    if not image_path.exists():
        raise MetadataError(f"Image file not found: {image_path}")

    if not is_supported_format(image_path):
        raise UnsupportedFormatError(
            f"Unsupported format: {image_path.suffix}. Supported: {SUPPORTED_FORMATS}"
        )

    # Initialize with empty values
    metadata_dict: Dict[str, Any] = {
        "prompt": "",
        "model": "",
        "tags": [],
        "custom_fields": {},
    }

    try:
        with Image.open(image_path) as img:
            # Read PNG text metadata
            if image_path.suffix.lower() == ".png":
                png_meta = _read_png_metadata(img)
                metadata_dict.update(png_meta)
            elif image_path.suffix.lower() == ".webp":
                # WebP stores metadata in info dict, not text chunks
                if hasattr(img, "info") and img.info:
                    for key, value in img.info.items():
                        if key == "prompt":
                            metadata_dict["prompt"] = value
                        elif key == "model":
                            metadata_dict["model"] = value
                        elif key == "description":
                            metadata_dict["description"] = value
                        elif key == "copyright":
                            metadata_dict["copyright"] = value
                        elif key == "artist":
                            metadata_dict["artist"] = value
                        elif key == "date":
                            metadata_dict["date"] = value
                        elif key == "tags":
                            metadata_dict["tags"] = [t.strip() for t in value.split(",") if t.strip()]
                        elif key.startswith("custom_"):
                            if "custom_fields" not in metadata_dict:
                                metadata_dict["custom_fields"] = {}
                            extracted_key = key[7:]
                            if extracted_key != "custom_fields":
                                metadata_dict["custom_fields"][extracted_key] = value

            # Read EXIF metadata (pass image_path for piexif)
            exif_meta = _read_exif_metadata(img, image_path)
            # Update only if not already set
            for key, value in exif_meta.items():
                if key not in metadata_dict or not metadata_dict[key]:
                    metadata_dict[key] = value

        # Read XMP metadata
        xmp_meta = _read_xmp_metadata(image_path)
        # Update only if not already set
        for key, value in xmp_meta.items():
            if key not in metadata_dict or not metadata_dict[key]:
                metadata_dict[key] = value

    except Exception as e:
        raise MetadataError(f"Failed to read metadata: {e}") from e

    # Ensure required fields (use placeholder values if empty)
    if "prompt" not in metadata_dict or not metadata_dict["prompt"]:
        metadata_dict["prompt"] = ""
    if "model" not in metadata_dict or not metadata_dict["model"]:
        metadata_dict["model"] = ""

    # Create metadata - allow empty strings for reading (validation happens on write)
    try:
        return ImageMetadata.from_dict(metadata_dict)
    except ValueError:
        # If validation fails (empty prompt/model), return with placeholder
        return ImageMetadata(
            prompt=metadata_dict.get("prompt", "") or " ",
            model=metadata_dict.get("model", "") or " ",
            date=metadata_dict.get("date"),
            description=metadata_dict.get("description"),
            tags=metadata_dict.get("tags", []),
            copyright=metadata_dict.get("copyright"),
            artist=metadata_dict.get("artist"),
            custom_fields=metadata_dict.get("custom_fields", {}),
        )


def _write_png_metadata(image_path: Path, metadata: ImageMetadata) -> None:
    """Write metadata to PNG image using text chunks.

    Parameters
    ----------
    image_path : Path
        Path to PNG image file.
    metadata : ImageMetadata
        Metadata to write.
    """
    try:
        from PIL import PngImagePlugin
        
        with Image.open(image_path) as img:
            # Strip placeholder values before writing (don't write " " placeholders)
            prompt = metadata.prompt.strip() if metadata.prompt else ""
            model = metadata.model.strip() if metadata.model else ""
            
            # Create PngInfo object for text chunks
            pnginfo = PngImagePlugin.PngInfo()
            
            # Only write if not empty and not just a space
            if prompt and prompt != " ":
                pnginfo.add_text("prompt", prompt)
            if model and model != " ":
                pnginfo.add_text("model", model)
            if metadata.description:
                pnginfo.add_text("description", metadata.description)
            if metadata.copyright:
                pnginfo.add_text("copyright", metadata.copyright)
            if metadata.artist:
                pnginfo.add_text("artist", metadata.artist)
            if metadata.date:
                pnginfo.add_text("date", metadata.date)
            if metadata.tags:
                pnginfo.add_text("tags", ", ".join(metadata.tags))

            # Add custom fields (skip if key is "custom_fields" to avoid nesting)
            for key, value in metadata.custom_fields.items():
                if key != "custom_fields":  # Avoid writing custom_fields as a custom field
                    pnginfo.add_text(f"custom_{key}", str(value))

            # Save with PngInfo
            img.save(image_path, pnginfo=pnginfo)
    except Exception as e:
        raise MetadataError(f"Failed to write PNG metadata: {e}") from e


def _write_exif_metadata(image_path: Path, metadata: ImageMetadata) -> None:
    """Write EXIF metadata to JPEG image.

    Parameters
    ----------
    image_path : Path
        Path to JPEG image file.
    metadata : ImageMetadata
        Metadata to write.
    """
    if piexif is None:
        # Fallback to PIL EXIF
        try:
            with Image.open(image_path) as img:
                exif_dict = img.getexif()
                # Strip placeholder values before writing (don't write " " placeholders)
                prompt = metadata.prompt.strip() if metadata.prompt else ""
                model = metadata.model.strip() if metadata.model else ""
                
                # Only write if not empty and not just a space
                if prompt and prompt != " ":
                    exif_dict[EXIF_IMAGE_DESCRIPTION] = prompt
                if model and model != " ":
                    exif_dict[EXIF_ARTIST] = model
                if metadata.copyright:
                    exif_dict[EXIF_COPYRIGHT] = metadata.copyright
                if metadata.date:
                    # Convert ISO date (YYYY-MM-DD) to EXIF format (YYYY:MM:DD HH:MM:SS)
                    date_str = metadata.date
                    if "-" in date_str and ":" not in date_str:
                        date_str = date_str.replace("-", ":") + " 00:00:00"
                    exif_dict[EXIF_DATETIME_ORIGINAL] = date_str
                img.save(image_path, exif=exif_dict)
        except Exception as e:
            raise MetadataError(f"Failed to write EXIF metadata: {e}") from e
        return

    try:
        # Use piexif for better EXIF support
        exif_dict = piexif.load(str(image_path))

        # Strip placeholder values before writing (don't write " " placeholders)
        prompt = metadata.prompt.strip() if metadata.prompt else ""
        model = metadata.model.strip() if metadata.model else ""
        
        # Only write if not empty and not just a space
        if prompt and prompt != " ":
            exif_dict["0th"][EXIF_IMAGE_DESCRIPTION] = prompt.encode("utf-8")
        if model and model != " ":
            exif_dict["0th"][EXIF_ARTIST] = model.encode("utf-8")
        if metadata.copyright:
            exif_dict["0th"][EXIF_COPYRIGHT] = metadata.copyright.encode("utf-8")
        if metadata.date:
            # Convert ISO date (YYYY-MM-DD) to EXIF format (YYYY:MM:DD HH:MM:SS)
            date_str = metadata.date
            if "-" in date_str and ":" not in date_str:
                date_str = date_str.replace("-", ":") + " 00:00:00"
            exif_dict["Exif"][EXIF_DATETIME_ORIGINAL] = date_str.encode("utf-8")

        exif_bytes = piexif.dump(exif_dict)
        piexif.insert(exif_bytes, str(image_path))
    except Exception as e:
        raise MetadataError(f"Failed to write EXIF metadata: {e}") from e


def _write_xmp_metadata(image_path: Path, metadata: ImageMetadata) -> None:
    """Write XMP metadata to image file.

    Parameters
    ----------
    image_path : Path
        Path to image file.
    metadata : ImageMetadata
        Metadata to write.
    """
    if XMPFiles is None:
        return

    try:
        xmp_file = XMPFiles(file_path=str(image_path), open_forupdate=True)
        xmp = xmp_file.get_xmp()

        if xmp:
            # Register custom namespace
            try:
                xmp.register_namespace(XMP_NS_CUSTOM, "vibe")
            except Exception:
                pass

            # Write DC namespace
            if metadata.description:
                xmp.set_property(XMP_NS_DC, "description", metadata.description)
            elif metadata.prompt:
                xmp.set_property(XMP_NS_DC, "description", metadata.prompt)

            # Write tags
            if metadata.tags:
                try:
                    xmp.delete_property(XMP_NS_DC, "subject")
                except Exception:
                    pass
                for i, tag in enumerate(metadata.tags, start=1):
                    try:
                        xmp.set_property_array_item(XMP_NS_DC, "subject", i, tag)
                    except Exception:
                        pass

            # Write custom namespace (strip placeholder values, don't write " " placeholders)
            prompt = metadata.prompt.strip() if metadata.prompt else ""
            model = metadata.model.strip() if metadata.model else ""
            
            # Only write if not empty and not just a space
            if prompt and prompt != " ":
                xmp.set_property(XMP_NS_CUSTOM, "prompt", prompt)
            if model and model != " ":
                xmp.set_property(XMP_NS_CUSTOM, "model", model)

            # Write custom fields
            for key, value in metadata.custom_fields.items():
                xmp.set_property(XMP_NS_CUSTOM, key, str(value))

            xmp_file.put_xmp(xmp)
        xmp_file.close_file()
    except Exception:
        # XMP writing failed, but continue
        pass


def write_metadata(image_path: str | Path, metadata: ImageMetadata) -> None:
    """Write metadata to image file, preserving existing metadata.

    Parameters
    ----------
    image_path : str | Path
        Path to image file.
    metadata : ImageMetadata
        Metadata to write.

    Raises
    ------
    UnsupportedFormatError
        If image format is not supported.
    MetadataError
        If metadata cannot be written.
    """
    image_path = Path(image_path)
    if not image_path.exists():
        raise MetadataError(f"Image file not found: {image_path}")

    if not is_supported_format(image_path):
        raise UnsupportedFormatError(
            f"Unsupported format: {image_path.suffix}. Supported: {SUPPORTED_FORMATS}"
        )

    # Read existing metadata first to preserve it
    try:
        existing_metadata = read_metadata(image_path)
        # If read metadata has empty prompt/model, use placeholders for merging
        if not existing_metadata.prompt or not existing_metadata.model:
            existing_metadata = ImageMetadata(
                prompt=existing_metadata.prompt or " ",
                model=existing_metadata.model or " ",
                date=existing_metadata.date,
                description=existing_metadata.description,
                tags=existing_metadata.tags,
                copyright=existing_metadata.copyright,
                artist=existing_metadata.artist,
                custom_fields=existing_metadata.custom_fields,
            )
    except Exception:
        # If reading fails, start with placeholder metadata
        existing_metadata = ImageMetadata(prompt=" ", model=" ")

    # Merge with new metadata (new values take precedence)
    # Strip placeholder values from existing metadata
    existing_prompt = existing_metadata.prompt.strip() if existing_metadata.prompt and existing_metadata.prompt.strip() != " " else ""
    existing_model = existing_metadata.model.strip() if existing_metadata.model and existing_metadata.model.strip() != " " else ""
    
    # Use new metadata if provided and not empty/placeholder, otherwise use existing
    merged_prompt = (metadata.prompt.strip() if metadata.prompt and metadata.prompt.strip() != " " else "") or existing_prompt
    merged_model = (metadata.model.strip() if metadata.model and metadata.model.strip() != " " else "") or existing_model
    merged_date = metadata.date if metadata.date else existing_metadata.date
    merged_description = metadata.description if metadata.description else existing_metadata.description
    merged_tags = metadata.tags if metadata.tags else existing_metadata.tags
    merged_copyright = metadata.copyright if metadata.copyright else existing_metadata.copyright
    merged_artist = metadata.artist if metadata.artist else existing_metadata.artist

    # Merge custom fields (exclude "custom_fields" key to avoid nesting)
    merged_custom = existing_metadata.custom_fields.copy()
    for key, value in metadata.custom_fields.items():
        if key != "custom_fields":  # Avoid nesting custom_fields
            merged_custom[key] = value

    # Ensure we have valid prompt and model (use placeholder if both are empty)
    if not merged_prompt and not merged_model:
        merged_prompt = " "
        merged_model = " "

    # Create merged metadata
    merged_metadata = ImageMetadata(
        prompt=merged_prompt,
        model=merged_model,
        date=merged_date,
        description=merged_description,
        tags=merged_tags,
        copyright=merged_copyright,
        artist=merged_artist,
        custom_fields=merged_custom,
    )

    # Write based on format
    ext = image_path.suffix.lower()
    if ext == ".png":
        _write_png_metadata(image_path, merged_metadata)
    elif ext in {".jpg", ".jpeg"}:
        _write_exif_metadata(image_path, merged_metadata)
    elif ext == ".webp":
        # WebP doesn't support PngInfo, use info dict approach
        try:
            with Image.open(image_path) as img:
                info = img.info.copy() if hasattr(img, 'info') and img.info else {}
                
                prompt = merged_metadata.prompt.strip() if merged_metadata.prompt else ""
                model = merged_metadata.model.strip() if merged_metadata.model else ""
                
                if prompt and prompt != " ":
                    info["prompt"] = prompt
                if model and model != " ":
                    info["model"] = model
                if merged_metadata.description:
                    info["description"] = merged_metadata.description
                if merged_metadata.copyright:
                    info["copyright"] = merged_metadata.copyright
                if merged_metadata.artist:
                    info["artist"] = merged_metadata.artist
                if merged_metadata.date:
                    info["date"] = merged_metadata.date
                if merged_metadata.tags:
                    info["tags"] = ", ".join(merged_metadata.tags)
                
                for key, value in merged_metadata.custom_fields.items():
                    if key != "custom_fields":
                        info[f"custom_{key}"] = str(value)
                
                img.save(image_path, **info)
        except Exception:
            # WebP metadata writing failed, but continue
            pass

    # Try to write XMP for all formats
    _write_xmp_metadata(image_path, merged_metadata)
