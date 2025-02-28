from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from pymongo import MongoClient
from datetime import datetime
from binance_dashboard.binance_dashboard.common import BinanceView
from binance_dashboard.Artifical_Inteligence.DATA.update_time import parse_relative_time

import time
import random
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def obtener_noticias_cointelegraph(activo):
    """
    Dado el nombre de un activo (por ejemplo, 'BTC' o 'ETH'),
    retorna una lista de noticias encontradas en CoinTelegraph usando Selenium.
    """
    driver = None
    try:
        # Configurar opciones de Chrome
        #chrome_options = Options()
        #chrome_options.add_argument('--headless')
        #chrome_options.add_argument('--no-sandbox')
        #chrome_options.add_argument('--disable-dev-shm-usage')
        #chrome_options.add_argument('--disable-gpu')
        #chrome_options.add_argument('--window-size=1920,1080')
        #chrome_options.add_argument('--disable-notifications')
        #chrome_options.add_argument('--disable-extensions')
        #chrome_options.add_argument('--disable-infobars')
        
        # User agent aleatorio
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Firefox/89.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/605.1.15'
        ]
        #chrome_options.add_argument(f'user-agent={random.choice(user_agents)}')

        # Inicializar el servicio de Chrome con webdriver-manager
        service = Service(ChromeDriverManager().install())
        
        logger.info("Iniciando Chrome WebDriver...")
        driver = webdriver.Chrome(service=service)
        
        # URL de búsqueda
        url = f"https://cointelegraph.com/search?query={activo}"
        
        logger.info(f"Accediendo a URL: {url}")
        driver.get(url)
        time.sleep(5)  # Aumentar tiempo de espera inicial

        # Intentar aceptar la política de privacidad si existe
        try:
            accept_button = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "privacy-policy__accept-btn"))
            )
            accept_button.click()
        except Exception as e:
            logger.info("No se encontró el botón de política de privacidad o ya fue aceptada")
        
        # Esperar a que carguen los artículos
        logger.info("Esperando que carguen los artículos...")
        wait = WebDriverWait(driver, 20)  # Aumentado a 20 segundos
        # Pausa para asegurar carga completa
        time.sleep(30)
        # Obtener el HTML
        logger.info("Procesando contenido de la página...")
        page_source = driver.page_source
        # Imprimir el HTML para debug
        logger.info("HTML extraído:")
        soup = BeautifulSoup(page_source, 'html.parser')
        resultados = []
        lista_articulos = soup.select('div.post-item.search-page__post-item')
        logger.info(f"Encontrados {len(lista_articulos)} artículos")

        for articulo in lista_articulos:
            try:
                # Extraer título - está en el h2.header > a > span
                titulo_tag = articulo.select_one('h2.header a span')
                # Extraer enlace - está en el h2.header > a[href]
                enlace_tag = articulo.select_one('h2.header a')
                # Extraer fecha - está en time.date
                fecha_tag = articulo.select_one('time.date')
                autor_tag = articulo.select_one('span.author a')
                if titulo_tag and enlace_tag and enlace_tag.get('href'):
                    titulo = titulo_tag.get_text(strip=True)
                    enlace = enlace_tag.get('href')
                    if isinstance(enlace, str) and not enlace.startswith('http'):
                        enlace = f"https://cointelegraph.com{enlace}"
                    fecha = fecha_tag.get_text(strip=True) if fecha_tag else None
                    autor = autor_tag.get_text(strip=True) if autor_tag else None
                    # Acceder al enlace de la noticia para extraer el texto
                    logger.info(f"Accediendo al artículo: {enlace}")
                    #print(enlace)
                    driver.get(enlace)
                    time.sleep(3)  # Esperar a que cargue el contenido
                    
                    # Obtener el contenido del artículo
                    article_soup = BeautifulSoup(driver.page_source, 'html.parser')
                    # El texto del artículo está en los párrafos dentro de la clase post-content
                    content_div = article_soup.select_one('div.post-content')
                    if content_div:
                        # Obtener todos los párrafos y limpiar el texto
                        parrafos = content_div.select('p')
                        texto_completo = ' '.join([p.get_text(strip=True) for p in parrafos if p.get_text(strip=True)])
                        
                        # Si no se encontró texto en los párrafos, intentar obtener todo el texto del div
                        if not texto_completo:
                            texto_completo = content_div.get_text(strip=True)
                    else:
                        # Intentar encontrar el contenido en otras clases comunes
                        content_alternatives = [
                            'div.post__content',
                            'div.article-content',
                            'div.entry-content'
                        ]
                        
                        for selector in content_alternatives:
                            alt_content = article_soup.select_one(selector)
                            if alt_content:
                                parrafos = alt_content.select('p')
                                texto_completo = ' '.join([p.get_text(strip=True) for p in parrafos if p.get_text(strip=True)])
                                break
                        else:
                            texto_completo = "No se pudo extraer el contenido"

                    resultados.append({
                        "titulo": titulo,
                        "enlace": enlace,
                        "fecha_publicacion": fecha,
                        "autor": autor,
                        "texto": texto_completo
                    })
                    #print(resultados)
                    #return resultados
                    logger.info(f"Artículo procesado: {titulo}")
            except Exception as e:
                logger.error(f"Error procesando artículo: {str(e)}")
                continue

        logger.info(f"Procesados exitosamente {len(resultados)} artículos")
        return resultados

    except Exception as e:
        logger.error(f"Error durante el scraping: {str(e)}")
        return []
        
    finally:
        if driver:
            try:
                driver.quit()
                logger.info("WebDriver cerrado correctamente")
            except Exception as e:
                logger.error(f"Error al cerrar WebDriver: {str(e)}")




def guardar_noticias_en_mongo(noticias, activo, fuente, mongo_uri="mongodb://localhost:27017", db_name="Crypto_news", collection_name="noticias"):
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
        
        if noticias:
            for noticia in noticias:
                print(noticia)
                # Verificar si la noticia ya existe usando el título y enlace como criterios
                noticia_existente = collection.find_one({
                    "titulo": noticia.get("titulo"),
                    "enlace": noticia.get("enlace")
                })

                
                if not noticia_existente:
                    tiempo_parseado = parse_relative_time(noticia.get("fecha_publicacion"),datetime.now())
                    documento = {
                        "activo": activo,
                        "titulo": noticia.get("titulo"),
                        "texto": noticia.get("texto", ""),
                        "fecha": noticia.get("fecha_publicacion"),
                        "autor": noticia.get("autor", ""),
                        "enlace": noticia.get("enlace"),
                        "fuente": fuente,
                        "time": tiempo_parseado,
                        "fecha_guardado": datetime.now()
                    }
                    collection.insert_one(documento)
                    #print(f"Se ha insertado la noticia '{documento['titulo']}' en la colección '{collection_name}'")
                else:
                    print(f"La noticia '{noticia.get('titulo')}' ya existe en la base de datos")
        else:
            print("No hay noticias para insertar.")
    except Exception as e:
        print(f"Ocurrió un error al guardar en MongoDB: {e}")
    finally:
        if 'client' in locals():
            client.close()

