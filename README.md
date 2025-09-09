![build passes](https://github.com/Post45-Data-Collective/openrefine-reconciliation-service/actions/workflows/python-app.yml/badge.svg)

# BookReconciler 📘💎 (0.2) — Metadata Enrichment and Work-Level Clustering

**BookReconciler 📘💎** is a tool that helps you reconcile and enrich bibliographic data from multiple library and knowledge sources:

1. **id.loc.gov** (Library of Congress)
2. **Google Books**
3. **OCLC / WorldCat**
4. **HathiTrust**
5. **VIAF** (Personal names and Works/Titles)
6. **Wikidata** (Works/Titles)

You can take a spreadsheet with only title and author information, and you can add identifiers like **ISBNs**, **OCLC numbers**, or **HathiTrust Volume IDs**, as well as valuable contextual information like Library of Congress **Subject Headings**, **genres**, **descriptions**, **page counts**, and **dates of first publicatio**n. Additionally, you can find and cluster different editions or manifestations of the same _Work_ (e.g., translations, reprints, etc.).

The tool currently works as an extension of the software application **[OpenRefine](https://openrefine.org/)**, which makes it accessible to those with and without computational experience. It includes a user-friendly, human-in-the-loop interface for manually evaluating matches, defining _Works_ (e.g., whether to include translations or not), and configuring the behavior of the service (e.g., matching all possible editions or just the best one).

The tool can also serve as a **bridge to computational text analysis**. A HathiTrust Volume ID can be used to computationally access the full text (for public domain works) or "bags of words" (for in-copyright works) for any text that is held by the HathiTrust Digital Library. This enable users to move from metadata to full computational text analysis.

- **Who is this for?** Digital humanities researchers, librarians, metadata specialists, and more!
- **What does it do?** Finds, clusters, and enriches records for books. Adding ISBNS, HathiTrust IDs, subject headings, descriptions, page counts, publication dates, and more.

## Installing OpenRefine

BookReconciler 📘💎 is designed to work with **OpenRefine**, an open-source tool for working with messy data.

1. Visit the [OpenRefine download page](https://openrefine.org/download).
2. Download the latest release for your operating system (Windows, macOS, or Linux).
3. Unzip the package (if needed) and follow the included instructions to start OpenRefine.
   - On macOS/Windows you can usually just double-click the launcher.
   - On Linux, run `./refine` from the extracted folder.
4. Once running, OpenRefine will be available at:  
   <http://127.0.0.1:3333/>

---

## BookReconciler Quick Start

The quickest way to get started with BookReconciler 📘💎 is to use Docker. If you don't have it installed already, install [Docker Desktop](https://www.docker.com/products/docker-desktop/), and then open Docker Desktop and make sure it's running.

## Download the App

Then download and unzip the BookReconciler App:

- <a href="BookReconcilerApp.zip" download="BookReconcilerApp.zip">BookReconciler App (Mac)</a>
- <a href="BookReconcilerApp.bat.zip" download="BookReconcilerApp.bat.zip">BookReconciler App (Windows)</a>

Double-click the app to launch it. When it’s ready, you can open your browser to <http://localhost:5001/> to access the configuration interface, or use the OpenRefine endpoint at <http://localhost:5001/api/v1/reconcile>.

## Run From the Command Line with Docker

You can also run Docker from the command line directly, which is a bit more flexible and works on any OS, as long as you have Docker installed.

```bash
git clone https://github.com/Post45-Data-Collective/openrefine-reconciliation-service.git
cd openrefine-reconciliation-service
docker compose up
```

---

## Launch Your Own Server

If you'd rather not use Docker, you can follow these steps.

## Requirements

- Python 3.10+
- macOS / Linux / Windows
- [OpenRefine](https://openrefine.org/) (see below)
- (Optional) OCLC API credentials if you plan to query WorldCat protected endpoints

### 1) Clone this GitHub repository

```bash
git clone https://github.com/<your-org-or-user>/openrefine-reconciliation-service.git
cd openrefine-reconciliation-service
```

### 2) Create a virtual environment (recommended but not required)

**macOS / Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows (PowerShell)**

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3) Install required packages

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4) Start the server, which runs the BookReconciler tool

```bash
# Tell Flask which app to run
export FLASK_APP=app.py          # Windows PowerShell: $env:FLASK_APP="app.py"

# Start BookReconciler on port 5001
flask run --host=0.0.0.0 --port=5001
# (Optional during development) add --debug to auto-reload on file changes:
# flask run --host=0.0.0.0 --port=5001 --debug
```

When it starts, the service will be available at:

- **Browser User Interface (for configuration):** <http://localhost:5001/>
- **OpenRefine endpoint:** <http://localhost:5001/api/v1/reconcile>

---

## Use with OpenRefine

1. Open your project in OpenRefine.
2. Click a column you want to reconcile.
3. Choose **Reconcile → Start reconciling…**
4. Click **Add Standard Service**.
5. Paste the service URL:

   ```
   http://localhost:5001/api/v1/reconcile
   ```

6. Select a reconciliation type (e.g., `LC_Work_Id`, `OCLC_Record`, `HathiTrust`, `VIAF_Personal`, `VIAF_Title`, `Wikidata_Title`).
7. Click **Start Reconciling**.

---

## Configure Behavior in the Browser

Open <http://localhost:5001/> to adjust how BookReconciler matches, clusters, and writes back data. No code editing required.

### 🔎 Title Matching Behavior

- **Single Match Mode**  
  Finds the _best single edition_ (manifestation) of a work.  
  Good when you care about a specific edition (e.g., a 1950 reprint).  
  Uses Title + Author (and Publication Year if available).

- **Cluster Match Mode**  
  Groups _all editions_ of the same **work** into a cluster (work-level).  
  Best for gathering as many identifiers as possible or studying works across editions.

### 🗂️ Extend Data Behavior (how identifiers are written back)

- **Join Mode** — all identifiers in one cell, separated by a pipe `|`.  
  Example:

  ```
  123456789 | 987654321 | 192837465 | 564738291
  ```

- **Row Mode** — each identifier in its own row.  
  Example:
  ```
  123456789
  987654321
  192837465
  564738291
  ```

### ✂️ Remove Subtitle from Titles

- **Keep Subtitles** — Titles remain as-is (e.g., _Moby-Dick: or, The Whale_).
- **Remove Subtitles** — Attempts to strip subtitles (e.g., _Moby-Dick_).

---

## Optional: OCLC / WorldCat API Keys

If you plan to use OCLC’s protected endpoints, you can input your API keys on the configuration page.

---

## Why This Matters

BookReconciler helps connect **library metadata** to **research data**:

- Link datasets to authoritative identifiers (ISBN, OCLC, VIAF, LCCN, Wikidata).
- Enrich corpora for literary, historical, or cultural analysis.
- Normalize titles to improve match quality.
- Analyze _works_ across multiple editions.

---

## Contributing

Issues and pull requests are welcome! If you have questions specific to DH workflows (work-level analysis, edition clustering, identifier coverage), please open an issue with a small sample of your data.

---

## License

This project is licensed under the **MIT License**. See the [`LICENSE`](LICENSE) file for details.

---
