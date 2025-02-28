from django.shortcuts import render
from binance.client import Client
from binance.exceptions import BinanceAPIException
import pandas as pd
from django.http import JsonResponse
from datetime import datetime
import pytz
import requests
import hmac
import hashlib
import os
import subprocess
import signal
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
import json
import logging
import openai
from dotenv import load_dotenv

from binance_dashboard import BinanceView

import numpy as np

load_dotenv()

def get_balances(request):
    try:
        binance = BinanceView()
        account_info = binance.get_account_info()
        # Convertir los balances a formato JSON serializable
        balances = []
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        total_balance_usd = 0.0
        
        for balance in account_info['balances']:
            asset = balance['asset']
            free_amount = float(balance['free'])
            
            # Obtener precio actual del par con USDT si existe
            current_price = 1.0  # Valor por defecto para USDT
            if asset != 'USDT':
                try:
                    symbol = f"{asset}USDT"
                    ticker = binance.client.get_symbol_ticker(symbol=symbol)
                    current_price = float(ticker['price'])
                except:
                    current_price = 0.0  # Si no existe el par con USDT
            
            # Calcular valor en USD del balance libre
            balance_usd = free_amount * current_price
            total_balance_usd += balance_usd
                    
            balances.append({
                'asset': asset,
                'free': free_amount,
                'locked': float(balance['locked']),
                'current_price': current_price
            })
            
        response_data = {
            'timestamp': timestamp,
            'total_balance_usd': total_balance_usd,
            'balances': balances,
        }

        # Leer historial existente
        history = []
        try:
            with open('bot/RL/real_trading_history.json', 'r') as f:
                history = json.load(f)
                if not isinstance(history, list):
                    history = [history]
        except (FileNotFoundError, json.JSONDecodeError):
            history = []

        # Agregar nuevo registro
        history.append(response_data)

        # Guardar historial actualizado con formato
        with open('bot/RL/real_trading_history.json', 'w') as f:
            json.dump(history, f, indent=4, sort_keys=True)
        
        return JsonResponse(response_data, safe=False)
        
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)

def get_balances_simulations(request, strategy_number):
    try:
        # Leer balances simulados desde el archivo
        with open(f'bot/RL/simulated_balances_strategy{strategy_number}.json', 'r') as f:
            simulated_balances = json.load(f)

        # Obtener precios actuales y calcular el balance total en USD
        binance = BinanceView()
        balances = []
        total_balance_usd = 0.0
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for asset, amount in simulated_balances.items():
            current_price = 1.0  # Valor por defecto para USDT
            if asset != 'USDT':
                try:
                    symbol = f"{asset}USDT"
                    ticker = binance.client.get_symbol_ticker(symbol=symbol)
                    current_price = float(ticker['price'])
                except:
                    current_price = 0.0  # Si no existe el par con USDT

            usd_value = amount * current_price
            total_balance_usd += usd_value

            balances.append({
                'asset': asset,
                'amount': amount,
                'current_price': current_price,
                'usd_value': usd_value
            })

        response_data = {
            'timestamp': timestamp,
            'total_balance_usd': total_balance_usd,
            'balances': balances,
        }

        # Leer historial existente
        history = []
        try:
            with open(f'bot/RL/strategy{strategy_number}_trading_history.json', 'r') as f:
                history = json.load(f)
                if not isinstance(history, list):
                    history = [history]
        except (FileNotFoundError, json.JSONDecodeError):
            history = []

        # Agregar nuevo registro
        history.append(response_data)

        # Guardar historial actualizado con formato
        with open(f'bot/RL/strategy{strategy_number}_trading_history.json', 'w') as f:
            json.dump(history, f, indent=4, sort_keys=True)

        return JsonResponse(response_data, safe=False)

    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)

# Variable global para los símbolos de los gráficos
symbols_graphs = ['BTCUSDT', 'ETHUSDT']

def dashboard(request):
    try:
        # Obtener balances como JSON
        balance_response = get_balances(request)
        balance_data = json.loads(balance_response.content)
        print(balance_data)
        # Preparar contexto para el template
        context = {
            'balances': balance_data['balances'],
            'total_balance_usd': balance_data['total_balance_usd'],
            'auto_refresh': True,
            'refresh_interval': 60000,
            'symbols_graphs': symbols_graphs  # Agregar la variable global al contexto
        }
        
        return render(request, 'trading/dashboard.html', context)
        
    except Exception as e:
        context = {
            'error': str(e),
            'auto_refresh': True,
            'refresh_interval': 60000,
            'symbols_graphs': symbols_graphs  # Agregar también en caso de error
        }
        return render(request, 'trading/dashboard.html', context)

def get_klines(request, symbol, interval, limit):

    try:
        binance = BinanceView()
        if symbol == 'USDT' or symbol == '/USDT':
            empty_data = {
                'timestamps': [],
                'timestamps_local': [],
                'open': [],
                'high': [],
                'low': [],
                'close': [],
                'volume': [],
                'number_of_trades': [],
                'taker_buy_base_asset_volume': [],
                'taker_buy_quote_asset_volume': []
            }
            return JsonResponse(empty_data)
            
        trading_symbol = symbol if symbol.endswith('USDT') else f'{symbol}USDT'
            
        klines = binance.client.get_klines(
            symbol=trading_symbol,
            interval=interval,
            limit=limit
        )
        
        data = {
            'timestamps': [],
            'timestamps_local': [],
            'open': [],
            'high': [],
            'low': [],
            'close': [],
            'volume': [],
            'number_of_trades': [],
            'taker_buy_base_asset_volume': [],
            'taker_buy_quote_asset_volume': []
        }
        
        for kline in klines:
            # Convertir timestamp a formato datetime UTC
            timestamp_utc = datetime.fromtimestamp(kline[0]/1000, tz=pytz.UTC)
            
            # Convertir a hora local
            local_tz = pytz.timezone('America/Santiago')
            timestamp_local = timestamp_utc.astimezone(local_tz)
            
            data['timestamps'].append(timestamp_utc.strftime('%Y-%m-%d %H:%M:%S'))
            data['timestamps_local'].append(timestamp_local.strftime('%Y-%m-%d %H:%M:%S'))
            data['open'].append(float(kline[1]))
            data['high'].append(float(kline[2]))
            data['low'].append(float(kline[3]))
            data['close'].append(float(kline[4]))
            data['volume'].append(float(kline[5]))
            data['number_of_trades'].append(float(kline[8]))
            data['taker_buy_base_asset_volume'].append(float(kline[9]))
            data['taker_buy_quote_asset_volume'].append(float(kline[10]))
            

        return JsonResponse(data)
    except BinanceAPIException as e:
        return JsonResponse({'error': str(e)}, status=400)

def get_trades(request, symbol, is_simulation):
    print(f"Tipo de transacción: {is_simulation}")
    
    if is_simulation == 'real':
        print("Real")
        binance = BinanceView()
        
        url = f'https://api.binance.com/api/v3/myTrades'
        
        params = {
            'symbol': symbol,
            'timestamp': int(datetime.now().timestamp() * 1000)
        }
        
        query_string = '&'.join([f"{key}={value}" for key, value in params.items()])
        signature = hmac.new(binance.api_secret.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
        params['signature'] = signature
        
        headers = {
            'X-MBX-APIKEY': binance.api_key
        }
        
        response = requests.get(url, headers=headers, params=params)
        trades = response.json()
        #print(trades)
        
        return JsonResponse(trades, safe=False)
        
    else:
        print(f"Simulación: {is_simulation}")
        try:
            # Determinar el nombre del archivo según la estrategia
            filename = ''
            if is_simulation == 'estrategia_1':
                filename = 'simulated_orders_strategy1.json'
            elif is_simulation == 'estrategia_2':
                filename = 'simulated_orders_strategy2.json'
            elif is_simulation == 'estrategia_3':
                filename = 'simulated_orders_strategy3.json'
                
            base_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'bot', 'RL')
            json_path = os.path.join(base_path, filename)
            
            with open(json_path, 'r') as f:
                all_trades = json.load(f)
            
            # Filtrar trades por símbolo
            trades = [trade for trade in all_trades if trade['symbol'] == symbol]
            #print(trades)
            
            return JsonResponse(trades, safe=False)
            
        except Exception as e:
            return JsonResponse({'error': f'Error reading simulated trades: {str(e)}'}, status=500)

def get_bot_code(request, file_name):
    """Vista para obtener el contenido del archivo del bot"""
    base_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'bot')
    file_path = os.path.join(base_path, file_name)
    
    try:
        with open(file_path, 'r') as file:
            content = file.read()
        return HttpResponse(content, content_type='text/plain')
    except Exception as e:
        return HttpResponse(str(e), status=500)

@csrf_exempt
def save_bot_code(request):
    """Vista para guardar cambios en el código del bot"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            file_name = data['file_name']
            content = data['content']
            
            base_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'bot')
            file_path = os.path.join(base_path, file_name)
            print(file_path)
            with open(file_path, 'w') as file:
                file.write(content)
                
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

# Variable global para almacenar el proceso del bot
bot_process = None

@csrf_exempt
def run_bot(request):
    """Vista para ejecutar el archivo actual"""
    global bot_process
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            current_file = data.get('current_file')
            
            if not current_file:
                return JsonResponse({
                    'success': False,
                    'error': 'No hay archivo seleccionado',
                    'is_running': False
                })
            
            base_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'bot')
            script_path = os.path.join(base_path, current_file)
            print(script_path)
            log_path = os.path.join(base_path, 'bot_output.log')
            
            # Verificar que el archivo existe y está dentro del directorio bot
            if not os.path.exists(script_path) or not script_path.startswith(base_path):
                return JsonResponse({
                    'success': False,
                    'error': 'Archivo no válido',
                    'is_running': False
                })
            
            # Si hay un proceso en ejecución, detenerlo
            if bot_process:
                bot_process.terminate()
                bot_process = None
            
            # Ejecutar el script y redirigir la salida a un archivo de log
            with open(log_path, 'w') as log_file:
                try:
                    bot_process = subprocess.Popen(
                        ['python', script_path],
                        stdout=log_file,
                        stderr=subprocess.STDOUT,
                        cwd=os.path.dirname(script_path)
                    )
                    
                    # Actualizar estado a running
                    with open(os.path.join(base_path, 'bot_status.txt'), 'w') as f:
                        f.write('running')
                        
                    return JsonResponse({
                        'success': True,
                        'is_running': True
                    })
                    
                except Exception as e:
                    error_msg = f"Error al iniciar el proceso: {str(e)}"
                    log_file.write(error_msg)
                    with open(os.path.join(base_path, 'bot_status.txt'), 'w') as f:
                        f.write('stopped')
                    return JsonResponse({
                        'success': False,
                        'error': error_msg,
                        'is_running': False
                    })
            
        except Exception as e:
            logging.error(f"Error ejecutando script: {str(e)}")
            # Asegurar que el estado se actualice si hay error
            try:
                with open(os.path.join(base_path, 'bot_status.txt'), 'w') as f:
                    f.write('stopped')
            except:
                pass
            return JsonResponse({
                'success': False,
                'error': str(e),
                'is_running': False
            })
    
    return JsonResponse({
        'success': False,
        'error': 'Método no permitido',
        'is_running': False
    })


def bot_status(request):
    """Vista para verificar el estado del bot"""
    try:
        base_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'bot')
        with open(os.path.join(base_path, 'bot_status.txt'), 'r') as f:
            status = f.read().strip()
        is_running = status == 'running'
        
        # Verificar si el proceso sigue vivo
        if is_running and bot_process:
            if bot_process.poll() is not None:  # El proceso terminó
                is_running = False
                with open(os.path.join(base_path, 'bot_status.txt'), 'w') as f:
                    f.write('stopped')
                    
        return JsonResponse({'is_running': is_running})
    except:
        return JsonResponse({'is_running': False})

@csrf_exempt
def stop_bot(request):
    """Vista para detener el bot"""
    global bot_process
    
    if request.method == 'POST':
        try:
            base_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'bot')
            
            if bot_process is None:
                # Si el proceso ya es None, actualizamos el estado y retornamos éxito
                with open(os.path.join(base_path, 'bot_status.txt'), 'w') as f:
                    f.write('stopped')
                return JsonResponse({
                    'success': True, 
                    'message': 'Bot ya estaba detenido',
                    'is_running': False
                })
            
            try:
                # Intentar terminar el proceso normalmente
                bot_process.terminate()
                bot_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                # Si falla el timeout, matarlo forzadamente
                logging.warning("Timeout al detener el bot, forzando kill")
                bot_process.kill()
                try:
                    bot_process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    logging.error("No se pudo matar el proceso")
                    with open(os.path.join(base_path, 'bot_status.txt'), 'w') as f:
                        f.write('stopped')
                    raise Exception("No se pudo detener el proceso del bot")
            except Exception as e:
                logging.error(f"Error al terminar proceso: {str(e)}")
                with open(os.path.join(base_path, 'bot_status.txt'), 'w') as f:
                    f.write('stopped')
                raise
            
            # Limpiar el proceso global y actualizar estado
            bot_process = None
            with open(os.path.join(base_path, 'bot_status.txt'), 'w') as f:
                f.write('stopped')
            
            return JsonResponse({
                'success': True,
                'message': 'Bot detenido correctamente',
                'is_running': False
            })
            
        except Exception as e:
            error_msg = f"Error al detener el bot: {str(e)}"
            logging.error(error_msg)
            # Intentar actualizar el estado a stopped incluso si hay error
            try:
                with open(os.path.join(base_path, 'bot_status.txt'), 'w') as f:
                    f.write('stopped')
            except:
                pass
            return JsonResponse({
                'success': False,
                'message': error_msg,
                'is_running': False
            }, status=500)
    
    return JsonResponse({
        'success': False,
        'message': 'Método no permitido',
        'is_running': False
    }, status=405)

def get_bot_output(request):
    """Vista para obtener la salida del bot"""
    try:
        base_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'bot')
        log_path = os.path.join(base_path, 'bot_output.log')
        
        # Verificar si el archivo existe, si no crearlo
        if not os.path.exists(log_path):
            # Asegurarse que el directorio existe
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            # Crear el archivo vacío
            with open(log_path, 'w') as f:
                f.write('')
        
        with open(log_path, 'r') as log_file:
            output = log_file.read()
        
        return HttpResponse(output, content_type='text/plain')
    except Exception as e:
        return HttpResponse(str(e), status=500)

def get_asset_info(request, symbol):
    binance = BinanceView()
    
    try:
        # Obtener el precio actual
        price = float(binance.client.get_symbol_ticker(symbol=f"{symbol}USDT")['price'])
        
        # Obtener el balance del activo
        account_info = binance.get_account_info()
        asset_balance = next(
            (balance for balance in account_info['balances'] if balance['asset'] == symbol),
            {'free': 0, 'locked': 0, 'usd_value': 0}
        )
        
        return JsonResponse({
            'price': price,
            'balance': float(asset_balance['free']) + float(asset_balance['locked']),
            'usd_value': asset_balance['usd_value']
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

def get_file_tree(request):
    """Vista para obtener la estructura de archivos del bot"""
    # Modificar la ruta base para apuntar a la carpeta bot
    base_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'bot')
    
    def build_tree(path, is_selected=False):
        tree = {}
        try:
            for item in os.listdir(path):
                # Ignorar archivos __pycache__ y .pyc
                if item == '__pycache__' or item.endswith('.pyc'):
                    continue
                    
                item_path = os.path.join(path, item)
                if os.path.isfile(item_path):
                    # Guardar la ruta relativa para cada archivo
                    rel_path = os.path.relpath(item_path, base_path)
                    tree[item] = {'path': rel_path, 'type': 'file'}
                elif os.path.isdir(item_path):
                    subtree = build_tree(item_path, is_selected)
                    tree[item] = {'type': 'directory', 'content': subtree if is_selected else {}}
            return tree
        except Exception as e:
            logging.error(f"Error al construir árbol de archivos: {str(e)}")
            return {}

    try:
        # Considerar la carpeta base como un directorio
        file_tree = {'bot': {'type': 'directory', 'content': build_tree(base_path, is_selected=True)}}
        logging.info(f"Árbol de archivos generado: {json.dumps(file_tree, indent=2)}")
        return JsonResponse(file_tree)
    except Exception as e:
        logging.error(f"Error al generar árbol de archivos: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def create_file_or_folder(request):
    """Vista para crear nuevos archivos o carpetas"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            name = data['name']
            item_type = data['type']
            #current_path = data.get('path', '')
            
            # Asegurar que estamos trabajando dentro de la carpeta bot
            base_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'bot')
            full_path = os.path.join(base_path, name)
            print(full_path)
            
            # Verificar que la ruta está dentro de la carpeta bot
            if not os.path.commonpath([base_path, full_path]).startswith(base_path):
                return JsonResponse({
                    'success': False, 
                    'error': 'Invalid path: must be within bot directory'
                })
            
            if item_type == 'file':
                with open(full_path, 'w') as f:
                    f.write('')
                logging.info(f"Archivo creado: {full_path}")
            else:
                os.makedirs(full_path, exist_ok=True)
                logging.info(f"Carpeta creada: {full_path}")
                
            return JsonResponse({'success': True})
        except Exception as e:
            logging.error(f"Error al crear archivo/carpeta: {str(e)}")
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

def get_file_content(request):
    """Vista para obtener el contenido de un archivo"""
    try:
        file_path = request.GET.get('path')
        base_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'bot')
        full_path = os.path.join(base_path, file_path)
        
        # Verificar que la ruta está dentro de la carpeta bot
        if not os.path.commonpath([base_path, full_path]).startswith(base_path):
            return HttpResponse('Invalid path', status=403)
        
        if not os.path.exists(full_path):
            return HttpResponse('File not found', status=404)
            
        with open(full_path, 'r') as f:
            content = f.read()
            
        return HttpResponse(content)
    except Exception as e:
        logging.error(f"Error al leer archivo: {str(e)}")
        return HttpResponse(str(e), status=500)

@csrf_exempt
def move_file(request):
    """Vista para mover archivos entre directorios"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            source_path = data['sourcePath']
            target_path = data['targetPath']
            
            # Obtener la ruta base del proyecto
            base_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'bot')
            
            # Construir rutas completas
            source_full_path = os.path.join(base_path, source_path)
            #print("source_full_path: ");    
            #print(source_full_path);
            target_full_path = base_path if target_path == 'bot' else os.path.join(base_path, target_path)
            #print("target_full_path: ");
            #print(target_full_path);
            
            # Verificar que la ruta origen está dentro del directorio bot
            if not os.path.commonpath([base_path, source_full_path]).startswith(base_path):
                return JsonResponse({
                    'success': False,
                    'error': 'Invalid source path: must be within bot directory'
                }, status=403)
            
            # Verificar que la ruta destino está dentro del directorio bot
            if not os.path.commonpath([base_path, target_full_path]).startswith(base_path):
                return JsonResponse({
                    'success': False,
                    'error': 'Invalid target path: must be within bot directory'
                }, status=403)
            
            # Obtener el nombre del archivo original con su extensión
            file_name = os.path.basename(source_path)
            
            # Si el destino es un directorio, usar la ruta completa del directorio
            if os.path.isdir(target_full_path):
                target_full_path = os.path.join(target_full_path, file_name)
            else:
                # Si el destino no es un directorio, asegurarse de mantener el nombre y extensión
                target_dir = os.path.dirname(target_full_path)
                os.makedirs(target_dir, exist_ok=True)  # Crear directorios si no existen
                target_full_path = os.path.join(target_dir, file_name)
            
            # Mover el archivo
            os.rename(source_full_path, target_full_path)
            
            logging.info(f"Archivo movido de {source_full_path} a {target_full_path}")
            return JsonResponse({
                'success': True,
                'newPath': os.path.relpath(target_full_path, base_path)
            })
            
        except Exception as e:
            logging.error(f"Error al mover archivo: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    return JsonResponse({
        'success': False,
        'error': 'Invalid request method'
    }, status=405)

@csrf_exempt
def delete_file_or_folder(request):
    """Vista para eliminar archivos o carpetas"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            path = data['path']
            
            # Obtener la ruta base del proyecto
            base_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'bot')
            full_path = os.path.join(base_path, path)
            
            # Verificar que la ruta está dentro del directorio bot
            if not os.path.commonpath([base_path, full_path]).startswith(base_path):
                return JsonResponse({
                    'success': False,
                    'error': 'Invalid path: must be within bot directory'
                }, status=403)
            
            if os.path.isfile(full_path):
                os.remove(full_path)
            elif os.path.isdir(full_path):
                import shutil
                shutil.rmtree(full_path)
                
            logging.info(f"Eliminado: {full_path}")
            return JsonResponse({'success': True})
            
        except Exception as e:
            logging.error(f"Error al eliminar: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    return JsonResponse({
        'success': False,
        'error': 'Invalid request method'
    }, status=405)

@csrf_exempt
def execute_terminal_command(request):
    """Vista para ejecutar comandos básicos del terminal: ls, clear, cd, pip, conda, python"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            command = data.get('command', '').strip()
            current_dir = data.get('current_directory', '')
            
            # Lista de comandos permitidos
            allowed_commands = ['ls', 'clear', 'cd', 'pip', 'conda', 'python']
            
            # Verificar comando base
            base_command = command.split()[0] if command else ''
            if base_command not in allowed_commands:
                return JsonResponse({
                    'success': False,
                    'output': f'Comando no permitido. Comandos permitidos: ls, clear, cd, pip, conda, python',
                    'error': True,
                    'current_directory': current_dir
                })
            
            # Establecer el directorio de trabajo
            working_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'bot')
            if current_dir:
                working_dir = os.path.join(working_dir, current_dir)
            
            # Manejar comando 'clear'
            if base_command == 'clear':
                # Limpiar el archivo de salida del bot
                base_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'bot')
                log_path = os.path.join(base_path, 'bot_output.log')
                with open(log_path, 'w') as f:
                    f.write('')
                    
                return JsonResponse({
                    'success': True,
                    'output': '',
                    'error': False,
                    'current_directory': current_dir,
                    'clear': True
                })
            
            # Manejar comandos pip, conda y python
            elif base_command in ['pip', 'conda', 'python']:
                try:
                    # Configurar el entorno para conda
                    if base_command == 'conda':
                        # Inicializar conda para el shell actual
                        conda_executable = os.path.join(os.environ.get('CONDA_EXE', ''), '..', '..', 'etc', 'profile.d', 'conda.sh')
                        if os.path.exists(conda_executable):
                            os.environ['CONDA_SHLVL'] = '1'
                            os.environ['PATH'] = f"{os.path.dirname(conda_executable)}:{os.environ['PATH']}"

                    # Ejecutar el comando usando subprocess
                    process = subprocess.Popen(
                        command.split(),
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        cwd=working_dir,
                        text=True,
                        shell=True,  # Usar shell para mejor compatibilidad con conda
                        env=os.environ
                    )
                    output, error = process.communicate()
                    
                    if process.returncode == 0:
                        return JsonResponse({
                            'success': True,
                            'output': output,
                            'error': False,
                            'current_directory': current_dir
                        })
                    else:
                        return JsonResponse({
                            'success': False,
                            'output': error,
                            'error': True,
                            'current_directory': current_dir
                        })
                except Exception as e:
                    return JsonResponse({
                        'success': False,
                        'output': str(e),
                        'error': True,
                        'current_directory': current_dir
                    })
            
            # Manejar comando 'cd'
            elif base_command == 'cd':
                try:
                    target_dir = command.split()[1] if len(command.split()) > 1 else ''
                    
                    # Obtener el directorio base del proyecto
                    base_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'bot')
                    
                    # Manejar diferentes casos de navegación
                    if target_dir == '..':
                        # Subir un nivel
                        if current_dir:
                            new_dir = os.path.dirname(current_dir)
                        else:
                            new_dir = ''
                    elif target_dir == '':
                        # Volver al directorio raíz
                        new_dir = ''
                    else:
                        # Navegar a un subdirectorio
                        if current_dir:
                            new_dir = os.path.join(current_dir, target_dir)
                        else:
                            new_dir = target_dir
                    
                    # Construir y verificar la ruta completa
                    full_path = os.path.join(base_dir, new_dir) if new_dir else base_dir
                    
                    if os.path.exists(full_path) and os.path.commonpath([base_dir, full_path]).startswith(base_dir):
                        return JsonResponse({
                            'success': True,
                            'output': '',
                            'error': False,
                            'current_directory': new_dir
                        })
                    else:
                        return JsonResponse({
                            'success': False,
                            'output': f'Directorio no encontrado: {target_dir}',
                            'error': True,
                            'current_directory': current_dir
                        })
                except Exception as e:
                    return JsonResponse({
                        'success': False,
                        'output': str(e),
                        'error': True,
                        'current_directory': current_dir
                    })
            
            # Manejar comando 'ls'
            elif base_command == 'ls':
                try:
                    files = os.listdir(working_dir)
                    files_info = []
                    for f in files:
                        if not f.startswith('__'):  # Ignorar archivos especiales de Python
                            path = os.path.join(working_dir, f)
                            files_info.append({
                                'name': f,
                                'type': 'directory' if os.path.isdir(path) else 'file'
                            })
                    
                    # Formatear la salida como un listado de terminal
                    output = '\n'.join([
                        f"{'📁 ' if f['type'] == 'directory' else '📄 '}{f['name']}"
                        for f in files_info
                    ])
                    
                    return JsonResponse({
                        'success': True,
                        'output': output,
                        'error': False,
                        'current_directory': current_dir
                    })
                except Exception as e:
                    return JsonResponse({
                        'success': False,
                        'output': str(e),
                        'error': True,
                        'current_directory': current_dir
                    })
            
        except Exception as e:
            logging.error(f"Error ejecutando comando: {str(e)}")
            return JsonResponse({
                'success': False,
                'output': str(e),
                'error': True,
                'current_directory': current_dir
            })
    
    return JsonResponse({
        'success': False,
        'output': 'Método no permitido',
        'error': True,
        'current_directory': ''
    })

@csrf_exempt
def chat_gpt(request):
    """Vista para manejar las solicitudes a ChatGPT"""
    if request.method == 'POST':
        try:
            print("Entrando a ChatGPT")
            data = json.loads(request.body)
            print("data: ", data)
            type = data.get('type', '')
            message = data.get('message', '')
            terminal_output = data.get('terminal_output', '')
            editor_code = data.get('editor_code', '')
            chart_data = data.get('chart_data', '')
            # Configurar API key de OpenAI
            client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

            # Definir el rol del sistema según el tipo de consulta
            if type == 'terminal':
                system_role = "Eres un experto en debugging y solución de problemas de programación. Tu objetivo es ayudar a identificar y resolver errores analizando la salida del terminal."
                prompt = f"""
                Usuario: {message}
                
                Output del terminal:
                ```
                {terminal_output}
                ```
                
                Por favor, analiza el output del terminal y proporciona una solución o explicación.
                """
            elif type == 'trading':
                system_role = "Eres un experto en trading y análisis técnico. Tienes amplio conocimiento en mercados financieros, criptomonedas, análisis técnico y estrategias de trading."
                prompt = f"""
                Datos del mercado:
                {chart_data}
                
                Pregunta del usuario:
                {message}
                
                Por favor analiza los datos del mercado proporcionados y responde la pregunta del usuario utilizando esta información junto con tu conocimiento experto.
                """
            elif type == 'coder':
                system_role = "Eres un experto en inteligencia artificial y Python. Tienes profundo conocimiento en machine learning, deep learning, y programación avanzada en Python."
                prompt = f"""
                Código a analizar:
                ```
                {editor_code}
                ```
                
                Pregunta del usuario:
                {message}
                
                Por favor analiza el código proporcionado y responde la pregunta del usuario utilizando esta información junto con tu conocimiento experto.
                """
            else:
                system_role = "Eres un asistente general útil y amigable."
                prompt = message
            
            
            print("editor_code: ", editor_code) 
            print(system_role)
            print("chart_data: ", chart_data)
            print("prompt: ", prompt)
            #response = "Hola"

            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_role},
                    {"role": "user", "content": prompt}
                ]
            )
            
            return JsonResponse({
                'success': True,
                'response': response.choices[0].message.content
            })
            
        except Exception as e:
            logging.error(f"Error en ChatGPT: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({
        'success': False,
        'error': 'Método no permitido'
    })

@csrf_exempt
def local_llm_chat(request):
    """Vista para manejar las solicitudes al modelo LLM local usando la API de OpenAI"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            message = data.get('message', '')
            editor_code = data.get('editor_code')
            terminal_output = data.get('terminal_output') 
            type = data.get('type', 'general')
            chart_data = data.get('chart_data')

            # Configurar el cliente de OpenAI para usar el servidor local
            client = openai.OpenAI(
                base_url="http://127.0.0.1:1233/v1",  # URL del servidor local
                api_key="not-needed" # No se necesita API key para servidor local
            )

            # Determinar el rol del sistema y construir el prompt
            if type == 'trading':
                system_role = "Eres un experto en trading y análisis técnico."
                prompt = f"""
                Mensaje del usuario: {message}
                
                Datos adicionales:
                - Código del editor: {editor_code if editor_code else 'No disponible'}
                - Salida del terminal: {terminal_output if terminal_output else 'No disponible'}
                - Datos del gráfico: {chart_data if chart_data else 'No disponible'}
                """
            elif type == 'coder':
                system_role = "Eres un experto en inteligencia artificial y Python."
                prompt = f"""
                Código a analizar:
                ```
                {editor_code}
                ```
                
                Pregunta del usuario:
                {message}
                """
            else:
                system_role = "Eres un asistente general útil y amigable."
                prompt = message
            
            print("system_role: ", system_role)
            print("prompt: ", prompt)

            # Realizar la solicitud al modelo
            response = client.chat.completions.create(
                model="finance-llama3-8b",  # El nombre del modelo local
                messages=[
                    {"role": "system", "content": system_role},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=4096
            )
            print("response: ", response)
            return JsonResponse({
                'success': True,
                'response': response.choices[0].message.content
            })

        except Exception as e:
            logging.error(f"Error en LLM local: {str(e)}")
            return JsonResponse({
                'success': False, 
                'error': str(e)
            }, status=500)

    return JsonResponse({
        'success': False,
        'error': 'Método no permitido'
    }, status=405)

def get_predictions(request, symbol, interval):
    try:
        print("symbol: ", symbol)
        print("interval: ", interval)
        with open('bot/forecasting/{}_{}_predictions.json'.format(symbol, interval), 'r') as f:
            predictions = json.load(f)
        return JsonResponse({
            'success': True,
            'predictions': predictions
        })
    except FileNotFoundError:
        return JsonResponse({
            'success': False,
            'predictions': []
        })
# views.py
def get_strategy_trading_history(request,strategy_number):
    # Obtener el número de estrategia del parámetro de la solicitud
    #strategy_number = request.GET.get('strategy', '1')  # Por defecto es 1 si no se especifica
    
    # Define la ruta al archivo JSON
    base_path = os.path.dirname(os.path.dirname(__file__))
    json_path = os.path.join(base_path, f'bot/RL/strategy{strategy_number}_trading_history.json')
    print("json_path: ", json_path)

    try:
        # Abre y lee el archivo JSON
        with open(json_path, 'r') as file:
            trading_history = json.load(file)
        
        # Devuelve el contenido del archivo como JSON
        return JsonResponse(trading_history, safe=False)
    
    except FileNotFoundError:
        logging.error(f"Archivo no encontrado: {json_path}")
        return JsonResponse({'error': 'Archivo no encontrado'}, status=404)
    
    except json.JSONDecodeError:
        logging.error(f"Error al decodificar JSON en: {json_path}")
        return JsonResponse({'error': 'Error al decodificar JSON'}, status=500)
    
    except Exception as e:
        logging.error(f"Error al leer el archivo: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

def get_trading_history(request):
    # Define la ruta al archivo JSON
    base_path = os.path.dirname(os.path.dirname(__file__))  # Ajusta según tu estructura de proyecto
    json_path = os.path.join(base_path, 'bot/RL/real_trading_history.json')  # Cambia 'path/to/your/' por la ruta correcta
    print("json_path: ", json_path)

    try:
        # Abre y lee el archivo JSON
        with open(json_path, 'r') as file:
            trading_history = json.load(file)
        
        # Devuelve el contenido del archivo como JSON
        return JsonResponse(trading_history, safe=False)
    
    except FileNotFoundError:
        logging.error(f"Archivo no encontrado: {json_path}")
        return JsonResponse({'error': 'Archivo no encontrado'}, status=404)
    
    except json.JSONDecodeError:
        logging.error(f"Error al decodificar JSON en: {json_path}")
        return JsonResponse({'error': 'Error al decodificar JSON'}, status=500)
    
    except Exception as e:
        logging.error(f"Error al leer el archivo: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def save_chart_config(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            # Aquí puedes guardar la configuración en la base de datos o en un archivo
            # Por ejemplo, guardar en un archivo JSON
            with open('bot/forecasting/chart_config.json', 'w') as f:
                json.dump(data, f)
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@csrf_exempt
def execute_strategy_1(request):
    """Vista para ejecutar el archivo execute_strategy_1.py"""
    if request.method == 'POST':
        try:
            # Ruta al script y directorio de trabajo
            script_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'bot','RL', 'execute_strategy_1.py')
            working_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'bot', 'RL')
            print("script_path: ", script_path)
            print("working_dir: ", working_dir)

            # Ejecutar el script en el directorio especificado
            process = subprocess.Popen(['python', script_path], cwd=working_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Guardar el PID del proceso
            with open('strategy1_pid.txt', 'w') as f:
                f.write(str(process.pid))
                
            return JsonResponse({'success': True, 'pid': process.pid})
        
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Método no permitido'}, status=405)

@csrf_exempt 
def stop_strategy_1(request):
    """Vista para detener la estrategia 1"""
    if request.method == 'POST':
        try:
            # Leer el PID del archivo
            with open('strategy1_pid.txt', 'r') as f:
                pid = int(f.read().strip())
            
            # Terminar el proceso
            os.kill(pid, signal.SIGTERM)
            
            # Eliminar el archivo PID
            os.remove('strategy1_pid.txt')
            
            return JsonResponse({'success': True})
            
        except FileNotFoundError:
            return JsonResponse({'success': False, 'error': 'Estrategia no está en ejecución'})
        except ProcessLookupError:
            return JsonResponse({'success': False, 'error': 'Proceso no encontrado'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
            
    return JsonResponse({'success': False, 'error': 'Método no permitido'}, status=405)

@csrf_exempt
def execute_strategy_2(request):
    """Vista para ejecutar el archivo execute_strategy_2.py"""
    if request.method == 'POST':
        try:
            # Ruta al script y directorio de trabajo
            script_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'bot','RL', 'execute_strategy_2.py')
            working_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'bot', 'RL')
            print("script_path: ", script_path)
            print("working_dir: ", working_dir)

            # Ejecutar el script en el directorio especificado
            process = subprocess.Popen(['python', script_path], cwd=working_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Guardar el PID del proceso
            with open('strategy2_pid.txt', 'w') as f:
                f.write(str(process.pid))
                
            return JsonResponse({'success': True, 'pid': process.pid})
        
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Método no permitido'}, status=405)

@csrf_exempt
def stop_strategy_2(request):
    """Vista para detener la estrategia 2"""
    if request.method == 'POST':
        try:
            # Leer el PID del archivo
            with open('strategy2_pid.txt', 'r') as f:
                pid = int(f.read().strip())
            
            # Terminar el proceso
            os.kill(pid, signal.SIGTERM)
            
            # Eliminar el archivo PID
            os.remove('strategy2_pid.txt')
            
            return JsonResponse({'success': True})
            
        except FileNotFoundError:
            return JsonResponse({'success': False, 'error': 'Estrategia no está en ejecución'})
        except ProcessLookupError:
            return JsonResponse({'success': False, 'error': 'Proceso no encontrado'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
            
    return JsonResponse({'success': False, 'error': 'Método no permitido'}, status=405)






def calculate_fourier_magnitudes(prices):
    if not prices:
        return []  # Devuelve una lista vacía si no hay precios

    # Encontrar la siguiente potencia de 2 mayor que la longitud de los precios
    next_power_of_2 = 2 ** int(np.ceil(np.log2(len(prices))))
    
    # Crear un nuevo array con ceros hasta alcanzar la siguiente potencia de 2
    padded_prices = np.pad(prices, (0, next_power_of_2 - len(prices)), 'constant')
    
    # Calcular la Transformada de Fourier
    fft_result = np.fft.fft(padded_prices)
    
    # Calcular las magnitudes y fases
    magnitudes = np.abs(fft_result)
    #print("magnitudes: ", magnitudes)
    phases = np.angle(fft_result)
    
    # Obtener las 3 frecuencias fundamentales (excluyendo la componente DC)
    sorted_indices = np.argsort(magnitudes[1:])[::-1]  # Ordenar índices por magnitud descendente
    fundamental_freqs = [sorted_indices[0], sorted_indices[1], sorted_indices[2]]  # Las 3 frecuencias seleccionadas
    
    # Generar las sinusoides en el tiempo para cada frecuencia fundamental
    t = np.arange(len(prices))
    sinusoids = []
    
    # Calcular las 3 sinusoides fundamentales
    fundamental_waves = []
    for freq_idx in fundamental_freqs:
        # Reconstruir la sinusoide usando magnitud, frecuencia y fase
        sinusoid = magnitudes[freq_idx] * np.cos(2 * np.pi * freq_idx * t / len(prices) + phases[freq_idx])
        fundamental_waves.append(sinusoid)
        sinusoids.append(sinusoid.tolist())
    
    # Calcular la suma de las 3 sinusoides
    sum_wave = np.sum(fundamental_waves, axis=0)
    sinusoids.append(sum_wave.tolist())
    
    # Calcular la resta de las 3 sinusoides
    diff_wave = fundamental_waves[0] - fundamental_waves[1] - fundamental_waves[2]
    sinusoids.append(diff_wave.tolist())
    
    # Calcular la multiplicación de las 3 sinusoides
    mult_wave = np.multiply.reduce(fundamental_waves)
    sinusoids.append(mult_wave.tolist())
        
    return sinusoids, magnitudes

@csrf_exempt
def fourier_view(request):
    if request.method == 'POST':
        # Obtener los datos del cuerpo JSON
        data = json.loads(request.body)
        #print("data: ", data)
        prices = data.get('prices', [])
        
        #print("prices: ", prices)
        sinusoids, fundamental_freqs = calculate_fourier_magnitudes(prices)
        #print("magnitudes: ", magnitudes[0])
        #print("sinusoids: ", sinusoids)
        #sinusoids = [int(s) for s in sinusoids]  # Convertir a int
        fundamental_freqs = [int(f) for f in fundamental_freqs]  # Convertir a int
        return JsonResponse({'sinusoids': sinusoids, 'fundamental_freqs': fundamental_freqs})
    



#import requests

def get_binance_symbols():
    url = "https://api.binance.com/api/v3/exchangeInfo"
    try:
        response = requests.get(url)
        response.raise_for_status()  # Lanza un error si la solicitud no fue exitosa
        data = response.json()
        symbols = [symbol['symbol'] for symbol in data['symbols']]
        return symbols
    except requests.exceptions.RequestException as e:
        print(f"Error al obtener símbolos de Binance: {e}")
        return []


def get_available_symbols(request):
    # Obtener los símbolos disponibles
    available_symbols = get_binance_symbols()
    print("available_symbols: ", available_symbols)
    return JsonResponse({'symbols': available_symbols})

def check_strategy_status(request, strategy_number):
    """Verifica si una estrategia está realmente ejecutándose"""
    try:
        # Intentar leer el PID del archivo
        pid_file = f'strategy{strategy_number}_pid.txt'
        
        if not os.path.exists(pid_file):
            return JsonResponse({'is_running': False})
            
        with open(pid_file, 'r') as f:
            pid = int(f.read().strip())
            
        # Verificar si el proceso existe
        try:
            os.kill(pid, 0)  # Señal 0 solo verifica existencia
            return JsonResponse({'is_running': True})
        except ProcessLookupError:
            # El proceso no existe, limpiar archivo
            os.remove(pid_file)
            return JsonResponse({'is_running': False})
            
    except Exception as e:
        logging.error(f"Error checking strategy {strategy_number} status: {str(e)}")
        return JsonResponse({'is_running': False})


