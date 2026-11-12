"""
Printable ArUco corner markers for the RoboArm work cell.

    python make_markers.py                      # IDs 0-3, 100 mm, DICT_4X4_50 -> corner_markers.pdf
    python make_markers.py --size 120 --dict DICT_5X5_100 --ids 10 11 12 13

One marker per A4 page, with a cross through its centre so you can line it up
with lines you draw on the table. Print at 100% / "Actual size" and check the
50 mm scale bar with a ruler.

Layout (top view, robot base at the centre, "front" = where the arm points with
the base servo at its zero angle):

      ID3 back-left ........ ID0 front-left        +X = front
           .                      .                 +Y = arm's left
           .        (arm)         .
           .                      .
      ID2 back-right ....... ID1 front-right

Marker centres at (+B,+B) (+B,-B) (-B,-B) (-B,+B), default B = 360 mm.
Must match LAYOUT_DEFAULT in web/js/vision-math.js (or edit the table in the
Vision tab of the web app).
"""

import argparse

import cv2
import numpy as np

CORNERS = ["FRONT-LEFT", "FRONT-RIGHT", "BACK-RIGHT", "BACK-LEFT"]
SIGNS = [(1, 1), (1, -1), (-1, -1), (-1, 1)]
A4_W, A4_H = 210.0, 297.0
DPI = 300
PPM = DPI / 25.4


def page(dic, mid, size_mm, corner, B):
    w, h = int(A4_W * PPM), int(A4_H * PPM)
    img = np.full((h, w), 255, np.uint8)
    side = int(round(size_mm * PPM))
    cx, cy = w // 2, int(h * 0.45)
    img[cy - side // 2: cy - side // 2 + side, cx - side // 2: cx - side // 2 + side] = cv2.aruco.generateImageMarker(dic, mid, side)
    # centre cross lines (dashed, outside the marker) to align with lines on the table
    for x0, y0, x1, y1 in [(0, cy, cx - side // 2 - 20, cy), (cx + side // 2 + 20, cy, w, cy), (cx, 0, cx, cy - side // 2 - 20), (cx, cy + side // 2 + 20, cx, h)]:
        n = int(max(abs(x1 - x0), abs(y1 - y0)) // (8 * PPM)) + 1
        for k in range(n):
            a = k / n
            b = min(1, a + 0.6 / n)
            cv2.line(img, (int(x0 + (x1 - x0) * a), int(y0 + (y1 - y0) * a)), (int(x0 + (x1 - x0) * b), int(y0 + (y1 - y0) * b)), 120, 3)
    f = cv2.FONT_HERSHEY_SIMPLEX
    sx, sy = SIGNS[CORNERS.index(corner)]
    lines = [
        f"ID {mid}  -  {corner}",
        f"centre at X = {sx * B:+.0f} mm, Y = {sy * B:+.0f} mm from the base centre",
        "arrow = the arm's FRONT direction",
    ]
    for i, t in enumerate(lines):
        cv2.putText(img, t, (int(15 * PPM), int(h * 0.75) + int(i * 11 * PPM)), f, 2.0 if i == 0 else 1.5, 0, 4 if i == 0 else 3, cv2.LINE_AA)
    # arrow pointing to +X (front): top of the page = front
    ax, ay = int(w * 0.85), int(h * 0.12)
    cv2.arrowedLine(img, (ax, ay + int(30 * PPM)), (ax, ay), 0, 6, tipLength=0.3)
    cv2.putText(img, "FRONT", (ax - int(14 * PPM), ay + int(40 * PPM)), f, 1.4, 0, 3, cv2.LINE_AA)
    # 50 mm scale bar
    x0, y0 = int(15 * PPM), int(h * 0.93)
    cv2.line(img, (x0, y0), (x0 + int(50 * PPM), y0), 0, 5)
    for k in range(0, 51, 10):
        cv2.line(img, (x0 + int(k * PPM), y0 - int(4 * PPM)), (x0 + int(k * PPM), y0), 0, 3)
    cv2.putText(img, "50 mm - check with a ruler", (x0 + int(55 * PPM), y0), f, 1.3, 0, 3, cv2.LINE_AA)
    return img


def write_pdf(path, pages, mm_w, mm_h):
    pw, ph = mm_w / 25.4 * 72, mm_h / 25.4 * 72
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>", None]
    kids = []
    for img in pages:
        ok, jpg = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 95])
        jb = jpg.tobytes()
        content = f"q {pw:.3f} 0 0 {ph:.3f} 0 0 cm /Im0 Do Q".encode()
        n = len(objs) + 1
        kids.append(n)
        objs.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {pw:.3f} {ph:.3f}] /Resources << /XObject << /Im0 {n + 1} 0 R >> >> /Contents {n + 2} 0 R >>".encode())
        objs.append(f"<< /Type /XObject /Subtype /Image /Width {img.shape[1]} /Height {img.shape[0]} /ColorSpace /DeviceGray /BitsPerComponent 8 /Filter /DCTDecode /Length {len(jb)} >>\nstream\n".encode() + jb + b"\nendstream")
        objs.append(f"<< /Length {len(content)} >>\nstream\n".encode() + content + b"\nendstream")
    objs[1] = f"<< /Type /Pages /Kids [{' '.join(f'{k} 0 R' for k in kids)}] /Count {len(kids)} >>".encode()
    out = bytearray(b"%PDF-1.4\n")
    offs = []
    for i, o in enumerate(objs, 1):
        offs.append(len(out))
        out += f"{i} 0 obj\n".encode() + o + b"\nendobj\n"
    x = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode() + b"".join(f"{o:010d} 00000 n \n".encode() for o in offs)
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{x}\n%%EOF\n".encode()
    open(path, "wb").write(out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Generate the 4 ArUco corner markers")
    ap.add_argument("--ids", type=int, nargs=4, default=[0, 1, 2, 3], help="front-left front-right back-right back-left")
    ap.add_argument("--size", type=float, default=100, help="marker side in mm")
    ap.add_argument("--B", type=float, default=360, help="marker centres at (+-B, +-B) mm")
    ap.add_argument("--dict", default="DICT_4X4_50")
    ap.add_argument("--out", default="corner_markers")
    a = ap.parse_args()
    dic = cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, a.dict))
    pages = [page(dic, mid, a.size, CORNERS[i], a.B) for i, mid in enumerate(a.ids)]
    write_pdf(a.out + ".pdf", pages, A4_W, A4_H)
    cv2.imwrite(a.out + "_preview.png", cv2.resize(np.hstack(pages), None, fx=0.15, fy=0.15, interpolation=cv2.INTER_AREA))
    print(f"Wrote {a.out}.pdf ({len(pages)} pages, {a.size:.0f} mm markers, {a.dict}). Print at 100% scale.")
