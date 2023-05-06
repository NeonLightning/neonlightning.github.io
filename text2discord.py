'''
Text2Discord
Sends the output of specific text files out to Discord. for "logs..."
just gotta set main.plugins.text2discord.files and main.plugins.text2discord.webhook
'''


import logging
import requests
import pwnagotchi
import pwnagotchi.plugins as plugins
import os
import time

class Text2Discord(plugins.Plugin):
    __author__ = 'NeonLightning'
    __version__ = '0.0.3'
    __license__ = 'GPL3'
    __description__ = '''
                    Sends the full content of specific text files to Discord, split into multiple messages if necessary.
                    '''

    def __init__(self):
        logging.debug("[*] Text2Discord plugin created")
        self.internet_on = False

    def on_loaded(self):
        logging.info("Text2Discord loaded")
        self.file_paths = pwnagotchi.config['main']['plugins']['text2discord']['files']
        self.webhook_url = pwnagotchi.config['main']['plugins']['text2discord']['webhook']
        logging.debug(f"File paths: {self.file_paths}")
        self.last_line_numbers = {file_path: 0 for file_path in self.file_paths}
        self.main_loop()

    def main_loop(self):
        while True:
            for file_path in self.file_paths:
                try:
                    if not os.path.exists(file_path):
                        logging.warning(f"File not found: {file_path}")
                        continue
                    with open(file_path, 'r') as f:
                        lines = f.readlines()
                        current_line_number = len(lines)
                        if current_line_number != self.last_line_numbers[file_path]:
                            logging.debug(f"Sending {current_line_number} lines from {file_path}")
                            messages = []
                            msg = ''
                            for line in lines[self.last_line_numbers[file_path]:]:
                                msg += line
                                if len(msg) >= 1650:
                                    messages.append(msg)
                                    msg = ''
                            if msg:
                                messages.append(msg)
                            for i, msg in enumerate(messages):
                                data = {'content': f'{file_path}\n{msg}'}
                                webhook_url = pwnagotchi.config['main']['plugins']['text2discord']['webhook']
                                response = requests.post(webhook_url, json=data)
                                if response.status_code != 204:
                                    logging.warning(f"Failed to send message to Discord: {msg.strip()}")
                                else:
                                    logging.info(f"Sent message {i + 1} from {file_path}")
                            self.last_line_numbers[file_path] = current_line_number
                except Exception as e:
                    logging.warning(f"An error occurred while processing the file: {file_path}. Error: {str(e)}")
            time.sleep(3600)
