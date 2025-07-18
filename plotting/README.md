```markdown
# 🖼️ Image Grid Viewer & Exporter

A powerful Python application for visually comparing sets of images in a zoomable, scrollable grid with optional fullscreen viewing, HTML export, and PNG snapshot export. Ideal for machine learning model comparisons, batch image processing reviews, and dataset inspection.

## ✨ Features

- Compare multiple image sets in a dynamic grid layout
- Scroll and zoom with smooth navigation
- View images fullscreen with overlay info
- Export entire grid as a PNG or lazy-loading HTML gallery
- Handles missing images with placeholders
- Auto-scaling based on base image resolution

## 📁 Folder Structure

- **Base Folder**: Contains the reference images (1st row)
- **Subfolders Dir**: Contains subfolders named after each base image (e.g. `baseimg.png` → `subfolders/baseimg/`)
  - Each subfolder contains variants of the base image using identical filenames.

Example:
project/
├── base/
│   ├── image1.png
│   └── image2.png
└── subfolders/
    ├── image1/
    │   ├── a.png
    │   └── b.png
    └── image2/
        ├── a.png
        └── b.png
```

## 🧠 Requirements

- Python 3.8+
- `pygame`
- `pillow` (PIL)

Install requirements via:

```bash
pip install pygame pillow
```

## 🚀 Usage

```bash
python plotsoftware.py [base_folder] [subfolders_dir]
or
plotsoftware.exe and select base_folder and subfolder_dir from dialogs.
```

Or run without arguments to open folder selectors via Tkinter dialogs.

### Keyboard Shortcuts

- `Mouse Wheel`: Zoom in/out
- `Click and Drag`: Pan the view
- `Click`: Toggle fullscreen on a cell
- `E`: Export grid as PNG
- `H`: Export grid as HTML
- `Arrow Keys`: Scroll
- `0`: Reset zoom
- `Esc`: Exit fullscreen or quit
- `R`: Reload grid

## 📤 Export Options

### PNG Export

- Trigger via the `Export PNG (E)` button or `E` key
- Outputs a large PNG snapshot of the full grid

### HTML Export

- Trigger via the `Export HTML (H)` button or `H` key
- Generates a responsive `index.html` with lazy-loaded images for efficient sharing or inspection

## 🛠 Configuration

The script auto-calculates the default cell size based on the largest base image resolution to optimize viewing quality.

## ❗Notes

- Missing images are visually marked in red
- Designed for clarity in model/dataset comparisons
- Export progress is shown via an in-app progress bar

## 📄 License

MIT License
```