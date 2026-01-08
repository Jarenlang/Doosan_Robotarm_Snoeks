import socket
import threading
import json
import os

CONFIG_FILE = "config.json"
COORD_FILE = "coordinates.json"

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

def _dir_to_vector(direction: str):
    """
    Converteer een richting-string ("x+", "x-", "y+", "y-", "z+", "z-")
    naar een (dx, dy, dz) eenheidsvector.
    """
    dx = dy = dz = 0.0
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
        return None
    return dx, dy, dz


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
        Zorgt dat precies één stand actief is:
        - ready=True  => DO1=1, DO2=0
        - moving=True => DO1=0, DO2=1
        - allebei False => DO1=0, DO2=0
        """
        # eerst alles uit
        self.set_digital_output(self.LAMP_DO_READY, 0)
        self.set_digital_output(self.LAMP_DO_MOVE, 0)
        if ready:
            self.set_digital_output(self.LAMP_DO_READY, 1)
        elif moving:
            self.set_digital_output(self.LAMP_DO_MOVE, 1)

        self.gateway.set_lamp(False, False)

    # ---------------- check_motion helpers ---------------- #

    @staticmethod
    def _parse_check_motion_resp(resp: str) -> int | None:
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

    def get_tcp(self, ref: int = 0) -> tuple[float, float, float, float, float, float]:
        """
        Lees de actuele TCP-positie (posx) van de robot.
        Retourneert (x, y, z, rx, ry, rz).
        """
        resp = self.send_raw(f"gettcp {int(ref)}\n")
        if not resp:
            raise RuntimeError("Empty response from gettcp")
        parts = resp.strip().split()
        # Verwacht: OK gettcp x y z rx ry rz
        if len(parts) == 8 and parts[0].upper() == "OK" and parts[1].lower() == "gettcp":
            try:
                vals = [float(v) for v in parts[2:8]]
                return tuple(vals)
            except ValueError:
                raise RuntimeError(f"Unexpected gettcp payload {parts[2:]!r} in {resp!r}")
        raise RuntimeError(f"gettcp error response {resp!r}")

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

    def sensor_amovel(self, base_pos, direction: str = "z-", pre_distance: float = 250.0, force_limit: float = 20.0,
                      return_direction: str | None = None, return_distance: float = 0.0, statuscallback=None, ):

        def log(msg: str):
            print(msg)
            if statuscallback:
                statuscallback(msg)

        self._stop_flag = False

        # Richtingsvector voor eerste beweging
        vec = _dir_to_vector(direction)
        if vec is None:
            log(f"Invalid direction: {direction}")
            return
        dx, dy, dz = vec

        bx, by, bz, brx, bry, brz = base_pos

        # EIND-positie van de eerste move
        first_end = [
            bx + dx * pre_distance,
            by + dy * pre_distance,
            bz + dz * pre_distance,
            brx,
            bry,
            brz,
        ]

        log(f"sensor_amovel: move towards {first_end}")
        self.gateway.amovel(*first_end, 20, 20)

        if self._stop_flag:
            log("Sequence stopped for force-check.")
            return

        # Force monitoren
        log(f"sensor_amovel: starting force-monitor, current limit: {force_limit} N")
        while not self._stop_flag:
            try:
                force_value = self.gateway.get_tool_force(0)
            except Exception as e:
                log(f"Error in reading force: {e}")
                self._stop_flag = True
                self.gateway.stop()
                force_value = None

            if force_value is not None:
                log(f"Current force: {force_value:.2f} N")
                if force_value >= force_limit:
                    log("Force-limit reached, send stop command.")
                    try:
                        self.gateway.stop()
                    except Exception as e:
                        log(f"Error with stop-command: {e}")
                    break

        # DO2 aan
        try:
            self.gateway.set_digital_output(2, 1)  # DO2 hoog
            log("DO2 = 1.")
        except Exception as e:
            log(f"Error while setting DO2: {e}")

        # huidige positie uitlezen
        try:
            cur_x, cur_y, cur_z, cur_rx, cur_ry, cur_rz = self.gateway.get_tcp(0)
            log(
                f"TCP now at: x={cur_x:.2f}, y={cur_y:.2f}, "
                f"z={cur_z:.2f}, rx={cur_rx:.2f}, ry={cur_ry:.2f}, rz={cur_rz:.2f}"
            )
        except Exception as e:
            log(f"Error reading TCP pose: {e}")
            # fallback: gebruik de oude base_pos als het misgaat
            cur_x, cur_y, cur_z, cur_rx, cur_ry, cur_rz = base_pos

        # Terug-beweging:
        if return_direction and return_distance > 0.0:
            ret_vec = _dir_to_vector(return_direction)
            if ret_vec is None:
                log(f"invalid return direction: {return_direction}, back to base_pos.")
                ret_target = [cur_x, cur_y, cur_z, cur_rx, cur_ry, cur_rz]
            else:
                rdx, rdy, rdz = ret_vec
                ret_target = [
                    cur_x + rdx * return_distance,
                    cur_y + rdy * return_distance,
                    cur_z + rdz * return_distance,
                    cur_rx,
                    cur_ry,
                    cur_rz,
                ]
                log(f"sensor_amovel: return move to {ret_target}")
        else:
            # Standaard: terug naar gemeten TCP-positie (geen extra offset)
            ret_target = [cur_x, cur_y, cur_z, cur_rx, cur_ry, cur_rz]
            log("sensor_amovel: back to measured TCP position")

        self.gateway.change_operation_speed(self.operation_speed)
        self.gateway.amovel(*ret_target, 20, 20)
        self.gateway.wait_until_stopped()

        log("sensor_amovel: done.")
