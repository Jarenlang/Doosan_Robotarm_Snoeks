import cv2
from pyzbar import pyzbar
import pandas as pd

db = pd.read_excel("producten.xlsx")

def combine_features(has_gordels, has_armsteunen):
    """
    Converteert losse velden naar jouw 4 codes:

    Gordels / Armsteunen:
      0 / 0 → 4
      1 / 0 → 1
      0 / 1 → 3
      1 / 1 → 2
    """

    if has_gordels and has_armsteunen:
        return 2   # beide
    elif has_gordels and not has_armsteunen:
        return 1   # alleen gordels
    elif not has_gordels and has_armsteunen:
        return 3   # alleen armsteunen
    else:
        return 4   # geen van beide


def scan_qr():
    cap = cv2.VideoCapture(0)
    detector = cv2.QRCodeDetector()
    qr_data = None

    while qr_data is None:
        ret, frame = cap.read()
        if not ret:
            continue

        data, points, _ = detector.detectAndDecode(frame)
        if data != "":
            qr_data = data.strip()
            break

    cap.release()

    # Zoek het product in de Excel
    product = db[db["Code"] == qr_data]

    if product.empty:
        return None

    row = product.iloc[0]

    # Excel kolommen bevatten 0 of 1
    has_armsteunen = int(row["Armsteun"]) == 1
    has_gordels = int(row["Gordels"]) == 1

    # Vertaal naar code 1,2,3,4
    return combine_features(has_gordels, has_armsteunen)
