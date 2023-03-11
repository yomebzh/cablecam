from argparse import Action
import threading
import http.server
import socketserver 
import os
import socket
import json
from urllib import request
from parse import *
from urllib.parse import urlparse
from Cablecam import PiTZ
def get_host_ip(): #Fonction de récupération de l'adresse ip
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    finally:
        s.close()
    return ip
host = get_host_ip() #On récupère notre adresse ip
portHTTP = 80 #cgi http port 80
addrHTTP = ('',portHTTP) 
print (f"Adresse IP = {host}")
print (f"Port HTTP CGI = {portHTTP}")
print ("\n")
print(os.path.abspath("config/config_default"))


listeActionsPanTilt=['up','down','left','right','leftup','rightup','leftdown','rightdown','ptzstop']
ListeActionsCableCam=['ccleft','ccright','ccstop','ccspeed']
pitz=PiTZ()

ptzThread=threading.Thread()
zoomThread=threading.Thread()
focusThread=threading.Thread()
CCThread=threading.Thread()
class Commande: 
    global pitz,ptzThread,CCThread
    def __init__(self, page): #initialisation de la commande
        self.attPrecedent=""
        self.listeAttributs=[]
        self.action=""
        self.sliderValueSpeed= "50"
        self.page=page
        
        
        
    def __setattr__(self, name, value): #passage des paramètres de la commande
        global listeActionsPanTilt, ListeActionsCableCam
        if(name!='listeAttributs' and name!='attPrecedent' and name!='action' and name!= 'sliderValueSpeed' and name!='pitz'):
            if name.isdigit()==True:#si la variable est un nombre alors on regarde ce qu'il y avait avant et on traduit
                value=name #la valeur devient le nombre
                if(self.attPrecedent=="action" and self.action in listeActionsPanTilt):#on regarde l'action et la variable précédente pour déterminer la  variable à laquelle correspond le nombre
                    name="panSpeed"
                elif(self.attPrecedent=="panSpeed"): #si la variable précédente c'était le panSpeed, alors maintenant nous avons le tiltSpeed
                    name="tiltSpeed"
                else:
                    name="value"
            if(self.attPrecedent=="action" and self.action in ListeActionsCableCam):
                    name="sliderValueSpeed"
                
                #fin si la variable est un nombre
            if(self.attPrecedent=="ptzcmd"):
                value=name
                name="action"
            
            

            
            self.listeAttributs.append(name)
            self.__dict__["attPrecedent"]=name
        self.__dict__[name] = value
              
        
    def __str__(self): #affichage de l'interpreteur
        touslesattributs=""
        for attribut in self.listeAttributs:
            touslesattributs += attribut+'='+getattr(self,attribut)+', '
        end=len(touslesattributs)-2
        listetouslesattributs=touslesattributs[0:end]
        return listetouslesattributs

    def interpreter(self):#interpretation de la commande
        global ptzThread,CCThread
        print (self) #on affiche ce que l'on a recu à interpreter

        #IMAGE PARAMETERS
        if(getattr(self,"page")=="param"):#si on appelle un changement de parametres (complet)
            if hasattr(self, 'config'):
                if hasattr(self, 'name'):#on demande d'afficher la config dont le nom est 
                    reponse=pitz.listConfigParams(str(self.name))
                    return json.dumps(reponse)
                if hasattr(self, 'save'):#on demande d'enregistrer la config actuelle sous le nom 
                    pitz.configSave(str(self.save))
                if hasattr(self, 'delete'):#on demande de supprimer la config portant le nom 
                    pitz.configDelete(str(self.delete))
                if hasattr(self, 'list'):#on demande d'afficher la liste des fichiers de configuration
                    reponse=pitz.listConfigFiles()
                    return json.dumps(reponse)
                if hasattr(self, 'reset'):#on charge la config par default
                    pitz.configCall("default")
                if hasattr(self, 'recall'):#on charge la config par default
                    pitz.configCall(str(self.recall))
            if hasattr(self, 'power'):
                if hasattr(self, 'off'):#on envoi un SHUTDOWN
                    pitz.SHUTDOWN()
                if hasattr(self, 'reboot'):#on envoi un REBOOT
                    pitz.REBOOT()
        #PTZ CONTROL
        if(getattr(self,"page")=="ptzctrl" and hasattr(self, 'ptzcmd')):#si on appelle un ordre PTZ (complet)
            
            #PAN TILT
            if(getattr(self,"action")=="ptzstop"):#on envoi un stop
                if ptzThread.is_alive():
                    pitz.ptzStop()
                    #print(f'Pan tilt stop')
            if(getattr(self,"action")=="up"):#on envoi un up et un panSpeed (1-24) et tiltSpeed (1-20)
                print(f'Up panSpeed={self.panSpeed} (1-24), tiltSpeed={self.tiltSpeed} (1-20)')
                ptzThread=threading.Thread(target=pitz.ptz,args=(self.panSpeed,self.tiltSpeed,"","up",))
                ptzThread.start()
            if(getattr(self,"action")=="down"):#on envoi un down et un panSpeed (1-24) et tiltSpeed (1-20)
                print(f'Down panSpeed={self.panSpeed} (1-24), tiltSpeed={self.tiltSpeed} (1-20)')
                ptzThread=threading.Thread(target=pitz.ptz,args=(self.panSpeed,self.tiltSpeed,"","down",))
                ptzThread.start()
            if(getattr(self,"action")=="left"):#on envoi un left et un panSpeed (1-24) et tiltSpeed (1-20)
                print(f'Left panSpeed={self.panSpeed} (1-24), tiltSpeed={self.tiltSpeed} (1-20)')
                ptzThread=threading.Thread(target=pitz.ptz,args=(self.panSpeed,self.tiltSpeed,"left","",))
                ptzThread.start()
            if(getattr(self,"action")=="right"):#on envoi un right et un panSpeed (1-24) et tiltSpeed (1-20)
                print(f'Right panSpeed={self.panSpeed} (1-24), tiltSpeed={self.tiltSpeed} (1-20)')
                ptzThread=threading.Thread(target=pitz.ptz,args=(self.panSpeed,self.tiltSpeed,"right","",))
                ptzThread.start()
            if(getattr(self,"action")=="leftup"):#on envoi un left, un up et un panSpeed (1-24) et tiltSpeed (1-20)
                print(f'Left & up panSpeed={self.panSpeed} (1-24), tiltSpeed={self.tiltSpeed} (1-20)')
                ptzThread=threading.Thread(target=pitz.ptz,args=(self.panSpeed,self.tiltSpeed,"left","up",))
                ptzThread.start()
            if(getattr(self,"action")=="leftdown"):#on envoi un left, un down et un panSpeed (1-24) et tiltSpeed (1-20)
                print(f'Left & down panSpeed={self.panSpeed} (1-24), tiltSpeed={self.tiltSpeed} (1-20)')
                ptzThread=threading.Thread(target=pitz.ptz,args=(self.panSpeed,self.tiltSpeed,"left","down",))
                ptzThread.start()
            if(getattr(self,"action")=="rightup"):#on envoi un right, un up et un panSpeed (1-24) et tiltSpeed (1-20)
                print(f'Right & up panSpeed={self.panSpeed} (1-24), tiltSpeed={self.tiltSpeed} (1-20)')
                ptzThread=threading.Thread(target=pitz.ptz,args=(self.panSpeed,self.tiltSpeed,"right","up",))
                ptzThread.start()
            if(getattr(self,"action")=="rightdown"):
                ptzThread=threading.Thread(target=pitz.ptz,args=(self.panSpeed,self.tiltSpeed,"right","down",))
                ptzThread.start()
            if(getattr(self,"action")=="home"):#on envoi Go to home!
                pitz.presetCall("home")
                print(f'Position Home')
            if(getattr(self,"action")=="posset"):#on envoi Rec to value (0-89)
                pitz.presetSave(self.value)
                print(f'Record to position {self.value}')
            if(getattr(self,"action")=="poscall"):#on envoi Call to value (0-89)
                pitz.presetCall(self.value)
                print(f'Call position {self.value}')
	    	#CABLECAM
            if(getattr(self,"action")=="ccleft"):
                CCThread=threading.Thread(target=pitz.ccMan,args=("ccleft",))
                CCThread.start()
            if(getattr(self,"action")=="ccright"):
               CCThread=threading.Thread(target=pitz.ccMan,args=("ccright",))
               CCThread.start()
            if(getattr(self,"action")=="ccstop"):
               CCThread=threading.Thread(target=pitz.ccManStop,args=("ccstop",))
               CCThread.start()
            if (getattr(self, "action", "")=="ccspeed"):
                self.sliderValueSpeed = int(getattr(self, "sliderValueSpeed", 0))
                CCThread=threading.Thread(target=pitz.ccVitesse,args=(self.sliderValueSpeed,))
                CCThread.start()                 
                print(f'vitesse1 = {self.sliderValueSpeed }')
            if(getattr(self,"action")=="ccloops"):
               CCThread=threading.Thread(target=pitz.ccManLoops,args=("ccloops",))
               CCThread.start()
            if(getattr(self,"action")=="cccalibrate"):
               CCThread=threading.Thread(target=pitz.ccAutoCalibrate,args=("cccalibrate",))
               CCThread.start()
        return 'ok'

class CgiBin: #classe d'interpretation des demande de pages http
    response=""
    def __init__(self,page,parsed_path):
        commande=Commande(page) #on initialise l'interpreteur de commandes
        query=parsed_path.query.split('&') #on récupères les différentes valeurs de la commande
        print (page)
        for item in query: #pour chaque variable on récupère la valeur
            values=item.split('=')
            if(len(values)==2):
                valeur=values[1]
            else:
                valeur="1"
            setattr(commande,values[0],valeur) #on passe les variables et les valeurs à interpreter
        self.response=commande.interpreter() #on demande l'interpretation de la commande
    def getResponse(self):
        if self.response=="ok":
            return 'ok'
        else:
            return self.response
    
       


class HTTPHandler(http.server.BaseHTTPRequestHandler):
    global host
    def do_GET(self):
        parsed_path = urlparse(self.path)
        file_cgi=parse("/cgi-bin/{}.cgi", parsed_path.path)
        controllerfiles=parse("/control/{}", parsed_path.path)
        if(file_cgi!=None):#si on a reçu une commande http interpretable
            cgibin=CgiBin(file_cgi[0],parsed_path)#on envoie la page à l'interpreteur
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            if cgibin.getResponse()=="ok":
                self.wfile.write(bytes('[{ "response":"ok" }]',"utf-8"))
            else:
                self.wfile.write(bytes(cgibin.getResponse(),"utf-8"))
            
        elif(parsed_path.path=="/"):#si on a reçu la demande d'affiche de la page d'accueil
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write("PiTZ Optics HTTP server by n0n0 and Yome - v1.0 (17/06/2020)".encode("utf-8"))
            self.wfile.write(f"<br>IP Address : {host}".encode("utf-8"))
            self.wfile.write(f"<br>VIDEO : udp://@224.167.1.84:5000".encode("utf-8"))
         
	
        elif(controllerfiles!=None):#si on a reçu la demande d'afficher le controleur
            with open(f'Camera-Control-master/{controllerfiles[0]}', 'rb') as filet:
                self.send_response(200)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(filet.read())
        elif(parsed_path.path=="/control/"):
            with open(f'Camera-Control-master/index.html', 'rb') as filet: 
                self.send_response(200)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(filet.read())
        else:
            self.send_error(404)
        return #réponse du serveur
class PiTZHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith('/cgi-bin/ptzctrl.cgi'):
            params = self.path.split('?')[1].split('&')
            action = params[1].split('=')[1]
            if action == 'ccspeed':
                sliderValueSpeed = params[2].split('=')[1]
                print(f'ccspeed: {sliderValueSpeed}')
    def ccVitesse(self, sliderValueSpeed=""):
        distance = 0
        self.vitesse = (sliderValueSpeed)
        # Enregistrer la position avant la commande de vitesse
        position_before = self.getPosition()
        time.sleep(self.vitesse)
        # Enregistrer la position après la commande de vitesse
        position_after = self.getPosition()
        # Calculer la distance parcourue
        if position_before < position_after:
            distance = position_after - position_before
        elif position_before > position_after:
            distance = position_before - position_after
            print(f"Distance parcourue: {distance}")
                # insérer ici le code pour la fonction ccAcceleration avec la valeur de sliderValue
        else:
            print(f'Unknown action: {Action}')

        if self.path == '/current_position.cgi':
            # insérer ici le code pour la fonction getPosition
            pass
        else:
            super().do_GET()  
    def getposition():
        response = request.get(base_url + "/current_position.cgi")
        position = float(response.content.decode().strip())
        return position  

def main():
    
    
    serverHTTP = socketserver.TCPServer(addrHTTP,HTTPHandler)
    
    t3 = threading.Thread(target=serverHTTP.serve_forever)
    t3.start()
    t3.join()
	

if __name__ == "__main__":
    main()
    
    
