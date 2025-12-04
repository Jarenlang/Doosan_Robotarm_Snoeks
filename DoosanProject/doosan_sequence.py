from doosan_backend import load_config, DoosanGatewayClient, save_config

# ----------------------------------------------------
# POSITIES VOOR QR-SEQUENCES
# ----------------------------------------------------

GORDELS_POSITIES = [
    (-66.746, 853.767, 300.617, 0.01, 179.999, 160.342),
    (-66.746, 753.767, 400.617, 0.01, 179.999, 160.342),
    (40.746, 853.767, 400.617, 0.01, 179.999, 160.342),
]

ARMSTEUNEN_POSITIES = [
    (-66.746, 853.767, 300.617, 0.01, 179.999, 160.342),
    (-66.746, 753.767, 400.617, 0.01, 179.999, 160.342),
    (-40.746, 853.767, 400.617, 0.01, 179.999, 160.342),
]


class RobotProgram:
    def __init__(self, gateway: DoosanGatewayClient):
        self.gateway = gateway
        self.config = load_config()

        self.operation_speed = self.config["operation_speed"]
        self.velx = self.config["velx"]
        self.accx = self.config["accx"]

        self.p_home = self.config["p_home"]
        self.p_pick = self.config["p_pick"]
        self.p_place = self.config["p_place"]

        self._stop_flag = False

    # --------------------------------------------------------
    # Config
    # --------------------------------------------------------

    def save_parameters_to_config(self):
        self.config["operation_speed"] = self.operation_speed
        self.config["velx"] = self.velx
        self.config["accx"] = self.accx
        self.config["p_home"] = self.p_home
        self.config["p_pick"] = self.p_pick
        self.config["p_place"] = self.p_place
        self.config["robot_ip"] = self.gateway.ip
        self.config["port"] = self.gateway.port
        save_config(self.config)

    def apply_parameters(self):
        self.gateway.change_operation_speed(self.operation_speed)
        self.gateway.set_velx(self.velx)
        self.gateway.set_accx(self.accx)

    # --------------------------------------------------------
    # Stop
    # --------------------------------------------------------

    def request_stop(self):
        self._stop_flag = True
        self.gateway.stop()

    def reset_stop(self):
        self._stop_flag = False

    # --------------------------------------------------------
    # IO
    # --------------------------------------------------------

    def set_do(self, i, v):
        self.gateway.set_digital_output(i, v)

    def get_di(self, i):
        return self.gateway.get_digital_input(i)

    # --------------------------------------------------------
    # SEQUENCES
    # --------------------------------------------------------

    def sequence_gordels(self, status_callback=None):
        def log(msg):
            if status_callback: status_callback(msg)

        self.reset_stop()
        self.apply_parameters()
        log("Gordels sequence gestart")

        for (x, y, z, rx, ry, rz) in GORDELS_POSITIES:
            if self._stop_flag:
                log("Sequence gestopt")
                return
            self.gateway.amovel(x, y, z, rx, ry, rz, self.velx, self.accx)
            self.gateway.wait_until_stopped()

        log("Gordels sequence klaar")

    def sequence_armsteunen(self, status_callback=None):
        def log(msg):
            if status_callback: status_callback(msg)

        self.reset_stop()
        self.apply_parameters()
        log("Armsteunen sequence gestart")

        for (x, y, z, rx, ry, rz) in ARMSTEUNEN_POSITIES:
            if self._stop_flag:
                log("Sequence gestopt")
                return
            self.gateway.amovel(x, y, z, rx, ry, rz, self.velx, self.accx)
            self.gateway.wait_until_stopped()

        log("Armsteunen sequence klaar")

    # --------------------------------------------------------
    # QR PRODUCTFLOW
    # --------------------------------------------------------

    def sequence_from_qr(self, code, status_callback=None):

        def log(msg):
            if status_callback: status_callback(msg)

        if code == 1:
            log("QR=1 → alleen gordels")
            self.sequence_gordels(status_callback)

        elif code == 2:
            log("QR=2 → gordels + armsteunen")
            self.sequence_gordels(status_callback)
            log("Wachten op operator voor armsteunen…")
            return "WAIT_OPERATOR"

        elif code == 3:
            log("QR=3 → alleen armsteunen")
            self.sequence_armsteunen(status_callback)

        elif code == 4:
            log("QR=4 → geen acties nodig")

        else:
            log("Onbekende QR-code")
