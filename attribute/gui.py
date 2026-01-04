"""Tkinter GUI interface for metadata editing with batch operations."""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from typing import Optional, List, Dict, Set
from PIL import Image, ImageTk

from attribute.metadata import (
    read_metadata,
    write_metadata,
    is_supported_format,
    MetadataError,
)
from attribute.models import ImageMetadata

# Supported image formats for GUI
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


class MetadataGUI:
    """Main GUI application for metadata editing."""

    def __init__(
        self,
        root: tk.Tk,
        directory: Path,
        initial_file: Optional[Path] = None,
    ) -> None:
        """Initialize GUI.

        Parameters
        ----------
        root : tk.Tk
            Tkinter root window.
        directory : Path
            Directory to browse.
        initial_file : Optional[Path]
            Initial file to select (if provided).
        """
        self.root = root
        self.directory = directory
        self.initial_file = initial_file
        self.current_file: Optional[Path] = None
        self.selected_files: Set[Path] = set()
        self.image_files: List[Path] = []

        self.setup_ui()
        self.load_directory()

        if initial_file:
            self.select_file(initial_file)

    def setup_ui(self) -> None:
        """Set up the UI components."""
        self.root.title("Image Metadata Editor")
        self.root.geometry("1200x800")

        # Create main paned window
        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Left panel: File browser
        left_frame = ttk.Frame(main_paned)
        main_paned.add(left_frame, weight=1)

        # File list with scrollbar
        list_frame = ttk.Frame(left_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.file_listbox = tk.Listbox(
            list_frame,
            yscrollcommand=scrollbar.set,
            selectmode=tk.EXTENDED,
        )
        self.file_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.file_listbox.bind("<<ListboxSelect>>", self.on_file_select)
        scrollbar.config(command=self.file_listbox.yview)

        # Batch selection checkbox
        self.batch_mode = tk.BooleanVar()
        batch_check = ttk.Checkbutton(
            left_frame,
            text="Batch mode (select multiple)",
            variable=self.batch_mode,
        )
        batch_check.pack(pady=5)

        # Batch apply button
        self.batch_apply_btn = ttk.Button(
            left_frame,
            text="Apply to Selected",
            command=self.batch_apply_metadata,
            state=tk.DISABLED,
        )
        self.batch_apply_btn.pack(pady=5)

        # Middle panel: Image preview
        middle_frame = ttk.Frame(main_paned)
        main_paned.add(middle_frame, weight=1)

        preview_label = ttk.Label(middle_frame, text="Preview")
        preview_label.pack(pady=5)

        self.preview_label = ttk.Label(middle_frame, text="No image selected")
        self.preview_label.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Right panel: Metadata form
        right_frame = ttk.Frame(main_paned)
        main_paned.add(right_frame, weight=2)

        form_label = ttk.Label(right_frame, text="Metadata")
        form_label.pack(pady=5)

        # Create form fields
        form_frame = ttk.Frame(right_frame)
        form_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Prompt
        ttk.Label(form_frame, text="Prompt:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.prompt_text = tk.Text(form_frame, height=3, width=40)
        self.prompt_text.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=2)

        # Model
        ttk.Label(form_frame, text="Model:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.model_entry = ttk.Entry(form_frame, width=40)
        self.model_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=2)

        # Date
        ttk.Label(form_frame, text="Date:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.date_entry = ttk.Entry(form_frame, width=40)
        self.date_entry.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=2)

        # Description
        ttk.Label(form_frame, text="Description:").grid(
            row=3, column=0, sticky=tk.W, pady=2
        )
        self.description_text = tk.Text(form_frame, height=3, width=40)
        self.description_text.grid(row=3, column=1, sticky=(tk.W, tk.E), pady=2)

        # Tags
        ttk.Label(form_frame, text="Tags:").grid(row=4, column=0, sticky=tk.W, pady=2)
        self.tags_entry = ttk.Entry(form_frame, width=40)
        self.tags_entry.grid(row=4, column=1, sticky=(tk.W, tk.E), pady=2)

        # Copyright
        ttk.Label(form_frame, text="Copyright:").grid(
            row=5, column=0, sticky=tk.W, pady=2
        )
        self.copyright_entry = ttk.Entry(form_frame, width=40)
        self.copyright_entry.grid(row=5, column=1, sticky=(tk.W, tk.E), pady=2)

        # Artist
        ttk.Label(form_frame, text="Artist:").grid(row=6, column=0, sticky=tk.W, pady=2)
        self.artist_entry = ttk.Entry(form_frame, width=40)
        self.artist_entry.grid(row=6, column=1, sticky=(tk.W, tk.E), pady=2)

        # Configure grid weights
        form_frame.columnconfigure(1, weight=1)

        # Buttons
        button_frame = ttk.Frame(right_frame)
        button_frame.pack(pady=10)

        self.save_btn = ttk.Button(
            button_frame, text="Save", command=self.save_metadata
        )
        self.save_btn.pack(side=tk.LEFT, padx=5)

        ttk.Button(button_frame, text="Clear", command=self.clear_form).pack(
            side=tk.LEFT, padx=5
        )

    def load_directory(self) -> None:
        """Load image files from directory."""
        self.image_files = [
            f
            for f in self.directory.iterdir()
            if f.is_file() and is_supported_format(f)
        ]
        self.image_files.sort()

        self.file_listbox.delete(0, tk.END)
        for img_file in self.image_files:
            self.file_listbox.insert(tk.END, img_file.name)

    def on_file_select(self, event: tk.Event) -> None:
        """Handle file selection."""
        selection = self.file_listbox.curselection()
        if not selection:
            return

        if self.batch_mode.get():
            # Batch mode: track selected files
            self.selected_files = {
                self.image_files[i] for i in selection
            }
            self.batch_apply_btn.config(
                state=tk.NORMAL if self.selected_files else tk.DISABLED
            )
        else:
            # Single file mode: load file
            selected_index = selection[0]
            self.select_file(self.image_files[selected_index])

    def select_file(self, file_path: Path) -> None:
        """Select and load a file.

        Parameters
        ----------
        file_path : Path
            Path to image file.
        """
        self.current_file = file_path
        self.load_preview(file_path)
        self.load_metadata(file_path)

    def load_preview(self, file_path: Path) -> None:
        """Load image preview.

        Parameters
        ----------
        file_path : Path
            Path to image file.
        """
        try:
            img = Image.open(file_path)
            # Resize for preview (max 400x400)
            img.thumbnail((400, 400), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)

            self.preview_label.config(image=photo, text="")
            self.preview_label.image = photo  # Keep a reference
        except Exception as e:
            self.preview_label.config(
                image="", text=f"Preview error: {e}"
            )

    def load_metadata(self, file_path: Path) -> None:
        """Load metadata into form.

        Parameters
        ----------
        file_path : Path
            Path to image file.
        """
        try:
            metadata = read_metadata(file_path)

            self.prompt_text.delete("1.0", tk.END)
            self.prompt_text.insert("1.0", metadata.prompt or "")

            self.model_entry.delete(0, tk.END)
            self.model_entry.insert(0, metadata.model or "")

            self.date_entry.delete(0, tk.END)
            self.date_entry.insert(0, metadata.date or "")

            self.description_text.delete("1.0", tk.END)
            self.description_text.insert("1.0", metadata.description or "")

            self.tags_entry.delete(0, tk.END)
            self.tags_entry.insert(0, ", ".join(metadata.tags) if metadata.tags else "")

            self.copyright_entry.delete(0, tk.END)
            self.copyright_entry.insert(0, metadata.copyright or "")

            self.artist_entry.delete(0, tk.END)
            self.artist_entry.insert(0, metadata.artist or "")

        except MetadataError as e:
            messagebox.showerror("Error", f"Failed to load metadata: {e}")

    def get_form_metadata(self) -> ImageMetadata:
        """Get metadata from form fields.

        Returns
        -------
        ImageMetadata
            Metadata from form.
        """
        tags_str = self.tags_entry.get().strip()
        tags = (
            [tag.strip() for tag in tags_str.split(",") if tag.strip()]
            if tags_str
            else []
        )

        return ImageMetadata(
            prompt=self.prompt_text.get("1.0", tk.END).strip(),
            model=self.model_entry.get().strip(),
            date=self.date_entry.get().strip() or None,
            description=self.description_text.get("1.0", tk.END).strip() or None,
            tags=tags,
            copyright=self.copyright_entry.get().strip() or None,
            artist=self.artist_entry.get().strip() or None,
            custom_fields={},
        )

    def save_metadata(self) -> None:
        """Save metadata to current file."""
        if not self.current_file:
            messagebox.showwarning("Warning", "No file selected")
            return

        try:
            metadata = self.get_form_metadata()
            write_metadata(self.current_file, metadata)
            messagebox.showinfo("Success", "Metadata saved successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save metadata: {e}")

    def batch_apply_metadata(self) -> None:
        """Apply metadata to selected files."""
        if not self.selected_files:
            messagebox.showwarning("Warning", "No files selected")
            return

        # Get metadata from form
        try:
            metadata = self.get_form_metadata()
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid metadata: {e}")
            return

        # Confirm
        if not messagebox.askyesno(
            "Confirm",
            f"Apply metadata to {len(self.selected_files)} file(s)?",
        ):
            return

        # Apply to all selected files
        success_count = 0
        for file_path in self.selected_files:
            try:
                write_metadata(file_path, metadata)
                success_count += 1
            except Exception as e:
                messagebox.showerror(
                    "Error", f"Failed to save {file_path.name}: {e}"
                )

        messagebox.showinfo(
            "Complete",
            f"Metadata applied to {success_count}/{len(self.selected_files)} file(s)",
        )

    def clear_form(self) -> None:
        """Clear all form fields."""
        self.prompt_text.delete("1.0", tk.END)
        self.model_entry.delete(0, tk.END)
        self.date_entry.delete(0, tk.END)
        self.description_text.delete("1.0", tk.END)
        self.tags_entry.delete(0, tk.END)
        self.copyright_entry.delete(0, tk.END)
        self.artist_entry.delete(0, tk.END)


def edit_metadata_gui(
    directory: Path,
    initial_file: Optional[Path] = None,
) -> None:
    """Launch GUI for metadata editing.

    Parameters
    ----------
    directory : Path
        Directory to browse.
    initial_file : Optional[Path]
        Initial file to select (if provided).
    """
    root = tk.Tk()
    app = MetadataGUI(root, directory, initial_file)
    root.mainloop()

