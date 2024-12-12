import tkinter as tk
import logging
from pymodbus.client import ModbusTcpClient
import time

# Logging Konfiguration
logging.basicConfig(level=logging.INFO)

# Modbus Konfiguration
IP_ADDRESS = "192.168.0.25"
OUTPUT_REGISTER = 0x0000  # Ausgaberegister (Überprüfen die Adressgenauigkeit)

# Verschiebung um 8 Positionen, da die Kanäle von Kanal 8 anstelle von 0 beginnen
BIT_SHIFT = 8

# Verbindung zum Modbus TCP-Server herstellen
def connect_to_modbus():
    client = ModbusTcpClient(IP_ADDRESS)
    if client.connect():
        logging.info(f"Verbindung zu {IP_ADDRESS} erfolgreich.")
        return client
    else:
        logging.error(f"Kann nicht zu {IP_ADDRESS} verbinden.")
        return None

# In das Modbus-Ausgaberegister schreiben (BIT_SHIFT für Offset hinzufügen)
def write_output(move_in=False, move_out=False, quit_error=False):
    output_value = (int(move_in) << (0 + BIT_SHIFT)) | (int(move_out) << (1 + BIT_SHIFT)) | (int(quit_error) << (2 + BIT_SHIFT))
    try:
        response = client.write_register(OUTPUT_REGISTER, output_value)
        if response.isError():
            logging.error("Fehler beim Schreiben der Ausgabe.")
        else:
            logging.info(f"Ausgabe geschrieben: move_in={move_in}, move_out={move_out}, quit_error={quit_error}")
    except Exception as e:
        logging.error(f"Fehler beim Schreiben der Ausgabe: {e}")

# Ausführen der Referenzbewegung (Anpassungen gemäß Ihren Referenzbefehlen)
def execute_reference_movement():
    try:
        logging.info("Führen Sie die Referenzbewegung aus...")
        # Aktivieren Sie Move In
        write_output(move_in=True)
        time.sleep(1)  # Verzögerung nach Bedarf anpassen
        write_output(move_in=False)  # Deaktivieren  Move In

        # Aktivieren Sie Move Out
        write_output(move_out=True)
        time.sleep(1)  # Verzögerung nach Bedarf anpassen
        write_output(move_out=False)  # Deaktivieren Sie Move Out

    except Exception as e:
        logging.error(f"Fehler beim Ausführen der Referenzbewegung: {e}")

# Ereignis-Handler für das Drücken der Schaltfläche (wird beim Drücken der Schaltfläche ausgelöst)
def on_button_press(action):
    if action == 'move_in':
        write_output(move_in=True)
    elif action == 'move_out':
        write_output(move_out=True)
    elif action == 'quit_error':
        write_output(quit_error=True)

# Ereignis-Handler für das Loslassen der Schaltfläche (setzt den Befehl beim Loslassen der Schaltfläche zurück)
def on_button_release(action):
    if action == 'move_in':
        write_output(move_in=False)  # Setzen  Move In auf False zurück
    elif action == 'move_out':
        write_output(move_out=False)  # Setzen  Move Out auf False zurück
    elif action == 'quit_error':
        write_output(quit_error=False)  # Setzen Quit Error auf False zurück

# Überschreiben Sie das Verhalten der Referenzschaltfläche
def on_reference_button():
    execute_reference_movement()

def create_gui():
    window = tk.Tk()
    window.title("EPCE-TB Steuerungsschnittstelle----SEMIR - THE Python and FESTO Master")
    
    # Move In Button (für Kanal 8)
    move_in_button = tk.Button(window, text="Move In")
    move_in_button.bind("<ButtonPress>", lambda event: on_button_press('move_in'))
    move_in_button.bind("<ButtonRelease>", lambda event: on_button_release('move_in'))
    move_in_button.pack(pady=10)
    
    # Move Out Button (für Kanal 9)
    move_out_button = tk.Button(window, text="Move Out")
    move_out_button.bind("<ButtonPress>", lambda event: on_button_press('move_out'))
    move_out_button.bind("<ButtonRelease>", lambda event: on_button_release('move_out'))
    move_out_button.pack(pady=10)
    
    # Referenzbewegungs-Schaltfläche (feste Aktion)
    reference_button = tk.Button(window, text="Reference", command=on_reference_button)
    reference_button.pack(pady=10)
    
    # Fehlerquittierungsschaltfläche (für Kanal 10)
    quit_error_button = tk.Button(window, text="Error Quit")
    quit_error_button.bind("<ButtonPress>", lambda event: on_button_press('quit_error'))
    quit_error_button.bind("<ButtonRelease>", lambda event: on_button_release('quit_error'))
    quit_error_button.pack(pady=10)
    
    window.mainloop()

# Modbus-Client initialisieren
client = connect_to_modbus()

if client:
    create_gui()
else:
    logging.error("Kann keine Verbindung zum Modbus-Server herstellen.")
