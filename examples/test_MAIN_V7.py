import tkinter as tk
import logging
from pymodbus.client import ModbusTcpClient
import time
import socket

# Logging-Konfiguration
logging.basicConfig(level=logging.INFO)

# Modbus-Konfiguration
AUSGABEREGISTER = 0x0000  # Ausgangsregister (Überprüfen  die Adressgenauigkeit)
client = None  # Globaler Client
BITSHIFT = 8# Bitverschiebung für Kanäle

# Funktion zum Scannen des Netzwerks
def netzwerk_scannen():
    verfügbare_ips = []
    for i in range(1, 251):  
        ip = f"192.168.0.{i}"
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.01)  
        try:
            result = sock.connect_ex((ip, 502))  # Modbus TCP port 502
            if result == 0:
                verfügbare_ips.append(ip)
                logging.info(f"Gerät gefunden auf IP: {ip}")
            else:
                logging.debug(f"Kein Gerät auf  IP: {ip}")  
        except Exception as e:
            logging.error(f"Fehler währen Überprüfen der IP {ip}: {e}")
        finally:
            sock.close()
    return verfügbare_ips


# Funktion zum Herstellen der Verbindung
def verbinden_modbus(selected_ip):
    global client
    client = ModbusTcpClient(selected_ip)
    if client.connect():
        logging.info(f"Verbindung zu {selected_ip} erfolgreich.")
        return True
    else:
        logging.error(f"Kann nicht zu {selected_ip} verbinden.")
        return False

# Schreiben in das Modbus-Ausgangsregister
def ausgabe_schreiben(move_in=False, move_out=False, quit_error=False):
    ausgabewert = (int(move_in) << 0 + BITSHIFT) | (int(move_out) << 1 + BITSHIFT) | (int(quit_error) << 2 + BITSHIFT)
    try:
        response = client.write_register(AUSGABEREGISTER, ausgabewert)
        if response.isError():
            logging.error("Fehler beim Schreiben der Ausgabe.")
        else:
            logging.info(f"Ausgabe geschrieben: move_in={move_in}, move_out={move_out}, quit_error={quit_error}")
    except Exception as e:
        logging.error(f"Fehler beim Schreiben der Ausgabe: {e}")

# Referenzbewegung ausführen
def referenzbewegung_ausführen():
    try:
        logging.info("Führen Sie die Referenzbewegung aus...")
        ausgabe_schreiben(move_in=True)
        time.sleep(1)  # Wartezeit anpassen
        ausgabe_schreiben(move_in=False)
        ausgabe_schreiben(move_out=True)
        time.sleep(1)  # Wartezeit anpassen
        ausgabe_schreiben(move_out=False)
    except Exception as e:
        logging.error(f"Fehler beim Ausführen der Referenzbewegung: {e}")

# Ereignis-Handler für Schaltflächen
def bei_schaltfläche_drücken(aktion):
    if aktion == 'move_in':
        ausgabe_schreiben(move_in=True)
    elif aktion == 'move_out':
        ausgabe_schreiben(move_out=True)
    elif aktion == 'quit_error':
        ausgabe_schreiben(quit_error=True)

def bei_schaltfläche_loslassen(aktion):
    if aktion == 'move_in':
        ausgabe_schreiben(move_in=False)
    elif aktion == 'move_out':
        ausgabe_schreiben(move_out=False)
    elif aktion == 'quit_error':
        ausgabe_schreiben(quit_error=False)

# GUI für Steuerung
def steuerungs_gui_erstellen(selected_ip):
    fenster = tk.Tk()
    fenster.title("EPCE-TB Steuerungsschnittstelle")
    fenster.geometry("800x800")

    # Anzeige für "Verbunden mit" IP-Adresse
    status_label = tk.Label(fenster, text=f"Verbunden mit: {selected_ip}", bg="green", fg="white", font=("Arial", 16))
    status_label.pack(pady=20)

    # Move In Button
    move_in_button = tk.Button(fenster, text="Move In", width=20, height=2, bg="lightblue", fg="black")
    move_in_button.bind("<ButtonPress>", lambda event: bei_schaltfläche_drücken('move_in'))
    move_in_button.bind("<ButtonRelease>", lambda event: bei_schaltfläche_loslassen('move_in'))
    move_in_button.pack(pady=10)

    # Move Out Button
    move_out_button = tk.Button(fenster, text="Move Out", width=20, height=2, bg="lightblue", fg="black")
    move_out_button.bind("<ButtonPress>", lambda event: bei_schaltfläche_drücken('move_out'))
    move_out_button.bind("<ButtonRelease>", lambda event: bei_schaltfläche_loslassen('move_out'))
    move_out_button.pack(pady=10)

    # Referenzbewegung Button
    referenz_button = tk.Button(fenster, text="Referenz", width=20, height=2, bg="orange", fg="black", command=referenzbewegung_ausführen)
    referenz_button.pack(pady=10)

    # Quit Error Button
    quit_error_button = tk.Button(fenster, text="Fehler Quittieren", width=20, height=2, bg="red", fg="white")
    quit_error_button.bind("<ButtonPress>", lambda event: bei_schaltfläche_drücken('quit_error'))
    quit_error_button.bind("<ButtonRelease>", lambda event: bei_schaltfläche_loslassen('quit_error'))
    quit_error_button.pack(pady=10)

    fenster.mainloop()

# GUI für Netzwerkscan
def scan_gui_erstellen():
    scan_fenster = tk.Tk()
    scan_fenster.title("Netzwerkscan")
    scan_fenster.geometry("800x800")

    def bei_scan():
        geräte = netzwerk_scannen()
        if geräte:
            logging.info("Gefundene Geräte:")
            for gerät in geräte:
                logging.info(gerät)

            # Dropdown-Menü zur Auswahl der IP-Adresse
            ausgewähltes_gerät = tk.StringVar(scan_fenster)
            ausgewähltes_gerät.set(geräte[0])  # Standardwert

            gerät_menü = tk.OptionMenu(scan_fenster, ausgewähltes_gerät, *geräte)
            gerät_menü.pack(pady=10)

            def verbinden():
                if verbinden_modbus(ausgewähltes_gerät.get()):
                    scan_fenster.destroy()  # Schließe das Scan-Fenster
                    steuerungs_gui_erstellen(ausgewähltes_gerät.get())  # Öffne Steuerungs-GUI

            verbinden_button = tk.Button(scan_fenster, text="Verbinden", command=verbinden, bg="green", fg="white")
            verbinden_button.pack(pady=10)
        else:
            logging.info("Keine Geräte gefunden.")

    scan_button = tk.Button(scan_fenster, text="Netzwerk Scannen", command=bei_scan, width=20, height=2, bg="blue", fg="white")
    scan_button.pack(pady=50)

    scan_fenster.mainloop()

# Initialisiere das Netzwerkscan-GUI
scan_gui_erstellen()
