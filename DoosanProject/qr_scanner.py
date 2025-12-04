# qr_scanner.py
import cv2
import pandas as pd

# Excel met productcodes
DB = pd.read_excel("producten.xlsx")  # kolommen: Code, Armsteun, Gordels

def combine_features(has_gordels: bool, has_armsteunen: bool) -> int:
    if has_gordels and has_armsteunen:
        return 2   # beide
    elif has_gordels and not has_armsteunen:
        return 1   # alleen gordels
    elif not has_gordels and has_armsteunen:
        return 3   # alleen armsteunen
    else:
        return 4   # geen van beide

def scan_qr_with_camera():
    cap = cv2.VideoCapture(0)
    detector = cv2.QRCodeDetector()
    qr_data = None

    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        data, points, _ = detector.detectAndDecode(frame)

        if points is not None and len(points) > 0:
            pts = points[0].astype(int)
            # Rechthoek om QR-code
            x_min, y_min = pts[:, 0].min(), pts[:, 1].min()
            x_max, y_max = pts[:, 0].max(), pts[:, 1].max()
            cv2.rectangle(frame, (x_min, y_min), (x_max, y_max), (0, 255, 0), 2)

        if data:
            qr_data = data.strip()
            # Tekst met inhoud QR-code
            cv2.putText(frame, qr_data, (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
            cv2.imshow("QR Scanner", frame)
            cv2.waitKey(500)  # kort tonen met tekst/kader
            break

        cv2.imshow("QR Scanner", frame)
        if cv2.waitKey(1) & 0xFF == 27:  # ESC om af te breken
            break

    cap.release()
    cv2.destroyAllWindows()

    if not qr_data:
        return None

    # Zoek product in Excel
    product = DB[DB["Code"] == qr_data]
    if product.empty:
        return None

    row = product.iloc[0]
    has_armsteunen = int(row["Armsteun"]) == 1
    has_gordels = int(row["Gordels"]) == 1

    return combine_features(has_gordels, has_armsteunen)
