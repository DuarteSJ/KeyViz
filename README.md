# Keyboard Visualizer

A PyQt6-based application for visualizing keyboard input in real-time. Features a modern, 3D-styled interface with the Nord color scheme.

## Features

- Real-time keyboard input visualization
- Custom keyboard layout editor
- Save and load keyboard layouts
- Modern 3D-styled keys with press animations
- Nord color scheme
- Multi-key selection and movement
- Key resizing with corner handles
- Support for custom key labels and bindings

## Requirements

- Python 3.8 or higher
- PyQt6
- evdev (for Linux keyboard input)
- sudo privileges (for keyboard monitoring)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/keyboard-visualizer.git
cd keyboard-visualizer
```

2. Create a virtual environment (optional but recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Linux/macOS
# or
venv\Scripts\activate  # On Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Start the application:
```bash
python -m keyboard_visualizer
```

2. When prompted, enter your sudo password to allow keyboard monitoring.

3. Use the editor mode to:
   - Click anywhere to add new keys
   - Drag keys to move them
   - Ctrl+Click to select multiple keys
   - Use corner handles to resize keys
   - Double-click keys to edit their label and binding
   - Right-click to delete keys

4. Click "Start Visualizer" to begin monitoring keyboard input.

5. Use "Save Layout" and "Load Layout" to persist your custom layouts.

## Project Structure

```
keyboard_visualizer/
├── core/               # Core functionality
│   ├── __init__.py
│   └── keyboard_manager.py
├── ui/                # User interface components
│   ├── __init__.py
│   ├── dialogs.py
│   ├── keyboard_canvas.py
│   ├── keyboard_key.py
│   └── main_window.py
├── utils/             # Utility functions
│   ├── __init__.py
│   └── sudo_helper.py
├── __init__.py
├── __main__.py
└── keyboard_helper.py
```

## License

MIT License 