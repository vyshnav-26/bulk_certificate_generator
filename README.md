# Bulk Certificate Generator

A Flask web application that takes a CSV or XLSX spreadsheet of names, courses, and dates and produces one professionally styled PDF certificate per row, bundled into a single downloadable ZIP archive.

---

## Prerequisites

- Python **3.10+**
- `pip` and `venv` available in your PATH

---

## Setup

```bash
# 1. Navigate to the project folder
cd bulk_certificate_generator/certgen

# 2. Create a virtual environment
python -m venv venv

# 3. Activate the virtual environment
#    Windows (PowerShell)
.\venv\Scripts\Activate.ps1
#    Windows (Command Prompt)
venv\Scripts\activate.bat
#    macOS / Linux
source venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt
```

---

## Run

```bash
python app.py
```

The server starts at **http://127.0.0.1:5000** in debug mode.

---

## Usage

1. Open **http://127.0.0.1:5000** in your browser.
2. Click **"Download sample_data.csv"** to grab a ready-to-use example file.
3. Upload your own CSV or XLSX file (max **5 MB**, max **500 rows**).
4. Click **"Generate Certificates"** — a `certificates.zip` file will download automatically.
5. The ZIP contains:
   - One `<Name>_CERT-2026-XXXX.pdf` per row.
   - An `index.csv` manifest (cert_id, name, course, date, filename).

### Required columns

| Column   | Required? | Description                           |
|----------|-----------|---------------------------------------|
| `name`   | ✅ Yes    | Recipient's full name                 |
| `course` | ✅ Yes    | Course / programme title              |
| `date`   | ✅ Yes    | Completion date (e.g. `15-06-2026`)   |
| `issuer` | ❌ No     | Defaults to *Department of AI & Data Science* |

> Column names are **case-insensitive** and leading/trailing spaces are ignored.

---

## Certificate design

| Feature          | Detail                                          |
|------------------|-------------------------------------------------|
| Page size        | A4 Landscape (842 × 595 pt)                    |
| Fonts            | Times-Bold, Times-Roman, Helvetica (built-in)  |
| Unique ID        | `CERT-2026-0001` … `CERT-2026-NNNN`            |
| QR code          | Encodes the cert ID (bottom-right corner)       |
| Auto-shrink text | Name ≤ 600 pt (min 18 pt), course ≤ 600 pt     |

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError: reportlab` | Run `pip install reportlab` inside the venv |
| `ModuleNotFoundError: openpyxl` | Run `pip install openpyxl` inside the venv |
| Upload returns "413 Request Entity Too Large" | File exceeds the 5 MB limit — split your spreadsheet |
| QR codes are blank / missing | Ensure `reportlab >= 4.0` is installed |
| PowerShell says "script execution is disabled" | Run `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser` then re-activate the venv |
| `flask` command not found | Use `python app.py` instead of the `flask` CLI |
