import subprocess
import os

def download(url, down_path, settings):
    if not os.path.exists(down_path):
        os.makedirs(down_path)
    subprocess.run("bilili %s -d %s -q %d -p %d -c %s --audio-quality %d --playlist-type no --danmaku no -y" %
                   (url, down_path, settings['quality'], settings['i'] + 1, settings['SESSDATA'], settings['audioQuality']), shell=True, check=True)
    ddir = os.path.join(down_path, os.listdir(down_path)[0])
    subdir = os.path.join(ddir, os.listdir(ddir)[0])
    video = os.path.join(subdir, os.listdir(subdir)[0])
    os.rename(video, os.path.join(down_path, 'video.mp4'))
    os.removedirs(subdir)
    f = open(os.path.join(down_path, 'done'), 'w')
    f.close()
