from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceRequestException


api_key = ''
api_secret = ''
client = Client(api_key, api_secret)

# Sincronizar el tiempo del cliente con el servidor de Binance
client.API_URL = 'https://api.binance.com/api'

try:
    #client.ping()
    #server_time = client.get_server_time()
    #print("Server time:", server_time)
    print(client.get_account())
except BinanceAPIException as e:
    print(f"Binance API Exception: {e}")
except BinanceRequestException as e:
    print(f"Binance Request Exception: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")

