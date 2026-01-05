import os
import cv2
import json
import pandas as pd
from datetime import datetime
from pyzbar.pyzbar import decode

DB = pd.read_excel("products.xlsx")
SCANNED_FILE = "scanned.json"

def combine_features(has_buckle: bool, has_armrest: bool) -> int:
    if has_buckle and has_armrest:
        return 2
    elif has_buckle and not has_armrest:
        return 1
    elif not has_buckle and has_armrest:
        return 3
    else:
        return 4


def _append_scan_to_json(raw_code: str, result_code: int | None) -> None:
    """Sla elke scan op in scanned.json."""
    entry = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "raw_code": raw_code,
        "result_code": result_code,
    }

    data = []
    if os.path.exists(SCANNED_FILE):
        try:
            with open(SCANNED_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = []

    data.append(entry)

    with open(SCANNED_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _detect_qr_or_barcode(frame) -> str | None:
    """Zoek QR of barcodes in een frame, geef de eerste payload terug."""
    # QR eerst
    detector = cv2.QRCodeDetector()
    data, points, _ = detector.detectAndDecode(frame)

    if points is not None and len(points) > 0 and data:
        pts = points[0].astype(int)
        x_min, y_min = pts[:, 0].min(), pts[:, 1].min()
        x_max, y_max = pts[:, 0].max(), pts[:, 1].max()
        cv2.rectangle(frame, (x_min, y_min), (x_max, y_max), (0, 255, 0), 2)
        return data.strip()

    # Dan barcodes (pyzbar)
    barcodes = decode(frame)
    for bc in barcodes:
        x, y, w, h = bc.rect
        cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)
        try:
            text = bc.data.decode("utf-8").strip()
        except Exception:
            text = str(bc.data)
        if text:
            return text

    return None


def scan_qr_with_camera():
    """Scan QR + barcode, zoek product in DB en log naar scanned.json."""
    cap = cv2.VideoCapture(0)
    qr_data = None

    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        qr_data = _detect_qr_or_barcode(frame)
        if qr_data:
            cv2.putText(
                frame,
                qr_data,
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.0,
                (0, 255, 0),
                2,
            )
            cv2.imshow("QR/Barcode Scanner", frame)
            cv2.waitKey(500)
            break

        cv2.imshow("QR/Barcode Scanner", frame)
        if cv2.waitKey(1) & 0xFF == 27:  # ESC
            break

    cap.release()
    cv2.destroyAllWindows()

    if not qr_data:
        _append_scan_to_json("", None)
        return None

    product = DB[DB["Code"] == qr_data]
    if product.empty:
        _append_scan_to_json(qr_data, None)
        return None

    row = product.iloc[0]
    has_armrest = int(row["armrest"]) == 1
    has_buckle = int(row["buckle"]) == 1
    result = combine_features(has_buckle, has_armrest)

    _append_scan_to_json(qr_data, result)
    return result


def scan_code_only() -> str | None:
    """Scan QR of barcode, geef alleen de code terug en log ruwe waarde."""
    cap = cv2.VideoCapture(0)
    code = None

    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        code = _detect_qr_or_barcode(frame)
        if code:
            cv2.putText(
                frame,
                code,
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.0,
                (0, 255, 0),
                2,
            )
            cv2.imshow("Test QR/Barcode", frame)
            cv2.waitKey(500)
            break

        cv2.imshow("Test QR/Barcode", frame)
        if cv2.waitKey(1) & 0xFF == 27:  # ESC
            break

    cap.release()
    cv2.destroyAllWindows()

    if not code:
        _append_scan_to_json("", None)
        return None

    _append_scan_to_json(code, None)
    return code


def detect_qr_only(frame) -> str | None:
    """Zoek alleen een QR-code in een frame en geef de payload terug."""
    detector = cv2.QRCodeDetector()
    data, points, _ = detector.detectAndDecode(frame)

    if points is not None and len(points) > 0 and data:
        pts = points[0].astype(int)
        xmin, ymin = pts[:, 0].min(), pts[:, 1].min()
        xmax, ymax = pts[:, 0].max(), pts[:, 1].max()
        cv2.rectangle(frame, (xmin, ymin), (xmax, ymax), (0, 255, 0), 2)
        return data.strip()

    return None


def detect_barcode_only(frame) -> str | None:
    """Zoek alleen barcodes met pyzbar en geef de payload terug."""
    barcodes = decode(frame)
    for bc in barcodes:
        x, y, w, h = bc.rect
        cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)
        try:
            text = bc.data.decode("utf-8").strip()
        except Exception:
            text = str(bc.data)
        if text:
            return text
    return None


def scan_qr_only() -> str | None:
    """Scan alleen QR, log ruwe code."""
    cap = cv2.VideoCapture(0)
    code = None

    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        code = detect_qr_only(frame)
        if code:
            cv2.putText(
                frame,
                code,
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.0,
                (0, 255, 0),
                2,
            )
            cv2.imshow("QR Scanner", frame)
            cv2.waitKey(500)
            break

        cv2.imshow("QR Scanner", frame)
        if cv2.waitKey(1) & 0xFF == 27:  # ESC
            break

    cap.release()
    cv2.destroyAllWindows()

    if not code:
        _append_scan_to_json("", None)
        return None

    _append_scan_to_json(code, None)
    return code


def scan_barcode_only() -> str | None:
    """Scan alleen barcode, log ruwe code."""
    cap = cv2.VideoCapture(0)
    code = None

    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        code = detect_barcode_only(frame)
        if code:
            cv2.putText(
                frame,
                code,
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.0,
                (0, 255, 0),
                2,
            )
            cv2.imshow("Barcode Scanner", frame)
            cv2.waitKey(500)
            break

        cv2.imshow("Barcode Scanner", frame)
        if cv2.waitKey(1) & 0xFF == 27:  # ESC
            break

    cap.release()
    cv2.destroyAllWindows()

    if not code:
        _append_scan_to_json("", None)
        return None

    _append_scan_to_json(code, None)
    return code
