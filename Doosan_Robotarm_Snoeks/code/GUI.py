import os
import sys
import threading
import webbrowser
import subprocess
import tkinter as tk
from PIL import Image
import customtkinter as ctk
from sequence import RobotProgram
from tkinter import messagebox, simpledialog
from calibrate_buckles import calibrate_pixels
from database import validate_workorder_exists
from backend import load_config,DoosanGatewayClient,ROBOT_IP,PORT,is_robot_enabled

cfg = load_config()
Snoeks_Red = cfg.get("Snoeks_Red") or cfg.get("SNOEKS_RED", "#c90000")
Snoeks_Dark = cfg.get("Snoeks_Dark") or cfg.get("SNOEKS_DARK", "#111111")
Snoeks_Dark2 = cfg.get("Snoeks_Dark2") or cfg.get("SNOEKS_DARK2", "#2c2c2c")
Snoeks_Text = cfg.get("Snoeks_Text") or cfg.get("SNOEKS_TEXT", "#ffffff")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "..", "assets")
LOGO_PATH = os.path.join(ASSETS_DIR, "Snoeks.png")

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
            tw,
            text=self.text,
            justify="left",
            background="#ffffe0",
            relief="solid",
            borderwidth=1,
            font=("tahoma", 8),
        )
        label.pack(ipadx=4, ipady=2)

    def _hide(self, event=None):
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()


class RobotGUI:
    def __init__(self, root: ctk.CTk):
        self.root = root
        self.root.title("Doosan sequence controller")
        self.root.configure(bg=Snoeks_Dark)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        try:
            img = Image.open(LOGO_PATH)
            self.logo_image = ctk.CTkImage(light_image=img, dark_image=img)
        except Exception as e:
            print(f"Couldn't load window icon: {e}")
            self.logo_image = None

        self.gateway = DoosanGatewayClient()
        self.program = RobotProgram(self.gateway)

        self.sequence_thread = None
        self._io_thread = None
        self._io_stop = threading.Event()
        self._io_error_reported = set()
        self._last_gui_status: str | None = None

        cfg_local = load_config()
        default_ip = cfg_local.get("robot_ip", ROBOT_IP)

        # ------------ LAYOUT-CONTAINER ------------
        main_frame = ctk.CTkFrame(self.root, fg_color=Snoeks_Dark2, corner_radius=50)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        main_frame.grid_columnconfigure(0, weight=0, minsize = 280)
        main_frame.grid_columnconfigure(1, weight=1)
        main_frame.grid_rowconfigure(0, weight=1)

        left_frame = ctk.CTkFrame(main_frame, fg_color=Snoeks_Dark2, corner_radius=50)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        right_frame = ctk.CTkFrame(main_frame, fg_color=Snoeks_Dark2, corner_radius=50)
        right_frame.grid(row=0, column=1, sticky="nsew")

        # ------------ LINKERKANT: CONNECT / PARAMS / CONTROL / IO ------------

        # Connect-regel
        top_frame = ctk.CTkFrame(left_frame, fg_color=Snoeks_Dark2, corner_radius=50)
        top_frame.pack(fill="x", pady=(0, 10))

        label_ip = ctk.CTkLabel(
            top_frame, text="Robot IP:", text_color=Snoeks_Text
        )
        label_ip.grid(row=0, column=0, sticky="w")

        self.ip_var = tk.StringVar(value=default_ip)
        self.ip_entry = ctk.CTkEntry(
            top_frame,
            textvariable=self.ip_var,
            width=140,
            fg_color=Snoeks_Dark,
            border_color=Snoeks_Red,
            text_color=Snoeks_Text,
            corner_radius=8,
        )
        self.ip_entry.grid(row=0, column=1, sticky="w", padx=(5, 5))

        self.btn_connect = ctk.CTkButton(
            top_frame,
            text="Connect",
            command=self.on_connect,
            fg_color=Snoeks_Red,
            hover_color="#e00000",
            text_color="white",
            corner_radius=16,
            width=110,
        )
        self.btn_connect.grid(row=0, column=2, padx=5)

        ToolTip(self.btn_connect, "Connect with the robot on given IP-adress.")

        # Parameters
        param_frame = ctk.CTkFrame(
            left_frame, fg_color=Snoeks_Dark2, corner_radius=50
        )
        param_frame.pack(fill="x", padx=0, pady=(0, 10))

        label_params = ctk.CTkLabel(
            param_frame, text="Parameters", text_color=Snoeks_Text
        )
        label_params.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 5))

        self.var_op_speed = tk.DoubleVar(value=self.program.operation_speed)
        self.var_velx = tk.DoubleVar(value=self.program.velx)
        self.var_accx = tk.DoubleVar(value=self.program.accx)

        ctk.CTkLabel(
            param_frame, text="Operation speed (%)", text_color=Snoeks_Text
        ).grid(row=1, column=0, sticky="w")
        entry_op_speed = ctk.CTkEntry(
            param_frame,
            textvariable=self.var_op_speed,
            width=80,
            fg_color=Snoeks_Dark,
            border_color=Snoeks_Red,
            text_color=Snoeks_Text,
            corner_radius=8,
        )
        entry_op_speed.grid(row=1, column=1, sticky="w", padx=(5, 0))

        ctk.CTkLabel(
            param_frame, text="velocity of TCP", text_color=Snoeks_Text
        ).grid(row=2, column=0, sticky="w", pady=(5, 0))
        entry_velx = ctk.CTkEntry(
            param_frame,
            textvariable=self.var_velx,
            width=80,
            fg_color=Snoeks_Dark,
            border_color=Snoeks_Red,
            text_color=Snoeks_Text,
            corner_radius=8,
        )
        entry_velx.grid(row=2, column=1, sticky="w", padx=(5, 0))

        ctk.CTkLabel(
            param_frame, text="acceleration of TCP", text_color=Snoeks_Text
        ).grid(row=3, column=0, sticky="w", pady=(5, 0))
        entry_accx = ctk.CTkEntry(
            param_frame,
            textvariable=self.var_accx,
            width=80,
            fg_color=Snoeks_Dark,
            border_color=Snoeks_Red,
            text_color=Snoeks_Text,
            corner_radius=8,
        )
        entry_accx.grid(row=3, column=1, sticky="w", padx=(5, 0))

        self.btn_apply = ctk.CTkButton(
            param_frame,
            text="Apply parameters",
            command=self.on_apply_params,
            fg_color=Snoeks_Red,
            hover_color="#ff3333",
            text_color="white",
            corner_radius=50,
            width=160,
        )
        self.btn_apply.grid(row=4, column=0, columnspan=3, pady=(10, 0), sticky="w")
        ToolTip(self.btn_apply, "Send the parameters to the robot and store.")

        # Control
        ctrl_frame = ctk.CTkFrame(
            left_frame, fg_color=Snoeks_Dark2, corner_radius=50
        )
        ctrl_frame.pack(fill="x", padx=0, pady=(0, 10))

        for col in range(4):
            ctrl_frame.grid_columnconfigure(col, weight=1)

        btn_width = 100

        self.btn_start = ctk.CTkButton(
            ctrl_frame,
            text="Start sequence",
            command=self.on_start_sequence,
            state="disabled",
            fg_color=Snoeks_Red,
            hover_color="#ff3333",
            text_color="white",
            corner_radius=50,
            width=btn_width,
        )
        self.btn_start.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        ToolTip(self.btn_start, "Scan QR and start the sequence after operator conformation.")

        self.btn_stop = ctk.CTkButton(
            ctrl_frame,
            text="Stop",
            command=self.on_stop,
            state="disabled",
            fg_color="#444444",
            hover_color="#666666",
            text_color="white",
            corner_radius=50,
            width=btn_width,
        )
        self.btn_stop.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        ToolTip(self.btn_stop, "Stop the current sequence.")

        self.btn_home = ctk.CTkButton(
            ctrl_frame,
            text="Home",
            command=self.on_home,
            state="disabled",
            fg_color="#444444",
            hover_color="#666666",
            text_color="white",
            corner_radius=50,
            width=btn_width,
        )
        self.btn_home.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        ToolTip(self.btn_home, "Move the robot to the home position.")

        self.btn_exit = ctk.CTkButton(
            ctrl_frame,
            text="Exit",
            command=self.on_exit,
            fg_color="#555555",
            hover_color="#777777",
            text_color="white",
            corner_radius=50,
            width=btn_width,
        )
        self.btn_exit.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        ToolTip(self.btn_exit, "Close the application.")

        self.btn_calib = ctk.CTkButton(
            ctrl_frame,
            text="Calibrate buckles",
            command=self.on_calibrate_buckles,
            fg_color=Snoeks_Red,
            hover_color="#ff3333",
            text_color="white",
            corner_radius=50,
            width=btn_width,
        )
        self.btn_calib.grid(row=1, column=2, padx=5, pady=5, sticky="ew")
        ToolTip(self.btn_calib, "Start the buckle calibration camera.")

        ctk.CTkLabel(
            ctrl_frame, text="Sequence", text_color=Snoeks_Text
        ).grid(row=3, column=0, sticky="w", padx=(10, 0))

        self.seq_choice = ctk.StringVar(value="1")

        def on_sequence_changed(choice: str):
            self.program.do_seatbelts = False
            self.program.do_armrests = False
            self.program.do_buckles = False
            self.program.do_everything = False
            if choice == "1":
                self.program.do_buckles = True
                label = "Buckles"
            elif choice == "2":
                self.program.do_armrests = True
                label = "Armrests"
            elif choice == "3":
                self.program.do_seatbelts = True
                label = "Seatbelts"
            elif choice == "4":
                self.program.do_everything = True
                label = "Complete sequence"
            else:
                label = f"Unknown ({choice})"
            self.append_status(f"Sequence choice changed to {label}.")

        self.seq_combo = ctk.CTkComboBox(
            ctrl_frame,
            values=["1", "2", "3", "4"],
            variable=self.seq_choice,
            command=on_sequence_changed,
            width=80,
            fg_color=Snoeks_Dark,
            border_color=Snoeks_Red,
            button_color=Snoeks_Red,
            button_hover_color="#ff3333",
            text_color=Snoeks_Text,
            corner_radius=8,
            state="readonly",
        )
        self.seq_combo.grid(row=3, column=0, sticky="w", padx=(5, 0))
        self.seq_combo.set("0")

        self.seq_state_var = tk.StringVar(value="")
        self.seq_state_label = ctk.CTkLabel(
            ctrl_frame,
            textvariable=self.seq_state_var,
            text_color="white",
            fg_color= "#880000",
            corner_radius=50,
        )
        self.seq_state_label.grid(
            row=2, column=0, columnspan=2, padx=10, pady=5, sticky="ew"
        )

        # Digital IO (volledige 16 DO / 16 DI)
        io_frame = ctk.CTkFrame(
            left_frame, fg_color=Snoeks_Dark2, corner_radius=50
        )
        io_frame.pack(fill="x", padx=0, pady=(0, 10))

        ctk.CTkLabel(io_frame, text="Digital Input Output", text_color=Snoeks_Text).grid(
            row=0, column=0, columnspan=18, sticky="w", padx=5, pady=(5, 5)
        )

        ctk.CTkLabel(io_frame, text="DO", text_color=Snoeks_Text).grid(
            row=1, column=0, sticky="w", padx=5
        )
        ctk.CTkLabel(io_frame, text="DI", text_color=Snoeks_Text).grid(
            row=4, column=0, sticky="w", padx=5
        )

        self.num_do = 16
        self.num_di = 16

        self.do_vars = []
        for i in range(1, self.num_do + 1):
            var = ctk.IntVar(value=0)
            row = 2 if i <= 8 else 3  # eerste 8 in rij 2, rest in rij 3
            col = (i if i <= 8 else i - 8)
            cb = ctk.CTkCheckBox(
                io_frame,
                text=str(i),
                variable=var,
                onvalue=1,
                offvalue=0,
                text_color=Snoeks_Text,
                border_width=1,
                corner_radius=8,
                fg_color=Snoeks_Red,
                hover_color="#ff3333",
                command=lambda idx=i, v=var: self._on_do_toggled(idx, v),
            )
            cb.grid(row=row, column=col, padx=2, pady=(0, 5), sticky="w")
            self.do_vars.append(var)

        self.di_labels = []
        for i in range(1, self.num_di + 1):
            row = 5 if i <= 8 else 6  # eerste 8 in rij 5, rest in rij 6
            col = (i if i <= 8 else i - 8)
            lbl = ctk.CTkLabel(
                io_frame,
                text=f"{i}: ?",
                text_color=Snoeks_Text,
                fg_color=Snoeks_Dark,
                corner_radius=6,
            )
            lbl.grid(row=row, column=col, padx=2, pady=(0, 5), sticky="w")
            self.di_labels.append(lbl)

        quick_frame = ctk.CTkFrame(
            io_frame, fg_color=Snoeks_Dark2, corner_radius=50
        )
        quick_frame.grid(
            row=7, column=0, columnspan=18, sticky="w", padx=5, pady=(5, 5)
        )

        self.btn_all_off = ctk.CTkButton(
            quick_frame,
            text="All Digital Out off",
            command=self._all_do_off,
            fg_color="#444444",
            hover_color="#666666",
            text_color="white",
            corner_radius=16,
            width=110,
        )
        self.btn_all_off.pack(side="left", padx=(0, 5))

        # Force / TCP
        force_frame = ctk.CTkFrame(
            left_frame, fg_color=Snoeks_Dark2, corner_radius=50
        )
        force_frame.pack(fill="x", padx=0, pady=(0, 10))

        self.forcevar = tk.StringVar(value="Force: ? N")
        self.forcelabel = ctk.CTkLabel(
            force_frame, textvariable=self.forcevar, text_color=Snoeks_Text
        )
        self.forcelabel.pack(anchor="w", padx=5, pady=(5, 0))

        self.tcpposevar = tk.StringVar(
            value="TCP: x=? y=? z=? rx=? ry=? rz=?"
        )
        self.tcpposelabel = ctk.CTkLabel(
            force_frame, textvariable=self.tcpposevar, text_color=Snoeks_Text
        )
        self.tcpposelabel.pack(anchor="w", padx=5, pady=(0, 5))

        # Logo links onderin
        logo_frame = ctk.CTkFrame(
            left_frame, fg_color=Snoeks_Dark2, corner_radius=50
        )
        logo_frame.pack(side="bottom", fill="x", padx=0, pady=10)

        if self.logo_image is not None:
            self.logolabel = ctk.CTkLabel(
                logo_frame, image=self.logo_image, text=""
            )
            self.logolabel.pack(anchor="w", padx=5, pady=5)

        # ------------ RECHTERKANT: STATUS / TERMINAL ------------

        status_frame = ctk.CTkFrame(
            right_frame, fg_color=Snoeks_Dark2, corner_radius=50
        )
        status_frame.pack(fill="both", expand=True, padx=0, pady=0)

        label_status = ctk.CTkLabel(
            status_frame, text="Status", text_color=Snoeks_Text
        )
        label_status.pack(anchor="w", padx=5, pady=(5, 0))

        self.status_text = ctk.CTkTextbox(
            status_frame,
            height=10,
            fg_color=Snoeks_Dark,
            text_color="white",
            corner_radius=8,
            border_width=1,
            width=500,
        )
        self.status_text.pack(fill="both", expand=True, padx=5, pady=(0, 5))

        filter_frame = ctk.CTkFrame(
            status_frame, fg_color=Snoeks_Dark2, corner_radius=50
        )
        filter_frame.pack(fill="x", pady=(0, 5))

        self.var_filter_errors = tk.BooleanVar(value=False)
        self.var_filter_seq = tk.BooleanVar(value=False)

        self.chk_errors = ctk.CTkCheckBox(
            filter_frame,
            text="Only show errors",
            variable=self.var_filter_errors,
            onvalue=True,
            offvalue=False,
            text_color=Snoeks_Text,
        )
        self.chk_errors.pack(side="left", padx=(5, 10))

        self.chk_seq = ctk.CTkCheckBox(
            filter_frame,
            text="only show sequence state",
            variable=self.var_filter_seq,
            onvalue=True,
            offvalue=False,
            text_color=Snoeks_Text,
        )
        self.chk_seq.pack(side="left", padx=(0, 10))

        self.append_status("Ready. Connect with the robot.")

        self.root.protocol("WM_DELETE_WINDOW", self.on_exit)
        self.root.bind_all("<Control-Alt-r>", self._on_rickroll)

        self._update_status_from_robot()

    # ---------- Helpers / callbacks ----------
    def append_status(self, msg: str):
        if (
            getattr(self, "var_filter_errors", None) is not None
            and self.var_filter_errors.get()
        ):
            lower = msg.lower()
            if not any(w in lower for w in ("fout", "error", "disconnected", "verbroken")):
                return

        if (
            getattr(self, "var_filter_seq", None) is not None
            and self.var_filter_seq.get()
        ):
            if "Sequence" not in msg and "Sequence" not in self.seq_state_var.get():
                return

        self.status_text.configure(state="normal")
        self.status_text.insert("end", msg + "\n")
        self.status_text.see("end")
        self.status_text.configure(state="disabled")

        if hasattr(self, "seq_state_var"):
            self.seq_state_var.set(msg)

    def _set_disconnected_state(self, reason: str | None = None):
        try:
            self.gateway.set_lamp(False, False)
        except Exception:
            pass

        if reason:
            self.append_status(f"Connection lost: {reason}")
        else:
            self.append_status("Connection lost.")

        self.btn_start.configure(state="disabled")
        self.btn_stop.configure(state="disabled")
        self.btn_home.configure(state="disabled")
        self.btn_connect.configure(state="normal")

        try:
            self.gateway.close()
        except Exception:
            pass

        self.gateway = DoosanGatewayClient()
        self.program = RobotProgram(self.gateway)
        self.append_status("Ready. Reconnect with the robot.")

    def _is_connection_lost_error(self, e: Exception) -> bool:
        msg = str(e)
        return (
            "Not connected to robot" in msg
            or "Robot connection closed" in msg
            or "Empty response from" in msg
        )

    def on_connect(self):
        self.btn_connect.configure(state="disabled")
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
                        self.append_status(
                            f"Connected through {self.gateway.ip}:{PORT}"
                        )
                        self.btn_start.configure(state="normal")
                        self.btn_stop.configure(state="normal")
                        self.btn_home.configure(state="normal")
                        self.btn_connect.configure(state="disabled")
                        self.program.save_parameters_to_config()
                    except Exception as e2:
                        messagebox.showerror("Connect error", str(e2))
                        self.btn_connect.configure(state="normal")
                else:
                    messagebox.showerror("Connect error", str(err))
                    self.btn_connect.configure(state="normal")

            self.root.after(0, finish)

        t = threading.Thread(target=do_connect, daemon=True)
        t.start()

    def _update_status_from_robot(self):
        try:
            try:
                force_value = self.gateway.get_tool_force(0)
                self.forcevar.set(f"Force: {force_value:.2f} N")
            except Exception:
                pass

            try:
                tcp_pose = self.gateway.get_tcppose()
                x, y, z, rx, ry, rz = tcp_pose
                self.tcpposevar.set(
                    f"TCP: x={x:.1f} y={y:.1f} z={z:.1f} "
                    f"rx={rx:.1f} ry={ry:.1f} rz={rz:.1f}"
                )
            except Exception:
                pass

            self._refresh_di()

        except Exception as e:
            if self._is_connection_lost_error(e):
                self._set_disconnected_state(str(e))

        self.root.after(1000, self._update_status_from_robot)

    def on_apply_params(self):
        try:
            self.program.operation_speed = float(self.var_op_speed.get())
            self.program.velx = float(self.var_velx.get())
            self.program.accx = float(self.var_accx.get())
            if self.gateway.sock is not None:
                self.program.apply_parameters()
            self.program.save_parameters_to_config()
            self.append_status("Parameters applied and stored.")
        except Exception as e:
            messagebox.showerror("Param error", str(e))

    def ask_and_validate_workorder(self) -> bool:
        workorder = simpledialog.askstring(
            "Give an work order",
            "Put in  WORK ORDER BASE ID:",
            parent=self.root,
        )
        if not workorder:
            messagebox.showerror(
                "Work order",
                "Work order failed or not filled in.",
            )
            return False

        workorder = workorder.strip()
        try:
            validate_workorder_exists(workorder)
        except Exception as e:
            messagebox.showerror("Work order-error", str(e))
            return False

        self.program.workorder_id = workorder
        self.append_status(f"Work order selected: {workorder}")
        return True

    def on_start_sequence(self):
        if self.sequence_thread and self.sequence_thread.is_alive():
            messagebox.showinfo("Info", "Sequence already running.")
            return

        if not self._check_robot_enabled_or_warn():
            return

        choice = self.seq_choice.get().strip()
        if choice not in ("1", "2", "3", "4"):
            messagebox.showerror(
                "Sequence error", f"unknown sequence choice: {choice}"
            )
            return

        if not self.ask_and_validate_workorder():
            return

        self.program.do_seatbelts = False
        self.program.do_armrests = False
        self.program.do_buckles = False
        self.program.do_everything = False

        if choice == "1":
            self.program.do_buckles = True
        elif choice == "2":
            self.program.do_armrests = True
        elif choice == "3":
            self.program.do_seatbelts = True
        elif choice == "4":
            self.program.do_everything = True

        self.append_status(
            f"Sequence selection: {choice}, "
            f"seatbelts={self.program.do_seatbelts}, "
            f"buckles={self.program.do_buckles}"
            f"armrests={self.program.do_armrests}, "
            f"buckles={self.program.do_everything}"
        )

        def run_seq():
            try:
                self.append_status("Sequence start...")
                self.seq_state_var.set("Sequence running")
                self.program.sequence_pick_and_place(self.append_status)
                self.append_status("Sequence done.")
                self.seq_state_var.set("Sequence done")
            except Exception as e:
                self.append_status(f"error in sequence: {e}")
                self.seq_state_var.set("Sequence error")
                if self._is_connection_lost_error(e):
                    self.root.after(
                        0, lambda: self._set_disconnected_state(str(e))
                    )
            finally:
                def clear_state():
                    self.seq_state_var.set("")
                self.root.after(1000, clear_state)

        self.sequence_thread = threading.Thread(target=run_seq, daemon=True)
        self.sequence_thread.start()

    def on_stop(self):
        try:
            self.append_status("Stop started.")
            self.program._stop_flag = True
            self.gateway.stop()
        except Exception as e:
            self.append_status(f"Stop error: {e}")
            if self.gateway.sock is None:
                self._set_disconnected_state(str(e))

    def on_exit(self):
        self.root.destroy()

    def on_home(self):
        if not self._check_robot_enabled_or_warn():
            return
        try:
            self.program.apply_parameters()
            self.append_status("Home-movement started...")
            self.gateway.amovej(
                *self.program.pj_home,
                self.program.velx,
                self.program.accx,
            )
            self.gateway.wait_until_stopped()
            self.append_status("Home-movement done.")
        except Exception as e:
            self.append_status(f"Home error: {e}")
            if self._is_connection_lost_error(e):
                self._set_disconnected_state(str(e))

    def on_calibrate_buckles(self):
        if not self._check_robot_enabled_or_warn():
            return
        try:
            basedir = os.path.dirname(os.path.abspath(__file__))
            script = os.path.join(basedir, "calibrate_buckles.py")
            subprocess.run([sys.executable, script], check=True)
            self.append_status("Buckle-calibration done.")
        except Exception as e:
            messagebox.showerror("Calibration error", "camera not connected, try reconnecting the USB.")

    def _on_do_toggled(self, index: int, var: ctk.IntVar):
        value = int(var.get())
        try:
            if self.gateway.sock is None:
                self.append_status("Can't set DO, robot not connected.")
                var.set(0)
                return
            self.gateway.set_digital_output(index, value)
            self.append_status(f"DO{index} -> {value}")
        except Exception as e:
            self.append_status(f"DO{index} error: {e}")
            if self._is_connection_lost_error(e):
                self._set_disconnected_state(str(e))

    def _all_do_off(self):
        if self.gateway.sock is None:
            self.append_status("Can't reset DO, robot not connected.")
            return
        try:
            for i, var in enumerate(self.do_vars, start=1):
                self.gateway.set_digital_output(i, 0)
                var.set(0)
            self.append_status("All DO turned off.")
        except Exception as e:
            self.append_status(f"All DO turned off error: {e}")
            if self._is_connection_lost_error(e):
                self._set_disconnected_state(str(e))

    def _reset_lamps(self):
        if self.gateway.sock is None:
            self.append_status("Kan lamps niet resetten: niet verbonden.")
            return
        try:
            self.gateway.set_lamp(False, False)
            self.append_status("Lampen gereset (READY/MOVE uit).")
        except Exception as e:
            self.append_status(f"Reset lamps fout: {e}")
            if self._is_connection_lost_error(e):
                self._set_disconnected_state(str(e))

    def _refresh_di(self):
        if self.gateway.sock is None:
            return
        try:
            for i in range(1, self.num_di + 1):
                try:
                    val = self.gateway.get_digital_input(i)
                    self.di_labels[i - 1].configure(
                        text=f"{i}: {val}",
                        fg_color=("#333333" if val else Snoeks_Dark),
                    )
                except Exception:
                    self.di_labels[i - 1].configure(text=f"{i}: ?")
        except Exception as e:
            self.append_status(f"Fout bij DI refresh: {e}")

    def _check_robot_enabled_or_warn(self) -> bool:
        try:
            enabled = is_robot_enabled(self.program)
        except Exception:
            enabled = False
        if not enabled:
            messagebox.showwarning(
                "Robot disabled",
                "De fysieke schakelaar staat uit.\n"
                "Zet de schakelaar AAN voordat je de robot beweegt.",
            )
            return False
        return True

    def _on_rickroll(self, event=None):
        try:
            webbrowser.open(
                "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                new=2,
            )
        except Exception:
            pass


if __name__ == "__main__":
    app_root = ctk.CTk()
    gui = RobotGUI(app_root)
    app_root.mainloop()
