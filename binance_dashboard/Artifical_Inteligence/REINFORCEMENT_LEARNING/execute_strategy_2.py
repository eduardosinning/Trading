from bot import TradingBot
import time
import logging
import signal
import sys
import keyboard
import json
from datetime import datetime
import os
from typing import Dict, Any
from concurrent.futures import ThreadPoolExecutor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

running = True

def signal_handler(signum, frame) -> None:
    """Manejador de señales para terminar el programa correctamente"""
    global running
    logging.info("Señal de terminación recibida. Deteniendo el bot...")
    running = False

def keyboard_handler() -> None:
    """Manejador de tecla de aborto"""
    global running
    if keyboard.is_pressed('q'):
        logging.info("Tecla de aborto presionada. Deteniendo el bot...")
        running = False

def save_trading_history(history_data: Dict[str, Any], history_file: str) -> None:
    """
    Guarda el historial de trading en un archivo JSON
    
    Args:
        history_data: Diccionario con datos de la operación
        history_file: Ruta del archivo donde guardar
    """
    try:
        history = []
        if os.path.exists(history_file):
            with open(history_file, 'r') as f:
                history = json.load(f)
                
        history.append(history_data)
        
        with open(history_file, 'w') as f:
            json.dump(history, f, indent=4)
            
        logging.info(f"Historial guardado en {history_file}")
    except Exception as e:
        logging.error(f"Error guardando historial: {e}")



def calculate_initial_balance(bot: TradingBot) -> float:
    """
    Calcula el balance inicial total en USDT
    
    Args:
        bot: Instancia del bot de trading
        
    Returns:
        float: Balance total en USDT
    """
    initial_total_balance = 0
    
    for asset in bot.available_assets:
        if not running:
            return 0
            
        try:
            balance = bot.get_account_balance(asset)
            #print(f"Balance para {asset}: {balance}")
            if balance <= 0:
                continue
                
            if asset != 'USDT':
                ticker = bot.client.get_symbol_ticker(symbol=f"{asset}USDT")
                if ticker and 'price' in ticker:
                    price = float(ticker['price'])
                    asset_balance = balance * price
                    print(f"Balance para {asset}: {asset_balance} USDT (Balance: {balance} {asset}, Precio: {price})")
                    initial_total_balance += asset_balance
                else:
                    logging.error(f"No se pudo obtener precio para {asset}")
                    continue
            else:
                #print(f"Balance USDT: {balance}")
                initial_total_balance += balance
                
        except Exception as e:
            logging.error(f"Error al calcular balance para {asset}: {str(e)}")
            continue
            
    return initial_total_balance

def main() -> None:
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        assets = ['ETH','USDT','BTC','XRP','BNB']
        bot = TradingBot(single_asset=False, simulation_mode=True, estrategia='strategy2', stop_loss_mode= True)
            
        target_profit = 0.20
        history_file = 'strategy_2_trading_history.json'

        # Inicializar archivo de historial vacío
        with open(history_file, 'w') as f:
            json.dump([], f)

        logging.info("Iniciando ejecución de estrategia...")
        logging.info("Presiona 'q' para abortar en cualquier momento")

        try:
            initial_total_balance = calculate_initial_balance(bot)            
            logging.info(f"Balance inicial total: {initial_total_balance:.8f} USDT")
            
            while running:
                keyboard_handler()
                try:
                    total_profit_usd, avg_profit_pct, total_balance, total_balance_usd = bot.execute_trade_strategy()
                    
                    usdt_balance = bot.get_account_balance('USDT')
                    current_balance = total_balance_usd + usdt_balance
                    current_profit = (current_balance - initial_total_balance) / initial_total_balance
                    
                    logging.info(f"Retorno estrategia: {total_profit_usd:.8f} USD, {avg_profit_pct:.2f}%, "
                               f"Balance: {current_balance:.8f}")
                    logging.info(f"Profit actual: {current_profit:.2%}")

                    trade_data = {
                        'timestamp': str(datetime.now()),
                        'initial_balance': initial_total_balance,
                        'current_balance': current_balance,
                        'profit_usd': total_profit_usd,
                        'profit_percentage': avg_profit_pct,
                        'simulation_mode': bot.simulation_mode,
                        'trading_pairs': bot.trading_pairs
                    }
                    
                    save_trading_history(trade_data, history_file)

                    if current_profit >= target_profit:
                        logging.info(f"¡Objetivo de ganancia alcanzado! Profit: {current_profit:.2%}")
                        break

                    time.sleep(10)

                except Exception as e:
                    logging.error(f"Error en ciclo de trading: {str(e)}")
                    time.sleep(10)

        except Exception as e:
            logging.error(f"Error en evaluación de estrategia: {str(e)}")

    except Exception as e:
        logging.error(f"Error crítico: {str(e)}")
    finally:
        logging.info("Finalizando bot...")
        sys.exit(0)

if __name__ == "__main__":
    main()