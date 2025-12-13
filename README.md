![build passes](https://github.com/Post45-Data-Collective/openrefine-reconciliation-service/actions/workflows/python-app.yml/badge.svg)

# BookReconciler 📘💎 — Metadata Enrichment and Work-Level Clustering

- **Who is this for?** Digital humanities researchers, librarians, metadata specialists, and more.
- **What does it do?** Finds, clusters, and enriches records for books. Adding ISBNS, HathiTrust IDs, subject headings, descriptions, page counts, publication dates, and more.

[![Watch the video](https://img.shields.io/badge/YouTube-Watch%20Demo-red?logo=youtube)](https://youtu.be/V9ZJoFowRJM)

[![YouTube Demo Video](images/youtube.png)](https://youtu.be/V9ZJoFowRJM)

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

Watch a YouTube demo/tutorial video here: https://youtu.be/V9ZJoFowRJM

## 1. Install OpenRefine

BookReconciler 📘💎 is designed to work with **OpenRefine**, an open-source tool for working with messy data.

1. Visit the [OpenRefine download page](https://openrefine.org/download).
2. Download the latest release for your operating system (Windows, macOS, or Linux).
3. Unzip the package (if needed) and follow the included instructions to start OpenRefine.
4. Once running, OpenRefine will be available at:  
   <http://127.0.0.1:3333/>

---

## 2. Install BookReconciler

Choose the installation method that works best for your system:

<details open>
<summary><b>Option 1: <img src="https://img.shields.io/badge/-MacOS-000000?logo=apple&logoColor=white" height="20"/> Mac or <img src="https://img.shields.io/badge/-Windows-0078D4?logo=windows&logoColor=white" height="20"/> Windows - One-Click Docker App</b></summary>

<br>

**Requirements:** Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) and make sure it's running.

#### <img src="https://img.shields.io/badge/-MacOS-000000?logo=apple&logoColor=white" height="20"/> Mac (Intel or Apple Silicon):

1. Download: [BookReconcilerApp.zip](https://github.com/Post45-Data-Collective/openrefine-reconciliation-service/releases/download/v0.2.0-beta.1/BookReconcilerApp.zip)
2. Unzip and double-click **BookReconcilerApp.app** to launch
3. Your browser will open to <http://127.0.0.1:5001/>

**Note:** You might get a security warning on first launch. Right-click the app and select **Open** → **Open** to bypass this message.

#### <img src="https://img.shields.io/badge/-Windows-0078D4?logo=windows&logoColor=white" height="20"/> Windows:

1. Download: [BookReconcilerApp.bat.zip](https://github.com/Post45-Data-Collective/openrefine-reconciliation-service/releases/download/v0.2.0-beta.1/BookReconcilerApp.bat.zip)
2. Unzip and double-click **BookReconcilerApp.bat** to launch
3. Your browser will open to <http://127.0.0.1:5001/>

Once launched, you can access:

- **Configuration interface:** <http://127.0.0.1:5001/>
- **OpenRefine endpoint:** <http://127.0.0.1:5001/api/v1/reconcile>

</details>

<details>
<summary><b>Option 2: Command Line with Docker</b></summary>

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
<summary><b>Option 3: Launch Your Own Server (Advanced)</b></summary>

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

- **Browser User Interface (for configuration):** <http://127.0.0.1:5001/>
- **OpenRefine endpoint:** <http://127.0.0.1:5001/api/v1/reconcile>

</details>

---

## 3. Use BookReconciler in OpenRefine

1. Open your dataset/project in OpenRefine.
2. Click a column you want to reconcile—for example, the book "title" column.
3. Choose **Reconcile → Start reconciling…**
   ![](images/start-reconciling.png)
4. Click **Add Standard Service**.
   ![](images/add-service.png)
5. Paste the service URL for BookReconciler, which will connect you with Library of Congress, Wikidata, Google Books, and more:

   ```
   http://127.0.0.1:5001/api/v1/reconcile
   ```

6. Select a reconciliation type (e.g., `LC_Work_Id`, `OCLC_Record`, `HathiTrust`, `VIAF_Personal`, `VIAF_Title`, `Wikidata_Title`).
7. Optionally, add "Additional Properties," like the book's author name, which may help improve match performance.
   ![](images/additional-properties.png)
8. Click **Start Reconciling**.
9. Wait for reconciliation to complete. This can take seconds to hours depending on the number of values. Then, inspect matches.
   ![](images/inspect.png)
10. Lastly, add new values—ISBNs, Subject Headings, Descriptions, etc.—based on matches. Select Edit Column -> Add columns from reconciled values...
    ![](images/add.png)
    Choose the values that you want to add from "Suggested Properties" (possible values are different for each service).
    ![](images/add-columns.png)
    They will be added to the spreadsheet.
    ![](images/new-values.png)

---

## Customize BookReconciler Behavior

Open <http://127.0.0.1:5001/> to adjust how BookReconciler matches, clusters, and writes back data. No code editing required.

### Book Title Matching

- **Single Match Mode**  
  Finds the _best single edition_ (manifestation) of a work.  
  Good when you care about a specific edition (e.g., a 1950 reprint).  
  Uses Title + Author (and Publication Year if available).

- **Cluster Match Mode**  
  Groups _all editions_ of the same **work** into a cluster (work-level).  
  Best for gathering as many identifiers as possible or studying works across editions.

### Extend Data Behavior (how identifiers are written back)

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

### Remove Subtitle from Titles

- **Keep Subtitles** — Titles remain as-is (e.g., _Moby-Dick: or, The Whale_).
- **Remove Subtitles** — Attempts to strip subtitles (e.g., _Moby-Dick_).

---

## Optional: OCLC / WorldCat API Keys

If you plan to use OCLC’s protected endpoints, you can input your API keys on the configuration page.

---

## Contributing

This project was inititally supported by an NEH grant that was cancelled in 2025. To grow and sustain this project, we welcome and encourage contributions from the broader community.

Feel free to add pull requests or get in touch if you have ideas. Please also note any issues or problems.

---

## License

This project is licensed under the **MIT License**. See the [`LICENSE`](LICENSE) file for details.

---
