from doosan_backend import *
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
        self.do_seatbelt = False
        self.do_armrest = False
        self.do_buckle = False

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
            statuscallback("Waiting for operator conformation (green button)...")

        while True:
            try:
                btn1 = self.gateway.get_digital_input(1)
                btn4 = self.gateway.get_digital_input(4)
            except Exception:
                btn1 = 0
                btn4 = 0
            if btn1 == 1 or btn4 == 1:
                if statuscallback:
                    statuscallback("Green button pressed, sequence continued.")
                break
            time.sleep(0.1)

    # ----------------- Voorbeeld-sequence -----------------

    def sequence_seatbelt(self, statuscallback=None):
        def log(msg: str):
            print(msg)
            if statuscallback:
                statuscallback(msg)

        # 1) Naar Home
        log("Naar home")
        self.gateway.amovel(*self.p_buckle_home, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence stopped")
            return

        log("Naar tussenstop")
        self.gateway.amovel(*self.p_buckle_tussen, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence stopped")
            return

        # 2) Naar
        log("Naar aside")
        self.gateway.amovel(*self.p_buckle_aside, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence stopped")
            return

        # 3) Naar
        log("naar pick")
        self.gateway.amovel(*self.p_buckle_pick, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence stopped")
            return

        # 3,5) Gripper dicht
        self.gateway.set_digital_output(1, 1)

        # 4) Naar pick
        log("terug omhoog bewegen")
        self.gateway.amovel(*self.p_buckle_move_out, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence stopped")
            return

        # 5) Naar tussen positie
        log("beweeg naar voor")
        self.gateway.amovel(*self.p_buckle_move_infront, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence stopped")
            return

        # 6) Naar houder
        log("beweeg in houder")
        self.gateway.change_operation_speed(60)
        self.gateway.amovel(*self.p_buckle_in_houder, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        self.gateway.change_operation_speed(self.operation_speed)
        if self._stop_flag:
            log("Sequence stopped")
            return

        # 6,5) Gripper open
        self.gateway.set_digital_output(1, 0)

        # 7) Naar vrije ruimte
        log("beweeg opzij")
        self.gateway.amovel(*self.p_buckle_opzij, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence stopped")
            return

        # 8) Naar home
        log("home")
        self.gateway.amovel(*self.p_buckle_home, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence stopped")
            return

    def sequence_armrest(self, statuscallback=None):
        def log(msg: str):
            print(msg)
            if statuscallback:
                statuscallback(msg)

        # 1) Naar home
        log("Naar tussentop")
        self.gateway.amovel(*self.p_armrest_tussenstop, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence stopped")
            return

        # 2) Naar pick
        log("Naar pick armrest")
        self.gateway.amovel(*self.p_armrest_pick, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence stopped")
            return

        # 3) Naar beneden en zuiger aan
        self.gateway.sensor_amovel(
            self,
            base_pos=self.p_armrest_pick,
            direction="z-",
            pre_distance=250.0,
            force_limit=9,
            return_direction="y+",  # bijvoorbeeld naar voren
            return_distance=100.0,  # bijvoorbeeld 100 mm
        )

        # 2) Naar pick
        log("Naar pick armrest")
        self.gateway.amovel(*self.p_armrest_pick, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence stopped")
            return

        # 4) Naar tussenstop
        log("Naar tussenstop armrest")
        self.gateway.amovel(*self.p_armrest_uitbewegen, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence stopped")
            return

        # 4) Naar prepositie frame
        log("Naar infront armrest")
        self.gateway.amovel(*self.p_armrest_infront, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence stopped")
            return

        # 5) Naar houder
        log("Naar inframe armrest")
        self.gateway.amovel(*self.p_armrest_inframe, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence stopped")
            return

        # 6) zuiger uit
        self.gateway.set_digital_output(2, 0)
        time.sleep(0.2)

        # 7) Terug naar tussenstop
        log("Naar tussenstop armrest")
        self.gateway.amovel(*self.p_armrest_tussenstop, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence stopped")
            return

        # 7) Terug naar pick
        log("Naar pick armrest")
        self.gateway.amovel(*self.p_armrest_pick, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence stopped")
            return

        # 7) Terug naar home
        log("Naar home")
        self.gateway.amovel(*self.p_home, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence stopped")
            return

    def sequence_seatbeltpoelen(self, statuscallback=None):
        def log(msg: str):
            print(msg)
            if statuscallback:
                statuscallback(msg)

        log("Naar home")
        self.gateway.amovel(*self.p_home, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence stopped")
            return

        log("seatbelt pickup")
        self.gateway.amovel(*self.p_seatbelt_pickup, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence stopped")
            return

        log("seatbelt down")
        self.gateway.amovel(*self.p_seatbelt_down, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence stopped")
            return

        self.gateway.set_digital_output(1, 1)

        log("seatbelt pickup")
        self.gateway.amovel(*self.p_seatbelt_pickup, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence stopped")
            return

        log("seatbelt tussen pos")
        self.gateway.amovel(*self.p_seatbelt_tussenpositie, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence stopped")
            return

        log("seatbelt door frame")
        self.gateway.amovel(*self.p_seatbelt_door_frame, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence stopped")
            return

        log("seatbelt boven gat?")
        self.gateway.amovel(*self.p_seatbelt_hoogte_gat, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence stopped")
            return

        log("seatbelt seatbelt voor gat")
        self.gateway.amovel(*self.p_seatbelt_voor_gat, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence stopped")
            return

        log("seatbelt seatbelt boven gat")
        self.gateway.amovel(*self.p_seatbelt_boven_gat, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence stopped")
            return

        log("seatbelt voor insteek")
        self.gateway.amovel(*self.p_seatbelt_voorinsteek, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence stopped")
            return

        log("seatbelt seatbelt in gat")
        self.gateway.amovel(*self.p_seatbelt_in_gat, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence stopped")
            return

        self.gateway.set_digital_output(1, 0)

        log("seatbelt seatbelt is los")
        self.gateway.amovel(*self.p_seatbelt_los, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence stopped")
            return

        log("seatbelt seatbelt weg")
        self.gateway.amovel(*self.p_seatbelt_weg, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence stopped")
            return

        log("seatbelt home")
        self.gateway.amovel(*self.p_home, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence stopped")
            return

    def sequence_pick_and_place(self, statuscallback=None):
        def log(msg: str):
            print(msg)
            if statuscallback:
                statuscallback(msg)

        self._stop_flag = False
        log("Main sequence active.")

        if not is_robot_enabled(self):
            log("Robot is not enabled by switch, sequence not allowed to start.")
            return

        # Wachten op operator
        self.wait_for_operator_confirm(statuscallback)

        # Bepaal welke sequence
        if self.do_buckle:
            self.sequence_seatbelt(statuscallback)
        elif self.do_armrest:
           self.sequence_armrest(statuscallback)
        elif self.do_seatbelt:
            self.sequence_seatbeltpoelen(statuscallback)
        else:
            log("No product found from QR-code, sequence not allowed to start.")
