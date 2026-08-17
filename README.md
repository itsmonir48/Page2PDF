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

---

## 🚀 How to Use It (User Guide)

If you are new to the application, here is how you use the Studio:

1. **Add Content:** 
   - Paste a web URL (like a GeeksforGeeks tutorial) into the input box and click **Add URL**.
   - Or, click **Upload Local PDF** to add an existing PDF from your laptop.
2. **Generate:** Once you've added all your links and files, click **Generate All PDFs**. 
3. **The Page Manager (Edit Mode):** 
   - You will be taken to a grid showing every page of your new PDF book.
   - **Delete:** Click a page to select it, then click "Remove Selected".
   - **Rotate:** Click the small rotation icon on any page thumbnail to spin it 90 degrees.
   - **Reorder:** Click and drag a page to move it to a different position.
   - **Insert:** Click the "+ Insert PDF/Image" button at the top to add a new file exactly where you need it (e.g. after Page 50).
4. **Download:** Click **Continue to Download** to get your final merged and edited PDF!

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
