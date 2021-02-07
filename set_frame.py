import sqlite3
import imagehash

def set_frame(image, brief, tags):
    phash = imagehash.phash(image)
    conn = sqlite3.connect('sql/frames.db')
    cursor = conn.cursor()
    