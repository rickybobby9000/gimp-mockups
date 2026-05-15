# 👕 T-Shirt Mockup Creator Pro

A comprehensive GTK3 desktop application for creating professional t-shirt mockups with batch processing capabilities.

## ✨ Features

### Complete UI Specification Implementation
- **Top Bar**: App title, preset dropdown, save/load presets, settings
- **Left Panel (30%)**: Template loading, transform controls, displacement & blending engine
- **Center Panel (50%)**: Interactive canvas with pan/zoom, view toggles, quality selector
- **Right Panel (20%)**: Batch queue, processing status, export configuration
- **Bottom Bar**: Progress info, ETA, quick controls

### Core Functionality

#### Template & Workspace Setup
- Drag-and-drop template loading (PNG, JPG, PSD)
- Template thumbnail preview (120x120)
- Auto-mask toggle for alpha matte edges
- Template metadata display (resolution, color space, alpha channel)

#### Transform & Positioning
- X/Y position sliders and spin buttons (-1000 to 3000px)
- Scale control (10-200%)
- Lock aspect ratio toggle
- 9-point anchor grid selector (TL, TC, TR, ML, C, MR, BL, BC, BR)
- Reset transform button
- Apply to batch toggle for global locking

#### Displacement & Blending Engine
- Displacement X/Y controls (0-50, step 0.5)
- Displacement map source selector (Auto-generate or external)
- Map contrast slider (0-100)
- Blend modes: Normal, Multiply, Overlay, Soft Light, Screen, Linear Light
- Opacity control (0-100%)
- Displacement map preview overlay toggle

#### Canvas & Interactive Preview
- WebGL-style canvas with pan/zoom (scroll wheel)
- View toggles: Template, Preview, Disp Map, Grid, Snap
- Quality selector: Draft (Fast) vs Full (Accurate)
- Interactive graphic bounding box with drag support
- Real-time preview updates (150ms debounced)

#### Batch Queue & Processing
- Input folder picker with recursive scanning
- Format filter checkboxes (PNG, JPG, SVG, WebP)
- Concurrency control (1, 2, 4, Auto)
- Virtualized queue list with thumbnails and status
- Process All / Cancel button
- Progress bar with per-item tracking
- Collapsible status log with auto-scroll

#### Export Settings
- Output folder picker
- Format selection: PNG, JPG, WebP
- Quality slider for JPG/WebP (60-100)
- Naming template with tokens: `{original}`, `{index}`, `{date}`
- Live naming preview
- Flatten export toggle
- Open output folder on completion toggle

#### Preset System
- Save current settings as named presets
- Load presets from JSON files
- Default preset included
- Presets stored in `~/.tshirt_mockup/presets/`

## 🖼️ Transparency Handling

**IMPORTANT**: The application ensures the top graphic layer maintains full transparency in exports:

- PNG exports preserve the alpha channel completely
- The graphic is pasted using its own alpha channel as a mask
- PIL/Pillow backend uses: `result.paste(graphic_img, position, graphic_img)` where the third argument is the transparency mask
- JPG exports automatically composite onto white background (format limitation)
- WebP exports maintain transparency support

## 🚀 Installation

### Requirements
- Python 3.8+
- GTK3
- PyGObject
- Pillow (for export processing)

### Install Dependencies
```bash
pip install -r requirements.txt
```

### System Dependencies
```bash
# Ubuntu/Debian
sudo apt-get install python3-gi python3-gi-cairo gir1.2-gtk-3.0

# Fedora
sudo dnf install python3-gobject gtk3

# macOS (with Homebrew)
brew install gtk+3 pygobject3
```

## 🎮 Usage

### Launch Application
```bash
python3 tshirt_mockup_gui.py
```

### Basic Workflow
1. **Load Template**: Drag & drop a t-shirt mockup image or click the drop zone
2. **Load Graphic**: Drag & drop your design onto the canvas or use batch processing
3. **Adjust Transform**: Use sliders or drag the graphic directly on canvas
4. **Fine-tune Displacement**: Adjust X/Y values and contrast for realistic wrinkles
5. **Set Blend Mode**: Choose appropriate blend mode and opacity
6. **Configure Export**: Set output folder, format, and naming pattern
7. **Process**: Click "Process All" for batch or save individual mockups

### Keyboard Shortcuts
- **Scroll Wheel**: Zoom in/out on canvas
- **Drag Graphic**: Reposition on canvas
- **R**: Reset transform (via button)
- **Ctrl+S**: Save preset (via button)
- **Space**: Preview toggle (planned)

## 📁 File Structure
```
/workspace/
├── tshirt_mockup_gui.py    # Main GUI application
├── tshirt_mockup_cli.py    # CLI version (legacy)
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

## 🛠️ Technical Details

### State Management
- Centralized reactive state dictionaries for transform, displacement, blend, canvas, batch, and export
- All UI controls bound to state variables
- Bidirectional sync between UI and state

### Performance Optimizations
- Preview updates debounced at 150ms
- Downsampled displacement maps for draft quality
- Background threading for batch processing
- Virtualized queue list for large batches

### Export Pipeline
- PIL/Pillow based processing for cross-platform compatibility
- Optional GIMP Python-Fu integration (if available)
- Transparency preserved via alpha channel masking
- Multiple format support with quality controls

## 📝 Batch Processing

The batch processor:
1. Scans input folder recursively for matching file extensions
2. Applies current transform/displacement/blend settings to each graphic
3. Exports with configurable naming patterns
4. Shows real-time progress and ETA
5. Logs all operations with timestamps
6. Opens output folder on completion (optional)

### Naming Pattern Tokens
- `{original}`: Original filename without extension
- `{index}`: Zero-based index in batch queue
- `{date}`: Current date in YYYYMMDD format

Example: `{original}_mockup_{date}` → `design1_mockup_20240101.png`

## ⚠️ Notes

- GIMP integration is optional; app falls back to PIL/Pillow
- JPG format does not support transparency (white background applied)
- Large batches processed in background thread to keep UI responsive
- Displacement map generation is simplified in this version

## 📄 License

MIT License - See LICENSE file for details

## 🤝 Contributing

Contributions welcome! Please follow the UI specification for any new features.
