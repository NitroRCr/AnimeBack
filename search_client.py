import socket
import json

class HashSearchClient:
    def __init__(self):
        self.IP_PORT = ('127.0.0.1', 8899)
        self.req_num = 0

    def req(self, req_str):
        socket = socket.socket()     # 创建套接字
        socket.settimeout(2)
        socket.connect(self.IP_PORT)
        socket.send(req_str.encode())
        socket.send("eof\n".encode())
        res = socket.recv(4096).decode()
        socket.close()
        return res

    def search_hash(self, hash):
        res = self.req(json.dumps({
            "jsonrpc": "2.0",
            "id": self.req_num,
            "method": "search",
            "params": {
                "searchMethod": "hash",
                "hash": hash
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
