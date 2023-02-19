import RPi.GPIO as GPIO
import time
import json
import os
from http.server import BaseHTTPRequestHandler
import socketserver
from urllib.parse import parse_qs

# Configuration des ports GPIO
PUL = 18  # Broche PUL connectée au port GPIO 18
DIR = 23  # Broche DIR connectée au port GPIO 23
ENA = 24  # Broche ENA connectée au port GPIO 24
SWITCH_LEFT = 25  # Broche SWITCH_LEFT connectée au port GPIO 25
SWITCH_RIGHT = 8  # Broche SWITCH_RIGHT connectée au port GPIO 8
SETTINGS_FILE = "/home/pi/monprojet/settings.json"
# Configuration des paramètres de mouvement
SPEED = 500  # Vitesse en pas par seconde
ACCELERATION = 100  # Accélération en pas par seconde carré
BRAKE_RATE = 10  # Taux de freinage en pourcentage
STEPS_PER_UNIT = 200  # 1.8 degrees per step
PULSE_WIDTH = 0.002  # 2 milliseconds
STEPS_PER_MM = 25
position = {}
positions = {}
current_step = 0
current_position = 0

# Configuration des paramètres de mémorisation de position
POSITION_FILE = "positions.json"
MAX_POSITION = 5
MAX_SPEED = 10
MIN_SPEED = 1

# Configuration du serveur web
PORT = 8080

# Initialisation des ports GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(PUL, GPIO.OUT)
GPIO.setup(DIR, GPIO.OUT)
GPIO.setup(ENA, GPIO.OUT)
GPIO.setup(SWITCH_LEFT, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(SWITCH_RIGHT, GPIO.IN, pull_up_down=GPIO.PUD_UP)
motor = GPIO.PWM(PUL, 100)
motor.start(0)

# Initialisation de la vitesse et de l'accélération
GPIO.output(ENA, GPIO.HIGH)
GPIO.output(DIR, GPIO.HIGH)
GPIO.output(PUL, GPIO.LOW)
time.sleep(0.1)
GPIO.output(PUL, GPIO.HIGH)
time.sleep(0.1)
GPIO.output(PUL, GPIO.LOW)
time.sleep(0.1)
GPIO.output(ENA, GPIO.LOW)

# Fonction pour déplacer le câblecam
def move(distance, direction):
    # Calcul du nombre de pas à effectuer
    steps = int(abs(distance) * 200)

    # Configuration de la direction
    if direction == "forward":
        GPIO.output(DIR, GPIO.LOW)
    else:
        GPIO.output(DIR, GPIO.HIGH)

    # Configuration de la vitesse et de l'accélération
    GPIO.output(ENA, GPIO.LOW)
    GPIO.output(PUL, GPIO.HIGH)
    time.sleep(0.1)
    GPIO.output(PUL, GPIO.LOW)
    time.sleep(0.1)
    GPIO.output(PUL, GPIO.HIGH)
    time.sleep(0.1)
    for i in range(steps):
        # Configuration de la vitesse et de l'accélération
        delay = 1 / (SPEED * (1 + ACCELERATION * i))
        GPIO.output(PUL, GPIO.HIGH)
        time.sleep(delay)
        GPIO.output(PUL, GPIO.LOW)
        time.sleep(delay)

    # Arrêt du mouvement
    for i in range(int(BRAKE_RATE * SPEED / 100)):
        GPIO.output(PUL, GPIO.HIGH)
        time.sleep(1 / SPEED)
        GPIO.output(PUL, GPIO.LOW)
        time.sleep(1 / SPEED)
    GPIO.output(ENA, GPIO.HIGH)

def calibrate():
    # Mouvement vers la gauche
    while GPIO.input(SWITCH_LEFT) == GPIO.HIGH:
        move(-0.1, "reverse")
    move(0.5, "forward")  # Mouvement vers la droite jusqu'à la fin du câble
    move(-0.05, "reverse")  # Mouvement vers la gauche pour se positionner entre les deux capteurs
    # Boucle pour affiner la position de départ
    while GPIO.input(SWITCH_RIGHT) == GPIO.HIGH:
        move(0.01, "forward")
    while GPIO.input(SWITCH_LEFT) == GPIO.HIGH:
        move(-0.01, "reverse")
    stop()
    time.sleep(1)
    print("Calibration terminée")

def stop():
    # Désactiver le moteur
    GPIO.output(ENA, GPIO.HIGH)
    time.sleep(0.1)
    GPIO.output(ENA, GPIO.LOW)
    time.sleep(0.1)

# Fonction pour arrêter le mouvement du moteur
def stop():
    GPIO.output(PUL, GPIO.LOW)
    GPIO.output(DIR, GPIO.LOW)
    GPIO.output(ENA, GPIO.LOW)

# Fonction pour faire bouger le câblecam
def move(distance, direction):
    # Calcul du nombre de pas nécessaires pour le déplacement souhaité
    steps = int(distance * STEPS_PER_MM)
    # Configuration de la direction du mouvement
    if direction == "forward":
        GPIO.output(DIR, GPIO.HIGH)
    elif direction == "reverse":
        GPIO.output(DIR, GPIO.LOW)
    else:
        return
    # Activation du moteur
    GPIO.output(ENA, GPIO.HIGH)
    # Génération des impulsions pour faire avancer le moteur
    for i in range(steps):
        GPIO.output(PUL, GPIO.HIGH)
        time.sleep(PULSE_WIDTH)
        GPIO.output(PUL, GPIO.LOW)
        time.sleep(PULSE_WIDTH)
    # Désactivation du moteur
    stop()

# Fonction pour revenir à la position centrale
def move_to_center():
    while GPIO.input(SWITCH_LEFT) == GPIO.LOW:
        move(-0.1, "reverse")
    while GPIO.input(SWITCH_RIGHT) == GPIO.LOW:
        move(0.1, "forward")

def move_to_position(position):
    global current_position
    steps = int((position - current_position) * STEPS_PER_UNIT)
    if steps < 0:
        direction = "reverse"
    else:
        direction = "forward"
    for i in range(abs(steps)):
        move(1 / STEPS_PER_UNIT, direction)
    current_position = position

# Fonction pour ralentir et s'arrêter avant d'atteindre les interrupteurs de fin de course
def slow_stop():
    # Désactivation du moteur pour le freinage
    GPIO.output(ENA, GPIO.LOW)
    # Boucle pour ralentir progressivement
    for i in range(MAX_SPEED, MIN_SPEED - 1, -1):
        GPIO.output(PUL, GPIO.HIGH)
        time.sleep(i / ACCELERATION)
        GPIO.output(PUL, GPIO.LOW)
        time.sleep(i / ACCELERATION)
    # Arrêt complet du moteur
    stop()

# Fonction pour mémoriser une position
def save_position(position):
    # Enregistrement de la position actuelle dans la liste des positions
        position[position] = get_position()
    # Envoi d'une réponse au client HTTP
        response = {"message": "Position enregistrée avec succès : " + position}
        send_response(response)

# Fonction pour rappeler une position
def recall_position(position):
    # Récupération de la position souhaitée dans la liste des positions
    target_position = position.get(position)
    if target_position is None:
        response = {"error": "Position inconnue : " + position}
    else:
        # Calcul de la distance à parcourir pour atteindre la position
        distance = target_position - get_position()
        # Choix de la direction de déplacement
        direction = "forward" if distance > 0 else "reverse"
        # Mouvement du câblecam jusqu'à la position
        move(abs(distance), direction)
        response = {"message": "Position rappelée avec succès : " + position}
    send_response(response)

# Fonction pour envoyer une réponse HTTP au client
def send_response(self, response):
    # Envoi de l'en-tête HTTP
    self.send_response(200)
    self.send_header('Content-type', 'application/json')
    self.end_headers()
    # Envoi du corps de la réponse au format JSON
    self.wfile.write(json.dumps(response).encode())

    # Fonction pour récupérer la position actuelle du câblecam
def get_position():
    return current_position

# Fonction pour enregistrer une position
def save_position(position_name):
    position[position_name] = current_position

# Fonction pour rappeler une position enregistrée
def recall_position(position_name):
    if position_name in position:
        target_position = position[position_name]
        move_to_position(target_position)
    else:
        print("La position demandée n'a pas été enregistrée.")

# Fonction pour ajuster la vitesse du câblecam
def set_speed(speed):
    global current_speed
    current_speed = speed
    motor.setSpeed(current_speed)

# Fonction pour ajuster l'accélération du câblecam
def set_acceleration(acceleration):
    global current_acceleration
    current_acceleration = acceleration
    motor.setAcceleration(current_acceleration)

# Fonction pour ajuster le taux de freinage du câblecam
def set_brake_rate(brake_rate):
    global current_brake_rate
    current_brake_rate = brake_rate
    motor.setBrakeRate(current_brake_rate)

# Fonction pour enregistrer les paramètres actuels
def save_settings(settings_name):
    settings = {
        "speed": current_speed,
        "acceleration": current_acceleration,
        "brake_rate": current_brake_rate
    }
    saved_settings[settings_name] = settings

# Fonction pour rappeler les paramètres enregistrés
def recall_settings():
    global steps_per_unit, max_speed, min_speed, saved_settings
    if os.path.isfile(SETTINGS_FILE):
        with open(SETTINGS_FILE, 'r') as f:
            saved_settings = json.load(f)
            steps_per_unit = saved_settings['steps_per_unit']
            max_speed = saved_settings['max_speed']
            min_speed = saved_settings['min_speed']
            print("Les paramètres ont été chargés à partir du fichier.")
    else:
        saved_settings = {}
        print("Aucun fichier de paramètres n'a été trouvé.")
        print("Les paramètres demandés n'ont pas été enregistrés.")
# Classe pour gérer les requêtes HTTP
class HTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            # Page d'accueil avec les contrôles pour bouger le câblecam
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()

            response = """
            <html>
            <head>
                <title>Câblecam</title>
            </head>
            <body>
                <h1>Câblecam</h1>
                <form method="POST" action="/move">
                    <button type="submit" name="direction" value="forward">Avancer</button>
                    <button type="submit" name="direction" value="reverse">Reculer</button>
                    <button type="submit" name="direction" value="stop">Stop</button>
                </form>
                <form method="POST" action="/move_to_switch">
                    <button type="submit" name="direction" value="cycle">Cyclique</button>
                    <button type="submit" name="direction" value="stop">Stop</button>
                </form>
                <h2>Positions enregistrées</h2>
                <ul>
            """

            for position_name, position in positions.items():
                response += f"<li>{position_name}: {position:.2f} mètres</li>"

            response += """
                </ul>
                <form method="POST" action="/save_position">
                    <label for="position_name">Nom de la position:</label>
                    <input type="text" name="position_name">
                    <button type="submit">Enregistrer la position</button>
                </form>
                <form method="POST" action="/recall_position">
                    <label for="position_name">Nom de la position:</label>
                    <input type="text" name="position_name">
                    <button type="submit">Rappeler la position</button>
                </form>
                <h2>Paramètres de mouvement</h2>
                <form method="POST" action="/set_speed">
                    <label for="speed">Vitesse:</label>
                    <input type="range" name="speed" min="0" max="100" value="{current_speed}">
                    <button type="submit">Définir la vitesse</button>
                </form>
                <form method="POST" action="/set_acceleration">
                    <label for="acceleration">Accélération:</label>
                    <input type="range" name="acceleration" min="0" max="1000" value="{current_acceleration}">
                    <button type="submit">Définir l'accélération</button>
                </form>
                <form method="POST" action="/set_brake_rate">
                    <label for="brake_rate">Taux de freinage:</label>
                    <input type="range" name="brake_rate" min="0" max="100" value="{current_brake_rate}">
                    <button type="submit">Définir le taux de freinage</button>
                </form>
                <h2>Paramètres enregistrés</h2>
                <ul>
            """

            for settings_name in saved_settings.keys():
                response += f"<li>{settings_name}</li>"

            response += """

                </ul>
                <form method="POST" action="/save_settings">
                    <label for="settings_name">Nom des paramètres:</label>
                    <input type="text" name="
                                     <input type="submit" value="Enregistrer les paramètres">
            </form>
        </div>
    </body>
</html>
"""

# Fonction pour sauvegarder les paramètres
def save_settings(name, position, speed, acceleration, braking):
    data = {
        "name": name,
        "position": position,
        "speed": speed,
        "acceleration": acceleration,
        "braking": braking
    }
    with open('settings.json', 'w') as f:
        json.dump(data, f)
    print("Paramètres enregistrés avec succès.")

# Fonction pour récupérer les paramètres sauvegardés
def load_settings(name):
    try:
        with open('settings.json', 'r') as f:
            data = json.load(f)
            if data['name'] == name:
                return data
            else:
                print("Les paramètres demandés n'ont pas été enregistrés.")
    except FileNotFoundError:
        print("Aucun paramètre enregistré.")
    except:
        print("Une erreur s'est produite lors de la récupération des paramètres.")

# Fonction pour supprimer les paramètres sauvegardés
def delete_settings():
    try:
        os.remove('settings.json')
        print("Paramètres supprimés avec succès.")
    except FileNotFoundError:
        print("Aucun paramètre enregistré.")
    except:
        print("Une erreur s'est produite lors de la suppression des paramètres.")

# Classe pour gérer les requêtes HTTP
class HTTPRequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/save_settings':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            post_data = parse_qs(post_data)
            name = post_data['settings_name'][0]
            position = post_data['position'][0]
            speed = post_data['speed'][0]
            acceleration = post_data['acceleration'][0]
            braking = post_data['braking'][0]
            save_settings(name, position, speed, acceleration, braking)
        elif self.path == '/load_settings':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            post_data = parse_qs(post_data)(post_data)
            name = post_data['settings_name'][0]
            settings = load_settings(name)
            if settings:
                response = json.dumps(settings)
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(response.encode())
        elif self.path == '/delete_settings':
            delete_settings()

        # Appelle la méthode parent pour toutes les autres requêtes
        else:
            super().do_POST()

# Fonction pour démarrer le serveur
def start_server():
    httpd = socketserver.TCPServer(("", PORT), HTTPRequestHandler)
    print("Serveur démarré sur le port :", PORT)
    httpd.serve_forever()
  

           
