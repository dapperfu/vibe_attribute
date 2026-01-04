"""Click CLI interface for attribute tool."""

import sys
from pathlib import Path
from typing import Optional

import click

from attribute.metadata import (
    MetadataError,
    UnsupportedFormatError,
    read_metadata,
    write_metadata,
    is_supported_format,
)
from attribute.models import ImageMetadata
from attribute.editor import edit_metadata_editor
from attribute.tui import edit_metadata_tui
from attribute.gui import edit_metadata_gui
from attribute.export import export_metadata, import_metadata


@click.group()
@click.version_option(version="0.1.0")
def main() -> None:
    """Add metadata to AI-generated images."""
    pass


@main.command()
@click.argument("image_path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--tui",
    is_flag=True,
    help="Launch TUI interface instead of editor",
)
@click.option(
    "--gui",
    is_flag=True,
    help="Launch GUI interface (for directories)",
)
def attribute(
    image_path: Path,
    tui: bool,
    gui: bool,
) -> None:
    """Add metadata to an image file.

    IMAGE_PATH: Path to image file or directory (for GUI mode)
    """
    if gui:
        # GUI mode - can handle directories
        if image_path.is_dir():
            edit_metadata_gui(image_path)
        elif image_path.is_file():
            edit_metadata_gui(image_path.parent, initial_file=image_path)
        else:
            click.echo(f"Error: {image_path} is not a file or directory", err=True)
            sys.exit(1)
    elif tui:
        # TUI mode
        if not image_path.is_file():
            click.echo(f"Error: {image_path} is not a file", err=True)
            sys.exit(1)
        if not is_supported_format(image_path):
            click.echo(
                f"Error: Unsupported format: {image_path.suffix}",
                err=True,
            )
            sys.exit(1)
        edit_metadata_tui(image_path)
    else:
        # Default editor mode
        if not image_path.is_file():
            click.echo(f"Error: {image_path} is not a file", err=True)
            sys.exit(1)
        if not is_supported_format(image_path):
            click.echo(
                f"Error: Unsupported format: {image_path.suffix}",
                err=True,
            )
            sys.exit(1)
        edit_metadata_editor(image_path)


@main.command()
@click.argument("image_path", type=click.Path(exists=True, path_type=Path))
def view(image_path: Path) -> None:
    """View existing metadata from an image file.

    IMAGE_PATH: Path to image file
    """
    if not image_path.is_file():
        click.echo(f"Error: {image_path} is not a file", err=True)
        sys.exit(1)

    if not is_supported_format(image_path):
        click.echo(
            f"Error: Unsupported format: {image_path.suffix}",
            err=True,
        )
        sys.exit(1)

    try:
        metadata = read_metadata(image_path)
        click.echo(f"\nMetadata for: {image_path}")
        click.echo("=" * 60)
        click.echo(f"Prompt:      {metadata.prompt or '(empty)'}")
        click.echo(f"Model:       {metadata.model or '(empty)'}")
        click.echo(f"Date:        {metadata.date or '(empty)'}")
        click.echo(f"Description: {metadata.description or '(empty)'}")
        click.echo(f"Tags:        {', '.join(metadata.tags) if metadata.tags else '(empty)'}")
        click.echo(f"Copyright:   {metadata.copyright or '(empty)'}")
        click.echo(f"Artist:      {metadata.artist or '(empty)'}")

        if metadata.custom_fields:
            click.echo("\nCustom fields:")
            for key, value in metadata.custom_fields.items():
                click.echo(f"  {key}: {value}")
        click.echo("")
    except UnsupportedFormatError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except MetadataError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.argument("image_path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--format",
    type=click.Choice(["json", "csv"], case_sensitive=False),
    default="json",
    help="Export format (json or csv)",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Output file path (default: <image_name>.metadata.<format>)",
)
def export(
    image_path: Path,
    format: str,
    output: Optional[Path],
) -> None:
    """Export metadata from an image file.

    IMAGE_PATH: Path to image file
    """
    if not image_path.is_file():
        click.echo(f"Error: {image_path} is not a file", err=True)
        sys.exit(1)

    if not is_supported_format(image_path):
        click.echo(
            f"Error: Unsupported format: {image_path.suffix}",
            err=True,
        )
        sys.exit(1)

    if output is None:
        output = image_path.with_suffix(f".metadata.{format}")

    try:
        metadata = read_metadata(image_path)
        export_metadata({str(image_path): metadata}, output, format.lower())
        click.echo(f"Metadata exported to: {output}")
    except (UnsupportedFormatError, MetadataError) as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.argument("metadata_file", type=click.Path(exists=True, path_type=Path))
def import_meta(metadata_file: Path) -> None:
    """Import metadata from JSON or CSV file and apply to images.

    METADATA_FILE: Path to JSON or CSV metadata file
    """
    if not metadata_file.is_file():
        click.echo(f"Error: {metadata_file} is not a file", err=True)
        sys.exit(1)

    try:
        imported = import_metadata(metadata_file)
        click.echo(f"Imported metadata for {len(imported)} image(s)")
        for image_path in imported:
            click.echo(f"  - {image_path}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

