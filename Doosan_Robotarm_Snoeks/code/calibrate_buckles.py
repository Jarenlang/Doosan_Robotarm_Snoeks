import cv2
import numpy as np
import json
import os
import time
from sklearn.cluster import KMeans

# ================= CONFIG =================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "..", "data")
PIXEL_JSON = os.path.join(DATA_DIR, "buckle_positions_pixels.json")

ROWS = 2
COLS = 3

CAMERA_ROTATION_DEG = 0

CAMERA_INDEX = 2
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480


# ---------------- Camera helpers ----------------
def rotate_point(p, width, height, rot):
    x, y = p
    if rot == 0:
        return x, y
    if rot == 90:
        return height - y, x
    if rot == 180:
        return width - x, height - y
    if rot == 270:
        return y, width - x
    raise ValueError("Ongeldige camera-rotatie")


# ---------------- Webcam camera ----------------
class WebcamCamera:
    def __init__(self, index, width, height):
        self.cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        if not self.cap.isOpened():
            raise RuntimeError("Webcam kon niet worden geopend")

    def get_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            return None
        return frame

    def stop(self):
        self.cap.release()


# ---------------- JSON helpers ----------------
def load_json(path):
    if not os.path.exists(path):
        return None
    with open(path, "r") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=4)


# ---------------- Buckle detectie ----------------
def detect_buckles(img):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    # Rood – ruimer dan origineel, maar zelfde principe
    mask = (
        cv2.inRange(hsv, (0, 80, 50), (15, 255, 255)) |
        cv2.inRange(hsv, (165, 80, 50), (180, 255, 255))
    )

    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(
        mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    centers = []
    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        centers.append((x + w // 2, y + h // 2))

    return centers


# ---------------- Buckle sortering (IDENTIEK) ----------------
def sort_buckles_auto(centers, cam):
    rotated = [
        rotate_point(p, cam.width, cam.height, CAMERA_ROTATION_DEG)
        for p in centers
    ]

    y_coords = np.array([[p[1]] for p in rotated])
    labels = KMeans(
        n_clusters=ROWS, n_init=10, random_state=42
    ).fit_predict(y_coords)

    rows = [[] for _ in range(ROWS)]
    for i, p in enumerate(rotated):
        rows[labels[i]].append((p, centers[i]))

    rows.sort(key=lambda r: np.mean([p[0][1] for p in r]))

    ordered = []
    n = 1
    for r in rows:
        # rechts → links
        r.sort(key=lambda x: x[0][0], reverse=True)
        for _, orig in r:
            ordered.append({
                "n": n,
                "pixel": [int(orig[0]), int(orig[1])]
            })
            n += 1

    return ordered


# ---------------- Calibratie (IDENTIEK FLOW) ----------------
def calibrate_pixels(cam):
    print("CALIBRATIE: Exact 6 buckles vereist")
    print("Druk SPACE om te bevestigen, ESC om te annuleren")

    while True:
        while True:
            img = cam.get_frame()
            if img is None:
                continue

            vis = img.copy()
            centers = detect_buckles(img)

            for c in centers:
                cv2.circle(vis, c, 5, (0, 0, 255), -1)

            cv2.putText(
                vis,
                f"Gevonden buckles: {len(centers)} / {ROWS * COLS}",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 0) if len(centers) == ROWS * COLS else (0, 0, 255),
                2
            )

            cv2.imshow("Pixel calibratie (SPACE=OK, ESC=STOP)", vis)

            key = cv2.waitKey(30) & 0xFF
            if key == 27:
                cv2.destroyAllWindows()
                return load_json(PIXEL_JSON)
            if key == 32:
                break

        if len(centers) != ROWS * COLS:
            print(f"Ongeldig aantal buckles: {len(centers)} gevonden, opnieuw...")
            time.sleep(1)
            continue

        cv2.destroyAllWindows()
        ordered = sort_buckles_auto(centers, cam)
        save_json(PIXEL_JSON, ordered)
        print("Calibratie geslaagd")
        return ordered


# ================= MAIN =================
if __name__ == "__main__":
    cam = WebcamCamera(
        CAMERA_INDEX,
        CAMERA_WIDTH,
        CAMERA_HEIGHT
    )

    calibrate_pixels(cam)
    cam.stop()
