from datetime import datetime
from bson import ObjectId
from pymongo import MongoClient

def imprimir_documento(doc):
    print("\n=== DETALLES DEL DOCUMENTO ===")
    print(f"\nID: {doc['_id']}")
    print(f"\nACTIVO: {doc['activo']}")
    print(f"\nTÍTULO: {doc['titulo']}")
    print(f"\nAUTOR: {doc['autor']}")
    print(f"\nFECHA: {doc['fecha']}")
    print(f"\nFUENTE: {doc['fuente']}")
    print(f"\nENLACE: {doc['enlace']}")
    print(f"\nFECHA DE GUARDADO: {doc['fecha_guardado']}")
    print("\nTEXTO COMPLETO:")
    print("-" * 80)
    print(doc['texto'])
    print("-" * 80)

# Conectar a MongoDB
client = MongoClient('mongodb://localhost:27017')
db = client['Crypto_news']
collection = db['noticias']

# Obtener y mostrar todos los documentos
for documento in collection.find():
    imprimir_documento(documento)
    print("\n" + "=" * 100 + "\n")  # Separador entre documentos

client.close() 