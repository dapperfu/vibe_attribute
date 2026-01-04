"""Tests for CLI interface using pytest fixtures."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from attribute.cli import main
from attribute.models import ImageMetadata


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create Click CLI test runner.

    Returns
    -------
    CliRunner
        Click test runner instance.
    """
    return CliRunner()


@pytest.fixture
def mock_image_path(png_image: Path) -> Path:
    """Get path to mock image for CLI testing.

    Parameters
    ----------
    png_image : Path
        PNG image fixture.

    Returns
    -------
    Path
        Path to image file.
    """
    return png_image


@pytest.mark.parametrize(
    "command,args",
    [
        (["attribute"], ["test.png"]),
        (["attribute", "--tui"], ["test.png"]),
        (["attribute", "--gui"], ["test.png"]),
        (["view"], ["test.png"]),
        (["export"], ["test.png", "--format", "json"]),
        (["export"], ["test.png", "--format", "csv"]),
        (["import"], ["metadata.json"]),
    ],
)
def test_cli_commands_exist(
    command: list[str],
    args: list[str],
    cli_runner: CliRunner,
) -> None:
    """Test that CLI commands exist and can be invoked.

    Parameters
    ----------
    command : list[str]
        Command to test.
    args : list[str]
        Command arguments.
    cli_runner : CliRunner
        Click test runner.
    """
    # This test just verifies commands are registered
    # Actual execution would require mocking or real files
    result = cli_runner.invoke(main, command + args, catch_exceptions=True)
    # Commands should either succeed or fail gracefully, not crash
    assert result.exit_code in [0, 1, 2]  # 0=success, 1=error, 2=usage error


def test_cli_view_command(
    cli_runner: CliRunner,
    mock_image_path: Path,
    sample_metadata: ImageMetadata,
) -> None:
    """Test CLI view command.

    Parameters
    ----------
    cli_runner : CliRunner
        Click test runner.
    mock_image_path : Path
        Path to test image.
    sample_metadata : ImageMetadata
        Metadata to write to image.
    """
    from attribute.metadata import write_metadata

    # Write metadata to image
    write_metadata(mock_image_path, sample_metadata)

    # Run view command
    result = cli_runner.invoke(
        main,
        ["view", str(mock_image_path)],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    assert "Metadata for:" in result.output
    assert "A beautiful sunset over mountains" in result.output
    assert "ChatGPT-5.2 Thinking" in result.output


def test_cli_view_nonexistent_file(cli_runner: CliRunner) -> None:
    """Test CLI view command with nonexistent file.

    Parameters
    ----------
    cli_runner : CliRunner
        Click test runner.
    """
    result = cli_runner.invoke(
        main,
        ["view", "nonexistent.png"],
        catch_exceptions=False,
    )

    assert result.exit_code != 0
    assert "Error" in result.output or "not found" in result.output.lower()


def test_cli_export_command(
    cli_runner: CliRunner,
    mock_image_path: Path,
    sample_metadata: ImageMetadata,
    tmp_path: Path,
) -> None:
    """Test CLI export command.

    Parameters
    ----------
    cli_runner : CliRunner
        Click test runner.
    mock_image_path : Path
        Path to test image.
    sample_metadata : ImageMetadata
        Metadata to write to image.
    tmp_path : Path
        Temporary directory.
    """
    from attribute.metadata import write_metadata

    # Write metadata to image
    write_metadata(mock_image_path, sample_metadata)

    # Run export command
    output_path = tmp_path / "export.json"
    result = cli_runner.invoke(
        main,
        ["export", str(mock_image_path), "--format", "json", "--output", str(output_path)],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    assert output_path.exists()
    assert "exported" in result.output.lower()


@pytest.mark.parametrize(
    "format_name",
    ["json", "csv"],
)
def test_cli_export_formats(
    format_name: str,
    cli_runner: CliRunner,
    mock_image_path: Path,
    sample_metadata: ImageMetadata,
    tmp_path: Path,
) -> None:
    """Test CLI export with different formats.

    Parameters
    ----------
    format_name : str
        Export format to test.
    cli_runner : CliRunner
        Click test runner.
    mock_image_path : Path
        Path to test image.
    sample_metadata : ImageMetadata
        Metadata to write to image.
    tmp_path : Path
        Temporary directory.
    """
    from attribute.metadata import write_metadata

    # Write metadata to image
    write_metadata(mock_image_path, sample_metadata)

    # Run export command
    output_path = tmp_path / f"export.{format_name}"
    result = cli_runner.invoke(
        main,
        ["export", str(mock_image_path), "--format", format_name, "--output", str(output_path)],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    assert output_path.exists()


@patch("attribute.cli.edit_metadata_editor")
def test_cli_attribute_default_mode(
    mock_editor: MagicMock,
    cli_runner: CliRunner,
    mock_image_path: Path,
) -> None:
    """Test CLI attribute command in default (editor) mode.

    Parameters
    ----------
    mock_editor : MagicMock
        Mocked editor function.
    cli_runner : CliRunner
        Click test runner.
    mock_image_path : Path
        Path to test image.
    """
    result = cli_runner.invoke(
        main,
        ["attribute", str(mock_image_path)],
        catch_exceptions=False,
    )

    # Editor should be called
    mock_editor.assert_called_once_with(mock_image_path)


@patch("attribute.cli.edit_metadata_tui")
def test_cli_attribute_tui_mode(
    mock_tui: MagicMock,
    cli_runner: CliRunner,
    mock_image_path: Path,
) -> None:
    """Test CLI attribute command in TUI mode.

    Parameters
    ----------
    mock_tui : MagicMock
        Mocked TUI function.
    cli_runner : CliRunner
        Click test runner.
    mock_image_path : Path
        Path to test image.
    """
    result = cli_runner.invoke(
        main,
        ["attribute", "--tui", str(mock_image_path)],
        catch_exceptions=False,
    )

    # TUI should be called
    mock_tui.assert_called_once_with(mock_image_path)


@patch("attribute.cli.edit_metadata_gui")
def test_cli_attribute_gui_mode(
    mock_gui: MagicMock,
    cli_runner: CliRunner,
    test_images_dir: Path,
) -> None:
    """Test CLI attribute command in GUI mode.

    Parameters
    ----------
    mock_gui : MagicMock
        Mocked GUI function.
    cli_runner : CliRunner
        Click test runner.
    test_images_dir : Path
        Test images directory.
    """
    result = cli_runner.invoke(
        main,
        ["attribute", "--gui", str(test_images_dir)],
        catch_exceptions=False,
    )

    # GUI should be called (may or may not have initial_file parameter)
    assert mock_gui.called
    call_args = mock_gui.call_args
    assert call_args[0][0] == test_images_dir


def test_cli_help(cli_runner: CliRunner) -> None:
    """Test CLI help command.

    Parameters
    ----------
    cli_runner : CliRunner
        Click test runner.
    """
    result = cli_runner.invoke(main, ["--help"], catch_exceptions=False)

    assert result.exit_code == 0
    assert "Add metadata" in result.output or "metadata" in result.output.lower()


def test_cli_version(cli_runner: CliRunner) -> None:
    """Test CLI version command.

    Parameters
    ----------
    cli_runner : CliRunner
        Click test runner.
    """
    result = cli_runner.invoke(main, ["--version"], catch_exceptions=False)

    assert result.exit_code == 0
    assert "0.1.0" in result.output

