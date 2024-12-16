from binance.client import Client
from binance.websockets import BinanceSocketManager
import json

class BinanceDataStream:
    def __init__(self, api_key, api_secret):
        self.client = Client(api_key, api_secret)
        self.bm = BinanceSocketManager(self.client)
        self.conn_key = None

    def start_kline_socket(self, symbol, interval):
        self.conn_key = self.bm.start_kline_socket(symbol, self.process_message, interval=interval)
        self.bm.start()

    def process_message(self, msg):
        print(json.dumps(msg, indent=2))