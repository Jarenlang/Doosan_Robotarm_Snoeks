from doosan_backend import load_config, DoosanGatewayClient, save_config, is_robot_enabled
import time
"""
doosan_sequence.py

 functies voor het maken van een sequence:

- Beweging (TCP, async + wachten tot stilstand):
    self.gateway.amovel(x, y, z, rx, ry, rz, velx, accx)        Hiermee wordt de robot aangestuurd om naar de coordinaat tussen de haakjes te bewegen
    self.gateway.wait_until_stopped()                           Hiermee wordt geforceerd te wachten in de sequence totdat de robot tot stilstand is gekomen

    Of met posities uit config:
    self.gateway.amovel(*self.p_home, self.velx, self.accx)     Je kan ook waarden opslaan in de Config.json bestand. Die kun je dan aanroepen in de sequence (bijvoorbeeld handig als je een plek vaker nodig hebt.
    self.gateway.wait_until_stopped()                           zie bovenstaande opmerking
    
    self.sensor_amovel(base_pos=self.ppick, direction="z-", pre_distance=250.0, force_limit=30.0, statuscallback=logmsg)        Hiermee kan de robot naar beneden bewegen totdat de robot iets raakt.

- Digitale IO:
    self.gateway.set_digital_output(index, value)               Hiermee kun je een Digital Output (index) aan of uit zetten (met Value 1 = hoog, 0 = laag)
    v = self.gateway.get_digital_input(index)                   Hiermee kun je de staat van de gekozen input uitlezen, en die opslaan in een waarde (nu v)

- Sequence-status loggen (wordt ook in de GUI getoond):
    def log(msg: str):
        print(msg)
        if status_callback:
            status_callback(msg)

- Skeleton van een eigen sequence-functie:
    def my_sequence(self, status_callback=None):                naam van de sequence is belangrijk (nu my_sequence) en daarmee roep je de sequence aan
        def log(msg: str):                                      dit zorgt ervoor dat de gegevens met de log() functie worden gestuurd naar de terminal van de GUI
            print(msg)
            if status_callback:
                status_callback(msg)

        self.reset_stop()                                       Dit voorkomt dat de robot in een soft stop staat, en dat we zeker weten dat er niks fout gaat.
        self.apply_parameters()

        log("Naar home")
        self.gateway.amovel(*self.p_home, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence gestopt")
            return

        # hier je eigen stappen...
"""

class RobotProgram:
    def __init__(self, gateway: DoosanGatewayClient):
        self.gateway = gateway
        self.config = load_config()

        self.operation_speed = self.config.get("operation_speed")
        self.velx = self.config.get("velx")
        self.accx = self.config.get("accx")

        self.p_home = self.config.get("p_home")
        self.p_pick = self.config.get("p_pick")
        self.p_aside = self.config.get("p_aside")
        self.p_move_out = self.config.get("p_move_out")
        self.p_move_up = self.config.get("p_move_up")
        self.p_move_infront = self.config.get("p_move_infront")
        self.p_tussenstop = self.config.get("p_tussenstop")
        self.p_tussenstop_2 = self.config.get("p_tussenstop_2")
        self.p_voor_beugel = self.config.get("p_voor_beugel")
        self.p_in_houder = self.config.get("p_in_houder")
        self.p_opzij = self.config.get("p_opzij")
        self.p_armrest_pick = self.config.get("p_armrest_pick")
        self.p_armrest_tussenstop = self.config.get("p_armrest_tussenstop")
        self.p_armrest_infront = self.config.get("p_armrest_infront")
        self.p_armrest_inframe = self.config.get("p_armrest_inframe")
        self._stop_flag = False

        # QR / product flags
        self.do_gordels = False
        self.do_armsteunen = False
        self.do_seatbelts = False

    # ----------------- Basis helpers -----------------

    def save_parameters_to_config(self):
        """Schrijf huidige waarden terug naar configuratiebestand (config.json)."""
        self.config["operation_speed"] = self.operation_speed
        self.config["velx"] = self.velx
        self.config["accx"] = self.accx
        self.config["p_home"] = self.p_home
        self.config["p_pick"] = self.p_pick
        self.config["p_aside"] = self.p_aside
        self.config["p_move_out"] = self.p_move_out
        self.config["p_move_up"] = self.p_move_up
        self.config["p_move_infront"] = self.p_move_infront
        self.config["p_tussenstop"] = self.p_tussenstop
        self.config["p_tussenstop_2"] = self.p_tussenstop_2
        self.config["p_voor_beugel"] = self.p_voor_beugel
        self.config["p_in_houder"] = self.p_in_houder
        self.config["p_opzij"] = self.p_opzij
        self.config["p_armrest_pick"] = self.p_armrest_pick
        self.config["p_armrest_tussenstop"] = self.p_armrest_tussenstop
        self.config["p_armrest_infront"] = self.p_armrest_infront
        self.config["p_armrest_inframe"] = self.p_armrest_inframe


        # eventueel ook IP en poort opslaan
        self.config["robot_ip"] = self.gateway.ip
        self.config["port"] = self.gateway.port
        save_config(self.config)

    def apply_parameters(self):
        """Stuur huidige parameters naar de robot."""
        self.gateway.change_operation_speed(self.operation_speed)
        self.gateway.set_velx(self.velx)
        self.gateway.set_accx(self.accx)

    def request_stop(self):
        """Externe stopaanvraag (bijv. vanuit GUI)."""
        self._stop_flag = True
        self.gateway.stop()

    def sensor_amovel(self, base_pos, direction="z-", pre_distance=250.0, force_limit=30.0, statuscallback=None):

        def logmsg(msg: str):
            print(msg)
            if statuscallback:
                statuscallback(msg)

        self._stop_flag = False

        # Richtingsvector
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
            logmsg(f"Ongeldige richting: {direction}")
            return

        bx, by, bz, brx, bry, brz = base_pos

        # Doelpositie: 250 mm in één keer in gekozen richting
        target = [
            bx + dx * pre_distance,
            by + dy * pre_distance,
            bz + dz * pre_distance,
            brx, bry, brz,
        ]

        self.gateway.change_operation_speed(20)
        logmsg(f"sensor_amovel: beweeg in één keer naar {target}")
        self.gateway.amovel(*target, 20, 1000)
        if self._stop_flag:
            logmsg("Sequence gestopt voor force-check.")
            return

        # Force monitoren; bij overschrijding direct stoppen en terug
        logmsg(f"sensor_amovel: force-monitor starten, limiet {force_limit} N")
        while not self._stop_flag:
            try:
                force_value = self.gateway.get_tool_force(0)
            except Exception as e:
                logmsg(f"Fout bij uitlezen force: {e}")
                self._stop_flag = True
                self.gateway.stop()
                force_value = None

            if force_value is not None:
                logmsg(f"Huidige force: {force_value:.2f} N")
                if force_value >= force_limit:
                    logmsg("Force-limiet bereikt, stuur stop en terug naar vorige coordinaat.")
                    try:
                        # directe stop
                        self.gateway.stop()
                    except Exception as e:
                        logmsg(f"Fout bij stop-commando: {e}")
                    break

        # DO2 aan
        try:
            self.gateway.set_digital_output(2, 1)  # DO2 hoog [file:1][file:3]
            logmsg("DO2 = 1 gezet.")
        except Exception as e:
            logmsg(f"Fout bij DO2 zetten: {e}")

        # Terug naar oorspronkelijke (base) positie in één beweging
        self.gateway.change_operation_speed(self.operation_speed)
        up_target = [bx, by, bz, brx, bry, brz]
        logmsg(f"sensor_amovel: terug naar vorige coordinaat {up_target}")
        self.gateway.amovel(*up_target, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        logmsg("sensor_amovel: klaar.")


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

    def sequence_pick_and_place(self, status_callback=None):

        def log(msg: str):
            print(msg)
            if status_callback:
                status_callback(msg)

        self._stop_flag = False
        log("sequence actief")

        if not is_robot_enabled(self):
            log("Robot is niet enabled via schakelaar; sequence wordt niet gestart.")
            return

        self.wait_for_operator_confirm(status_callback)
        """"
        Begin hieronder met het coderen van de sequence-functie:
        """

        log("Naar home")
        self.gateway.amovel(*self.p_home, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence gestopt")
            return

        log("Naar pick armrest")
        self.gateway.amovel(*self.p_armrest_pick, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence gestopt")
            return

        self.sensor_amovel(base_pos=self.p_armrest_pick, direction="z-", pre_distance=250.0, force_limit=7)

        log("Naar tussenstop armrest")
        self.gateway.amovel(*self.p_armrest_tussenstop, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence gestopt")
            return

        log("Naar infront armrest")
        self.gateway.amovel(*self.p_armrest_infront, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence gestopt")
            return

        log("Naar inframe armrest")
        self.gateway.amovel(*self.p_armrest_inframe, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence gestopt")
            return

        self.gateway.set_digital_output(2, 0)
        time.sleep(0.2)

        log("Naar tussenstop armrest")
        self.gateway.amovel(*self.p_armrest_tussenstop, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence gestopt")
            return

        log("Naar pick armrest")
        self.gateway.amovel(*self.p_armrest_pick, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence gestopt")
            return

        log("Naar home")
        self.gateway.amovel(*self.p_home, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence gestopt")
            return

        #Sequence voor het oppakken van de buckles
        
        # 2) Naar pick
        log("Naar pick buckle")
        self.gateway.amovel(*self.p_pick, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence gestopt")
            return

        # 3) Naar place
        log("naar aside")
        self.gateway.change_operation_speed(15)
        self.gateway.amovel(*self.p_aside, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        self.gateway.change_operation_speed(100)

        # 3,5)
        self.gateway.set_digital_output(1, 1)
        self.wait_for_operator_confirm(status_callback)

        # 4) Naar pick
        log("terug omhoog bewegen")
        self.gateway.amovel(*self.p_move_out, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence gestopt")
            return

        # 5)
        log("beweeg naar voor")
        self.gateway.amovel(*self.p_move_infront, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence gestopt")
            return

        # 6)
        log("beweeg in houder")
        self.gateway.change_operation_speed(15)
        self.gateway.amovel(*self.p_in_houder, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        self.gateway.change_operation_speed(100)
        if self._stop_flag:
            log("Sequence gestopt")
            return

        # 6,5)
        self.gateway.set_digital_output(1, 0)
        self.wait_for_operator_confirm(status_callback)


        # 7)
        log("beweeg opzij")
        self.gateway.amovel(*self.p_opzij, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence gestopt")
            return

        # 8)
        log("home")
        self.gateway.amovel(*self.p_home, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence gestopt")
            return
