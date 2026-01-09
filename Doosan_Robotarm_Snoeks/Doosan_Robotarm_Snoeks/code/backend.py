import socket
import threading
import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "..", "data")

CONFIG_FILE = os.path.join(DATA_DIR, "config.json")
COORD_FILE = os.path.join(DATA_DIR, "coordinates.json")

def load_config():
    if not os.path.exists(CONFIG_FILE):
        # defaults als config nog niet bestaat
        return {
            "robot_ip": "192.168.137.50",
            "port": 56666,
            "LAMP_DO_READY": 1,
            "LAMP_DO_MOVE": 2,
            "operation_speed": 50,
            "velx": 500,
            "accx": 300,
            "SNOEKS_RED": "#c90000",
            "SNOEKS_DARK": "#111111",
            "SNOEKS_DARK2": "#2c2c2c",
            "SNOEKS_TEXT": "#000000"
        }

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def load_coordinates() -> dict:
    if not os.path.exists(COORD_FILE):
        return {}
    with open(COORD_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_coordinates(coords: dict) -> None:
    with open(COORD_FILE, "w", encoding="utf-8") as f:
        json.dump(coords, f, indent=2)

def save_config(cfg: dict):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)

# ----------------- Operator / safety helpers -----------------

def is_robot_enabled(self) -> bool:
    try:
        return self.gateway.get_digital_input(2) == 1  # pas index aan als je andere DI gebruikt
    except Exception:
        return False

# Laad globale config
_config = load_config()
ROBOT_IP = _config.get("robot_ip")
PORT = _config.get("port")


def sensor_amovel(
    self,
    base_pos,
    direction="z-",
    pre_distance=250.0,
    return_direction="y+",
    return_distance=100.0,
    force_limit=30.0,
    statuscallback=None,
):

    def log(msg: str):
        print(msg)
        if statuscallback:
            statuscallback(msg)

    self._stop_flag = False

    # -------- helper om richtingsvector uit string te halen --------
    def dir_to_vec(direction: str):
        dx, dy, dz = 0.0, 0.0, 0.0
        if direction == "x+":
            dx = 1.0
        elif direction == "x-":
            dx = -1.0
        elif direction == "y+":
            dy = 1.0
        elif direction == "y-":
            dy = -1.0
        elif direction == "z+":
            dz = 1.0
        elif direction == "z-":
            dz = -1.0
        else:
            raise ValueError(f"Ongeldige richting: {direction}")
        return dx, dy, dz

    # -------- eerste beweging vanaf base_pos --------
    try:
        dx1, dy1, dz1 = dir_to_vec(direction)
    except ValueError as e:
        log(str(e))
        return

    bx, by, bz, brx, bry, brz = base_pos

    target1 = [
        bx + dx1 * pre_distance,
        by + dy1 * pre_distance,
        bz + dz1 * pre_distance,
        brx,
        bry,
        brz,
    ]

    log(f"sensor_amovel: eerste beweging naar {target1}")
    self.gateway.amovel(*target1, 10, 50)

    if self._stop_flag:
        log("Sequence gestopt voor force-check.")
        return

    # -------- force monitor --------
    log(f"sensor_amovel: force-monitor starten, limiet {force_limit} N")
    trigger_reached = False

    while not self._stop_flag:
        try:
            force_value = self.gateway.get_tool_force(0)
        except Exception as e:
            log(f"Fout bij uitlezen force: {e}")
            self._stop_flag = True
            self.gateway.stop()
            force_value = None

        if force_value is not None:
            log(f"Huidige force: {force_value:.2f} N")
            if force_value >= force_limit:
                log("Force-limiet bereikt, directe stop.")
                try:
                    self.gateway.stop()
                except Exception as e:
                    log(f"Fout bij stop-commando: {e}")
                trigger_reached = True
                break

    # DO2 aan als trigger bereikt is
    if trigger_reached:
        try:
            self.gateway.set_digital_output(2, 1)  # DO2 hoog
            log("DO2 = 1 gezet.")
        except Exception as e:
            log(f"Fout bij DO2 zetten: {e}")

        try:
            curx, cury, curz, currx, curry, currz = self.gateway.get_tcppose()
            log(f"sensor_amovel actuele TCP na stop voor kleine lift: ")
            log(f"{curx:.1f}, {cury:.1f}, {curz:.1f}, {currx:.1f}, {curry:.1f}, {currz:.1f}")

            lift_mm = 5.0  # hier kun je 4.0 of 5.0 van maken
            lift_target = (
                curx - dx1 * lift_mm,
                cury - dy1 * lift_mm,
                curz - dz1 * lift_mm,
                currx,
                curry,
                currz,
            )

            log(f"sensor_amovel kleine lift van {lift_mm} mm naar {lift_target}")
            self.gateway.change_operation_speed(self.operation_speed)
            self.gateway.amovel(*lift_target, self.velx, self.accx)
            self.gateway.wait_until_stopped()
            log("sensor_amovel kleine lift klaar.")
        except Exception as e:
            log(f"Fout bij kleine lift-beweging: {e}")

    # -------- tweede beweging vanaf actuele TCP-pose --------
    if trigger_reached:
        try:
            cur_x, cur_y, cur_z, cur_rx, cur_ry, cur_rz = self.gateway.get_tcppose()
            log(
                f"sensor_amovel: actuele TCP na stop: "
                f"[{cur_x:.1f}, {cur_y:.1f}, {cur_z:.1f}, "
                f"{cur_rx:.1f}, {cur_ry:.1f}, {cur_rz:.1f}]"
            )
        except Exception as e:
            log(f"Fout bij uitlezen TCP-pose: {e}")
            # als we de pose niet kunnen lezen, stoppen we hier
            return

        try:
            dx2, dy2, dz2 = dir_to_vec(return_direction)
        except ValueError as e:
            log(str(e))
            return

        target2 = [
            cur_x + dx2 * return_distance,
            cur_y + dy2 * return_distance,
            cur_z + dz2 * return_distance,
            cur_rx,
            cur_ry,
            cur_rz,
        ]

        self.gateway.change_operation_speed(self.operation_speed)
        log(f"sensor_amovel: tweede beweging vanaf TCP naar {target2}")
        self.gateway.amovel(*target2, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        log("sensor_amovel: tweede beweging klaar.")
    else:
        # als force-limiet nooit bereikt is: optioneel terug naar base_pos zoals vroeger
        self.gateway.change_operation_speed(self.operation_speed)
        up_target = [bx, by, bz, brx, bry, brz]
        log(f"sensor_amovel: force-limiet niet bereikt, terug naar {up_target}")
        self.gateway.amovel(*up_target, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        log("sensor_amovel: klaar (terug naar base_pos).")

def apply_parameters(self):
    """Stuur huidige parameters naar de robot."""
    self.gateway.change_operation_speed(self.operation_speed)
    self.gateway.set_velx(self.velx)
    self.gateway.set_accx(self.accx)

class DoosanGatewayClient:
    def __init__(self, ip: str | None = None, port: int | None = None):
        self.gateway = None
        if port is None:
            port = PORT
        if ip is None:
            ip = ROBOT_IP

        self.ip: str = ip
        self.port: int = port
        self.sock: socket.socket | None = None
        self.lock = threading.Lock()

        # --- status-poller extra's ---
        self._status_lock = threading.Lock()
        self._last_status: str | None = None
        self._poll_thread: threading.Thread | None = None
        self._poll_stop = threading.Event()
        self._poll_error_reported = False  # alleen eerste fout loggen

    # ---------------- Basis socket-API ---------------- #

    def connect(self) -> None:
        if self.sock:
            return
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((self.ip, self.port))
        self.sock = s

    def close(self) -> None:
        # eerst poller stoppen
        self.stop_status_poller()
        with self.lock:
            if self.sock:
                try:
                    self.send_raw("quit\n", expect_response=False)
                except Exception:
                    pass
                self.sock.close()
                self.sock = None

    def send_raw(self, msg: str, expect_response: bool = True) -> str | None:
        with self.lock:
            if not self.sock:
                raise RuntimeError("Not connected to robot")

            try:
                self.sock.sendall(msg.encode("ascii"))
                if not expect_response:
                    return None

                data = self.sock.recv(4096)
                if not data:
                    # lege read = verbinding verbroken
                    raise ConnectionError("Robot connection closed")

                return data.decode("ascii", errors="ignore")

            except Exception as e:
                # bij elke fout: socket ongeldig maken, zodat de GUI dit ziet
                try:
                    if self.sock:
                        self.sock.close()
                except Exception:
                    pass
                self.sock = None
                raise e

    # ---------------- High-level helpers ---------------- #

    def amovel(self, x, y, z, rx, ry, rz, vel, acc):
        cmd = f"amovel {x} {y} {z} {rx} {ry} {rz} {vel} {acc}\n"
        return self.send_raw(cmd)

    def amovej(self, j1, j2, j3, j4, j5, j6, vel, acc):
        cmd = f"amovej {j1} {j2} {j3} {j4} {j5} {j6} {vel} {acc}"
        return self.send_raw(cmd)

    def amovejx(self, x, y, z, rx, ry, rz, vel, acc):
        cmd = f"amovejx {x} {y} {z} {rx} {ry} {rz} {vel} {acc}\n"
        return self.send_raw(cmd)

    def stop(self):
        return self.send_raw("stop\n")

    def change_operation_speed(self, speed: int | float):
        return self.send_raw(f"change_operation_speed {speed}\n")

    def set_velx(self, vel: int | float):
        return self.send_raw(f"set_velx {vel}\n")

    def set_accx(self, acc: int | float):
        return self.send_raw(f"set_accx {acc}\n")

    # ---------------- Digital / analog IO helpers ---------------- #

    def set_digital_output(self, index: int, value: int):
        """
        Zet een digitale uitgang (0/1).
        """
        cmd = f"digout {index} {int(value)}\n"
        return self.send_raw(cmd)

    def get_digital_input(self, index: int) -> int:
        """
        Lees een digitale ingang (0/1). Retourneert 0 of 1.
        """
        resp = self.send_raw(f"digin {index}\n")
        if not resp:
            raise RuntimeError("Empty response from digin")

        parts = resp.strip().split()

        # verwacht: "OK digin <0/1>"
        if len(parts) >= 3 and parts[0].upper() == "OK":
            try:
                return int(parts[2])
            except ValueError:
                raise RuntimeError(f"Unexpected digin payload: {parts[2]!r} in {resp!r}")

        # alles wat geen 'OK ...' is, behandelen als fout van de robot
        raise RuntimeError(f"digin error response: {resp!r}")

    def set_analog_output(self, ch: int, value: float):
        """
        Zet een analoge uitgang. Schaal/units afhankelijk van je hardware-config.
        """
        cmd = f"anout {ch} {value}\n"
        return self.send_raw(cmd)

    def get_analog_input(self, ch: int) -> float:
        """
        Lees een analoge ingang. Retourneert float.
        """
        resp = self.send_raw(f"anin {ch}\n")
        if not resp:
            raise RuntimeError("Empty response from anin")
        parts = resp.strip().split()
        # verwacht: "OK anin <value>"
        if len(parts) >= 3:
            return float(parts[2])
        raise RuntimeError(f"Unexpected anin response: {resp!r}")

    LAMP_DO_READY = _config.get("LAMP_DO_READY")
    LAMP_DO_MOVE = _config.get("LAMP_DO_MOVE")  # DO2

    def set_lamp(self, ready: bool, moving: bool):
        """
        Zorgt dat precies Ã©Ã©n stand actief is:
        - ready=True  => DO1=1, DO2=0
        - moving=True => DO1=0, DO2=1
        - allebei False => DO1=0, DO2=0
        """
        # eerst alles uit
        self.set_digital_output(self.LAMP_DO_READY, 0)  # +1 omdat robot DO's 1..16 zijn
        self.set_digital_output(self.LAMP_DO_MOVE, 0)
        if ready:
            self.set_digital_output(self.LAMP_DO_READY, 1)
        elif moving:
            self.set_digital_output(self.LAMP_DO_MOVE, 1)

        self.gateway.set_lamp(False, False)

    # ---------------- check_motion helpers ---------------- #

    @staticmethod
    def _parse_check_motion_resp(resp: str) -> int | None:
        """
        Parseer een antwoordregel van 'check_motion'.
        Verwacht iets als: 'OK check_motion 0' of 'OK check_motion 1'.
        Retourneert 0 of 1, of None als het niet te parsen is.
        """
        if not resp:
            return None
        parts = resp.strip().split()
        if len(parts) < 3:
            return None
        try:
            return int(parts[2])
        except ValueError:
            return None

    # ---------------- Status-poller API ---------------- #

    def start_status_poller(self, interval: float = 0.1) -> None:

        if self._poll_thread and self._poll_thread.is_alive():
            return

        self._poll_stop.clear()
        self._poll_error_reported = False

        def _poll():
            while not self._poll_stop.is_set():
                try:
                    resp = self.send_raw("check_motion\n")
                    if resp is not None:
                        with self._status_lock:
                            self._last_status = resp.strip()
                except Exception as e:
                    # Alleen eerste fout loggen om spam te voorkomen
                    if not self._poll_error_reported:
                        print(f"Exception while polling check_motion: {e}")
                        self._poll_error_reported = True
                self._poll_stop.wait(interval)

        self._poll_thread = threading.Thread(target=_poll, daemon=True)
        self._poll_thread.start()

    def stop_status_poller(self) -> None:
        self._poll_stop.set()
        if self._poll_thread and self._poll_thread.is_alive():
            self._poll_thread.join(timeout=1.0)

    def get_last_status(self) -> str | None:
        with self._status_lock:
            return self._last_status

    def wait_until_stopped(self, poll_interval: float = 0.1, timeout: float | None = None) -> None:
        import time

        start = time.time()
        while True:
            resp = self.send_raw("check_motion\n")
            moving = self._parse_check_motion_resp(resp or "")
            if moving == 0:
                return  # robot staat stil

            if timeout is not None and (time.time() - start) > timeout:
                raise TimeoutError("Robot still moving after wait_until_stopped timeout")

            time.sleep(poll_interval)

    def get_tool_force(self, ref: int = 0) -> float:
        resp = self.send_raw(f"toolforce {int(ref)}")
        if not resp:
            raise RuntimeError("Empty response from toolforce")
        parts = resp.strip().split()
        # Verwacht: OK toolforce value
        if len(parts) == 3 and parts[0].upper() == "OK" and parts[1].lower() == "toolforce":
            try:
                return float(parts[2])
            except ValueError:
                raise RuntimeError(f"Unexpected toolforce payload {parts[2]!r} in {resp!r}")
        raise RuntimeError(f"toolforce error response {resp!r}")

    def get_tcppose(self):
        resp = self.send_raw("tcp_pose", expect_response=True)
        if not resp:
            raise RuntimeError("Empty response from tcppose")

        parts = resp.strip().split()
        # Verwacht: ["OK", "tcppose", "x", "y", "z", "rx", "ry", "rz"]
        if len(parts) != 8 or parts[0].upper() != "OK" or parts[1].lower() != "tcppose":
            raise RuntimeError(f"Unexpected tcppose response {resp!r}")

        try:
            x = float(parts[2])
            y = float(parts[3])
            z = float(parts[4])
            rx = float(parts[5])
            ry = float(parts[6])
            rz = float(parts[7])
        except ValueError:
            raise RuntimeError(f"Unable to parse tcppose payload in {resp!r}")

        return x, y, z, rx, ry, rz