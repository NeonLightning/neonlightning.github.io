import configparser, subprocess, pkg_resources, sys, os, logging, time, threading, random

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

from flask import Flask, render_template, request, redirect, url_for, jsonify
from pytube import Search, YouTube, innertube, Playlist
from pytube.innertube import _default_clients
from pytube.exceptions import AgeRestrictedError
import tkinter as tk

innertube._cache_dir = os.path.join(os.path.dirname(__file__), 'cache')
innertube._token_file = os.path.join(innertube._cache_dir, 'tokens.json')
innertube._default_clients["ANDROID"]["context"]["client"]["clientVersion"] = "19.08.35"
innertube._default_clients["IOS"]["context"]["client"]["clientVersion"] = "19.08.35"
innertube._default_clients["ANDROID_EMBED"]["context"]["client"]["clientVersion"] = "19.08.35"
innertube._default_clients["IOS_EMBED"]["context"]["client"]["clientVersion"] = "19.08.35"
innertube._default_clients["IOS_MUSIC"]["context"]["client"]["clientVersion"] = "6.41"
innertube._default_clients["ANDROID_MUSIC"] = _default_clients["ANDROID_CREATOR"]
os.environ['DISPLAY'] = ':0'
app = Flask(__name__, template_folder=os.path.join(os.path.dirname(__file__)))
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)
app.config['VIDEO_QUEUE'] = []
app.config['ready_for_new_queue'] = True

def display_black_screen():
    global root
    root = tk.Tk()
    root.attributes('-fullscreen', True)
    root.configure(background='black')
    font = ('Helvetica', 24)
    main_frame = tk.Frame(root, bg='black')
    main_frame.pack(expand=True)
    ip_eth0 = get_ip_address('eth0')
    ip_wlan0 = get_ip_address('wlan0')
    ip_address = ip_eth0 if ip_eth0 is not None else ip_wlan0
    label_ip = tk.Label(text=f"http://{ip_address if ip_address else 'Not available'}{':5000' if ip_address else ''}", fg="purple", bg="black", font=font)
    label_ip.pack(anchor='nw')
    title_frame = tk.Frame(main_frame, bg='black')
    title_frame.pack(expand=True)
    label = tk.Label(title_frame, text="No video playing", fg="white", bg="black", font=font)
    label.pack(expand=True)
    loading_label = tk.Label(title_frame, text="", fg="white", bg="black", font=font)
    loading_label.pack(expand=True)
    def update_text():
        if app.config.get('next_video_title'):
            next_video_title = app.config['next_video_title']
            label.config(text=next_video_title)
            loading_label.config(text="Loading...")
        else:
            label.config(text="No video playing")
            loading_label.config(text="")
        ip_eth0 = get_ip_address('eth0')
        ip_wlan0 = get_ip_address('wlan0')
        ip_address = ip_eth0 if ip_eth0 is not None else ip_wlan0
        label_ip.config(text=f"http://{ip_address if ip_address else 'Not available'}{':5000' if ip_address else ''}")
        root.after(200, update_text)
    update_text()
    subprocess.run(['xset', 's', 'off'])
    subprocess.run(['xset', '-dpms'])    
    root.mainloop()
    
def extract_playlist_id(url):
    query = url.split('?')[1]
    params = query.split('&')
    for param in params:
        key, value = param.split('=')
        if key == 'list':
            return value
    return None

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

def play_video_from_queue():
    while app.config.get('is_playing', False):
        while app.config['VIDEO_QUEUE']:
            video_info = app.config['VIDEO_QUEUE'].pop(0)
            app.config['next_video_title'] = f"{video_info['title']}"
            video_url = f'https://www.youtube.com/watch?v={video_info["video_id"]}'
            videopath = "/tmp/ytvid.mp4"
            try:
                stream = YouTube(video_url).streams.get_highest_resolution()
                stream.download(output_path="/tmp", filename="ytvid.mp4")
            except AgeRestrictedError as e:
                app.config['next_video_title'] = f"THIS VIDEO IS AGE RESTRICTED {video_info['title']}"
                stream = YouTube(video_url, use_oauth=True).streams.get_highest_resolution()
                stream.download(output_path="/tmp", filename="ytvid.mp4")
            process = subprocess.Popen(["vlc", "-fq", "--play-and-exit", "--extraintf", "--no-mouse-events", "--video-on-top", "--intf", "dummy", "--no-video-title-show", "--mouse-hide-timeout", "0", videopath])
            while True:
                if process.poll() is not None:
                    break
                time.sleep(1)
            app.config['next_video_title'] = None
            subprocess.Popen(["rm", "-rf", videopath])
        app.config['ready_for_new_queue'] = True
        break

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

@app.route('/add_to_queue', methods=['POST'])
def add_to_queue():
    video_url = request.form['video_url']
    if '&list=' in video_url and 'watch?v=' in video_url:
        # This is a playlist URL that starts with a video
        playlist_id = extract_playlist_id(video_url)
        playlist_url = f'https://www.youtube.com/playlist?list={playlist_id}'
        playlist = Playlist(playlist_url)
        for video in playlist.videos:
            video_info = {
                'title': video.title,
                'video_id': video.video_id,
            }
            app.config['VIDEO_QUEUE'].append(video_info)
    elif '?list=' in video_url:
        # This is a regular playlist URL
        playlist_id = extract_playlist_id(video_url)
        playlist_url = f'https://www.youtube.com/playlist?list={playlist_id}'
        playlist = Playlist(playlist_url)
        for video in playlist.videos:
            video_info = {
                'title': video.title,
                'video_id': video.video_id,
            }
            app.config['VIDEO_QUEUE'].append(video_info)
    else:
        # This is a single video URL
        yt = YouTube(video_url)
        video_info = {
            'title': yt.title,
            'video_id': yt.video_id,
        }
        app.config['VIDEO_QUEUE'].append(video_info)
    return redirect(url_for('index'))

@app.route('/close', methods=['POST'])
def close():
    if os.path.exists("/tmp/ytvid.mp4"):
        subprocess.Popen(["rm", "-rf", "/tmp/ytvid.mp4"])
    subprocess.run(["pkill", "vlc"])
    os.system('kill %d' % os.getpid())
    
@app.route('/clear', methods=['POST'])
def clear():
    app.config['VIDEO_QUEUE'] = []
    return redirect(url_for('index'))

@app.route('/get_queue')
def get_queue():
    queue_data = app.config['VIDEO_QUEUE']
    return jsonify(queue_data)

@app.route('/move_to_bottom', methods=['POST'])
def move_to_bottom():
    index = int(request.form['index'])
    if index >= 0 and index < len(app.config['VIDEO_QUEUE']) - 1:
        video = app.config['VIDEO_QUEUE'].pop(index)
        app.config['VIDEO_QUEUE'].append(video)
    return redirect(url_for('index'))

@app.route('/move_down', methods=['POST'])
def move_down():
    index = int(request.form['index'])
    if index >= 0 and index < len(app.config['VIDEO_QUEUE']) - 1:
        app.config['VIDEO_QUEUE'][index], app.config['VIDEO_QUEUE'][index + 1] = app.config['VIDEO_QUEUE'][index + 1], app.config['VIDEO_QUEUE'][index]
    return redirect(url_for('index'))

@app.route('/move_to_top', methods=['POST'])
def move_to_top():
    index = int(request.form['index'])
    if index > 0 and index < len(app.config['VIDEO_QUEUE']):
        video = app.config['VIDEO_QUEUE'].pop(index)
        app.config['VIDEO_QUEUE'].insert(0, video)
    return redirect(url_for('index'))

@app.route('/move_up', methods=['POST'])
def move_up():
    index = int(request.form['index'])
    if index > 0 and index < len(app.config['VIDEO_QUEUE']):
        app.config['VIDEO_QUEUE'][index], app.config['VIDEO_QUEUE'][index - 1] = app.config['VIDEO_QUEUE'][index - 1], app.config['VIDEO_QUEUE'][index]
    return redirect(url_for('index'))

@app.route('/play', methods=['POST', 'GET'])
def play():
    if not app.config.get('is_playing', False):
        app.config['is_playing'] = True
        threading.Thread(target=play_video_from_queue).start()
    elif app.config['ready_for_new_queue']:
        if not app.config['VIDEO_QUEUE']:
            app.config['is_playing'] = False
        else:
            app.config['ready_for_new_queue'] = False
            threading.Thread(target=play_video_from_queue).start()
    return redirect(url_for('index'))

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

@app.route('/remove', methods=['POST'])
def remove():
    index = int(request.form['index'])
    if 0 <= index < len(app.config['VIDEO_QUEUE']):
        removed_video = app.config['VIDEO_QUEUE'].pop(index)
        if app.config.get('next_video_title') == removed_video['title']:
            app.config['next_video_title'] = None
    return redirect(url_for('index'))

@app.route('/shuffle_queue', methods=['GET'])
def shuffle_queue():
    random.shuffle(app.config['VIDEO_QUEUE'])
    return redirect(url_for('index'))

@app.route('/skip', methods=['POST'])
def skip():
    try:
        if app.config.get('is_playing', False):
            subprocess.run(["pkill", "vlc"])
        return redirect(url_for('index'))
    except Exception as e:
        return f"An error occurred: {e}"

if __name__ == '__main__':
    gui_thread = threading.Thread(target=display_black_screen)
    gui_thread.start()
    app.run(host='0.0.0.0', port=5000, use_reloader=False)