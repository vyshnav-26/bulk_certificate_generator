"""
certificate.py
--------------
PDF certificate drawing using ReportLab only (no template images or external fonts).
Built-in fonts used: Times-Bold, Times-Roman, Helvetica, Helvetica-Oblique.
"""

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape

from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.graphics import renderPDF


# ---------------------------------------------------------------------------
# Colour constants (RGB 0-1 scale)
# ---------------------------------------------------------------------------
CREAM_BG   = (1.0,   0.976, 0.925)   # #FFF9EC  – light cream background
DARK_BLUE  = (0.118, 0.227, 0.373)   # #1F3A5F  – outer border / title
GOLD       = (0.788, 0.635, 0.153)   # #C9A227  – inner border line
GOLD_BROWN = (0.545, 0.420, 0.059)   # #8B6B0F  – recipient name
BLACK      = (0.0,   0.0,   0.0)


def _set_fill(c: canvas.Canvas, rgb: tuple) -> None:
    """Helper: set fill colour from an (r, g, b) tuple."""
    c.setFillColorRGB(*rgb)


def _set_stroke(c: canvas.Canvas, rgb: tuple) -> None:
    """Helper: set stroke colour from an (r, g, b) tuple."""
    c.setStrokeColorRGB(*rgb)


def _auto_shrink(text: str, font_name: str, start_size: int,
                 max_width: float, min_size: int = 18) -> int:
    """
    Return the largest font size (>= min_size) such that the rendered
    string width does not exceed max_width points.
    """
    size = start_size
    while size > min_size and stringWidth(text, font_name, size) > max_width:
        size -= 1
    return size


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def make_certificate(path: str, name: str, course: str, date: str,
                     issuer: str, cert_id: str) -> None:
    """
    Draw a single A4 landscape PDF certificate and save it to *path*.

    Parameters
    ----------
    path     : Absolute or relative file path for the output PDF.
    name     : Recipient full name.
    course   : Course / programme title.
    date     : Completion date string (e.g. '15-06-2026').
    issuer   : Signing authority name.
    cert_id  : Unique identifier string (e.g. 'CERT-2026-0001').
    """

    PAGE_W, PAGE_H = landscape(A4)   # 842 x 595 pt
    CENTRE_X = PAGE_W / 2

    c = canvas.Canvas(path, pagesize=landscape(A4))

    # ------------------------------------------------------------------
    # 1.  Light cream background
    # ------------------------------------------------------------------
    _set_fill(c, CREAM_BG)
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)

    # ------------------------------------------------------------------
    # 2.  Double border
    #     Outer: 3 pt dark-blue, inset 20 pt
    #     Inner: 1 pt gold,      inset 30 pt
    # ------------------------------------------------------------------
    _set_stroke(c, DARK_BLUE)
    c.setLineWidth(3)
    c.rect(20, 20, PAGE_W - 40, PAGE_H - 40, fill=0, stroke=1)

    _set_stroke(c, GOLD)
    c.setLineWidth(1)
    c.rect(30, 30, PAGE_W - 60, PAGE_H - 60, fill=0, stroke=1)

    # ------------------------------------------------------------------
    # 3.  Title: "CERTIFICATE"  –  Times-Bold 48, dark blue, y=470
    # ------------------------------------------------------------------
    _set_fill(c, DARK_BLUE)
    c.setFont("Times-Bold", 48)
    c.drawCentredString(CENTRE_X, 470, "CERTIFICATE")

    # ------------------------------------------------------------------
    # 4.  Subtitle: "OF ACHIEVEMENT"  –  Helvetica 16, centred, y=440
    #     Simulate letter-spacing by inserting thin spaces between chars.
    # ------------------------------------------------------------------
    _set_fill(c, DARK_BLUE)
    c.setFont("Helvetica", 16)
    spaced = "  ".join("OF ACHIEVEMENT")       # visual letter-spacing trick
    c.drawCentredString(CENTRE_X, 440, spaced)

    # ------------------------------------------------------------------
    # 5.  "This is proudly presented to"  –  Helvetica-Oblique 14, y=390
    # ------------------------------------------------------------------
    _set_fill(c, BLACK)
    c.setFont("Helvetica-Oblique", 14)
    c.drawCentredString(CENTRE_X, 390, "This is proudly presented to")

    # ------------------------------------------------------------------
    # 6.  Recipient name  –  Times-Bold 40 (auto-shrink), gold-brown, y=335
    # ------------------------------------------------------------------
    name_size = _auto_shrink(name, "Times-Bold", 40, max_width=600)
    _set_fill(c, GOLD_BROWN)
    c.setFont("Times-Bold", name_size)
    c.drawCentredString(CENTRE_X, 335, name)

    # ------------------------------------------------------------------
    # 7.  Thin horizontal rule under name  –  width 400, centred, y=322
    # ------------------------------------------------------------------
    _set_stroke(c, DARK_BLUE)
    c.setLineWidth(0.75)
    rule_x = CENTRE_X - 200
    c.line(rule_x, 322, rule_x + 400, 322)

    # ------------------------------------------------------------------
    # 8.  "for successfully completing the course"  –  Helvetica-Oblique 14, y=290
    # ------------------------------------------------------------------
    _set_fill(c, BLACK)
    c.setFont("Helvetica-Oblique", 14)
    c.drawCentredString(CENTRE_X, 290, "for successfully completing the course")

    # ------------------------------------------------------------------
    # 9.  Course name  –  Times-Bold 26 (auto-shrink), dark blue, y=250
    # ------------------------------------------------------------------
    course_size = _auto_shrink(course, "Times-Bold", 26, max_width=600)
    _set_fill(c, DARK_BLUE)
    c.setFont("Times-Bold", course_size)
    c.drawCentredString(CENTRE_X, 250, course)

    # ------------------------------------------------------------------
    # 10. Date  –  Helvetica 13, bottom-left (x=90, y=95)
    # ------------------------------------------------------------------
    _set_fill(c, BLACK)
    c.setFont("Helvetica", 13)
    c.drawString(90, 95, f"Date: {date}")

    # ------------------------------------------------------------------
    # 11. Signature line at bottom-centre  –  160 pt line at y=100,
    #     issuer text in Helvetica 12 at y=82
    # ------------------------------------------------------------------
    sig_x = CENTRE_X - 80      # start of the 160-pt line
    _set_stroke(c, BLACK)
    c.setLineWidth(0.75)
    c.line(sig_x, 100, sig_x + 160, 100)

    _set_fill(c, BLACK)
    c.setFont("Helvetica", 12)
    c.drawCentredString(CENTRE_X, 82, issuer)

    # ------------------------------------------------------------------
    # 12. QR code  –  70x70 pt, bottom-right (x=680, y=60)
    #     cert_id text in Helvetica 9 centred under the QR box.
    # ------------------------------------------------------------------
    qr = QrCodeWidget(cert_id)
    bounds = qr.getBounds()
    qr_w = bounds[2] - bounds[0]
    qr_h = bounds[3] - bounds[1]

    d = Drawing(70, 70,
                transform=[70.0 / qr_w, 0, 0, 70.0 / qr_h, 0, 0])
    d.add(qr)
    renderPDF.draw(d, c, 680, 60)

    # Cert ID label under QR code
    _set_fill(c, BLACK)
    c.setFont("Helvetica", 9)
    c.drawCentredString(680 + 35, 52, cert_id)   # 680 + half of 70 = 715

    # ------------------------------------------------------------------
    # Finalise page
    # ------------------------------------------------------------------
    c.showPage()
    c.save()
