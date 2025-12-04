from doosan_backend import load_config, DoosanGatewayClient, save_config
"""
doosan_sequence.py

test voor github

 functies voor het maken van een sequence:

- Beweging (TCP, async + wachten tot stilstand):
    self.gateway.amovel(x, y, z, rx, ry, rz, velx, accx)        Hiermee wordt de robot aangestuurd om naar de coordinaat tussen de haakjes te bewegen
    self.gateway.wait_until_stopped()                           Hiermee wordt geforceerd te wachten in de sequence totdat de robot tot stilstand is gekomen

    Of met posities uit config:
    self.gateway.amovel(*self.p_home, self.velx, self.accx)     Je kan ook waarden opslaan in de Config.json bestand. Die kun je dan aanroepen in de sequence (bijvoorbeeld handig als je een plek vaker nodig hebt.
    self.gateway.wait_until_stopped()                           zie bovenstaande opmerking

- Digitale IO:
    self.set_do(index, value)   # 0/1, bv. self.set_do(0, 1)    Hiermee kun je een Digital Output (index) aan of uit zetten (met Value 1 = hoog, 0 = laag)
    v = self.get_di(index)      # 0/1, bv. v = self.get_di(3)   Hiermee kun je de staat van de gekozen input uitlezen, en die opslaan in een waarde (nu v)

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
        self.p_place = self.config.get("p_place")
        self._stop_flag = False

    # ----------------- Basis helpers -----------------

    def save_parameters_to_config(self):
        """Schrijf huidige waarden terug naar configuratiebestand (config.json)."""
        self.config["operation_speed"] = self.operation_speed
        self.config["velx"] = self.velx
        self.config["accx"] = self.accx
        self.config["p_home"] = self.p_home
        self.config["p_pick"] = self.p_pick
        self.config["p_place"] = self.p_place
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

    # ----------------- IO helpers (voor sequences) -----------------

    def set_do(self, index: int, value: int):
        """Digitaal output zetten (0/1)."""
        self.gateway.set_digital_output(index, value)

    def get_di(self, index: int) -> int:
        """Digitaal input lezen (0/1)."""
        return self.gateway.get_digital_input(index)

    # ----------------- Voorbeeld-sequence -----------------

    def sequence_pick_and_place(self, status_callback=None):

        def log(msg: str):
            print(msg)
            if status_callback:
                status_callback(msg)

        self._stop_flag = False

        """"
        Begin hieronder met het coderen van de sequence-functie:
        """

        # 1) Naar home
        log("Naar home")
        self.gateway.set_lamp(False, True)
        self.gateway.amovel(*self.p_home, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence gestopt")
            return

        # 2) Naar pick
        log("Naar pick")
        self.gateway.set_lamp(False, True)
        self.gateway.amovel(*self.p_pick, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence gestopt")
            return

        # 3) Naar place
        log("Naar place")
        self.gateway.set_lamp(False, True)
        self.gateway.amovel(*self.p_place, self.velx, self.accx)
        self.gateway.wait_until_stopped()

        # voorbeeld IO: DO0 aan, wachten op DI3
        self.set_do(1, 1)
        if self.get_di(3) == 1:
            log("Sensor actief")
        if self._stop_flag:
            log("Sequence gestopt")
            return

        # 4) Naar pick
        log("Naar pick")
        self.gateway.set_lamp(False, True)
        self.gateway.amovel(*self.p_pick, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        if self._stop_flag:
            log("Sequence gestopt")
            return

        # 5) Terug naar home
        log("Terug naar home")
        self.gateway.set_lamp(False, True)
        self.gateway.amovel(*self.p_home, self.velx, self.accx)
        self.gateway.wait_until_stopped()
        self.set_do(1, 0)
        if self._stop_flag:
            log("Sequence gestopt")
            return
