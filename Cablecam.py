
import RPi.GPIO as GPIO
from PCA9685 import PCA9685
import json
import os
import time
import subprocess
from parse import *
import sys
class PiTZ:

    sys.setrecursionlimit(100000) # set the recursion limit to 10000 or a higher value if needed
    Step=18
    Dir=23
    En=24
    pas=1
    TiltSensorPin = 12
    TiltSensorPin2 = 25
    vitesse = 00.002785
    t=0.1
    Moteur_status = ""
    pwm = PCA9685() #On charge le driver du pan tilt Waveshare
    pwm.setPWMFreq(50) #Pour les servo moteur, la fréquence doit rester à 50Hz
    homePan=90
    homeTilt=90
    panMin=1
    panMax=165
    tiltMin=1
    tiltMax=165
    pan=homePan
    tilt=homeTilt
    panStep=2
    tiltStep=2
    panSpeed = 1
    tiltSpeed = 1
    current_position = 0
    move_to_position = 0
    current_speed = 0
    ccspeed = 0
    value = 0
    sliderValue = 0
    max_speed = 0.00018
    min_speed= 0.018
    angle_de_pas = 1.8
    distance_parcourue = 0
    valcc = 0
    ccMax = 100000
    ccMin = 0
    distanceRight = 0
    sliderValue = 0
    udpStreamConfig="224.168.1.84:5000"
    ptz_stop=False
    distance_restante = 0
    distance = 0
    position = 0
    homeposition = position
    

    def __init__(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(self.En, GPIO.OUT)
        GPIO.setup(self.Step, GPIO.OUT)
        GPIO.setup(self.Dir, GPIO.OUT)
        GPIO.setup(self.TiltSensorPin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self.TiltSensorPin2, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    
        self.ccAutoCalibrate()
        self.configCall("default")
        self.initPan()
        self.initTilt()
        self.initccMan()
        self.Value = None
        self.current_position = 0
        
        

    def set_speed(speed):
        global current_speed
        current_speed = speed
    
    def __del__(self):
        self.pwm.exit_PCA9685()
        print ('extinction de PiTZ')
    def initccMan(self):
        self.ccMan()
        self.ccManStop()
        self.initccVitesse()
        self.ccMax = 0
        self.ccMin = 0
        self.position = self.homeposition
        self.vitesse = 0.000995
        self.sliderValue = 0.000995
        self.Homecc = self.ccMax/2

    def initPan(self):
        print ('Initialisation Pan')
        self.pwm.setRotationAngle(1, self.homePan)
        self.pan=self.homePan
    def initTilt(self):
        print ('Initialisation Tilt')
        self.pwm.setRotationAngle(0, self.homeTilt)
        self.tilt=self.homeTilt
        print ('IMG Config Initialized')
    def initccVitesse(self):
        self.ccVitesse(self.value)
    ## RETURN LIST OF CONFIG FILES
    def listConfigFiles(self):
        files=[]
        for (dirpath,dirnames,filenames) in os.walk("config/"):
            for file in filenames:
                files.append(parse("config_{}", file)[0])
        return (files)
    ## RETURN LIST OF PARAMS OF A CONFIG FILE
    def listConfigParams(self,n=""):
        paramlist=[]
        if n!="":
            paramlist=self.getConfig(n)
        else:
            paramlist.append(self.homePan)
            paramlist.append(self.homeTilt)
            paramlist.append(self.panMin)
            paramlist.append(self.panMax)
            paramlist.append(self.tiltMin)
            paramlist.append(self.tiltMax)
            paramlist.append(self.ccspeed)
            
            
        return paramlist
    def getConfig(self,n):
        paramlist=[]
        if os.path.exists(f'config/config_{n}'): #Si on a un fichier de configuration on le charge
            file=open(f'config/config_{n}',"r")
            paramlist=json.load(file)
            file.close()
        return paramlist
    ## SAVE CONFIG FILE (name)
    def configSave(self,n):
        paramlist=self.listConfigParams()
        file=open(f'config/config_{n}',"w")
        file.write(json.dumps(paramlist))
        file.close()
        print (f"Config saved in config_{n}")
    ## DELETE CONFIG FILE (name)
    def configDelete(self,n):
        if os.path.exists(f'config/config_{n}'):
            os.remove(f'config/config_{n}')
        print (f"Config file config_{n} removed")
    ## RECALL CONFIG FILE (name)
    def configCall(self,n):
        paramlist=self.getConfig(n)
        if paramlist!=[]: #Si on a un fichier de configuration on le charge
            self.homePan=paramlist[0]
            self.homeTilt=paramlist[1]
            self.panMin=paramlist[2]
            self.panMax=paramlist[3]
            self.tiltMin=paramlist[4]
            self.tiltMax=paramlist[5]
            self.ccspeed=paramlist[6]
            
            print (f'Loading configuration config_{n}')
        elif n=="default": #si on n'a pas de fichier de configuration, on le crée avec les valeurs par défaut
            print ('Loading default configuration and saving file')
            self.configSave("default")


    #### SHUTDOWN CAM
    def SHUTDOWN(self):
        subprocess.call("sudo shutdown --poweroff now", shell=True)
    #### REBOOT CAM
    def REBOOT(self):
        subprocess.call("sudo reboot now", shell=True)
    def ptzGoTo(self,pan,tilt, panSpeed="",tiltSpeed="", distance_parcourue=""):
        steps = 25
        
        if pan!="":
            if pan>self.panMax:
                valpan=self.panMax
            elif pan<self.panMin:
                valpan=self.panMin
            else:
                valpan=pan
            # Diviser en 18 étapes
            
            angle_step = (valpan - self.pan) / steps
            for i in range(steps):
                # Déplacer progressivement le servomoteur d'une étape à la fois
                angle = self.pan + round(angle_step)
                self.pwm.setRotationAngle(1, angle)
                self.pan = angle
                time.sleep(0.1) # Attendre un petit laps de temps

        if tilt!="":
            if tilt>self.tiltMax:
                valtilt=self.tiltMax
            elif tilt<self.tiltMin:
                valtilt=self.tiltMin
            else:
                valtilt=tilt
            angle_step = (valtilt - self.tilt) / steps
            for i in range(steps):
            # Déplacer progressivement le servomoteur d'une étape à la fois
                angle = self.tilt + round(angle_step)
                self.pwm.setRotationAngle(0, angle)
                self.tilt = angle
                time.sleep(0.1) # Attendre un petit laps de temps

        if self.current_position < distance_parcourue :
                self.ccGoto(ccDir="ccleft", position=(distance_parcourue - self.current_position))
        elif self.current_position > distance_parcourue:
                self.ccGoto(ccDir="ccright", position=(self.current_position - distance_parcourue))
            
    #### Rappel de valeurs PTZ FOCUS ZOOM
    #### PTZ
    def ptz(self,panSpeed,tiltSpeed,panDir="",tiltDir=""):
        breakingPan=False
        breakingTilt=False
        pan_step = 1 #Valeur du pas de pan
        tilt_step = 1 #Valeur du pas de tilt
        while True:
            if panDir=="left":
                valPan=self.pan+int(panSpeed)*pan_step
                if valPan>self.panMax:
                    valPan=self.panMax
                    breakingPan=True
            elif panDir=="right":
                valPan=self.pan-int(panSpeed)*pan_step
                if valPan<self.panMin:
                    valPan=self.panMin
                    breakingPan=True
            else:
                breakingPan=True
            if panDir!="" and breakingPan!=True:
                self.pwm.setRotationAngle(1, valPan)
                self.pan=valPan

            if tiltDir=="up":
                valTilt=self.tilt-int(tiltSpeed)*tilt_step
                if valTilt<self.tiltMin:
                    valTilt=self.tiltMin
                    breakingTilt=True
            elif tiltDir=="down":
                valTilt=self.tilt+int(tiltSpeed)*tilt_step
                if valTilt>self.tiltMax:
                    valTilt=self.tiltMax
                    breakingTilt=True
            else:
                breakingTilt=True
            if tiltDir!="" and breakingTilt!=True:
                self.pwm.setRotationAngle(0, valTilt)
                self.tilt=valTilt
            if breakingPan==True and breakingTilt==True:
                print(f'stop PTZ Thread values max pan={self.pan}, tilt={self.tilt}')
                break
            time.sleep(0.01)
            if self.ptz_stop:
                print(f'stop PTZ Thread pan={self.pan}, tilt={self.tilt}') 
                self.ptz_stop=False
                break
    #### PTZ STOP
    def ptzStop(self):
        self.ptz_stop=True


    #### PRESET SAVE
    def presetSave(self,n):
        paramlist=[]# pan,tilt,zoom,focus
        paramlist.append(str(self.pan))
        paramlist.append(str(self.tilt))
        paramlist.append(str(1000))
        paramlist.append(str(1000))
        paramlist.append(str(self.current_position))
        file=open(f'mem/mem_{n}',"w")
        file.write(json.dumps(paramlist))
        file.flush()
        file.close()
        print (f'Writing {paramlist} to mem_{n}')
    #### PRESET CALL
    def presetCall(self,n):
        if n=="home":
            self.ptzGoTo(int(self.homePan),int(self.homeTilt),distance_parcourue = self.Homecc)
          
        elif os.path.exists(f'mem/mem_{n}'):
            paramlist=[]# pan,tilt,zoom,focus
            file=open(f'mem/mem_{n}',"r")
            paramlist=json.load(file)
            file.close()
            self.ptzGoTo(int(paramlist[0]),int(paramlist[1]),int(paramlist[2]),int(paramlist[3]),int(paramlist[4]))
            print (f'Reading {paramlist} from mem_{n}')
        else:
            print (f'Nada in mem_{n}')

    def ccVitesse(self, sliderValue=""):
                steps = 1
                sliderValue = int(sliderValue)/steps
                for i in range(steps):
                    time_per_step = (sliderValue/100) * (0.000018- 0.0018) + 0.0018
                    rounded_time_per_step = round(time_per_step, 6)
                    nb_impulsions = int(sliderValue * (400/4))
                    for i in range(nb_impulsions):
                        self.sliderValue = rounded_time_per_step
                
                    print(f'vitesse2 = {self.sliderValue}')
                    print(f'step {rounded_time_per_step}')


    def ccGoto(self, ccDir="", position=""):
        global Moteur_status
        Step = 18
        Dir = 23
        GPIO.cleanup()
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(Step, GPIO.OUT)
        GPIO.setup(Dir, GPIO.OUT)
        GPIO.output(Step, self.Moteur_status)
        GPIO.output(Dir, self.Moteur_status)

        if ccDir == "ccleft":
            print("ccleft")
            self.Moteur_status = 1
            GPIO.cleanup(self.En)
            GPIO.output(Dir, GPIO.HIGH)
            nb_pas_left = 0
            distance_parcourue_actuelle = 0
            distance_restante = position

            while distance_restante > 0:
            # Calcule la distance parcourue
                nb_pas_left += 1
                distance_parcourue_actuelle = (nb_pas_left * self.angle_de_pas)
                distance_restante = position - distance_parcourue_actuelle
                
                if distance_restante > position * 0.995:
                    vitesse = float(self.sliderValue) / 0.1
                elif distance_restante > position * 0.990:
                    vitesse = float(self.sliderValue) / 0.2
                elif distance_restante > position * 0.985:
                    vitesse = float(self.sliderValue) / 0.3
                elif distance_restante > position * 0.980:
                    vitesse = float(self.sliderValue) / 0.4
                elif distance_restante > position * 0.975:
                    vitesse = float(self.sliderValue) / 0.5
                elif distance_restante > position * 0.970:
                    vitesse = float(self.sliderValue) / 0.6
                elif distance_restante > position * 0.965:
                    vitesse = float(self.sliderValue) / 0.7
                elif distance_restante > position * 0.960:
                    vitesse = float(self.sliderValue) / 0.8
                elif distance_restante > position * 0.955:
                    vitesse = float(self.sliderValue) / 0.9
                elif distance_restante > position * 1:
                    vitesse = float(self.sliderValue)
                else:
                    if distance_restante > position * 0.1:
                        vitesse = float(self.sliderValue)
                    elif distance_restante > position * 0.09:
                        vitesse = float(self.sliderValue)/ 0.9
                    elif distance_restante > position * 0.08:
                        vitesse = float(self.sliderValue)/ 0.8
                    elif distance_restante > position * 0.07:
                        vitesse = float(self.sliderValue)/ 0.6
                    elif distance_restante > position * 0.06:
                        vitesse = float(self.sliderValue)/ 0.5
                    elif distance_restante > position * 0.05:
                        vitesse = float(self.sliderValue)/ 0.4
                    elif distance_restante > position * 0.04:
                        vitesse = float(self.sliderValue)/ 0.3
                    elif distance_restante > position * 0.03:
                        vitesse = float(self.sliderValue)/ 0.2
                    elif distance_restante > position * 0.01:
                        vitesse = float(self.sliderValue)/ 0.1
                    else:
                        vitesse = float(self.sliderValue)/ 0.05

            # Tourne le moteur avec la vitesse calculée
                GPIO.output(Step, GPIO.HIGH)
                time.sleep(vitesse)
                GPIO.output(Step, GPIO.LOW)
                time.sleep(vitesse)

            self.current_position += round(position)
            print(f'la position actuelle est: {self.current_position}')

        elif ccDir == "ccright":
            print("ccright")
            self.Moteur_status = 0
            GPIO.cleanup(self.En)
            GPIO.output(Dir, GPIO.LOW)
            nb_pas_right = 0
            distance_parcourue_actuelle = 0
            distance_restante = position

            while distance_restante > 0:
                # Calcule la distance parcourue
                nb_pas_right += 1
                distance_parcourue_actuelle = (nb_pas_right * self.angle_de_pas)
                distance_restante = position - distance_parcourue_actuelle

                

            # Calcule la vitesse en fonction de la distance restante
                if distance_restante > position * 0.995:
                    vitesse = float(self.sliderValue) / 0.1
                elif distance_restante > position * 0.985:
                    vitesse = float(self.sliderValue) / 0.2
                elif distance_restante > position * 0.980:
                    vitesse = float(self.sliderValue) / 0.3
                elif distance_restante > position * 0.975:
                    vitesse = float(self.sliderValue) / 0.4
                elif distance_restante > position * 0.970:
                    vitesse = float(self.sliderValue) / 0.5
                elif distance_restante > position * 0.965:
                    vitesse = float(self.sliderValue) / 0.6
                elif distance_restante > position * 0.960:
                    vitesse = float(self.sliderValue) / 0.7
                elif distance_restante > position * 0.955:
                    vitesse = float(self.sliderValue) / 0.8
                elif distance_restante > position * 1:
                    vitesse = float(self.sliderValue)
                else:
                    if distance_restante > position * 0.1:
                        vitesse = float(self.sliderValue)
                    elif distance_restante > position * 0.09:
                        vitesse = float(self.sliderValue)/ 0.9
                    elif distance_restante > position * 0.08:
                        vitesse = float(self.sliderValue)/ 0.8
                    elif distance_restante > position * 0.07:
                        vitesse = float(self.sliderValue)/ 0.6
                    elif distance_restante > position * 0.06:
                        vitesse = float(self.sliderValue)/ 0.5
                    elif distance_restante > position * 0.05:
                        vitesse = float(self.sliderValue)/ 0.4
                    elif distance_restante > position * 0.04:
                        vitesse = float(self.sliderValue)/ 0.3
                    elif distance_restante > position * 0.03:
                        vitesse = float(self.sliderValue)/ 0.2
                    elif distance_restante > position * 0.01:
                        vitesse = float(self.sliderValue)/ 0.15
                    else:
                        vitesse = float(self.sliderValue)/ 0.1

            # Tourne le moteur avec la vitesse calculée
                GPIO.output(Step, GPIO.HIGH)
                time.sleep(vitesse)
                GPIO.output(Step, GPIO.LOW)
                time.sleep(vitesse)
            self.current_position -= round(position)
            print(f'la position actuelle est: {self.current_position}')

    def ccMan(self,ccDir=""):
        global Moteur_status
        breakingcc=False
        Step=18
        Dir=23
        GPIO.cleanup()
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(Step, GPIO.OUT)
        GPIO.setup(Dir, GPIO.OUT)
        self.Moteur_status = not self.Moteur_status
        GPIO.output(Step, self.Moteur_status)
        GPIO.output(Dir, self.Moteur_status)

            
        if ccDir=="ccleft":
            self.Moteur_status = 1
            GPIO.cleanup(self.En)
            GPIO.output(Dir,GPIO.HIGH)
            nb_pas = 0
            while True:
                
                GPIO.output(Step, GPIO.HIGH)
                time.sleep(float(self.sliderValue))
                GPIO.output(Step, GPIO.LOW)
                time.sleep(float(self.sliderValue))
                nb_pas += 1
                nb_tours, nb_pas_partiels = divmod(nb_pas, 400)
                self.distance_parcourue = round((nb_tours * 400 + nb_pas_partiels) * self.angle_de_pas)
                if (self.distance_parcourue + self.current_position) > self.ccMax:
                    self.distance_parcourue = (self.ccMax - self.current_position)
                    breakingcc=True
                    if breakingcc==True:
                        print(f'stop cc values max ={self.ccMax - self.current_position}')
                        self.ccManStop("ccstop")
                else:
                    self.valcc=round(self.distance_parcourue)

                
       


        if ccDir=="ccright":
            
            self.Moteur_status = 0
            GPIO.cleanup(self.En)
            GPIO.output(Dir,GPIO.LOW)
            nb_pas = 0
            while True:
                GPIO.output(Step, GPIO.HIGH)
                time.sleep(float(self.sliderValue))
                GPIO.output(Step, GPIO.LOW)
                time.sleep(float(self.sliderValue))
                nb_pas += 1
                nb_tours, nb_pas_partiels = divmod(nb_pas, 400)
                self.distance_parcourue = round(((nb_tours * 400 + nb_pas_partiels) * self.angle_de_pas))
                if self.current_position - self.distance_parcourue < self.ccMin:
                    self.distance_parcourue = (self.ccMin - self.current_position)
                    breakingcc=True
                    if breakingcc==True:
                        print(f'stop cc values Min ={self.ccMin - self.current_position}')
                        self.ccManStop("ccstop")
                else:
                    self.valcc=round(self.distance_parcourue)
       
    def ccManStop(self,ccstop=""):
        if ccstop=="ccstop":
            GPIO.setup(self.En, GPIO.OUT)
            GPIO.output(self.En, GPIO.LOW)
            GPIO.cleanup()
            time.sleep(0.1)
            print ("stop tout")
            
            if self.Moteur_status == 1:
                self.current_position = round(self.current_position+self.valcc)
                print(f'distance parcourue à gauche: {self.valcc}')
                print(f'la position actuelle est: {self.current_position}')
                GPIO.setup(self.En, GPIO.OUT)
                GPIO.output(self.En, GPIO.LOW)
                GPIO.cleanup()
            if self.Moteur_status == 0:
                self.current_position = round(self.current_position-self.valcc)
                print(f'distance parcourue à droite : {self.valcc}')
                print(f'la position actuelle est: {self.current_position}')
            
    def ccManLoops(self,ccloops=""):

        if ccloops=="ccloops":

            print("Démarrage de ccloops")
            while True:
                self.ccGoto(ccDir="ccleft", position=((self.ccMax) - self.current_position))
                print(f'stop cc values max ={self.current_position}')
                self.current_position = self.ccMax
                time.sleep(1)  # import time
                if self.current_position == self.ccMax:
                    self.ccGoto(ccDir="ccright", position=(self.current_position - (self.ccMin)))
                    print(f'stop cc values Min ={self.current_position}')
                    self.current_position = self.ccMin
                    time.sleep(1)
                    
    def ccAutoCalibrate(self,cccalibrate=""):
            GPIO.setmode(GPIO.BCM)
            TiltSensorPin = 12
            self.ccMin = 0
            self.ccMax = 0
            Step=18
            Dir=23
            nb_pas = 0
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(Step, GPIO.OUT)
            GPIO.setup(Dir, GPIO.OUT)
            GPIO.setup(TiltSensorPin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            
            if cccalibrate == "cccalibrate":
                print("calibrate")
                while True:
                    
                    GPIO.output(Dir,GPIO.LOW)
                    GPIO.output(Step, GPIO.HIGH)
                    time.sleep(float(self.vitesse))
                    GPIO.output(Step, GPIO.LOW)
                    time.sleep(float(self.vitesse))
                    nb_pas += 1
                    nb_tours, nb_pas_partiels = divmod(nb_pas, 400)
                    self.distance_parcourue = round((nb_tours * 400 + nb_pas_partiels) * self.angle_de_pas)
                    self.valcc=round(self.distance_parcourue)
                    etat = GPIO.input(TiltSensorPin)
                    
                    if etat == 0 :
                        self.ccMin= self.ccMin +10
                        print(f'ccMin= {self.ccMin}')
                        self.ccMarche(ccDir="ccleft")

    def ccMarche(self,ccDir=""):
        global Moteur_status
        Step=18
        Dir=23
        TiltSensorPin2 = 25
        GPIO.cleanup()
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(Step, GPIO.OUT)
        GPIO.setup(Dir, GPIO.OUT)
        self.Moteur_status = not self.Moteur_status
        GPIO.output(Step, self.Moteur_status)
        GPIO.output(Dir, self.Moteur_status)
        GPIO.setup(TiltSensorPin2, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        

            
        if ccDir=="ccleft":
            self.Moteur_status = 1
            GPIO.cleanup(self.En)
            GPIO.output(Dir,GPIO.HIGH)
            nb_pas = 0
            while True:
                
                GPIO.output(Step, GPIO.HIGH)
                time.sleep(float(self.vitesse))
                GPIO.output(Step, GPIO.LOW)
                time.sleep(float(self.vitesse))
                nb_pas += 1
                nb_tours, nb_pas_partiels = divmod(nb_pas, 400)
                self.distance_parcourue = round((nb_tours * 400 + nb_pas_partiels) * self.angle_de_pas)
                etat = GPIO.input(TiltSensorPin2)
                if etat == 0 :
                    self.ccMax = (self.distance_parcourue )-10
                    print(f'ccMax= {self.ccMax}')
                    self.ccGoto(ccDir="ccright", position=self.ccMax/2)

        