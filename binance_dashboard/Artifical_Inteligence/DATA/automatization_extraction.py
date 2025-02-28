from binance_dashboard.Artifical_Inteligence.DATA.binance_script import save_mongo_ohlcv
from binance_dashboard.Artifical_Inteligence.DATA.coinmarketcap import obtener_noticias_cointelegraph
from binance_dashboard.Artifical_Inteligence.DATA.coinmarketcap import guardar_noticias_en_mongo
import time

def cycle_extraction():

    while True:
        try:
            #client = BinanceView()
            #cryptos = client.get_binance_crypto_symbols()
            cryptos = ["BTC", "ETH", "XRP", "BCH", "LTC", "ADA"]
            for crypto in cryptos:

                symbol = crypto
                current_symbol = "{}USDT".format(symbol)
                print("guardamos los datos de {}".format(current_symbol))
                save_mongo_ohlcv(current_symbol)
                print("guardamos las noticias de {}".format(symbol))
                noticias = obtener_noticias_cointelegraph(symbol)
                if noticias:

                    guardar_noticias_en_mongo(noticias, symbol, "cointelegraph")    

                    for noticia in noticias:
                        print(f"Título: {noticia['titulo']}")
                        #print(f"Enlace: {noticia['enlace']}")
                        #print(f"Fecha: {noticia['fecha_publicacion']}")
                        #print("-" * 80)
                else:
                    print("No se encontraron noticias")
                print("esperamos 3 horas")
                time.sleep(10800)  # 3 horas = 3 * 60 * 60 segundos
        except Exception as e:
            print(f"Error en la ejecución principal: {str(e)}")

cycle_extraction()