from django.shortcuts import render
from binance.client import Client
from binance.exceptions import BinanceAPIException
import pandas as pd
from django.http import JsonResponse
from datetime import datetime
import os
import certifi
from dotenv import load_dotenv


from django.views.decorators.csrf import csrf_exempt

load_dotenv()

class BinanceView:
    def __init__(self):
        
        self.api_key = os.getenv('BINANCE_API_KEY')
        self.api_secret = os.getenv('BINANCE_SECRET_KEY')
        self.client = Client(self.api_key, self.api_secret, {"verify": certifi.where()})
    
    def get_binance_data(self, symbol, columns=['Open','High','Low','Close','Volume'], interval='1m', limit=1000):
        """Obtener datos de Binance por minuto"""
        klines = self.client.get_klines(symbol=symbol, interval=interval, limit=limit)
        dates = [datetime.fromtimestamp(entry[0] / 1000).strftime('%Y-%m-%d %H:%M:%S') for entry in klines]
        
        # Extraer todos los datos OHLCV
        ohlcv_data = {
            'Open': [float(entry[1]) for entry in klines],
            'High': [float(entry[2]) for entry in klines], 
            'Low': [float(entry[3]) for entry in klines],
            'Close': [float(entry[4]) for entry in klines],
            'Volume': [float(entry[5]) for entry in klines]
        }
        
        data = pd.DataFrame(ohlcv_data, index=dates)
        return data
    
    def get_binance_crypto_symbols(self):
        exchange_info = self.client.get_exchange_info()
        symbols_info = exchange_info['symbols']
        cryptos = set()
        for s in symbols_info:
            cryptos.add(s['baseAsset'])
        return cryptos
    
        
    def get_account_info(self):
        try:
            account = self.client.get_account()
            total_balance_usd = 0
            balances = []
            
            for balance in account['balances']:
                if float(balance['free']) > 0 or float(balance['locked']) > 0:
                    asset = balance['asset']
                    free = float(balance['free'])
                    locked = float(balance['locked'])
                    
                    # Calcular valor en USD
                    if asset != 'USDT':
                        try:
                            price = float(self.client.get_symbol_ticker(symbol=f"{asset}USDT")['price'])
                        except:
                            price = 0
                    else:
                        price = 1
                        
                    total_asset = free + locked
                    asset_value_usd = total_asset * price
                    total_balance_usd += asset_value_usd
                    
                    balances.append({
                        'asset': asset,
                        'free': free,
                        'locked': locked,
                        'usd_value': asset_value_usd
                    })
            
            return {
                'balances': balances,
                'total_balance_usd': total_balance_usd
            }
        except BinanceAPIException as e:
            return {'error': str(e)}