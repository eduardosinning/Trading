import re
from datetime import datetime, timedelta, timezone

def parse_relative_time(relative_time_str: str, reference_time: datetime) -> datetime:
    """
    Convierte una cadena de texto con tiempo relativo (e.g. '2 hours ago') o fecha absoluta (e.g. 'Jan 21, 2025')
    a un objeto datetime UTC, asumiendo que 'reference_time' se encuentra en UTC.
    
    :param relative_time_str: Cadena con formato '[N] [unit] ago' o 'MMM DD, YYYY',
                              por ejemplo: '2 hours ago', '1 day ago', 'Jan 21, 2025', etc.
    :param reference_time: Objeto datetime en UTC que indica el momento en que 
                           se leyó la noticia o se obtuvo la cadena.
    :return: Objeto datetime en UTC que corresponde al tiempo real de la noticia.
    """
    
    # Primero intentamos parsear como fecha absoluta
    try:
        return datetime.strptime(relative_time_str.strip(), '%b %d, %Y').replace(tzinfo=timezone.utc)
    except ValueError:
        pass
        
    # Si no es fecha absoluta, intentamos como tiempo relativo
    match = re.match(r'(\d+)\s+(\w+)\s+ago', relative_time_str.strip().lower())
    if not match:
        raise ValueError(f"Formato de tiempo no reconocido: '{relative_time_str}'")
    
    quantity = int(match.group(1))         # 2, 1, 15, etc.
    unit = match.group(2)                 # hours, day, minutes, etc.
    
    # Asignamos la unidad de tiempo correspondiente en forma de timedelta
    if 'second' in unit:
        delta = timedelta(seconds=quantity)
    elif 'minute' in unit:
        delta = timedelta(minutes=quantity)
    elif 'hour' in unit:
        delta = timedelta(hours=quantity)
    elif 'day' in unit:
        delta = timedelta(days=quantity)
    elif 'week' in unit:
        delta = timedelta(weeks=quantity)
    else:
        raise ValueError(f"Unidad de tiempo no soportada: '{unit}'")

    # Restamos el delta a la hora de referencia
    result_time = reference_time - delta
    
    return result_time


