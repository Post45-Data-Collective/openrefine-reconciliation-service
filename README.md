![build passes](https://github.com/Post45-Data-Collective/openrefine-reconciliation-service/actions/workflows/python-app.yml/badge.svg)

# BookReconciler 📘💎 — Metadata Enrichment and Work-Level Clustering

- **Who is this for?** Digital humanities researchers, librarians, metadata specialists, and more.
- **What does it do?** Finds, clusters, and enriches records for books. Adding ISBNS, HathiTrust IDs, subject headings, descriptions, page counts, publication dates, and more.

[![YouTube Demo Video](images/youtube.png)](https://youtu.be/V9ZJoFowRJM)

[![Watch the video](https://img.shields.io/badge/YouTube-Watch%20Demo-red?logo=youtube)](https://youtu.be/V9ZJoFowRJM)

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

Watch a YouTube demo/tutorial Video here: https://youtu.be/V9ZJoFowRJM

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

Choose the installation method that works best for your system:

<details open>
<summary><b>Option 1: <img src="https://img.shields.io/badge/-MacOS-000000?logo=apple&logoColor=white" height="20"/> Mac (Apple Silicon M1/M2/M3) - Standalone App (No Docker Required!) ⭐ RECOMMENDED</b></summary>

<br>

**Easiest option for Apple Silicon Macs** - Download the DMG and you're ready to go:

1. Download [BookReconciler.dmg](https://github.com/Post45-Data-Collective/openrefine-reconciliation-service/releases/latest)
2. Open the DMG file
3. Drag BookReconciler.app to your Applications folder
4. Double-click BookReconciler.app to launch
5. Your browser will open to <http://localhost:5001/>

**No Python or Docker installation required!** The app includes everything you need.

Note: You might get a security warning on first launch. Right-click the app and select **Open** → **Open** to bypass this message.

</details>

<details>
<summary><b>Option 2: <img src="https://img.shields.io/badge/-MacOS-000000?logo=apple&logoColor=white" height="20"/> Mac (Intel) or <img src="https://img.shields.io/badge/-Windows-0078D4?logo=windows&logoColor=white" height="20"/> Windows - Docker App</b></summary>

<br>

If you have an Intel Mac or Windows, use the Docker-based apps:

**Requirements:** Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) and make sure it's running.

#### <img src="https://img.shields.io/badge/-MacOS-000000?logo=apple&logoColor=white" height="20"/> Mac (Intel or Apple Silicon):

- Download: [BookReconciler App (Automator)](https://github.com/Post45-Data-Collective/openrefine-reconciliation-service/releases/download/v0.2.0-beta.1/BookReconcilerApp.zip)
- Unzip and double-click to launch
- Note: Right-click → **Open** → **Open** if you get a security warning

#### <img src="https://img.shields.io/badge/-Windows-0078D4?logo=windows&logoColor=white" height="20"/> Windows:

- Download: [BookReconciler App (Batch file)](https://github.com/Post45-Data-Collective/openrefine-reconciliation-service/releases/download/v0.2.0-beta.1/BookReconcilerApp.bat.zip)
- Unzip and double-click the `.bat` file to launch

Once the app is launched, your browser should open to <http://localhost:5001/> where you can access the configuration interface, or you can use the OpenRefine endpoint at <http://localhost:5001/api/v1/reconcile>.

</details>

<details>
<summary><b>Option 3: Command Line with Docker</b></summary>

<br>

Works on any OS with Docker installed:

```bash
git clone https://github.com/Post45-Data-Collective/openrefine-reconciliation-service.git
cd openrefine-reconciliation-service
docker compose up
```

</details>

---

<details>
<summary><b>Option 4: Launch Your Own Server (Advanced)</b></summary>

<br>

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

</details>

---

## How to Use BookReconciler with OpenRefine

1. Open your dataset/project in OpenRefine.
2. Click a column you want to reconcile—for example, the book "title" column.
3. Choose **Reconcile → Start reconciling…**
4. Click **Add Standard Service**.
5. Paste the service URL for BookReconciler, which will connect you with Library of Congress, Wikidata, Google Books, and more:

   ```
   http://localhost:5001/api/v1/reconcile
   ```

6. Select a reconciliation type (e.g., `LC_Work_Id`, `OCLC_Record`, `HathiTrust`, `VIAF_Personal`, `VIAF_Title`, `Wikidata_Title`).
7. Optionally, add "Additional Properties," like the book's author name.
8. Click **Start Reconciling**.

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

## Contributing

Issues and pull requests are welcome! If you have questions specific to DH workflows (work-level analysis, edition clustering, identifier coverage), please open an issue with a small sample of your data.

---

## License

This project is licensed under the **MIT License**. See the [`LICENSE`](LICENSE) file for details.

---
