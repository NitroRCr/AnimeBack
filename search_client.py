# -*- coding: utf-8 -*-
import socket
import json

class HashSearchClient(object):
    def __init__(self):
        self.IP_PORT = ('127.0.0.1', 8899)
        self.req_num = 0

    def req(self, req_str):
        s = socket.socket()     # 创建套接字
        s.settimeout(5)
        s.connect(self.IP_PORT)
        print("search client:", self.solve_len(req_str))
        s.send(req_str.encode())
        s.send("eof\n".encode())
        res = s.recv(4096).decode()
        print("search server:", self.solve_len(res))
        s.close()
        return res

    def search_hash(self, hash_str):
        res = self.req(json.dumps({
            "jsonrpc": "2.0",
            "id": self.req_num,
            "method": "search",
            "params": {
                "searchMethod": "hash",
                "hash": hash_str
            }
        }))
        res_obj = json.loads(res)
        if res_obj['id'] != self.req_num:
            pass
        if 'error' in res_obj or 'result' not in res_obj:
            pass
        self.req_num += 1
        return res_obj['result']['results']

    def add_hash(self, hashList):
        res = self.req(json.dumps({
            "jsonrpc": "2.0",
            "id": self.req_num,
            "method": "addHash",
            "params": {
                "hashArray": hashList
            }
        }))
        res_obj = json.loads(res)
        if res_obj['id'] != self.req_num:
            pass
        if 'error' in res_obj or 'result' not in res_obj:
            pass
        self.req_num += 1
        return res_obj['result']

    
    def solve_len(self, string):
        if len(string) > 1000:
            return string[0:1000] + "..."
        else:
            return string
