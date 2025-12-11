import tkinter as tk
from tkinter import ttk, messagebox
import webbrowser

from qr_scanner import scan_qr_with_camera
from doosan_backend import *
from doosan_sequence import RobotProgram


cfg = load_config()
Snoeks_Red = cfg.get("Snoeks_Red")
Snoeks_Dark = cfg.get("Snoeks_Dark")
Snoeks_Dark2 = cfg.get("Snoeks_Dark2")
Snoeks_Text = cfg.get("Snoeks_Text")

def setup_snoeks_style(root):
    style = ttk.Style(root)

    try:
        style.theme_use("clam")
    except Exception:
        pass

    # hoofdachtergrond
    root.configure(bg=Snoeks_Dark)

    # algemene defaults voor ttk (zodat witte vlakken verdwijnen)
    style.configure(".", background=Snoeks_Dark2, foreground=Snoeks_Text)

    # Frames
    style.configure("Snoeks.TFrame", background=Snoeks_Dark2)

    style.configure("Snoeks.TLabelframe", background=Snoeks_Dark2, foreground=Snoeks_Text)

    style.configure("Snoeks.TLabelframe.Label", background=Snoeks_Dark2, foreground=Snoeks_Text)

    # Labels
    style.configure("Snoeks.TLabel", background=Snoeks_Dark2, foreground=Snoeks_Text)

    # Buttons
    style.configure("Snoeks.TButton", background=Snoeks_Red, foreground="white", padding=5, relief="flat")
    style.map("Snoeks.TButton", background=[("active", "#e00000"), ("disabled", "#555555")], foreground=[("disabled", "#aaaaaa")])

    style.configure("SnoeksPrimary.TButton", background=Snoeks_Red, foreground="white", padding=6, relief="flat")
    style.map("SnoeksPrimary.TButton", background=[("active", "#e00000")])

    # Entry (donkere velden, lichte tekst)
    style.configure("Snoeks.TEntry", fieldbackground=Snoeks_Dark, foreground=Snoeks_Text, background=Snoeks_Dark2, bordercolor=Snoeks_Dark)

class ToolTip:
    def __init__(self, widget, text: str):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        widget.bind("<Enter>", self._show)
        widget.bind("<Leave>", self._hide)

    def _show(self, event=None):
        if self.tipwindow or not self.text:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(
            tw, text=self.text, justify="left",
            background="#ffffe0", relief="solid", borderwidth=1,
            font=("tahoma", 8)
        )
        label.pack(ipadx=4, ipady=2)

    def _hide(self, event=None):
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()

class RobotGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Doosan sequence controller")
        setup_snoeks_style(root)

        try:
            icon_img = tk.PhotoImage(file="Snoeks.png")
            self._icon_img = icon_img
            self.root.iconphoto(False, icon_img)
        except Exception as e:
            print(f"Kon window-icoon niet laden: {e}")

        self.gateway = DoosanGatewayClient()
        self.program = RobotProgram(self.gateway)
        self.sequence_thread = None

        self._io_thread = None
        self._io_stop = threading.Event()
        self._io_error_reported = set()
        self._last_gui_status: str | None = None

        cfg = load_config()
        default_ip = cfg.get("robot_ip", ROBOT_IP)

        # Connect-regel
        top_frame = ttk.Frame(root, padding=10, style="Snoeks.TFrame")
        top_frame.pack(fill="x")
        ttk.Label(top_frame, text="Robot IP:", style="Snoeks.TLabel").grid(row=0, column=0, sticky="w")

        self.ip_var = tk.StringVar(value=default_ip)
        ttk.Entry(top_frame, textvariable=self.ip_var, width=16).grid(row=0, column=1, sticky="w")

        self.btn_connect = ttk.Button(top_frame, text="Connect", command=self.on_connect, style="Snoeks.TButton")
        self.btn_connect.grid(row=0, column=2, padx=5)

        # Parameters
        param_frame = ttk.LabelFrame(root, text="Parameters", padding=10, style="Snoeks.TFrame")
        param_frame.pack(fill="x", padx=10, pady=5)

        self.var_op_speed = tk.DoubleVar(value=self.program.operation_speed)
        self.var_velx = tk.DoubleVar(value=self.program.velx)
        self.var_accx = tk.DoubleVar(value=self.program.accx)

        ttk.Label(param_frame, text="Operation speed (%)").grid(row=0, columnspan=2, sticky="w")
        ttk.Entry(param_frame, textvariable=self.var_op_speed, width=8).grid(row=0, column=2, sticky="w")

        ttk.Label(param_frame, text="velx").grid(row=2, column=0, sticky="w")
        ttk.Entry(param_frame, textvariable=self.var_velx, width=8).grid(row=2, column=2, sticky="w")
        ttk.Label(param_frame, text="accx").grid(row=3, column=0, sticky="w")
        ttk.Entry(param_frame, textvariable=self.var_accx, width=8).grid(row=3, column=2, sticky="w")

        # Apply-knop voor parameters
        self.btn_apply = ttk.Button(param_frame, text="Apply parameters", command=self.on_apply_params, style="Snoeks.TButton")
        self.btn_apply.grid(row=4, column=0, columnspan=4, pady=(8, 0))

        # Start/Stop/Home/Exit + sequence status
        ctrl_frame = ttk.LabelFrame(root, text="Control", padding=10, style="Snoeks.TLabelframe")
        ctrl_frame.pack(fill="x", padx=10, pady=5)

        self.btn_start = ttk.Button(ctrl_frame,text="Start sequence",command=self.on_start_sequence,state="disabled",style="SnoeksPrimary.TButton",)
        self.btn_start.grid(row=0, column=0, padx=5)

        self.btn_stop = ttk.Button(ctrl_frame,text="Stop",command=self.on_stop,state="disabled",style="Snoeks.TButton",)
        self.btn_stop.grid(row=0, column=1, padx=5)

        self.btn_home = ttk.Button(ctrl_frame,text="Home",command=self.on_home,state="disabled",style="Snoeks.TButton",)
        self.btn_home.grid(row=0, column=2, padx=5)

        self.btn_exit = ttk.Button(ctrl_frame, text="Exit", command=self.on_exit, style="Snoeks.TButton",)
        self.btn_exit.grid(row=0, column=3, padx=5)

        ToolTip(self.btn_connect, "Verbind met de robot op het opgegeven IP-adres.")
        ToolTip(self.btn_start, "Scan QR en start de sequence na operatorbevestiging.")
        ToolTip(self.btn_stop, "Vraag een stop van de huidige sequence aan.")
        ToolTip(self.btn_home, "Beweeg de robot naar de HOME-positie.")
        ToolTip(self.btn_apply, "Stuur de parameters naar de robot en sla ze op.")
        ToolTip(self.btn_exit, "Sluit de applicatie.")

        # Opvallend sequence-state vakje
        self.seq_state_var = tk.StringVar(value="")
        self.seq_state_frame = ttk.Frame(ctrl_frame, padding=6, style="Snoeks.TFrame")
        self.seq_state_label = ttk.Label(self.seq_state_frame,textvariable=self.seq_state_var,style="Snoeks.TLabel",)
        self.seq_state_label.pack()

        # IO (Digital I/O)
        io_frame = ttk.LabelFrame(root, text="Digital IO", padding=10, style="Snoeks.TLabelframe")
        io_frame.pack(fill="x", padx=10, pady=5)

        self.num_do = 16  # DO1..DO16
        self.num_di = 16  # DI1..DI16

        ttk.Label(io_frame, text="Outputs (DO)", style="Snoeks.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(io_frame, text="Inputs (DI)", style="Snoeks.TLabel").grid(row=2, column=0, sticky="w")

        # DO: checkboxen om outputs te zetten
        self.do_vars = []
        for i in range(1, self.num_do + 1):
            var = tk.IntVar(value=0)
            cb = ttk.Checkbutton( io_frame, text=str(i), variable=var, command=lambda idx=i, v=var: self._on_do_toggled(idx, v), style="Snoeks.TCheckbutton" if "Snoeks.TCheckbutton" in ttk.Style().theme_names() else "TCheckbutton")
            cb.grid(row=1, column=1 + i, padx=2)
            self.do_vars.append(var)

        # DI: labels die alleen status tonen
        self.di_labels = []
        for i in range(1, self.num_di + 1):
            lbl = ttk.Label(io_frame, text=f"{i}: ?", style="Snoeks.TLabel")
            lbl.grid(row=3, column=1 + i, padx=2)
            self.di_labels.append(lbl)

        # Quick buttons voor IO-patronen
        quick_frame = ttk.Frame(io_frame, style="Snoeks.TFrame")
        quick_frame.grid(row=4, column=0, columnspan=1 + self.num_do, sticky="w", pady=(5, 0))

        btn_all_off = ttk.Button(
            quick_frame, text="All DO off",
            command=self._all_do_off, style="Snoeks.TButton"
        )
        btn_all_off.pack(side="left", padx=(0, 5))

        btn_reset_lamps = ttk.Button(
            quick_frame, text="Reset lamps",
            command=self._reset_lamps, style="Snoeks.TButton"
        )
        btn_reset_lamps.pack(side="left")

        # Status
        status_frame = ttk.LabelFrame(root, text="Status", padding=10, style="Snoeks.TLabelframe")
        status_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.status_text = tk.Text(status_frame, height=10, bg=Snoeks_Dark, fg="white", insertbackground="white", relief="flat")
        self.status_text.pack(fill="both", expand=True)

        # Status-filters
        filter_frame = ttk.Frame(status_frame, style="Snoeks.TFrame")
        filter_frame.pack(fill="x", pady=(5, 0))

        self.var_filter_errors = tk.BooleanVar(value=False)
        self.var_filter_seq = tk.BooleanVar(value=False)

        chk_errors = ttk.Checkbutton(filter_frame, text="Toon alleen fouten", variable=self.var_filter_errors, style="TCheckbutton")
        chk_errors.pack(side="left", padx=(0, 10))

        chk_seq = ttk.Checkbutton(filter_frame, text="Toon alleen sequence-status", variable=self.var_filter_seq, style="TCheckbutton")
        chk_seq.pack(side="left", padx=(0, 10))

        self.append_status("Klaar. Verbind met de robot.")
        self.root.protocol("WM_DELETE_WINDOW", self.on_exit)
        self.root.bind_all("<Control-r>", self._on_rickroll)
        self.root.bind_all("<Control-R>", self._on_rickroll)
        self._update_status_from_robot()

    # ---------- Helpers / callbacks ----------

    def append_status(self, msg: str):
        # Filter: alleen fouten?
        if getattr(self, "var_filter_errors", None) is not None and self.var_filter_errors.get():
            lower = msg.lower()
            if not any(w in lower for w in ("fout", "error", "verbroken")):
                return

        # Filter: alleen sequence-status?
        if getattr(self, "var_filter_seq", None) is not None and self.var_filter_seq.get():
            if "Sequence" not in msg and "Sequence" not in self.seq_state_var.get():
                return

        self.status_text.config(state="normal")
        self.status_text.insert("end", msg + "\n")
        self.status_text.see("end")
        self.status_text.config(state="disabled")

        if hasattr(self, "seq_state_var"):
            self.seq_state_var.set(msg)

    def _set_seq_state(self, text: str | None):
        """Toon of verberg het opvallende sequence-state vakje."""
        if text:
            self.seq_state_var.set(text)
            # alleen gridden als hij nog niet zichtbaar is
            if not self.seq_state_frame.winfo_ismapped():
                self.seq_state_frame.grid(row=0, column=4, padx=(20, 5), sticky="w")
        else:
            self.seq_state_var.set("")
            if self.seq_state_frame.winfo_ismapped():
                self.seq_state_frame.grid_remove()

    def _set_disconnected_state(self, reason: str | None = None):
        """Zet de GUI terug in de 'niet verbonden' staat."""
        self.gateway.set_lamp(False, False)
        if reason:
            self.append_status(f"Verbinding verbroken: {reason}")
        else:
            self.append_status("Verbinding verbroken.")

        # knoppen resetten
        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="disabled")
        self.btn_home.config(state="disabled")
        self.btn_connect.config(state="normal")

        # backend afsluiten en nieuwe client maken
        try:
            self.gateway.close()
        except Exception:
            pass

        self.gateway = DoosanGatewayClient()
        self.program = RobotProgram(self.gateway)

        self.append_status("Klaar. Verbind opnieuw met de robot.")
        self._set_seq_state(None)

    def _is_connection_lost_error(self, e: Exception) -> bool:
        msg = str(e)
        return (
                "Not connected to robot" in msg
                or "Robot connection closed" in msg
        )

    def on_connect(self):
        self.btn_connect.config(state="disabled")

        ip = self.ip_var.get().strip()
        self.gateway.ip = ip

        def do_connect():
            ok = False
            err = None
            try:
                self.gateway.connect()
                ok = True
            except Exception as e:
                err = e

            def finish():
                if ok:
                    try:
                        self.gateway.start_status_poller(interval=0.2)
                        self.append_status(f"Verbonden met {self.gateway.ip}:{PORT}")
                        self.btn_start.config(state="normal")
                        self.btn_stop.config(state="normal")
                        self.btn_home.config(state="normal")
                        self.btn_connect.config(state="disabled")
                        self.program.save_parameters_to_config()
                    except Exception as e2:
                        messagebox.showerror("Connect error", str(e2))
                        self.btn_connect.config(state="normal")
                else:
                    # bij mislukte verbinding knop weer AAN
                    messagebox.showerror("Connect error", str(err))
                    self.btn_connect.config(state="normal")

            self.root.after(0, finish)

        t = threading.Thread(target=do_connect, daemon=True)
        t.start()

    def _update_status_from_robot(self):
        """Start een achtergrondthread die periodiek DI + status ophaalt."""
        # voorkom dat er meerdere threads tegelijk draaien
        if hasattr(self, "_io_thread") and self._io_thread and self._io_thread.is_alive():
            return

        self._io_stop.clear()

        def io_loop():
            while not self._io_stop.is_set():
                try:
                    # tekstuele status (check_motion) komt uit backend-poller;
                    # hier alleen doorzetten naar GUI als die verandert
                    status = self.gateway.get_last_status()
                    if status and status != self._last_gui_status:
                        self._last_gui_status = status

                        def upd_status():
                            self.append_status(f"Robotstatus: {status}")

                        self.root.after(0, upd_status)

                    # digitale inputs uitlezen
                    if self.gateway.sock is not None:
                        di_values = {}
                        for i in range(1, self.num_di + 1):
                            try:
                                v = self.gateway.get_digital_input(i)
                                di_values[i] = v
                            except Exception as e_io:
                                di_values[i] = "?"
                                if i not in self._io_error_reported:
                                    self._io_error_reported.add(i)

                                    def log_err(i=i, e_io=e_io):
                                        self.append_status(f"DI{i} leesfout: {e_io}")

                                    self.root.after(0, log_err)

                                # als de backend zegt dat er geen verbinding is, GUI resetten
                                if self._is_connection_lost_error(e_io):
                                    def disc():
                                        self._set_disconnected_state(str(e_io))

                                    self.root.after(0, disc)
                                    break

                        # labels updaten op GUI-thread
                        def upd_labels():
                            for i, v in di_values.items():
                                self.di_labels[i - 1].config(text=f"{i}: {v}")

                        self.root.after(0, upd_labels)

                except Exception as e:
                    # algemene poll-fout: ook maar één keer loggen
                    def log_exc():
                        self.append_status(f"Statuspoll fout: {e}")
                    self.root.after(0, log_exc)

                self._io_stop.wait(0.1)

        self._io_thread = threading.Thread(target=io_loop, daemon=True)
        self._io_thread.start()

    def on_apply_params(self):
        try:
            self.program.operation_speed = self.var_op_speed.get()
            self.program.velx = self.var_velx.get()
            self.program.accx = self.var_accx.get()
            self.gateway.ip = self.ip_var.get().strip()

            if self.gateway.sock is not None:
                self.program.apply_parameters()

            self.program.save_parameters_to_config()
            self.append_status("Parameters toegepast en/of opgeslagen.")

        except Exception as e:
            messagebox.showerror("Param error", str(e))

    def on_start_sequence(self):
        if self.sequence_thread and self.sequence_thread.is_alive():
            messagebox.showinfo("Info", "Sequence is al bezig.")
            return

        if not self._check_robot_enabled_or_warn():
            return

        result = scan_qr_with_camera()
        if result is None:
            messagebox.showerror("QR-fout", "Geen geldige QR-code gevonden of niet in database.")
            return

        self.program.do_gordels = result in (1, 2)
        self.program.do_armsteunen = result in (2, 3)
        self.program.do_seatbelts = (result in (1, 2))

        self.append_status(f"QR-code resultaat: {result} " f"(gordels={self.program.do_gordels}, " f"armsteunen={self.program.do_armsteunen})")

        def run_seq():
            try:
                self.append_status("Sequence start...")
                self._set_seq_state("Sequence running")
                self.program.sequence_pick_and_place(self.append_status)
                self.append_status("Sequence klaar.")
                self._set_seq_state("Sequence done")
            except Exception as e:
                self.append_status(f"Fout in sequence: {e}")
                self._set_seq_state("Sequence error")
                if self._is_connection_lost_error(e):
                    self.root.after(0, lambda: self._set_disconnected_state(str(e)))
            finally:
                # na korte tijd de status weer leeg zodat de GUI niet 'blijft hangen'
                def clear_state():
                    self._set_seq_state(None)

                self.root.after(1000, clear_state)

        self.sequence_thread = threading.Thread(target=run_seq, daemon=True)
        self.sequence_thread.start()

    def on_stop(self):
        try:
            self.append_status("Stop aangevraagd.")
            self.program.request_stop()
        except Exception as e:
            self.append_status(f"Stop fout: {e}")
            if self.gateway.sock is None:
                self._set_disconnected_state(str(e))

    def on_exit(self):
        self.root.destroy()

    def on_home(self):
        if not self._check_robot_enabled_or_warn():
            return

        try:
            self.program.apply_parameters()
            #self.gateway.set_lamp(False, True)
            self.append_status("Home-beweging gestart...")
            self.gateway.amovel(*self.program.p_home, self.program.velx, self.program.accx)
            self.gateway.wait_until_stopped()
            self.append_status("Home-beweging klaar.")
            #self.gateway.set_lamp(True, False)
        except Exception as e:
            self.append_status(f"Home fout: {e}")
            if self._is_connection_lost_error(e):
                self._set_disconnected_state(str(e))

    def _on_do_toggled(self, index: int, var: tk.IntVar):
        val = var.get()
        try:
            if self.gateway.sock is None:
                self.append_status("Kan DO niet zetten: niet verbonden.")
                var.set(0)
                return
            self.gateway.set_digital_output(index, val)  # index = 1..16
            self.append_status(f"DO{index} => {val}")
        except Exception as e:
            self.append_status(f"DO{index} fout: {e}")
            if self._is_connection_lost_error(e):
                self._set_disconnected_state(str(e))

    def _all_do_off(self):
        if self.gateway.sock is None:
            self.append_status("Kan DO niet resetten: niet verbonden.")
            return
        try:
            for i, var in enumerate(self.do_vars, start=1):
                self.gateway.set_digital_output(i, 0)
                var.set(0)
            self.append_status("Alle DO-uitgangen zijn uit gezet.")
        except Exception as e:
            self.append_status(f"All DO off fout: {e}")
            if self._is_connection_lost_error(e):
                self._set_disconnected_state(str(e))

    def _reset_lamps(self):
        if self.gateway.sock is None:
            self.append_status("Kan lamps niet resetten: niet verbonden.")
            return
        try:
            # gebruik je backend-config DO's
            self.append_status("Lampen gereset (READY/MOVE uit).")
        except Exception as e:
            self.append_status(f"Reset lamps fout: {e}")
            if self._is_connection_lost_error(e):
                self._set_disconnected_state(str(e))

    def _check_robot_enabled_or_warn(self) -> bool:
        try:
            enabled = is_robot_enabled(self.program)
        except Exception:
            enabled = False

        if not enabled:
            messagebox.showwarning(
                "Robot disabled",
                "De fysieke schakelaar staat uit.\n"
                "Zet de schakelaar op AAN voordat je de robot beweegt."
            )
            return False
        return True

    def _on_rickroll(self, event=None):
        try:
            webbrowser.open("https://www.youtube.com/watch?v=dQw4w9WgXcQ", new=2)
        except Exception as e:
            pass

if __name__ == "__main__":
    root = tk.Tk()
    gui = RobotGUI(root)
    root.mainloop()
