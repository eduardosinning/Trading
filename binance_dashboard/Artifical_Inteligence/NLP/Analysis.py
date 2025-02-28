import pymongo
import openai
from binance_dashboard.Artifical_Inteligence.DATA.update_time import parse_relative_time

def local_llm_chat(Titulo,noticia):
    """Vista para manejar las solicitudes al modelo LLM local usando la API de OpenAI"""
  
    try:

        # Configurar el cliente de OpenAI para usar el servidor local
        client = openai.OpenAI(
                base_url="http://127.0.0.1:1234/v1",  # URL del servidor local
                api_key="not-needed" # No se necesita API key para servidor local
            )

        # Determinar el rol del sistema y construir el prompt
        system_role = "Eres un experto en trading y análisis técnico. Quiero que me me entregues un resumen de 3 lineas de la noticia."
        prompt = f"""
                Titulo: {Titulo}
                Noticia: {noticia}
                """

        # Realizar la solicitud al modelo
        response = client.chat.completions.create(
                model="deepseek-r1-distill-qwen-7b",  # El nombre del modelo local
                messages=[
                    {"role": "system", "content": system_role},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=4096
            )
        print("respuesta: ", response.choices[0].message.content)
    except Exception as e:
        print("Error: ", e)

def buscar_todas_las_noticias():
    # Conexión al cliente de MongoDB (por defecto en el puerto 27017)
    client = pymongo.MongoClient("mongodb://localhost:27017/")
    
    # Seleccionar la base de datos
    db = client["Crypto_news"]
    
    # Seleccionar la colección
    noticias_collection = db["noticias"]
    
    # Realizar la consulta (en este caso, obtener todos los documentos)
    resultados = noticias_collection.find()
    
    # Convertir el cursor en una lista de documentos
    return list(resultados)

if __name__ == "__main__":
    noticias = buscar_todas_las_noticias()
    for noticia in noticias:
        # Calcular el tiempo parseado
        tiempo_parseado = parse_relative_time(noticia["fecha"], noticia["fecha_guardado"])
        
        # Actualizar la noticia con el nuevo campo time
        client = pymongo.MongoClient("mongodb://localhost:27017/")
        db = client["Crypto_news"]
        noticias_collection = db["noticias"]
        noticias_collection.update_one(
            {"_id": noticia["_id"]},
            {"$set": {"time": tiempo_parseado}}
        )
        


