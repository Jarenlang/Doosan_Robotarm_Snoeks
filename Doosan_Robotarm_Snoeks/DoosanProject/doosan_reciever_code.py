PORT = 56666

def parse_floats(tokens, start_idx, count):
    vals = []
    for i in range(count):
        vals.append(float(tokens[start_idx + i]))
    return vals

def all_outputs_off():
    # Zet DO1 t/m DO4 laag
    try:
        set_digital_output(1, 0)
        set_digital_output(2, 0)
        set_digital_output(3, 0)
        set_digital_output(4, 0)
    except Exception as e:
        server_socket_write(sock, b"OK amovel\n")

def handle_command(sock, line):
    tokens = line.split()
    if len(tokens) == 0:
        return

    cmd = tokens[0].lower()

    if cmd == "amovel":
        if len(tokens) != 9:
            server_socket_write(sock, b"ERR amovel needs 8 args\n")
            return

        vals = parse_floats(tokens, 1, 8)
        x, y, z, rx, ry, rz, vel, acc = vals
        target = [x, y, z, rx, ry, rz]

        set_velj(vel)
        set_accj(acc)
        set_velx(vel)
        set_accx(acc)

        amovel(target)
        server_socket_write(sock, b"OK amovel\n")
        return

    if cmd == "amovejx":
        if len(tokens) != 9:
            server_socket_write(sock, b"ERR amovejx needs 8 args\n")
            return

        vals = parse_floats(tokens, 1, 8)
        x, y, z, rx, ry, rz, vel, acc = vals
        target = [x, y, z, rx, ry, rz]

        set_velj(vel)
        set_accj(acc)
        set_velx(vel)
        set_accx(acc)

        amovejx(target)
        server_socket_write(sock, b"OK amovejx\n")
        return

    # DIGOUT index val (val=0/1)
    if cmd == "digout":
        if len(tokens) != 3:
            server_socket_write(sock, b"ERR digout needs 2 args\n")
            return
        try:
            idx = int(tokens[1])
            val = int(tokens[2])
            # Doosan DRL: setdigitaloutput(index, val)
            set_digital_output(idx, val)
            server_socket_write(sock, b"OK digout\n")
        except:
            server_socket_write(sock, b"ERR digout invalid args\n")
        return

    # DIGIN index  -> OK digin <0/1>
    if cmd == "digin":
        if len(tokens) != 2:
            server_socket_write(sock, b"ERR digin needs 1 arg\n")
            return
        try:
            idx = int(tokens[1])
            # Doosan DRL: getdigitalinput(index) -> 0/1
            v = get_digital_input(idx)
            msg = "OK digin {}\n".format(int(v))
            server_socket_write(sock, msg.encode())
        except:
            server_socket_write(sock, b"ERR digin invalid args\n")
        return

    # ANOUT ch value (bijv. 0..1, 0.0..10.0, afhankelijk van je config)
    if cmd == "anout":
        if len(tokens) != 3:
            server_socket_write(sock, b"ERR anout needs 2 args\n")
            return
        try:
            ch = int(tokens[1])
            val = float(tokens[2])
            # Doosan DRL: setanalogoutput(ch, val)
            set_analog_output(ch, val)
            server_socket_write(sock, b"OK anout\n")
        except:
            server_socket_write(sock, b"ERR anout invalid args\n")
        return

    # ANIN ch -> OK anin <value>
    if cmd == "anin":
        if len(tokens) != 2:
            server_socket_write(sock, b"ERR anin needs 1 arg\n")
            return
        try:
            ch = int(tokens[1])
            # Doosan DRL: getanaloginput(ch)
            v = get_analog_input(ch)
            msg = "OK anin {}\n".format(v)
            server_socket_write(sock, msg.encode())
        except:
            server_socket_write(sock, b"ERR anin invalid args\n")
        return


    if cmd == "stop":
        stop(DR_SSTOP)
        server_socket_write(sock, b"OK stop\n")
        return

    if cmd == "change_operation_speed":
        if len(tokens) != 2:
            server_socket_write(sock, b"ERR change_operation_speed needs 1 arg\n")
            return
        spd = int(float(tokens[1]))
        change_operation_speed(spd)
        server_socket_write(sock, b"OK change_operation_speed\n")
        return

    if cmd == "set_velx":
        if len(tokens) != 2:
            server_socket_write(sock, b"ERR set_velx needs 1 arg\n")
            return
        vel = int(float(tokens[1]))
        set_velx(vel)
        server_socket_write(sock, b"OK set_velx\n")
        return

    if cmd == "set_velj":
        if len(tokens) != 2:
            server_socket_write(sock, b"ERR set_velj needs 1 arg\n")
            return
        vel = int(float(tokens[1]))
        set_velj(vel)
        server_socket_write(sock, b"OK set_velj\n")
        return

    if cmd == "set_accx":
        if len(tokens) != 2:
            server_socket_write(sock, b"ERR set_accx needs 1 arg\n")
            return
        acc = int(float(tokens[1]))
        set_accx(acc)
        server_socket_write(sock, b"OK set_accx\n")
        return

    if cmd == "set_accj":
        if len(tokens) != 2:
            server_socket_write(sock, b"ERR set_accj needs 1 arg\n")
            return
        acc = int(float(tokens[1]))
        set_accj(acc)
        server_socket_write(sock, b"OK set_accj\n")
        return

    if cmd == "check_motion":
        mv = check_motion()
        msg = "OK check_motion {}\n".format(int(mv))
        server_socket_write(sock, msg.encode())
        return

    if cmd == "toolforce":
        # Verwacht: 'toolforce 0' of 'toolforce 1' (ref-frame)
        if len(tokens) != 2:
            server_socket_write(sock, b"ERR toolforce needs 1 arg")
            return
        try:
            ref = int(tokens[1])
            # DRL-call: get_tool_force(ref) -> lijst/vector met 6 waardes
            f = get_tool_force(ref)
            # Neem de norm (totale kracht) of bijv. f[0] als enkel component
            # Stel dat je de norm wilt sturen:
            fx = f[0]
            fy = f[1]
            fz = f[2]
            total = (fx*fx + fy*fy + fz*fz) ** 0.5
            msg = "OK toolforce {}".format(total)
            server_socket_write(sock, msg.encode())
        except:
            server_socket_write(sock, b"ERR toolforce invalid args")
        return

    if cmd == "tcp_pose":
        if len(tokens) != 1:
            server_socket_write(sock, b"ERR tcppose takes no args\n")
            return
        try:
            # --- HIER get_current_posx() gebruiken ---
            # Zonder extra argumenten krijg je pose in DR_BASE terug.
            cur_posx, sol = get_current_posx()  # of get_current_posx(DR_BASE)
            # cur_posx is een posx of list met 6 waarden: [x, y, z, rx, ry, rz]

            x = cur_posx[0]
            y = cur_posx[1]
            z = cur_posx[2]
            rx = cur_posx[3]
            ry = cur_posx[4]
            rz = cur_posx[5]

            msg = "OK tcppose {:.3f} {:.3f} {:.3f} {:.3f} {:.3f} {:.3f}\n".format(
                x, y, z, rx, ry, rz
            )
            server_socket_write(sock, msg.encode())
        except Exception:
            server_socket_write(sock, b"ERR tcppose invalid\n")
        return

    server_socket_write(sock, b"ERR unknown command\n")


def main():
    while True:
        try:
            blue_pressed = get_digital_input(3)
            if blue_pressed == 1:
                try:
                    set_digital_output(1, 0)
                    set_digital_output(2, 0)
                    set_digital_output(3, 0)
                    set_digital_output(4, 0)
                except Exception as e:
                    tp_log("Fout bij alle outputs uitzetten: {e}")
        except Exception as e:
            tp_log("Error bij uitlezen blauwe knop: {e}")

        tp_log("waiting for connection")
        sock = server_socket_open(PORT)
        tp_log("connected")

        while True:
            res, rxdata = server_socket_read(sock, -1, -1)
            if res <= 0:
                tp_log("client disconnected or error, stopping robot and closing socket")
                try:
                    stop(DR_SSTOP)
                except:
                    tp_log("error while stopping robot after disconnect")
                try:
                    server_socket_close(sock)
                except:
                    tp_log("error while closing socket after disconnect")
                break

            try:
                text = rxdata.decode()
            except:
                server_socket_write(sock, b"ERR decode\n")
                continue

            lines = text.splitlines()
            for line in lines:
                line = line.strip()
                if line == "":
                    continue
                if line.lower() == "quit":
                    server_socket_write(sock, b"OK bye then\n")
                    try:
                        server_socket_close(sock)
                    except:
                        tp_log("error while closing socket after quit")
                    # robot ook netjes stoppen bij quit
                    try:
                        stop(DR_SSTOP)
                    except:
                        tp_log("error while stopping robot after quit")
                    # terug naar outer loop: wacht op nieuwe client
                    break
                handle_command(sock, line)

main()
