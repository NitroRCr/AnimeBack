import plyvel
import time

class LDB:
    def __init__(self, name, *args, **kw):
        self.name = name
        self.db = None
        self.isopen = False
        self.args = args
        self.kw = kw

    def open(self, wait=None):
        if wait is None:
            wait = [0.1, 0.2, 0.5, 1, 3, 5, 10, 20, 30]
        if not self.isopen:
            try:
                if (not self.db) or self.db.closed:
                    self.db = plyvel.DB(self.name, *self.args, **self.kw)
            except plyvel.IOError as e:
                if len(wait) == 0:
                    raise e
                time.sleep(wait.pop(0))
                self.open(wait)
                return
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

    def destroy(self):
        plyvel.destroy_db(self.name)

    def repair(self):
        plyvel.repair_db(self.name)