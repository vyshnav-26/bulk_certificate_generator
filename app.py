"""
app.py
------
Flask application for Bulk Certificate Generator.
Accepts a CSV or XLSX upload and returns a ZIP of individual PDF certificates.
"""

import io
import logging
import os
import re
import tempfile
import traceback
import zipfile

import pandas as pd
from flask import (Flask, flash, redirect, render_template,
                   request, send_file, url_for)

from certificate import make_certificate

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = Flask(__name__)
app.secret_key = "bulk-cert-gen-secret-2026"          # required for flash()
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024    # 5 MB upload limit

# ---------------------------------------------------------------------------
# Configuration constants
# ---------------------------------------------------------------------------
MAX_ROWS   = 500
ALLOWED    = {"csv", "xlsx"}
ID_PREFIX  = "CERT-2026-"
DEFAULT_ISSUER = "Department of AI & Data Science"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _allowed(filename: str) -> bool:
    """Return True if the file extension is in ALLOWED."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED


def _sanitize_filename(text: str) -> str:
    """
    Keep only letters, digits, spaces, hyphens, underscores.
    Then replace spaces with underscores.
    """
    safe = re.sub(r"[^\w\s\-]", "", text, flags=re.UNICODE)
    safe = re.sub(r"\s+", "_", safe.strip())
    return safe or "unknown"


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/", methods=["GET"])
def index():
    """Render the upload form."""
    return render_template("index.html")


@app.route("/sample", methods=["GET"])
def sample():
    """Serve the sample CSV file for download."""
    sample_path = os.path.join(app.root_path, "sample_data.csv")
    return send_file(
        sample_path,
        mimetype="text/csv",
        as_attachment=True,
        download_name="sample_data.csv",
    )


@app.route("/generate", methods=["POST"])
def generate():
    """
    Handle CSV/XLSX upload, generate one PDF per row, and return a ZIP.

    Steps:
      1. Validate file presence and extension.
      2. Parse with pandas; normalise column names.
      3. Validate required columns (name, course, date).
      4. Strip whitespace; drop blank-name rows; enforce MAX_ROWS.
      5. Create a temp directory.
      6. Generate one PDF per row with a unique CERT-ID.
      7. Write index.csv (manifest) into the temp dir.
      8. Zip everything into an in-memory buffer and return it.
    """

    # ------------------------------------------------------------------
    # Step 1 – Validate the uploaded file
    # ------------------------------------------------------------------
    if "file" not in request.files:
        flash("No file part in the request.", "danger")
        return redirect(url_for("index"))

    file = request.files["file"]

    if file.filename == "":
        flash("No file selected. Please choose a CSV or XLSX file.", "danger")
        return redirect(url_for("index"))

    if not _allowed(file.filename):
        flash(
            f"Unsupported file type '{file.filename}'. "
            "Please upload a .csv or .xlsx file.",
            "danger",
        )
        return redirect(url_for("index"))

    # ------------------------------------------------------------------
    # Step 2 – Read the file with pandas
    # ------------------------------------------------------------------
    try:
        ext = file.filename.rsplit(".", 1)[1].lower()
        if ext == "csv":
            df = pd.read_csv(file, dtype=str)
        else:
            df = pd.read_excel(file, dtype=str, engine="openpyxl")
    except Exception:
        flash("Could not read the file. Make sure it is a valid CSV or XLSX.", "danger")
        logger.error(traceback.format_exc())
        return redirect(url_for("index"))

    # Normalise column names: lowercase + strip whitespace
    df.columns = [str(col).strip().lower() for col in df.columns]

    # Fill NaN with empty string so comparisons work cleanly
    df = df.fillna("")

    # ------------------------------------------------------------------
    # Step 3 – Validate required columns
    # ------------------------------------------------------------------
    required = {"name", "course", "date"}
    missing = sorted(required - set(df.columns))
    if missing:
        flash(f"Missing columns: {', '.join(missing)}", "danger")
        return redirect(url_for("index"))

    # ------------------------------------------------------------------
    # Step 4 – Strip whitespace in all cells; drop rows with empty name
    # ------------------------------------------------------------------
    for col in df.columns:
        df[col] = df[col].astype(str).str.strip()

    df = df[df["name"] != ""]       # drop rows where name is blank

    if df.empty:
        flash("No valid rows found after removing entries with an empty name.", "danger")
        return redirect(url_for("index"))

    if len(df) > MAX_ROWS:
        flash(
            f"File contains {len(df)} rows, which exceeds the limit of {MAX_ROWS}. "
            "Please split your file and try again.",
            "danger",
        )
        return redirect(url_for("index"))

    # ------------------------------------------------------------------
    # Step 5 – Create temp directory
    # ------------------------------------------------------------------
    try:
        with tempfile.TemporaryDirectory() as tmp_dir:

            manifest_rows = []   # collect rows for index.csv

            # --------------------------------------------------------------
            # Step 6 – Generate one PDF per row
            # --------------------------------------------------------------
            for idx, (_, row) in enumerate(df.iterrows(), start=1):
                cert_id   = f"{ID_PREFIX}{idx:04d}"
                name      = row["name"]
                course    = row["course"]
                date      = row["date"]
                issuer    = row.get("issuer", "").strip() or DEFAULT_ISSUER

                # Build safe filename:  SanitizedName_CERT-2026-0001.pdf
                safe_name = _sanitize_filename(name)
                pdf_name  = f"{safe_name}_{cert_id}.pdf"
                pdf_path  = os.path.join(tmp_dir, pdf_name)

                make_certificate(
                    path=pdf_path,
                    name=name,
                    course=course,
                    date=date,
                    issuer=issuer,
                    cert_id=cert_id,
                )

                manifest_rows.append(
                    {
                        "cert_id":  cert_id,
                        "name":     name,
                        "course":   course,
                        "date":     date,
                        "filename": pdf_name,
                    }
                )

            # --------------------------------------------------------------
            # Step 7 – Write index.csv manifest
            # --------------------------------------------------------------
            index_path = os.path.join(tmp_dir, "index.csv")
            pd.DataFrame(manifest_rows).to_csv(index_path, index=False)

            # --------------------------------------------------------------
            # Step 8 – Zip everything into an in-memory buffer
            # --------------------------------------------------------------
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
                for fname in os.listdir(tmp_dir):
                    zf.write(
                        os.path.join(tmp_dir, fname),
                        arcname=fname,
                    )

            buf.seek(0)

            logger.info(
                "Generated %d certificate(s) successfully.", len(manifest_rows)
            )

            return send_file(
                buf,
                mimetype="application/zip",
                as_attachment=True,
                download_name="certificates.zip",
            )

    except Exception:
        logger.error("Certificate generation failed:\n%s", traceback.format_exc())
        flash(
            "An unexpected error occurred while generating certificates. "
            "Please check your file and try again.",
            "danger",
        )
        return redirect(url_for("index"))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)
