import cv2
import pytesseract
import json
import time
import re

# Alleen nodig op Windows: pad naar tesseract.exe
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Regex: alle alfanumerieke reeksen van 8 t/m 16 karakters (hoofdletters + cijfers)
PATROON = re.compile(r"\b[A-Z0-9]{8,16}\b")

def preprocess(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return thresh

def main():
    cap = cv2.VideoCapture(0)  # 0 = standaard camera
    if not cap.isOpened():
        print("Kan camera niet openen")
        return

    herkende_items = []  # lijst met codes die voldoen aan je patronen

    laatste_opslaan = time.time()
    autosave_interval = 10  # seconden

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Geen frame ontvangen, stoppen...")
                break

            processed = preprocess(frame)

            # Tesseract: whitelist cijfers + hoofdletters, psm 6 = blok tekst
            custom_config = r'-c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ --psm 6'
            tekst = pytesseract.image_to_string(processed, config=custom_config)

            # Zoek alle reeksen van 8 t/m 16 alfanumerieke karakters
            matches = PATROON.findall(tekst)

            for code in matches:
                if code not in herkende_items:
                    herkende_items.append(code)
                    print("Nieuw gevonden code:", code)

            cv2.imshow("Camera (q om te stoppen)", frame)

            nu = time.time()
            if nu - laatste_opslaan > autosave_interval:
                with open("resultaten.json", "w", encoding="utf-8") as f:
                    json.dump(herkende_items, f, ensure_ascii=False, indent=2)
                laatste_opslaan = nu

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    finally:
        cap.release()
        cv2.destroyAllWindows()

        with open("resultaten.json", "w", encoding="utf-8") as f:
            json.dump(herkende_items, f, ensure_ascii=False, indent=2)

        print("Opgeslagen naar resultaten.json")

if __name__ == "__main__":
    main()
