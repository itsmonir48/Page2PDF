# Page2PDF Studio — User Guide

Page2PDF Studio turns webpages, PDFs and images into one clean, well-formatted PDF. You can merge sources, reorder and edit pages, add page numbers, a watermark or a password, and then download the result.

This guide covers every feature. If you only want the short version, read [Quick start](#quick-start).

---

## Contents

1. [Quick start](#quick-start)
2. [Feature overview](#feature-overview)
3. [Step 1 — Add your sources](#step-1--add-your-sources)
4. [PDF settings](#pdf-settings)
5. [Step 2 — Build the PDF](#step-2--build-the-pdf)
6. [Step 3 — Edit pages](#step-3--edit-pages)
7. [Insert more content](#insert-more-content)
8. [PDF index (bookmarks)](#pdf-index-bookmarks)
9. [Step 4 — Export and download](#step-4--export-and-download)
10. [Keyboard shortcuts](#keyboard-shortcuts)
11. [Limits and good to know](#limits-and-good-to-know)
12. [Troubleshooting](#troubleshooting)
13. [For self-hosters: configuration](#for-self-hosters-configuration)

---

## Quick start

1. Open the app (for example `http://localhost:8000`).
2. Paste a link into the box and press **Enter**. To add several links, paste a whole list at once. You can also click **Upload PDFs or images**.
3. Click **Build PDF**.
4. On the **Edit pages** screen, remove or reorder pages if you want, then click **Continue to export**.
5. Choose a file name and click **Download PDF**.

---

## Feature overview

| Area | What you can do |
|---|---|
| **Sources** | Add webpage links, PDFs and images (PNG, JPG, WEBP). Paste many links at once. Drag and drop files or links onto the card. Reorder or remove sources. |
| **Clean extraction** | Ads, pop-ups, navigation and sidebars are removed. Images are embedded and code blocks are syntax-highlighted. Pages that need JavaScript are rendered in a real browser as a fallback. |
| **Layout settings** | Page size (A4 / Letter), font size, font family, include or exclude images, links and code blocks, and a clickable contents page. |
| **Merging** | All sources are merged in your order, with an optional cover page and separator pages between sources. |
| **Page editor** | See every page as a thumbnail. Select, remove, keep only, rotate, duplicate, reverse and drag to reorder. Undo/redo, select by range, full-size preview and keyboard shortcuts. |
| **Insert** | Insert another PDF, image or webpage at the start, at the end or after any page. |
| **Index** | Keep automatic bookmarks, write your own (with a linked contents page), or remove them all. |
| **Export options** | Page numbers (three positions), a diagonal watermark, author metadata and an AES-256 password. |
| **Download** | Live preview, custom file name, **Save as…** (in supported browsers) and download of each source as its own PDF. |
| **Comfort** | Light and dark themes, settings remembered on your device, and a warning before you leave the page with unsaved work. |
| **Safety** | Links to private networks and `localhost` are blocked, uploads are size-limited, and invalid or password-protected uploads are rejected. |

---

## Step 1 — Add your sources

A *source* is one webpage, PDF or image. Sources are merged in the order shown in the list.

### Add webpage links

- Paste a link into the box and press **Enter** or click **Add**.
- **Several links at once:** paste a list (one per line, or separated by spaces or commas). Every link in it is added.
- You can type `example.com/page` without `https://`; it is added automatically.
- While a link is being added, it shows *Fetching page title…*. This can take a few seconds per link.
- The **Try:** chips under the card fill in example links.

> Only **public** pages work. Pages behind a login or paywall, and addresses on private networks (such as `localhost` or `192.168.x.x`), are rejected.

### Upload files

- Click **Upload PDFs or images**, or drag files from your computer anywhere onto the card.
- Supported formats: **PDF, PNG, JPG/JPEG, WEBP**.
- Images are placed on their own A4 page and scaled to fit.
- Password-protected PDFs are rejected. Remove the password first.

### Manage the list

| Action | How |
|---|---|
| Reorder | Drag a row by its handle (⋮⋮), or use the ↑ / ↓ buttons |
| Remove | Click the 🗑 button. A link can be restored with **Undo** in the message that appears |
| Remove everything | **Clear all** (above the list) |

The icon on each row shows the source type: the site's first letter for links, **PDF** for PDF files and **IMG** for images.

---

## PDF settings

Click **PDF settings** under the source list to open them. Everything except the title is remembered on your device for next time.

| Setting | Meaning |
|---|---|
| **Title** | Name of the final document. Used on the cover page, in the PDF metadata and as the default file name. |
| **Author** | Stored in the PDF's metadata. |
| **Page size** | A4 or Letter (applies to webpages; uploaded PDFs keep their own size). |
| **Font size / Font family** | Text style for converted webpages. |
| **Images / Links / Code blocks** | Turn these parts of webpages on or off. |
| **Contents page** | Adds a clickable table of contents as the first page. |
| **Cover page** | Adds a title page at the start of the merged PDF. |
| **Source separators** | Adds a page before each source showing its title and link. |

Change settings **before** you click **Build PDF**. They apply to that build.

---

## Step 2 — Build the PDF

Click **Build PDF**. A step bar at the top shows where you are: **Build → Edit pages → Export**.

- Each source shows its own status: *Fetching page…*, *Extracting content…*, *Rendering PDF…*, then **Ready**.
- The ring shows overall progress.
- When all sources are ready, they are merged automatically and the page editor opens.

### If some sources fail

The reason is shown under that source (for example, *No meaningful article content was found*). You can:

- click **Retry** next to a failed source,
- click **Continue with the rest** to build without the failed ones, or
- click **Back to sources** to change the list and build again.

---

## Step 3 — Edit pages

Every page of the merged PDF is shown as a thumbnail.

### Reading the thumbnails

- The large number under a page is its **position in the final PDF**.
- **was p.N** means the page has moved. N is its original position.
- A **90° / 180° / 270°** badge means the page will be rotated.
- Greyed-out pages marked **Removed** will not be in the final PDF.

### Selecting pages

| Do this | Result |
|---|---|
| Click a page | Select or deselect it |
| **Shift + click** | Select every page between the last click and this one |
| **Select all** | Select all pages (click again to select none) |
| Type a range and click **Select** | Select those pages, e.g. `1-5, 8, 10-` |
| **Esc** | Clear the selection |

**Range format:** numbers and ranges separated by commas. `10-` means "page 10 to the end". Numbers refer to the positions shown in the grid, counting removed pages too.

### Changing pages

| Button | What it does |
|---|---|
| **Remove** | Mark selected pages as removed. If they are all removed already, it restores them. |
| **Keep only** | Keep the selected pages and remove all others. |
| **Rotate** | Rotate selected pages 90° clockwise (press again for 180°, 270°). |
| **Duplicate** | Insert a copy right after each selected page. |
| **Reverse** | Reverse the order of all pages. |
| **Reset** | Undo every change made since the last time changes were applied. |
| **Keep** (next to the range box) | Keep only the pages in the range. |
| **↶ / ↷** | Undo / redo. |

Each thumbnail also has its own buttons when you hover over it (always visible on phones): 🔍 **preview**, ⟳ **rotate** and 🗑 **remove/restore**.

### Reordering

Drag a page and drop it before or after another page. A coloured line shows where it will go. If you drag a **selected** page, all selected pages move together.

> On phones and tablets, drag-and-drop is not available yet. Use **Reverse**, or **Keep only** plus **Insert**, instead.

### Preview a page

Double-click a page, or click its 🔍 button, to see it full size. Use **← / →** or the arrow buttons to move between pages, and **Esc** to close.

### Thumbnail size

Use the slider in the toolbar (grid icon) to make thumbnails bigger or smaller. Your choice is remembered.

### Applying changes

Changes are only a plan until you apply them. While anything is unapplied, you will see **● Unapplied changes**, and the main button reads **Apply & continue**. Click it to apply your edits and go to export.

Opening **Insert** or **Index** also applies pending changes first, so page numbers always match what you see.

---

## Insert more content

Click **Insert** in the toolbar to add content to the PDF you are editing.

1. Choose **one** of:
   - a **file** (PDF or image) — click the box or drop a file on it, **or**
   - a **webpage link** — it is converted with default settings (A4, medium text, images, links and code included).
2. Choose the **Position**: *At the end*, *At the beginning*, or *After page…* and enter a page number.
3. Click **Insert**.

The new pages appear in the grid straight away.

---

## PDF index (bookmarks)

The *index* is the list of clickable bookmarks that PDF readers show in their sidebar. Click **Index** in the toolbar.

| Mode | What happens |
|---|---|
| **Automatic** | Uses the headings and bookmarks found in your sources. |
| **Manual** | You write the entries yourself. A clickable **Contents** page is added at the front and linked to them. |
| **Off** | Removes all bookmarks and the contents page. |

### Manual format

One entry per line:

```
Title | page | level
```

- **page** is the page number in the current PDF (as shown in the editor).
- **level** is optional: `1` = chapter (default), `2` = section, `3` = sub-section.

Example:

```
Introduction | 2
Chapter 1: Classes | 3
Inheritance | 5 | 2
Chapter 2: Modules | 9
```

Because a contents page is inserted at the front, the page count goes up, and your entries still point to the right pages.

---

## Step 4 — Export and download

The export screen shows a **live preview** of the PDF on the left. If your browser can't show PDFs inline, use **Open preview in a new tab**.

On the right you'll find:

- **Sources / Pages / Size** of the document.
- **File name** — the name for the downloaded file (`.pdf` is added for you).

### Export options

Open **Export options** to finish the document. These are applied only to the downloaded copy, so your editable pages are never changed.

| Option | Details |
|---|---|
| **Page numbers** | Printed as `3 / 12`. Choose *Bottom centre*, *Bottom right* or *Top right*. **Skip first page** leaves the cover/contents page unnumbered. |
| **Watermark** | Light diagonal text on every page, e.g. `DRAFT` or your name (up to 60 characters). |
| **Password** | Encrypts the PDF with AES-256. Anyone opening the file needs this password. **Don't forget it — it cannot be recovered.** |

Click **Apply export options** to update the preview. If you forget, the options are applied automatically when you click **Download PDF**.

> When a password is set, the preview shows the unprotected working copy so it can be displayed. The **downloaded** file is the protected one.

To remove all options, turn them off, clear the fields and click **Apply export options** again.

### Download buttons

| Button | What it does |
|---|---|
| **Download PDF** | Downloads the final PDF. |
| **Save as…** | Lets you choose the folder and name. Only shown in browsers that support it (Chrome, Edge, Opera). |
| **Edit pages** | Goes back to the page editor. Any later edit clears the export options, so apply them again afterwards. |
| **Individual PDFs** | When you used 2+ sources, download each one as its own PDF. |
| **Start a new collection** | Clears everything and returns to the start. Download first! |

---

## Keyboard shortcuts

These work on the **Edit pages** screen when you are not typing in a box.

| Keys | Action |
|---|---|
| `Click` | Select / deselect a page |
| `Shift` + `Click` | Select a range |
| `Ctrl` + `A` | Select all / none |
| `Delete` or `Backspace` | Remove selected (press again to restore) |
| `R` | Rotate selected |
| `D` | Duplicate selected |
| `Ctrl` + `Z` | Undo |
| `Ctrl` + `Shift` + `Z` or `Ctrl` + `Y` | Redo |
| `Double-click` | Open page preview |
| `←` / `→` | Previous / next page in the preview |
| `Esc` | Clear selection, or close a dialog |

On macOS, use `Cmd` instead of `Ctrl`. The list is also available in the app under **shortcuts**.

---

## Limits and good to know

- **Up to 20 sources** per collection and **50 MB per uploaded file** (defaults; the server owner can change these).
- **Your work lives on the server only while the session is active.** If the server restarts, the collection is gone. Download your PDF when you're done. The browser warns you before you close the page with work in progress.
- Sources are processed **one after another**, so a long list of links takes longer.
- Some websites block automated access, or load their content in ways that can't be extracted. Try a different page or print it to PDF and upload it.
- **Theme:** the ☾/☀ button in the top bar switches between light and dark. By default the app follows your system setting.

---

## Troubleshooting

| Problem | What to try |
|---|---|
| *Access to this host is not allowed* | The link points to a private or local address. Only public websites are supported. |
| *No meaningful article content was found* | The page has little readable text, or needs a login. Try another page, or save it as PDF in your browser and upload that. |
| *This URL has already been added* | Each link can only be in the list once. |
| *File is larger than 50 MB* | Compress or split the file first. |
| *Password-protected PDFs can't be edited* | Open the PDF, remove its password, then upload it again. |
| *This session has expired* | The server was restarted. Click **Start a new collection** and add your sources again. |
| Preview is blank | Your browser can't display PDFs inline. Use **Open preview in a new tab** or just download. |
| **Save as…** button is missing | Your browser doesn't support it. Use **Download PDF**. |

---

## For self-hosters: configuration

Copy `.env.example` to `.env` and adjust these values. See the [README](../README.md) for installation.

| Variable | Default | Purpose |
|---|---|---|
| `APP_HOST` / `APP_PORT` | `0.0.0.0` / `8000` | Address the server listens on |
| `MAX_URLS_PER_COLLECTION` | `20` | Maximum sources per collection |
| `MAX_UPLOAD_SIZE_MB` | `50` | Maximum size of one uploaded file |
| `MAX_PAGE_SIZE_MB` | `20` | Maximum size of a fetched webpage |
| `REQUEST_TIMEOUT` | `30` | Seconds to wait for a webpage |
| `MAX_REDIRECTS` | `5` | Redirects followed when fetching |
| `MAX_IMAGE_SIZE_MB` | `5` | Largest image embedded from a webpage |
| `MAX_IMAGES_PER_PAGE` | `50` | Images embedded per webpage |
| `ENABLE_PLAYWRIGHT` | `true` | Use a headless browser for JavaScript-heavy pages (requires `playwright install chromium`) |
| `OUTPUT_DIR` | `output` | Where generated PDFs are stored |
| `PDF_RETENTION_HOURS` | `1` | Files older than this are deleted when the server starts |

> Note: old files are currently cleaned up **only at server start-up**. On a long-running server, clear `OUTPUT_DIR` periodically (for example with a cron job).

### HTTP API

The app is built on a JSON API under `/api/collections`, and FastAPI's interactive documentation is available at **`/docs`** while the server is running. The main flow is:

```
POST   /api/collections                         create a collection
POST   /api/collections/{id}/urls               add a link            {"url": "..."}
POST   /api/collections/{id}/upload             upload a file         (multipart "file")
POST   /api/collections/{id}/generate           convert all sources   (layout settings)
GET    /api/collections/{id}/status             poll progress
POST   /api/collections/{id}/merge              merge into one PDF
POST   /api/collections/{id}/edit-pages         {"keep_pages": [...], "rotations_by_position": [...]}
POST   /api/collections/{id}/insert-file        insert a file or link (multipart)
POST   /api/collections/{id}/edit-index         bookmarks
POST   /api/collections/{id}/finalize           page numbers / watermark / password
GET    /api/collections/{id}/download           ?custom_filename=&inline=1
```
