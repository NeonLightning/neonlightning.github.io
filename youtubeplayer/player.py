import configparser, subprocess, pkg_resources, sys, os

def check_and_install_package(package_name, apt_name=None):
    try:
        pkg_resources.get_distribution(package_name)
        return True
    except pkg_resources.DistributionNotFound:
        pass
    if apt_name:
        apt_check = subprocess.run(['dpkg', '-s', apt_name], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        apt_installed = apt_check.returncode == 0 and "Status: install ok installed" in apt_check.stdout.decode()
    else:
        apt_installed = False
    pip_check = subprocess.run(['pip3', 'show', package_name], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    pip_installed = pip_check.returncode == 0
    if apt_installed or pip_installed:
        return True
    if apt_name:
        try:
            subprocess.check_call(['sudo', 'apt', 'install', '-y', apt_name])
            return True
        except subprocess.CalledProcessError:
            pass
    if package_name == 'vlc':
        vlc_check = subprocess.run(['vlc', '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        vlc_installed = vlc_check.returncode == 0
        if vlc_installed:
            return True
    return False

def setup():
    config = configparser.ConfigParser()
    if not os.path.exists('config.ini'):
        config['app'] = {'is_setup_done': 'False'}
        with open('config.ini', 'w') as configfile:
            config.write(configfile)
    config.read('config.ini')
    is_setup_done = config.getboolean('app', 'is_setup_done')
    if not is_setup_done:
        if not check_and_install_package('tk', 'python3-tk'):
            print("Failed to install Pygame.")
            sys.exit(1)
        if not check_and_install_package('flask', 'python3-flask'):
            print("Failed to install Flask.")
            sys.exit(1)
        if not check_and_install_package('pytube', 'python3-pytube'):
            print("Failed to install PyTube.")
            sys.exit(1)
        if not check_and_install_package('vlc'):
            print("Failed to install VLC.")
            sys.exit(1)
        config.set('app', 'is_setup_done', 'True')
        with open('config.ini', 'w') as configfile:
            config.write(configfile)
setup()

from flask import Flask, render_template, request, redirect, url_for
from pytube import Search, YouTube
from pytube.innertube import _default_clients
from pytube.exceptions import AgeRestrictedError
from pytube import innertube
import tkinter as tk
import time, threading, pytube, logging

innertube._cache_dir = os.path.join(os.path.dirname(__file__), 'cache')
innertube._token_file = os.path.join(innertube._cache_dir, 'tokens.json')
_default_clients["ANDROID"]["context"]["client"]["clientVersion"] = "19.08.35"
_default_clients["IOS"]["context"]["client"]["clientVersion"] = "19.08.35"
_default_clients["ANDROID_EMBED"]["context"]["client"]["clientVersion"] = "19.08.35"
_default_clients["IOS_EMBED"]["context"]["client"]["clientVersion"] = "19.08.35"
_default_clients["IOS_MUSIC"]["context"]["client"]["clientVersion"] = "6.41"
_default_clients["ANDROID_MUSIC"] = _default_clients["ANDROID_CREATOR"]
os.environ['DISPLAY'] = ':0'
app = Flask(__name__)
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)
app.config['VIDEO_QUEUE'] = []

def get_ip_address(interface):
    try:
        result = subprocess.run(['ip', '-4', 'addr', 'show', interface], check=True, stdout=subprocess.PIPE)
        lines = result.stdout.decode().split('\n')
        for line in lines:
            if 'inet ' in line:
                ip = line.strip().split()[1].split('/')[0]
                return ip
        return None
    except subprocess.CalledProcessError:
        return None

def display_black_screen():
    global root
    root = tk.Tk()
    root.attributes('-fullscreen', True)
    root.configure(background='black')
    font = ('Helvetica', 24)
    ip_eth0 = get_ip_address('eth0')
    ip_wlan0 = get_ip_address('wlan0')
    ip_address = ip_eth0 if ip_eth0 is not None else ip_wlan0
    label_ip = tk.Label(root, text=f"IP: {ip_address or 'Not available'}:5000", fg="white", bg="black", font=font)
    label_ip.pack(anchor='nw')
    label = tk.Label(root, text="No video playing", fg="white", bg="black", font=font)
    label.pack(expand=True)
    def update_text():
        if app.config.get('next_video_title'):
            next_video_title = app.config['next_video_title']
            label.config(text=next_video_title)
        else:
            label.config(text="No video playing")
        root.after(200, update_text)
    update_text()
    root.mainloop()

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        search_term = request.form['search_term']
        s = Search(search_term)
        if s.results:
            results_data = []
            for i, result in enumerate(s.results, start=1):
                result_data = {
                    "title": result.title,
                    "video_url": result.watch_url,
                }
                results_data.append(result_data)
            return render_template('index.html', results=results_data, app=app)
        else:
            return render_template('index.html', message='No search results found.', app=app)
    return render_template('index.html', app=app)

@app.route('/queue', methods=['POST'])
def queue():
    video_url = request.form['video_url']
    yt = YouTube(video_url)
    video_info = {
        'title': yt.title,
        'video_id': yt.video_id,
    }
    app.config['VIDEO_QUEUE'].append(video_info)
    return redirect(url_for('index'))

def play_video_from_queue():
    while True:
        if app.config['VIDEO_QUEUE']:
            video_info = app.config['VIDEO_QUEUE'].pop(0)
            app.config['next_video_title'] = f"{video_info['title']}      loading..."
            video_url = f'https://www.youtube.com/watch?v={video_info["video_id"]}'
            videopath = "/tmp/ytvid.mp4"
            try:
                if 'age_restricted' in video_info and video_info['age_restricted']:
                    stream = YouTube(video_url, use_oauth=True).streams.get_highest_resolution()
                else:
                    stream = YouTube(video_url).streams.get_highest_resolution()
                stream.download(output_path="/tmp", filename="ytvid.mp4")
            except AgeRestrictedError as e:
                print(f"Age restricted video '{video_info['title']}': {e}")
                app.config['next_video_title'] = None
                continue
            process = subprocess.Popen(["vlc", "-fq", "--play-and-exit", "--extraintf", "--no-mouse-events", "--video-on-top", "--intf", "dummy", "--no-video-title-show", "--mouse-hide-timeout", "0", videopath])
            while True:
                if process.poll() is not None:
                    break
                time.sleep(1)
            app.config['next_video_title'] = None
            subprocess.Popen(["rm", "-rf", videopath])
        else:
            break

@app.route('/play', methods=['POST', 'GET'])
def play():
    if not app.config.get('is_playing', False):
        app.config['is_playing'] = True
        threading.Thread(target=play_video_from_queue).start()
    elif not app.config['VIDEO_QUEUE']:
        app.config['is_playing'] = False
    return redirect(url_for('index'))

@app.route('/skip', methods=['POST'])
def skip():
    try:
        if app.config.get('is_playing', False):
            subprocess.run(["pkill", "vlc"])
        return redirect(url_for('index'))
    except Exception as e:
        return f"An error occurred: {e}"

@app.route('/remove', methods=['POST'])
def remove():
    index = int(request.form['index'])
    if 0 <= index < len(app.config['VIDEO_QUEUE']):
        removed_video = app.config['VIDEO_QUEUE'].pop(index)
        if app.config.get('next_video_title') == removed_video['title']:
            app.config['next_video_title'] = None
    return redirect(url_for('index'))

@app.route('/close', methods=['POST'])
def close():
    if os.path.exists("/tmp/ytdl.mp4"):
        subprocess.Popen(["rm", "-rf", "/tmp/ytdl.mp4"])
    subprocess.run(["pkill", "vlc"])
    os.system('kill %d' % os.getpid())

if __name__ == '__main__':
    gui_thread = threading.Thread(target=display_black_screen)
    gui_thread.start()
    subprocess.Popen(["flask", "run", "--port", str(5000)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    #app.run(host='0.0.0.0', port=5000, use_reloader=False)