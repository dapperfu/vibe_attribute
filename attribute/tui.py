"""Textual TUI interface for metadata editing."""

from pathlib import Path
from typing import Optional

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import (
    Button,
    Input,
    TextArea,
    Label,
    Header,
    Footer,
)
from textual.binding import Binding

from attribute.metadata import read_metadata, write_metadata, MetadataError
from attribute.models import ImageMetadata


class MetadataForm(Container):
    """Form widget for editing metadata."""

    def __init__(
        self,
        metadata: ImageMetadata,
        *args,
        **kwargs,
    ) -> None:
        """Initialize form with metadata.

        Parameters
        ----------
        metadata : ImageMetadata
            Initial metadata values.
        """
        super().__init__(*args, **kwargs)
        self.metadata = metadata

    def compose(self) -> ComposeResult:
        """Compose the form widgets."""
        with Vertical():
            yield Label("Prompt:", classes="field-label")
            yield TextArea(
                self.metadata.prompt or "",
                id="prompt",
                classes="field-input",
            )

            yield Label("Model:", classes="field-label")
            yield Input(
                self.metadata.model or "",
                id="model",
                placeholder="e.g., ChatGPT-5.2 Thinking",
            )

            yield Label("Date (YYYY-MM-DD):", classes="field-label")
            yield Input(
                self.metadata.date or "",
                id="date",
                placeholder="2024-01-15",
            )

            yield Label("Description:", classes="field-label")
            yield TextArea(
                self.metadata.description or "",
                id="description",
                classes="field-input",
            )

            yield Label("Tags (comma-separated):", classes="field-label")
            yield Input(
                ", ".join(self.metadata.tags) if self.metadata.tags else "",
                id="tags",
                placeholder="tag1, tag2, tag3",
            )

            yield Label("Copyright:", classes="field-label")
            yield Input(
                self.metadata.copyright or "",
                id="copyright",
            )

            yield Label("Artist:", classes="field-label")
            yield Input(
                self.metadata.artist or "",
                id="artist",
            )

        with Horizontal(classes="button-container"):
            yield Button("Save", id="save", variant="primary")
            yield Button("Cancel", id="cancel", variant="default")

    def get_metadata(self) -> ImageMetadata:
        """Get metadata from form fields.

        Returns
        -------
        ImageMetadata
            Metadata from form.
        """
        prompt_widget = self.query_one("#prompt", TextArea)
        model_widget = self.query_one("#model", Input)
        date_widget = self.query_one("#date", Input)
        description_widget = self.query_one("#description", TextArea)
        tags_widget = self.query_one("#tags", Input)
        copyright_widget = self.query_one("#copyright", Input)
        artist_widget = self.query_one("#artist", Input)

        # Parse tags
        tags_str = tags_widget.value.strip()
        tags = (
            [tag.strip() for tag in tags_str.split(",") if tag.strip()]
            if tags_str
            else []
        )

        # Parse custom fields (not implemented in UI yet, but structure ready)
        custom_fields: dict[str, str] = {}

        return ImageMetadata(
            prompt=prompt_widget.text or "",
            model=model_widget.value or "",
            date=date_widget.value or None,
            description=description_widget.text or None,
            tags=tags,
            copyright=copyright_widget.value or None,
            artist=artist_widget.value or None,
            custom_fields=custom_fields,
        )


class MetadataApp(App):
    """Textual app for editing image metadata."""

    CSS = """
    Screen {
        background: $surface;
    }

    .field-label {
        margin-top: 1;
        color: $text;
    }

    .field-input {
        margin-bottom: 1;
        height: 3;
    }

    #prompt, #description {
        height: 5;
    }

    .button-container {
        align: center;
        margin-top: 2;
        height: 3;
    }

    Button {
        margin: 1;
        width: 20;
    }
    """

    BINDINGS = [
        Binding("ctrl+s", "save", "Save", show=True),
        Binding("escape", "cancel", "Cancel", show=True),
    ]

    def __init__(
        self,
        image_path: Path,
        *args,
        **kwargs,
    ) -> None:
        """Initialize app.

        Parameters
        ----------
        image_path : Path
            Path to image file.
        """
        super().__init__(*args, **kwargs)
        self.image_path = image_path
        self.metadata: Optional[ImageMetadata] = None

    def compose(self) -> ComposeResult:
        """Compose the app."""
        yield Header(show_clock=True)
        yield Label(
            f"Editing metadata for: {self.image_path.name}",
            classes="title",
        )

        # Load existing metadata
        try:
            self.metadata = read_metadata(self.image_path)
        except MetadataError:
            # Start with empty metadata
            self.metadata = ImageMetadata(prompt="", model="")

        yield MetadataForm(self.metadata, id="form")

        yield Footer()

    def action_save(self) -> None:
        """Save metadata."""
        form = self.query_one("#form", MetadataForm)
        try:
            new_metadata = form.get_metadata()
            write_metadata(self.image_path, new_metadata)
            self.notify("Metadata saved successfully!", severity="success")
            self.exit()
        except Exception as e:
            self.notify(f"Error saving metadata: {e}", severity="error")

    def action_cancel(self) -> None:
        """Cancel editing."""
        self.exit()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "save":
            self.action_save()
        elif event.button.id == "cancel":
            self.action_cancel()


def edit_metadata_tui(image_path: Path) -> None:
    """Edit metadata using Textual TUI.

    Parameters
    ----------
    image_path : Path
        Path to image file.

    Raises
    ------
    MetadataError
        If metadata cannot be read or written.
    """
    app = MetadataApp(image_path)
    app.run()

