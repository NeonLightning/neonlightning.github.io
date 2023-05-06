import logging
import requests
import pwnagotchi.plugins as plugins
import os

class Text2Discord(plugins.Plugin):
    __author__ = 'NeonLightning'
    __version__ = '0.0.2'
    __license__ = 'GPL3'
    __description__ = '''
                    Sends the output of specific text files line by line out to Discord.
                    '''

    def __init__(self):
        logging.debug("[*] Text2Discord plugin created")
        self.last_line_numbers = {}

    def process_file(self, file_path):
        try:
            if not os.path.exists(file_path):
                logging.warning(f"File not found: {file_path}")
                return

            with open(file_path, 'r') as f:
                lines = f.readlines()
                logging.debug(f"Sending {len(lines)} lines from {file_path}")
                webhook_url = pwnagotchi.config['main']['plugins']['text2discord']['webhook']
                self.send_lines(lines, webhook_url)
        except Exception as e:
            logging.warning(f"An error occurred while processing the file: {file_path}. Error: {str(e)}")

    def send_lines(self, lines, webhook_url):
        message = ''
        for i, line in enumerate(lines):
            if len(message) + len(line) > 2000:
                data = {'content': message}
                response = requests.post(webhook_url, json=data)
                if response.status_code != 204:
                    logging.warning(f"Failed to send message to Discord: {message.strip()}")
                message = line
            elif i + 1 < len(lines) and len(message) + len(lines[i+1]) > 2000:
                data = {'content': message + line}
                response = requests.post(webhook_url, json=data)
                if response.status_code != 204:
                    logging.warning(f"Failed to send message to Discord: {message.strip()}")
                message = ''
            else:
                message += line
        if len(message) > 0:
            data = {'content': message}
            response = requests.post(webhook_url, json=data)
            if response.status_code != 204:
                logging.warning(f"Failed to send message to Discord: {message.strip()}")

    def on_loaded(self):
        self.file_paths = pwnagotchi.config['main']['plugins']['text2discord']['files']
        for file_path in self.file_paths:
            self.last_line_numbers[file_path] = 0

        for file_path in self.file_paths:
            self.process_file(file_path)

        logging.info(f"[*] Text2Discord plugin done")


