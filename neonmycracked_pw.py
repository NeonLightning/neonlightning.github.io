import pwnagotchi.plugins as plugins
import pwnagotchi
import logging
import qrcode
from PIL import Image
import html
import csv
import os
import io


class NeonMyCrackedPasswords(plugins.Plugin):
    __author__ = '@silentree12th'
    __version__ = '5.1.1'
    __license__ = 'GPL3'
    __description__ = 'A plugin to grab all cracked passwords and creates wifi qrcodes and a wordlist which can be used for the quickdic plugin. It stores them in the home directory. Read with cat'
        
    wordlist_dir = '/home/pi/wordlists/'
    qrcode_dir = '/home/pi/qrcodes/'
        
    def on_loaded(self):
        logging.info(f"[mycracked_pw] Wordlist directory: {self.wordlist_dir}")
        logging.info("[mycracked_pw] loaded")
        if not os.path.exists('/home/pi/wordlists/'):
            os.makedirs('/home/pi/wordlists/')
            
        if not os.path.exists('/home/pi/qrcodes/'):
            os.makedirs('/home/pi/qrcodes/')
            
        self._update_all()
        
    def on_handshake(self, agent, filename, access_point, client_station):
        self._update_all()
        
    def _update_all(self):
        all_passwd=[]
        all_bssid=[]
        all_ssid=[]

        wpa_sec_filepath = '/root/handshakes/wpa-sec.cracked.potfile'
        f = open(wpa_sec_filepath, 'r+', encoding='utf-8')
        try:
            for line_f in f:
                pwd_f = line_f.split(':')
                all_passwd.append(str(pwd_f[-1].rstrip('\n')))
                all_bssid.append(str(pwd_f[0]))
                all_ssid.append(str(pwd_f[-2]))
        except:
            logging.error('[mycracked_pw] encountered a problem in wpa-sec.cracked.potfile')
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
                    all_bssid.append(bssid_h)
                    all_ssid.append(ssid_h)
        except:
            logging.error('[mycracked_pw] encountered a problem in onlinehashcrack.cracked')
        h.close()
        
        logging.info(f"[mycracked_pw] Updating QR codes and wordlists for {len(set(all_ssid))} networks")
        for ssid, password in zip(all_ssid, all_passwd):
            logging.info(f"[mycracked_pw] Updating QR code and wordlist for {ssid}")

            # Create the file names
            filename = ssid + '-' + password + '.txt'
            logging.info(f"[mycracked_pw] Updating QR for {filename}")
            logging.info(f"[mycracked_pw] Wordlist directory: {self.wordlist_dir}")
            filepath = os.path.join(self.wordlist_dir, filename)
            logging.info(f"[mycracked_pw] Wordlist directory: {self.wordlist_dir}")
            logging.info(f"[mycracked_pw] Updating QR for filespath {filepath}")
            png_filepath = os.path.join(self.qrcode_dir, ssid + '-' + password + '.png')
            logging.info(f"[mycracked_pw] Updating QR for png filepath {png_filepath}")

            # Check if PNG file already exists
            if os.path.exists(png_filepath):
                continue

            # Create the QR code object
            logging.info(f"[mycracked_pw] creating QR for {filename}")
            qr_code = qrcode.QRCode(
                version=None,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr_code.add_data(f"WIFI:T:WPA;S:{html.escape(ssid)};P:{html.escape(password)};;")
            qr_code.make(fit=True)

            try:
                # Generate ASCII QR code
                filename = "{}.txt".format(password)
                filepath = os.path.join(self.qrcode_dir, filename)
                logging.info(f"[mycracked_pw] ASCII creating QR for {filename}")

                with open(filepath, 'w+') as file:
                    qr_code.print_ascii(out=file)
                    q = io.StringIO()
                    qr_code.print_ascii(out=q)
                    q.seek(0)
                    logging.info(filename)
                    logging.info(q.read())

                # Generate PNG QR code
                img = qr_code.make_image(fill_color="yellow", back_color="black")
                img.save(png_filepath)
                logging.info("[mycracked_pw] PNG qrcode generated.")
            except:
                logging.error("[mycracked_pw] something went wrong generating QR code.")

        # start with blank file
        wordlist_filepath = os.path.join(self.wordlist_dir, 'mycracked.txt')

        # create pw list
        new_lines = sorted(set(all_passwd))
        with open(wordlist_filepath, 'w+') as g:
            for i in new_lines:
                g.write(i + "\n")

        logging.info("[mycracked_pw] pw list updated")
