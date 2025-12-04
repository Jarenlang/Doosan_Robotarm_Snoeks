import socket
import threading
import json
import os

CONFIG_FILE = "config.json"

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {
            "robot_ip": "192.168.137.50",
            "port": 56666,
            "operation_speed": 50,
            "velx": 500,
            "accx": 300,
            "p_home": [-66, 850, 300, 3.14, 179.99, 163.55],
            "p_pick": [-585, -489, 771, 127, -151, 62],
            "p_place": [-585, -289, 571, 127, -151, 62],
        }

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_config(cfg: dict):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


_config = load_config()
ROBOT_IP = _config.get("robot_ip")
PORT = _config.get("port")

class DoosanGatewayClient:
    def __init__(self, ip=None, port=None):
        self.ip = ip or ROBOT_IP
        self.port = port or PORT
        self.sock = None
        self.lock = threading.Lock()

        self._status_lock = threading.Lock()
        self._last_status = None
        self._poll_thread = None
        self._poll_stop = threading.Event()
        self._poll_error_reported = False

    # --------------------------------------------------------
    # Socket laag
    # --------------------------------------------------------

    def connect(self):
        if self.sock:
            return
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((self.ip, self.port))
        self.sock = s

    def close(self):
        self.stop_status_poller()
        with self.lock:
            if self.sock:
                try:
                    self.send_raw("quit\n", expect_response=False)
                except:
                    pass
                self.sock.close()
                self.sock = None

    def send_raw(self, msg: str, expect_response=True):
        with self.lock:
            if not self.sock:
                raise RuntimeError("Not connected to robot")

            try:
                self.sock.sendall(msg.encode("ascii"))
                if not expect_response:
                    return None

                data = self.sock.recv(4096)
                if not data:
                    raise ConnectionError("Robot connection closed")

                return data.decode("ascii", errors="ignore")

            except Exception as e:
                try:
                    if self.sock:
                        self.sock.close()
                except:
                    pass
                self.sock = None
                raise e

    # --------------------------------------------------------
    # Motion
    # --------------------------------------------------------

    def amovel(self, x, y, z, rx, ry, rz, vel, acc):
        return self.send_raw(f"amovel {x} {y} {z} {rx} {ry} {rz} {vel} {acc}\n")

    def amovejx(self, x, y, z, rx, ry, rz, vel, acc):
        return self.send_raw(f"amovejx {x} {y} {z} {rx} {ry} {rz} {vel} {acc}\n")

    def stop(self):
        return self.send_raw("stop\n")

    def change_operation_speed(self, s):
        return self.send_raw(f"change_operation_speed {s}\n")

    def set_velx(self, v):
        return self.send_raw(f"set_velx {v}\n")

    def set_accx(self, a):
        return self.send_raw(f"set_accx {a}\n")

    # --------------------------------------------------------
    # I/O
    # --------------------------------------------------------

    def set_digital_output(self, i, v):
        return self.send_raw(f"digout {i} {int(v)}\n")

    def get_digital_input(self, i):
        resp = self.send_raw(f"digin {i}\n")
        parts = resp.strip().split()
        if len(parts) >= 3:
            return int(parts[2])
        raise RuntimeError("Bad digin response")

    # --------------------------------------------------------
    # Status poller
    # --------------------------------------------------------

    def start_status_poller(self, interval=0.2):
        if self._poll_thread and self._poll_thread.is_alive():
            return

        self._poll_stop.clear()
        self._poll_error_reported = False

        def loop():
            while not self._poll_stop.is_set():
                try:
                    resp = self.send_raw("check_motion\n")
                    if resp:
                        with self._status_lock:
                            self._last_status = resp.strip()
                except Exception as e:
                    if not self._poll_error_reported:
                        print("Poll error:", e)
                        self._poll_error_reported = True
                self._poll_stop.wait(interval)

        self._poll_thread = threading.Thread(target=loop, daemon=True)
        self._poll_thread.start()

    def stop_status_poller(self):
        self._poll_stop.set()
        if self._poll_thread:
            self._poll_thread.join(timeout=1)

    def get_last_status(self):
        with self._status_lock:
            return self._last_status

    # --------------------------------------------------------
    # Blocking wait
    # --------------------------------------------------------

    @staticmethod
    def _parse_check_motion_resp(resp):
        try:
            parts = resp.split()
            return int(parts[2])
        except:
            return None

    def wait_until_stopped(self, poll=0.1, timeout=None):
        import time
        t0 = time.time()
        while True:
            r = self.send_raw("check_motion\n")
            m = self._parse_check_motion_resp(r)
            if m == 0:
                return
            if timeout and time.time() - t0 > timeout:
                raise TimeoutError("Robot did not stop in time")
            time.sleep(poll)

    # --------------------------------------------------------
    # QR integratie
    # --------------------------------------------------------

    def run_qr_sequence(self, program, code, callback=None):
        return program.sequence_from_qr(code, callback)
