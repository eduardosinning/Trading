from binance_dashboard.binance_dashboard.common import BinanceView
from pymongo import MongoClient
from datetime import datetime


def save_mongo_ohlcv(symbol):
    client = BinanceView()
    data = client.get_binance_data(symbol)
    guardar_ohlcv_en_mongo(data, symbol, "Binance")

def guardar_ohlcv_en_mongo(prices, activo, fuente, mongo_uri="mongodb://localhost:27017", db_name="Crypto", collection_name="ohlcv"):
    """
    Guarda noticias individualmente en una colección de MongoDB si no existen previamente.
    :param noticias: Lista de diccionarios, cada uno representando una noticia
    :param activo: Nombre del activo/criptomoneda

    :param mongo_uri: URI de conexión a MongoDB (por defecto localhost)
    :param db_name: Nombre de la base de datos
    :param collection_name: Nombre de la colección donde se guardarán las noticias
    """
    try:
        client = MongoClient(mongo_uri)
        db = client[db_name]
        collection = db[collection_name]
        for i in prices.index:
            timestamp = datetime.strptime(i, '%Y-%m-%d %H:%M:%S')
            price=prices.loc[i]

            ochlv_existente = collection.find_one({
                    "timestamp": timestamp
                })

            if not ochlv_existente:
                    documento = {
                        "fuente": fuente,
                        "activo": activo,
                        "timestamp": timestamp,
                        "Open": price.get("Open"),
                        "High": price.get("High"),
                        "Low": price.get("Low"),
                        "Close": price.get("Close"),
                        "Volume": price.get("Volume"),
                    }
                    collection.insert_one(documento)
        

    except Exception as e:
        print(f"Ocurrió un error al guardar en MongoDB: {e}")
    finally:
        if 'client' in locals():
            client.close()

save_mongo_ohlcv("BTCUSDT")




