import os
import sqlite3
class FrameBox:
    def __init__(self):
        self.DB_PATH = os.path.join("sql", "frames.db")
        self.INIT_SQL_PATH = os.path.join("sql", "init.sql")
        self.hash_buffer = []

    def connect(self):
        self.sql_conn = sqlite3.connect(self.DB_PATH)
        self.sql_cursor = self.sql_conn.cursor()

    def close(self):
        self.sql_cursor.close()
        self.sql_conn.close()

    def add_hash(self, hash_str, brief):
        name = brief['name']
        cid = brief['cid']
        time = brief['time']
        self.sql_cursor.execute(
            'INSERT INTO hash (hash, cid, time) VALUES (%d, %s, %d)'
            %(int(hash_str, 16), cid, time)
            )
        self.sql_cursor.execute(
            'INSERT INTO cid (cid, name) VALUES (%s, %s)'%(cid, name)
            )

        self.hash_buffer.append(hash_str)

    

    def search_hash(self, half_results):
        self.connect()
        keys = self.sql_cursor.execute('SELECT TOP(0) * FROM hash').fetchall()[0]
        results = []
        for i in half_results:
            self.sql_cursor.execute('select * from hash where hash=?', (i.hash,))
            for j in self.sql_cursor.fetchall():
                result = {}
                for k in range(len(keys)):
                    result[keys[k]] = j[k]
                for k2 in i:
                    result[k2] = i[k2]
                results.append(result)
        self.close()
        return results
    
    def search_cid(self, half_results):
        self.connect()
        keys = self.sql_cursor.execute('SELECT TOP(0) * FROM hash').fetchall()[0]
        for i in half_results:
            self.sql_cursor.execute('select * from cid where cid=?', (i.cid,))
            for j in range(len(keys)):
                i[keys[j]] = self.sql_cursor.fetchall()[0][j]
            self.close()
        return half_results

    def init_db(self):
        sql_cmd_f = open(self.INIT_SQL_PATH)
        self.connect()
        self.sql_cursor.execute(sql_cmd_f.read())
        self.close()
        sql_cmd_f.close()