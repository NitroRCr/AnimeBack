import plyvel
import time

class LDB:
    def __init__(self, name, *args, **kw):
        self.name = name
        self.db = None
        self.isopen = False
        self.args = args
        self.kw = kw
        self.tried = 0

    def open(self, wait=10):
        if not self.isopen:
            try:
                self.db = plyvel.DB(self.name, *self.args, **self.kw)
            except plyvel.IOError as e:
                if self.tried >= wait:
                    self.tried = 0
                    raise e
                self.tried += 1
                time.sleep(0.2)
                self.open()
            self.isopen = True

    def close(self):
        if self.isopen:
            self.db.close()
            self.isopen = False

    def put(self, key, value, with_action=True, *args, **kw):
        if with_action:
            self.open()
        ret = self.db.put(key, value, *args, **kw)
        if with_action:
            self.close()
        return ret

    def get(self, key, with_action=True, *args, **kw):
        if with_action:
            self.open()
        ret = self.db.get(key, *args, **kw)
        if with_action:
            self.close()
        return ret