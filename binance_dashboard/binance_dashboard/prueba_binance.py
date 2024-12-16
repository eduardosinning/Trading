from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceRequestException


api_key = 'akOyfC3602O1NAnRHqMCItE6Z7R5phRTr2e33pKKigzHUP3TNtq1u6Nixh8Z6I9J'
api_secret = 'UyywNH3aUIpCsIUw4u2Zedy5p7hQ0EHKtSAJzPAEh1XR3x0iYzMVhpFpkCzMJb4N'
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

