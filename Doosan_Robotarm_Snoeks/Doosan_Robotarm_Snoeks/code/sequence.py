import time
from backend import (load_config, save_config, load_coordinates, DoosanGatewayClient, is_robot_enabled, sensor_amovel, scan_and_validate_single)


class RobotProgram:
    def __init__(self, gateway: DoosanGatewayClient):
        self.gateway = gateway
        self.config = load_config()

        self.operation_speed = self.config.get("operation_speed")
        self.velx = self.config.get("velx")
        self.accx = self.config.get("accx")

        coord_cfg = load_coordinates()
        for key, value in coord_cfg.items():
            if key.startswith("p_") or key.startswith("pj_"):
                setattr(self, key, value)
        self._stop_flag = False

        # QR / product flags
        self.do_seatbelts = False
        self.do_armrests = False
        self.do_buckles = False
        self.workorder_id: str | None = None

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

    def sequence_buckles(self, statuscallback=None):
        def log(msg: str):
            print(msg)
            if statuscallback:
                statuscallback(msg)
        log("buckles")

        scan_and_validate_single(self, "buckles", statuscallback)
        if self._stop_flag:
            return
        log("successsssssssssssssssssssssssssssssssssssssssssss")


    def sequence_armrest(self, statuscallback=None):
        def log(msg: str):
            print(msg)
            if statuscallback:
                statuscallback(msg)

        buffer_vol = self.gateway.get_digital_input(16)

        if not buffer_vol:
            self.gateway.set_digital_output(16, 1)
            log("Armrest cover buffer is empty")  # De tekst "Armrest cover buffer is empty"
            self.wait_for_operator_confirm(statuscallback)

        if buffer_vol:  # Wanneer buffer vol is en de knop niet ingedrukt
            log("Buffer filled")  # De tekst "Buffer filled, waiting for operator"

        self.gateway.set_digital_output(16, 0)

        # 1) Naar home
        log("Naar home")
        self.gateway.amovej(*self.pj_home, self.velx, self.accx)
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
        sensor_amovel(self, base_pos=self.p_armrest_pick, force_limit=7, direction="z-", pre_distance=150.0, return_direction="y+", return_distance=200.0)

        # 4) Naar tussenstop
        log("Naar tussenstop armrest")
        self.gateway.amovej(*self.pj_home, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence gestopt")
            return

        self.gateway.set_digital_output(2, 0)

    def sequence_seatbelts(self, statuscallback=None):
        def log(msg: str):
            print(msg)
            if statuscallback:
                statuscallback(msg)

        scan_and_validate_single(self, "seatbelts", statuscallback)
        if self._stop_flag:
            return

        # Seatbelt buffer, vooraf gaand aan het proces wordt gekeken of de buffer vol is.
        buffer_leeg_seatbelt_1 = self.gateway.get_digital_input(9)  # Code kijkt hier naar pin 17
        buffer_leeg_seatbelt_2 = self.gateway.get_digital_input(10)  # Code kijkt hier naar pin 18
        buffer_leeg_seatbelt_3 = self.gateway.get_digital_input(11)  # Code kijkt hier naar pin 19
        log("test")

        if buffer_leeg_seatbelt_1 and buffer_leeg_seatbelt_2 and buffer_leeg_seatbelt_3:  # als buffer 1, 2, 3 leeg zijn...
            log("Buffer seatbelt full")  # Stuur de tekst "buffer seatbelt full"

        if not buffer_leeg_seatbelt_1 and not buffer_leeg_seatbelt_2 and not buffer_leeg_seatbelt_3:  # Als de buffer NIET leeg is...
            self.gateway.set_digital_output(16, 1)  # Stuur een signiaal (1) naar pin 16 (Warning Light)
            log("All seatbelt buffers are empty")  # Stuur de tekst: "All seatbelt buffers are empty"
            self.wait_for_operator_confirm(statuscallback)  # Wacht tot de groene knop wordt ingedrukt.

        self.gateway.set_digital_output(16,0)  # Naar pin 16 (warning light) wordt geen signiaal meer gestuurd (0)


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
            self.sequence_buckles(statuscallback)
        elif self.do_armrests:
            self.sequence_armrest(statuscallback)
        elif self.do_seatbelts:
            self.sequence_seatbelts(statuscallback)
        else:
            log("Geen geldig product gekozen uit QR-code, sequence wordt niet uitgevoerd.")