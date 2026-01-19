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

        scan_and_validate_single(self, "buckles", statuscallback)
        if self._stop_flag:
            return


    def sequence_armrest(self, statuscallback=None):
        def log(msg: str):
            print(msg)
            if statuscallback:
                statuscallback(msg)

        while True:
            buffer_vol = self.gateway.get_digital_input(16)

            if buffer_vol:
                log("Buffer filled")
                break

            self.gateway.set_digital_output(4, 1)
            time.sleep(0.5)
            self.gateway.set_digital_output(4, 0)
            time.sleep(0.1)

        self.wait_for_operator_confirm(statuscallback)
        self.gateway.set_digital_output(4, 0)

        # 1) Naar home
        log("Naar home")
        self.gateway.amovej(*self.pj_home, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence gestopt")
            return

        log("Naar armrest pick")
        self.gateway.amovej(*self.pj_armrest_pick, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence gestopt")
            return

        # 3) Naar beneden en zuiger aan
        sensor_amovel(self, base_pos=self.p_armrest_pick, force_limit=12, direction="z+", pre_distance=250.0, return_direction="y+", return_distance=200.0)

        # 4) Naar tussenstop
        log("Naar tussenstop armrest")
        self.gateway.amovej(*self.pj_armrest_tussenstop, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence gestopt")
            return

        log("Naar infront")
        self.gateway.amovej(*self.pj_armrest_infront, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence gestopt")
            return

        log("Naar inframe")
        self.gateway.amovel(*self.p_armrest_inframe, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence gestopt")
            return

        self.gateway.set_digital_output(2, 0)
        time.sleep(0.5)

        log("Naar infront")
        self.gateway.amovej(*self.pj_armrest_infront, self.velx, (self.accx/4))
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence gestopt")
            return

        # 4) Naar home
        log("Naar home")
        self.gateway.amovej(*self.pj_home, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence gestopt")
            return

        log("Naar armrest pick")
        self.gateway.amovej(*self.pj_armrest_pick, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence gestopt")
            return

        # 3) Naar beneden en zuiger aan
        sensor_amovel(self, base_pos=self.p_armrest_pick, force_limit=12, direction="z+", pre_distance=250.0,return_direction="y+", return_distance=200.0)

        # 4) Naar tussenstop
        log("Naar tussenstop armrest")
        self.gateway.amovej(*self.pj_armrest_tussenstop, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence gestopt")
            return

        log("Naar infront")
        self.gateway.amovej(*self.pj_armrest_infront2, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence gestopt")
            return

        log("Naar inframe")
        self.gateway.amovel(*self.p_armrest_inframe2, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence gestopt")
            return

        log("Naar inframe")
        self.gateway.amovel(*self.p_armrest_inframe_down, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence gestopt")
            return

        self.gateway.set_digital_output(2, 0)
        time.sleep(0.5)

        log("Naar infront")
        self.gateway.amovej(*self.pj_armrest_infront2, self.velx, (self.accx/4))
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence gestopt")
            return

        # 4) Naar tussenstop
        log("Naar home")
        self.gateway.amovej(*self.pj_home, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence gestopt")
            return

    def sequence_seatbelts(self, statuscallback=None):
        def log(msg: str):
            print(msg)
            if statuscallback:
                statuscallback(msg)

        while True:
            try:
                s13 = self.gateway.get_digital_input(13)
                s14 = self.gateway.get_digital_input(14)
                s15 = self.gateway.get_digital_input(15)
            except Exception:
                s13 = s14 = s15 = 0

            if not (s13 and s14 and s15):
                self.gateway.set_digital_output(4, 1)
                time.sleep(0.5)
                self.gateway.set_digital_output(4, 0)
                time.sleep(0.1)

                continue

            log("Alle seatbelt-buffers gevuld, sequence gaat verder.")
            self.gateway.set_digital_output(4, 0)
            break

        self.gateway.set_digital_output(1, 0)

        # Seatbelt buffer, vooraf gaand aan het proces wordt gekeken of de buffer vol is.
        buffer_leeg_seatbelt_1 = self.gateway.get_digital_input(9)
        buffer_leeg_seatbelt_2 = self.gateway.get_digital_input(10)
        buffer_leeg_seatbelt_3 = self.gateway.get_digital_input(11)

        if buffer_leeg_seatbelt_1 and buffer_leeg_seatbelt_2 and buffer_leeg_seatbelt_3:
            log("Buffer seatbelt full")

        if not buffer_leeg_seatbelt_1 or not buffer_leeg_seatbelt_2 or not buffer_leeg_seatbelt_3:
            self.gateway.set_digital_output(16, 1)
            log("All seatbelt buffers are empty")
            self.wait_for_operator_confirm(statuscallback)

        scan_and_validate_single(self, "seatbelts", statuscallback)

        self.gateway.set_digital_output(16, 0)

        log("home")
        self.gateway.amovej(*self.pj_home, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence gestopt")
            return

        log("boven pickup point")
        self.gateway.amovej(*self.pj_seatbelt_boven_pickup, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence gestopt")
            return

        log("pickup point")
        self.gateway.amovel(*self.p_seatbelt_pickup, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence gestopt")
            return

        self.gateway.set_digital_output(1, 1)

        log("move up")
        self.gateway.amovel(*self.p_seatbelt_moveup, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence gestopt")
            return

        log("move up v2")
        self.gateway.amovej(*self.pj_seatbelt_moveupv2, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence gestopt")
            return

        log("passthrough")
        self.gateway.amovej(*self.pj_seatbelt_passthrough, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence gestopt")
            return

        log("doorframe")
        self.gateway.amovel(*self.p_seatbelt_doorframe, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence gestopt")
            return

        log("half")
        self.gateway.amovel(*self.p_seatbelt_half, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence gestopt")
            return

        log("above")
        self.gateway.amovel(*self.p_seatbelt_aboveholder, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence gestopt")
            return

        log("in")
        self.gateway.amovel(*self.p_seatbelt_inholder, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence gestopt")
            return

        self.gateway.set_digital_output(1, 0)

        log("uit")
        self.gateway.amovel(*self.p_seatbelt_pre_uit, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence gestopt")
            return

        log("uit")
        self.gateway.amovel(*self.p_seatbelt_uit, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence gestopt")
            return

        log("boven pickup")
        self.gateway.amovej(*self.pj_seatbelt2_boven_pickup, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence gestopt")
            return

        log("pickup")
        self.gateway.amovel(*self.p_seatbelt2_pickup, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence gestopt")
            return

        self.gateway.set_digital_output(1, 1)

        log("2 moveup")
        self.gateway.amovel(*self.p_seatbelt2_moveup, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence gestopt")
            return

        log("2 moveupv2")
        self.gateway.amovej(*self.pj_seatbelt2_moveupv2, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence gestopt")
            return

        log("2 passthrough")
        self.gateway.amovej(*self.pj_seatbelt2_passthrough, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence gestopt")
            return

        log("doorframe")
        self.gateway.amovel(*self.p_seatbelt2_doorframe, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence gestopt")
            return

        log("half")
        self.gateway.amovel(*self.p_seatbelt2_half, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence gestopt")
            return

        log("above")
        self.gateway.amovel(*self.p_seatbelt2_aboveholder, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence gestopt")
            return

        log("in")
        self.gateway.amovel(*self.p_seatbelt2_inholder, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence gestopt")
            return

        self.gateway.set_digital_output(1, 0)

        log("uit")
        self.gateway.amovel(*self.p_seatbelt2_pre_uit, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence gestopt")
            return

        log("uit")
        self.gateway.amovel(*self.p_seatbelt2_uit, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence gestopt")
            return

        log("3 boven pickup")
        self.gateway.amovej(*self.pj_seatbelt3_boven_pickup, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence gestopt")
            return

        log("3 pickup")
        self.gateway.amovel(*self.p_seatbelt3_pickup, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence gestopt")
            return

        self.gateway.set_digital_output(1, 1)

        log("3 moveup")
        self.gateway.amovel(*self.p_seatbelt3_moveup, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence gestopt")
            return

        log("3 moveupv2")
        self.gateway.amovej(*self.pj_seatbelt3_moveupv2, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence gestopt")
            return

        log("3 passthrough")
        self.gateway.amovej(*self.pj_seatbelt3_passthrough, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence gestopt")
            return

        log("3 doorframe")
        self.gateway.amovej(*self.pj_seatbelt3_doorframe, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence gestopt")
            return

        log("3 half")
        self.gateway.amovel(*self.p_seatbelt3_half, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence gestopt")
            return

        log("3 above")
        self.gateway.amovel(*self.p_seatbelt3_aboveholder, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence gestopt")
            return

        log("3 in")
        self.gateway.amovel(*self.p_seatbelt3_inholder, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence gestopt")
            return

        self.gateway.set_digital_output(1, 0)

        log("3 uit")
        self.gateway.amovel(*self.p_seatbelt3_pre_uit, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence gestopt")
            return

        log("3 uit")
        self.gateway.amovel(*self.p_seatbelt3_uit, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence gestopt")
            return


        log("home")
        self.gateway.amovej(*self.pj_home, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence gestopt")
            return

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
        self.sequence_armrest(statuscallback)
