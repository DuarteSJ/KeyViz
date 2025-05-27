# Keyboard Visualizer

A customizable keyboard layout visualizer that allows you to create, save, and visualize keyboard layouts with real-time keypress detection.

## Features

- Create custom keyboard layouts by dragging and positioning keys
- Customize key labels and sizes
- Save and load keyboard configurations
- Real-time keypress visualization
- Support for any keyboard layout

## Installation

1. Clone this repository
2. Install the required dependencies:
```bash
pip install -r requirements.txt
```
3. Run the application:
```bash
python main.py
```

## Usage

1. **Editor Mode**:
   - Click "New Key" to create a new key
   - Drag keys to position them
   - Double-click a key to edit its label
   - Use the save button to store your configuration

2. **Visualizer Mode**:
   - Load a saved configuration
   - Keys will highlight when pressed
   - Press ESC to exit

## Note

This application requires root/admin privileges to detect keypresses system-wide. 