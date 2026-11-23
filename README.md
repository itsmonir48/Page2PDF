# Page2PDF Studio

**Turn Any Webpage Into a Clean PDF & Professional PDF Editing Workspace**

Page2PDF Studio is a complete web application that not only converts public educational webpages into beautifully formatted PDFs, but also acts as a full-featured PDF editor. You can upload existing PDFs, merge them with web articles, insert images, rotate pages, reorder pages with drag-and-drop, and delete unwanted pages before exporting the final document.

Built for students, researchers, programmers, and anyone who builds customized study materials.

---

## 🔥 Key Features

1. **Web to PDF Conversion** — Paste multiple URLs to extract their content into clean PDFs (removes ads and clutter).
2. **Local File Uploads** — Upload your own existing PDFs or Images directly into the workspace.
3. **Smart Merging** — Automatically generates a Table of Contents and Cover Page for merged documents.
4. **Drag & Drop Reordering** — Visually drag thumbnail pages to reorder your entire PDF book.
5. **Page Manipulation** — Rotate individual pages, delete ranges of pages, or insert new files directly in the middle of a document.
6. **Code & Math Support** — Preserves syntax highlighting for code blocks and handles complex HTML structures.
7. **Bulk Links** — Paste a whole list of URLs at once; drop files or links anywhere on the workspace card.
8. **Visual Page Editor** — Multi-select (Shift+Click), duplicate, reverse, rotate, undo/redo and keyboard shortcuts.
9. **Export Options** — Stamp page numbers, add a watermark, set the author and protect the PDF with an AES-256 password.
10. **Live Preview & Themes** — Preview the final PDF before downloading; light and dark themes; settings are remembered.

---

## 🚀 How to Use It

> 📖 **Full manual:** see the **[User Guide](docs/USER_GUIDE.md)** for every feature, keyboard shortcuts, limits and troubleshooting.

1. **Add sources** — Paste a link and press **Enter** (paste a whole list to add many at once), or click **Upload PDFs or images**. You can also drag files onto the card. Reorder with drag-and-drop or the ↑/↓ buttons.
2. **Adjust settings (optional)** — Open **PDF settings** for title, author, page size, fonts, contents page, cover page and separators.
3. **Build** — Click **Build PDF**. Each source shows its progress; failed ones can be retried or skipped.
4. **Edit pages** — Click pages to select them (Shift+Click for a range), then **Remove**, **Keep only**, **Rotate**, **Duplicate** or **Reverse**. Drag to reorder, use **Insert** to add more files or links, and **Index** for bookmarks. Undo/redo is available.
5. **Export** — Click **Apply & continue**, preview the PDF, optionally add **page numbers**, a **watermark** or a **password**, choose a file name and click **Download PDF**.

---

## 🚀 Live Demo

Don't want to install anything? Use the live hosted version of the app here:

👉 **[Click Here to Use Page2PDF Studio](https://page2pdf.onrender.com)**

---

## 💻 Run it Locally (For Developers)

If you prefer to clone the repository and run it locally on your own machine, you can do so using Docker or manual installation.

### Option 1: The Easiest Way (Using Docker)

If you have Docker installed on your computer, you don't need to manually configure dependencies.

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/page2pdf.git
cd page2pdf

# 2. Build and run the Docker container
docker build -t page2pdf .
docker run -p 8000:8000 page2pdf
```
Open **http://localhost:8000** in your browser to use the app!

---

### Option 2: Manual Local Setup (Linux / macOS)

If you wish to modify the code locally, ensure you have Python 3.10+ and the required system libraries.

**1. Install System Dependencies (For PDF Rendering)**
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install libpango-1.0-0 libcairo2 libgdk-pixbuf2.0-0 libffi-dev

# macOS
brew install pango cairo libffi
```

**2. Setup Python Environment**
```bash
cd page2pdf
python -m venv venv
source venv/bin/activate  # Or `venv\Scripts\activate` on Windows

pip install -r requirements.txt
cp .env.example .env
```

**3. Install Playwright (For rendering JavaScript-heavy websites)**
```bash
playwright install chromium
```

**4. Run the Server**
```bash
python run.py
```
Open **http://localhost:8000** in your browser.

---

## 🏗️ Technology Stack

- **Backend:** Python, FastAPI, Uvicorn
- **PDF Engine:** PyMuPDF (fitz) for editing/merging, WeasyPrint for HTML-to-PDF
- **Web Scraping:** Trafilatura, BeautifulSoup4, Playwright
- **Frontend:** HTML5, Vanilla CSS3, Vanilla JavaScript

## 🔒 Security

- **SSRF Protection** — Blocks requests to private IPs and localhost during URL fetching.
- **Resource Limits** — Enforces max file sizes and timeouts to prevent server crashes.
- **Path Traversal Prevention** — Safely generates randomized filenames for all uploads.

## 📄 License
This project is for educational and personal use.
