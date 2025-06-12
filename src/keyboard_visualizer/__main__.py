#!/usr/bin/env python3
import sys
import argparse
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from keyboard_visualizer.ui.main_window import MainWindow


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Keyboard Visualizer - A visual keyboard layout manager and sound feedback system",
        prog="keyboard-visualizer"
    )
    
    parser.add_argument(
        "-l", "--layout",
        type=str,
        help="Path to keyboard layout file to load on startup",
        metavar="FILE"
    )
    
    parser.add_argument(
        "-c", "--config",
        type=str,
        help="Path to configuration file",
        metavar="CONFIG"
    )
    
    return parser.parse_args()


def validate_file_path(file_path: str) -> Path:
    """Validate that the file path exists and is readable."""
    path = Path(file_path)
    
    if not path.exists():
        print(f"Error: File '{file_path}' does not exist.", file=sys.stderr)
        sys.exit(1)
    
    if not path.is_file():
        print(f"Error: '{file_path}' is not a file.", file=sys.stderr)
        sys.exit(1)
    
    if not path.suffix.lower() in ['.json', '.yaml', '.yml', '.toml']:
        print(f"Warning: '{file_path}' may not be a supported layout file format.")
    
    try:
        # Test if file is readable
        with open(path, 'r') as f:
            f.read(1)
    except PermissionError:
        print(f"Error: Permission denied reading '{file_path}'.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: Cannot read '{file_path}': {e}", file=sys.stderr)
        sys.exit(1)
    
    return path


def main():
    """Main entry point for the keyboard visualizer application."""
    args = parse_arguments()
    
    # Validate file path if provided
    layout_file = None
    if args.layout:
        layout_file = validate_file_path(args.layout)
    # Validate config file path
    config_file = None
    if args.config:
        config_file = validate_file_path(args.config)
    
    # Create QApplication
    app = QApplication(sys.argv)
    app.setApplicationName("Keyboard Visualizer")
    app.setApplicationVersion("0.1.0")
    app.setOrganizationName("KeyViz")
    
    # Create main window with optional file path
    try:
        print(args.config, args.layout)
        window = MainWindow(
            layout_path=layout_file,
            config_path=args.config,
        )
        window.show()
        
    except Exception as e:
        print(f"Error starting application: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Run the application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
