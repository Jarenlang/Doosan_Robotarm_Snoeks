from backend import (load_config, save_config, load_coordinates, DoosanGatewayClient, is_robot_enabled, sensor_amovel)
import time

class RobotProgram:
    def __init__(self, gateway: DoosanGatewayClient):
        self.gateway = gateway
        self.config = load_config()

        self.operation_speed = self.config.get("operation_speed")
        self.velx = self.config.get("velx")
        self.accx = self.config.get("accx")

        coord_cfg = load_coordinates()
        for key, value in coord_cfg.items():
            if key.startswith("p_"):
                setattr(self, key, value)
        self._stop_flag = False

        # QR / product flags
        self.do_gordels = False
        self.do_armsteunen = False
        self.do_buckles = False

    # ----------------- Basis helpers -----------------

    def save_parameters_to_config(self):
        # bestaande config-waarden
        self.config["operation_speed"] = self.operation_speed
        self.config["velx"] = self.velx
        self.config["accx"] = self.accx
        save_config(self.config)

    def apply_parameters(self):
        """Stuur huidige parameters naar de robot."""
        self.gateway.change_operation_speed(self.operation_speed)
        self.gateway.set_velx(self.velx)
        self.gateway.set_accx(self.accx)

    def wait_for_operator_confirm(self, statuscallback=None):
        if statuscallback:
            statuscallback("Wachten op operatorbevestiging (groene knop)...")

        while True:
            try:
                btn1 = self.gateway.get_digital_input(1)
                btn4 = self.gateway.get_digital_input(4)
            except Exception:
                btn1 = 0
                btn4 = 0
            if btn1 == 1 or btn4 == 1:
                if statuscallback:
                    statuscallback("Groene knop ingedrukt, sequence gaat verder.")
                break
            time.sleep(0.1)

    # ----------------- Voorbeeld-sequence -----------------

    def sequence_seatbelt(self, statuscallback=None):
        def log(msg: str):
            print(msg)
            if statuscallback:
                statuscallback(msg)


    def sequence_armrest(self, statuscallback=None):
        def log(msg: str):
            print(msg)
            if statuscallback:
                statuscallback(msg)

        # 1) Naar home
        log("Naar home")
        self.gateway.amovel(*self.p_home, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence gestopt")
            return

        log("Naar armrest pick")
        self.gateway.amovel(*self.p_armrest_pick, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence gestopt")
            return

        # 3) Naar beneden en zuiger aan
        sensor_amovel(self, base_pos=self.p_armrest_pick, force_limit=9, direction="z-", pre_distance=150.0, return_direction="y+", return_distance=200.0)

        # 4) Naar tussenstop
        log("Naar tussenstop armrest")
        self.gateway.amovel(*self.p_home, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence gestopt")
            return

        # 4) Naar tussenstop
        log("Naar tussenstop armrest")
        self.gateway.amovel(*self.p_home, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence gestopt")
            return

        self.gateway.set_digital_output(2, 0)


    def sequence_gordelspoelen(self, statuscallback=None):
        def log(msg: str):
            print(msg)
            if statuscallback:
                statuscallback(msg)



    def sequence_pick_and_place(self, statuscallback=None):
        def log(msg: str):
            print(msg)
            if statuscallback:
                statuscallback(msg)

        self._stop_flag = False
        log("Hoofdsequence actief.")

        if not is_robot_enabled(self):
            log("Robot is niet enabled via schakelaar, sequence wordt niet gestart.")
            return

        # Wachten op operator
        self.wait_for_operator_confirm(statuscallback)

        # Bepaal welke sequence
        if self.do_buckles:
            self.sequence_seatbelt(statuscallback)
        elif self.do_armsteunen:
            self.sequence_armrest(statuscallback)
        elif self.do_gordels:
            self.sequence_gordelspoelen(statuscallback)
        else:
            log("Geen geldig product gekozen uit QR-code, sequence wordt niet uitgevoerd.")