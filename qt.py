import pwnagotchi.plugins as plugins
from pwnagotchi import config
import pwnagotchi
import logging
import qrcode
from PIL import Image
import html
import csv
import os
import io
import glob
import telegram
import time


class qt(plugins.Plugin):
    __author__ = 'NeonLightning'
    __version__ = '0.1.3'
    __license__ = 'GPL3'
    __description__ = ''
        
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
                    
        for ssid, password in zip(all_ssid, all_passwd):
            png_filepath = os.path.join("/home/pi/qrcodes/", f"{ssid}-{password}.png")

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
                logging.info(f"[qt] QR code generated and saved for {ssid}-{password}")
            except Exception as e:
                logging.error(f"[qt] something went wrong generating QR code for {ssid}-{password}: {e}")

    def on_internet_available(self, agent):
        pass
        
    def send_qr_codes(self):
        dir_path = "/home/pi/qrcodes"
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)

        try:
            f = open("/home/pi/qrcodes/.qrlist", "a+")
            last_files = set(f.read().splitlines())
        except Exception as e:
            logging.error(f"[qt] something went wrong while reading : {e}")
        finally:
            if f is not None:
                f.close()

        sent_files = set()

        while True:
            self._update_all()
            current_files = set(f for f in os.listdir('/home/pi/qrcodes') if f.endswith('.png'))
            new_files = current_files - last_files
            if new_files:
                for filename in new_files:
                    if filename in sent_files:
                        continue
                    bssid = filename.split('-')[1]
                    bssid = bssid.lower().replace(':', '')
                    geojson_files = glob.glob(f"/root/handshakes/*_{bssid}.geo.json")
                    # logging.info(f"[qt] geo.json : {geojson_files}")
                    if geojson_files:
                        with open(f"/home/pi/qrcodes/{filename}", 'rb') as f_png, open(geojson_files[0], 'rb') as f_geojson:
                            self.bot.send_message(self.chat_id, f"Sending file {filename}")
                            self.bot.send_photo(self.chat_id, f_png)
                            self.bot.send_document(self.chat_id, f_geojson)
                            time.sleep(1)
                    else:
                        with open(f"/home/pi/qrcodes/{filename}", 'rb') as f:
                            self.bot.send_message(self.chat_id, f"Sending file {filename}")
                            self.bot.send_photo(self.chat_id, f)
                            time.sleep(1)
                    sent_files.add(filename)

            deleted_files = last_files - current_files

            with open("/home/pi/qrcodes/.qrlist", "w") as f:
                f.write("\n".join(current_files))

            last_files = current_files
            time.sleep(60)
