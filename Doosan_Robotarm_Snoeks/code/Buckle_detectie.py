import cv2
import numpy as np
import json
import os
import time

# ================= CONFIG =================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "..", "data")
PIXEL_JSON = os.path.join(DATA_DIR, "buckle_positions_pixels.json")
OUTPUT_JSON = os.path.join(DATA_DIR, "latest_buckle_detection.json")

INTERVAL_SEC = 2.0
CALIBRATION_MODE = False  # <-- zet op True om opnieuw te calibreren

ROWS = 2
COLS = 3

CAMERA_ROTATION_DEG = 180

# -------- Robot vaste waarden --------
Z_CONST = 724.01
RX_CONST = 88.47
RY_CONST = -32.96
RZ_CONST = 88.70

# -------- MM GRID CONSTANTEN --------
MM_X1 = -526.20
MM_Y1 = -502.96
MM_DX = 75
MM_DY = 55.0
MM_APPROACH_DY = 100.0

MATCH_TOLERANCE_PX = 20

CAMERA_INDEX = 2
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480


# ---------------- Helpers ----------------
def atomic_write_json(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=4)
    os.replace(tmp, path)


def load_json(path):
    with open(path, "r") as f:
        return json.load(f)


# ---------------- Webcam ----------------
cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)

if not cap.isOpened():
    raise RuntimeError("Webcam kon niet worden geopend")


# ---------------- Detectie ----------------
def detect_buckles(img):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    mask = (
            cv2.inRange(hsv, (0, 80, 50), (15, 255, 255)) |
            cv2.inRange(hsv, (165, 80, 50), (180, 255, 255))
    )

    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    centers = []
    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        centers.append((x + w // 2, y + h // 2))

    return centers


# ---------------- CALIBRATIE ----------------
def run_calibration():
    print("CALIBRATIE START – zorg dat alle buckles zichtbaar zijn")
    time.sleep(2)

    samples = []

    for _ in range(15):
        ret, frame = cap.read()
        if not ret:
            continue
        samples.extend(detect_buckles(frame))
        time.sleep(0.1)

    if len(samples) < ROWS * COLS:
        raise RuntimeError("Te weinig buckles gedetecteerd voor calibratie")

    pts = np.array(samples)

    # Cluster naar exact ROWS*COLS punten
    from sklearn.cluster import KMeans
    kmeans = KMeans(n_clusters=ROWS * COLS, n_init=10)
    centers = kmeans.fit(pts).cluster_centers_

    # Sorteren: eerst Y (rijen), dan X (kolommen)
    centers = sorted(centers, key=lambda p: (p[1], p[0]))

    calibrated = []
    for i, (x, y) in enumerate(centers, start=1):
        calibrated.append({
            "n": i,
            "pixel": [int(x), int(y)]
        })

    atomic_write_json(PIXEL_JSON, calibrated)
    print(f"CALIBRATIE KLAAR – opgeslagen in {PIXEL_JSON}")


# ---------------- MM berekeningen ----------------
def buckle_mm(n):
    row = (n - 1) // COLS
    col = (n - 1) % COLS
    return MM_X1 + col * MM_DX, MM_Y1 + row * MM_DY


def approach_mm(n):
    x, y = buckle_mm(n)
    return x, y + MM_APPROACH_DY


# ================= START =================
if CALIBRATION_MODE:
    run_calibration()

pixels_buffer = load_json(PIXEL_JSON)

print("Vision service gestart – JSON update elke 2 seconden")

try:
    while True:
        t0 = time.time()

        ret, frame = cap.read()
        if not ret:
            time.sleep(INTERVAL_SEC)
            continue

        centers = detect_buckles(frame)

        found = []
        for b in pixels_buffer:
            for c in centers:
                if np.linalg.norm(np.array(b["pixel"]) - np.array(c)) < MATCH_TOLERANCE_PX:
                    found.append(b)
                    break

        result = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "buckle_found": False,
            "buckle_number": None,
            "start_position": None,
            "grip_position": None
        }

        if found:
            b = min(found, key=lambda x: x["n"])
            n = b["n"]

            ax, ay = approach_mm(n)
            sx, sy = buckle_mm(n)

            result.update({
                "buckle_found": True,
                "buckle_number": n,
                "start_position": {
                    "x": ax, "y": ay, "z": Z_CONST,
                    "rx": RX_CONST, "ry": RY_CONST, "rz": RZ_CONST
                },
                "grip_position": {
                    "x": sx, "y": sy, "z": Z_CONST,
                    "rx": RX_CONST, "ry": RY_CONST, "rz": RZ_CONST
                }
            })

        atomic_write_json(OUTPUT_JSON, result)
        time.sleep(max(0.0, INTERVAL_SEC - (time.time() - t0)))

except KeyboardInterrupt:
    print("Vision service gestopt")

finally:
    cap.release()
