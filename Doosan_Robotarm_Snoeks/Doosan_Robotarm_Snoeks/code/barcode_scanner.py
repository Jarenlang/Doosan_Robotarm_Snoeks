import cv2
from pyzbar import pyzbar

webcam_id = 2

class BarcodeScanError(Exception):
    pass

def scan_camera(required_letters=None, zoom_factors=None):
    if zoom_factors is None:
        zoom_factors = [1.0, 1.5, 2.0, 3.0]
    if required_letters is None:
        required_letters = ["P", "H"]
    clahe_clip = 4.0
    clahe_tile = 8

    # Open camera
    cap = cv2.VideoCapture(webcam_id)
    if not cap.isOpened():
        raise RuntimeError("Kan de camera niet openen")

    print("Camera geopend. Scannen gestart...")

    used_barcodes = set()

    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        annotated = frame.copy()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        all_detected = set()

        for zoom in zoom_factors:
            gray_resized = cv2.resize(gray, (0, 0), fx=zoom, fy=zoom, interpolation=cv2.INTER_CUBIC)
            filters = [
                gray_resized,
                cv2.threshold(gray_resized, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1],
                cv2.createCLAHE(clipLimit=clahe_clip, tileGridSize=(clahe_tile, clahe_tile)).apply(gray_resized)
            ]

            for fimg in filters:
                for bc in pyzbar.decode(fimg):
                    data = bc.data.decode("utf-8").strip().upper()
                    all_detected.add(data)
                    if any(letter in data for letter in required_letters):
                        used_barcodes.add(data)
                        color = (0, 0, 255)  # rood
                    else:
                        color = (255, 0, 0)  # blauw

                    # bbox terug naar origineel
                    bx, by, bw, bh = bc.rect
                    bx_orig = int(bx / zoom)
                    by_orig = int(by / zoom)
                    bw_orig = int(bw / zoom)
                    bh_orig = int(bh / zoom)

                    cv2.rectangle(annotated, (bx_orig, by_orig),
                                  (bx_orig + bw_orig, by_orig + bh_orig),
                                  color, 2)
                    cv2.putText(annotated, data, (bx_orig, by_orig - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

        cv2.imshow("Barcode Scan", annotated)

        # Stop automatisch als alle required_letters aanwezig zijn
        found_letters = set()
        for code in used_barcodes:
            for letter in required_letters:
                if letter in code:
                    found_letters.add(letter)
        if found_letters == set(required_letters):
            print("Alle vereiste codes gevonden, scanner stopt automatisch.")
            break

        key = cv2.waitKey(1)
        if key == 27:  # ESC sluit alles
            break

    cap.release()
    cv2.destroyAllWindows()
    return used_barcodes

def scan_part_and_trace(required_letters=("P", "H")):
    used_barcodes = scan_camera(required_letters=required_letters)
    if not used_barcodes:
        raise BarcodeScanError("Geen barcodes gevonden.")

    part = None
    trace = None
    for code in used_barcodes:
        code = code.strip().upper()
        if code.startswith("P") and len(code) > 1:
            part = code[0:]
            print(part)
        elif code.startswith("H") and len(code) > 1:
            trace = code[0:]
            print(trace)

    if not part:
        raise BarcodeScanError("Geen P‑code (partnumber) gevonden.")
    if not trace:
        raise BarcodeScanError("Geen H‑code (traceID) gevonden.")

    return part, trace
