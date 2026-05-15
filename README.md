# T-Shirt Mockup Creator GUI

A GIMP 3.2 compatible GUI application for creating professional t-shirt mockups with live preview functionality.

## Features

- **Drag & Drop Interface**: Easily drag and drop t-shirt mockup images and graphics directly onto the canvas
- **Live Preview**: See real-time updates as you adjust position, scale, and rotation
- **Interactive Controls**:
  - Drag the graphic with your mouse to reposition it
  - Use scroll wheel to zoom in/out
  - Fine-tune with sliders for precise positioning
  - Rotate the graphic to any angle
- **GIMP Integration**: Uses GIMP Python-Fu when available, falls back to Pillow otherwise
- **Export**: Save your final mockup as a high-quality PNG

## Requirements

- Python 3.8+
- GTK+ 3.0 (for GUI version)
- PyGObject (GTK bindings for Python, for GUI version)
- Pillow (for image processing)
- GIMP 3.2+ with Python-Fu support (optional, for advanced processing in GUI version)

## Installation

### Install System Dependencies

**Ubuntu/Debian:**
```bash
sudo apt-get install python3-gi python3-gi-cairo gir1.2-gtk-3.0
sudo apt-get install gimp gimp-python3  # Optional, for GIMP integration
pip3 install Pillow
```

**Fedora/RHEL:**
```bash
sudo dnf install python3-gobject gtk3
sudo dnf install gimp gimp-devel-tools  # Optional, for GIMP integration
pip3 install Pillow
```

**macOS (with Homebrew):**
```bash
brew install gtk+3 pygobject3
pip3 install Pillow
# GIMP can be installed via: brew install --cask gimp (optional)
```

**Windows:**
```bash
# Install GIMP from https://www.gimp.org/downloads/ (optional)
# Then install Python packages:
pip install PyGObject Pillow
```

### Install Python Dependencies

```bash
pip install -r requirements.txt
```

## Usage

### GUI Version (Full Featured with Live Preview)

The GUI version provides a visual interface with live preview, drag-and-drop support, and interactive controls.

**Requirements:** GTK+ 3.0 and PyGObject must be installed.

```bash
python3 tshirt_mockup_gui.py
```

Or make it executable:

```bash
chmod +x tshirt_mockup_gui.py
./tshirt_mockup_gui.py
```

### CLI Version (Simple, No GUI Dependencies)

The command-line version works anywhere with just Pillow installed. Perfect for servers or systems without a display.

**Requirements:** Only Pillow is required.

```bash
python3 tshirt_mockup_cli.py
```

Or:

```bash
chmod +x tshirt_mockup_cli.py
./tshirt_mockup_cli.py
```

### Workflow (GUI Version)

1. **Load T-Shirt Mockup**: 
   - Click "Load T-Shirt Mockup" button, OR
   - Drag and drop a t-shirt image file onto the canvas

2. **Load Graphic**:
   - Click "Load Graphic" button, OR
   - Drag and drop a graphic/image file onto the canvas

3. **Adjust Position & Scale**:
   - **Drag** the graphic with your mouse to move it
   - **Scroll** up/down to zoom in/out
   - Use the **sliders** on the right panel for fine adjustments
   - Adjust **rotation** if needed

4. **Process & Export**:
   - Click "Process Mockup" button
   - Choose where to save your final image
   - The application will composite the graphic onto the t-shirt with your specified transformations

### Workflow (CLI Version)

1. Run `python3 tshirt_mockup_cli.py`
2. Enter the path to your t-shirt mockup image when prompted
3. Enter the path to your graphic image when prompted
4. Enter transformation parameters:
   - Scale factor (default: 1.0)
   - Rotation in degrees (default: 0)
   - X offset position (default: centered)
   - Y offset position (default: centered)
5. Enter output filename (or press Enter for default)
6. Your mockup will be saved!

## Tips

- **Best Results**: Use PNG files with transparency for graphics
- **High Quality**: Start with high-resolution t-shirt mockups for better output
- **Centering**: The graphic is automatically centered when first loaded
- **Reset**: Use the "Reset Position & Scale" button to start over
- **Precision**: Use both mouse dragging and sliders for precise positioning

## Troubleshooting

### "GIMP Python-Fu not available"
This is normal if GIMP is not installed or doesn't have Python-Fu support. The application will fall back to using Pillow for image processing, which works perfectly for most use cases.

### "No module named 'gi'"
Install PyGObject using your system package manager (see installation instructions above).

### Images won't load
Ensure your image files are in a supported format (PNG, JPG, GIF, etc.) and are not corrupted.

## File Structure

```
/workspace/
├── tshirt_mockup_gui.py    # Main GUI application (requires GTK+3)
├── tshirt_mockup_cli.py    # Command-line version (Pillow only)
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## License

This project is provided as-is for educational and practical use.

## Contributing

Feel free to modify and extend this application for your specific needs!
