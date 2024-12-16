from binance.client import Client
from binance.enums import *
import openai
import pandas as pd
import numpy as np
from datetime import datetime
import config
import logging
import ta
from trading_env import TradingEnv
from rl_agent import RLTradingAgent
import math
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor
import json
import os
from dotenv import load_dotenv
from typing import Dict, List, Optional, Tuple

load_dotenv()
class TradingBot:
    def __init__(self, single_asset: str = False, interval: str = '1m', simulation_mode: bool = True, estrategia: str='strategy1', stop_loss_mode: bool = True, re_load: bool = True):
        """
        Inicializa el bot de trading
        
        Args:
            single_asset: Activo único para operar (opcional)
            interval: Intervalo de tiempo para las velas
            simulation_mode: Si es True opera en modo simulación
        """
        self.client = Client(os.getenv('BINANCE_API_KEY'), os.getenv('BINANCE_SECRET_KEY'))
        self.client_llm = openai.OpenAI(
            base_url="http://127.0.0.1:1233/v1",  # URL del servidor local
            api_key="not-needed" # No se necesita API key para servidor local
        )
        self.available_assets = self._get_available_assets()
        self.interval = interval
        self.simulation_mode = simulation_mode
        self.stop_loss_mode = stop_loss_mode
        self.strategy = estrategia
        
        if single_asset:
            for asset in single_asset:
                if asset not in self.available_assets:
                    raise ValueError(f"El activo {asset} no está disponible")
            self.available_assets = single_asset

        self.trading_pairs = self._generate_trading_pairs()
        self.positions: Dict[str, bool] = {}
        self.entry_prices: Dict[str, Optional[float]] = {}
        
        
        def init_positions(self) -> None:
            """
            Inicializa las posiciones y precios de entrada basado en los balances existentes
            y el historial de órdenes
            """
            try:
                for pair in self.trading_pairs:
                    base_asset = pair.replace('USDT', '')
                    balance = self.get_account_balance(base_asset)
                    
                    if balance > 0:

                        orders = self.client.get_all_orders(symbol=pair, limit=5000)
                            
                        # Buscar última orden de compra ejecutada
                        entry_price = None
                        #print(orders)
                        for order in reversed(orders):
                            if (order['symbol'] == pair and 
                                order['side'] == 'BUY' and 
                                order['status'] == 'FILLED' and
                                float(order['price']) != 0):
                                entry_price = float(order['price'])
                                break
                                    
                        
                        if entry_price is not None:
                            self.entry_prices[pair] = entry_price
                            self.positions[pair] = True
                        else:
                            try:
                                ticker = self.client.get_symbol_ticker(symbol=pair)
                                self.entry_prices[pair] = float(ticker['price'])
                                self.positions[pair] = True
                            except Exception as e:
                                logging.error(f"Error obteniendo precio actual para {pair}: {e}")
                                self.entry_prices[pair] = None
                                self.positions[pair] = False

                    else:
                        self.positions[pair] = False
                        self.entry_prices[pair] = None
                        
            except Exception as e:
                logging.error(f"Error inicializando posiciones: {e}")
                
        
        #self.trade_quantity = 0.0
        
        self._setup_logging()
        # Archivos separados para cada estrategia
        self.simulated_orders_files = {
            'strategy1': 'simulated_orders_strategy1.json',
            'strategy2': 'simulated_orders_strategy2.json'
        }
        self.simulated_orders = {
            'strategy1': [],
            'strategy2': []
        }
        # Archivos para balances simulados por estrategia
        self.simulated_balances_files = {
            'strategy1': 'simulated_balances_strategy1.json',
            'strategy2': 'simulated_balances_strategy2.json'
        }
        self.simulated_balances = {
            'strategy1': {},
            'strategy2': {}
        }
        self._init_simulated_balances()
        self._init_simulated_orders()
        init_positions(self)
        
        self._load_simulated_orders()

        if self.strategy == 'strategy2':
            self.envs: Dict[str, TradingEnv] = {}
            self.agents: Dict[str, RLTradingAgent] = {}
            self._setup_rl_agents(re_load = re_load)
            self.executing_strategy = self.strategy_2
        if self.strategy == 'strategy1':
            self.executing_strategy = self.strategy_1

    
    #Configuracion de loggingcle
    def _setup_logging(self) -> None:
        """Configura el sistema de logging"""
        logging.basicConfig(
            filename=f'trading_log_{datetime.now().strftime("%Y%m%d")}.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

    #Inicializacion de balances simulados
    def _init_simulated_balances(self) -> None:
        """Inicializa o carga los balances simulados para cada estrategia"""
        # Siempre crear un nuevo archivo de balances
        self._create_initial_balances(self.strategy)

    def _create_initial_balances(self, strategy: str) -> None:
        """
        Crea balances iniciales basados en los balances reales para una estrategia
        
        Args:
            strategy: Nombre de la estrategia
        """
        try:
            account = self.client.get_account()
            self.simulated_balances[strategy] = {
                balance['asset']: float(balance['free']) 
                for balance in account['balances']
                if float(balance['free']) > 0 or float(balance['locked']) > 0
            }
            self._save_simulated_balances(strategy)
        except Exception as e:
            logging.error(f"Error creando balances iniciales para {strategy}: {e}")
            self.simulated_balances[strategy] = {'USDT': 1000.0}  # Balance por defecto
            self._save_simulated_balances(strategy)

    def _save_simulated_balances(self, strategy: str) -> None:
        """
        Guarda los balances simulados en archivo para una estrategia
        
        Args:
            strategy: Nombre de la estrategia
        """
        try:
            with open(self.simulated_balances_files[strategy], 'w') as f:
                json.dump(self.simulated_balances[strategy], f, indent=4)
        except Exception as e:
            logging.error(f"Error guardando balances simulados para {strategy}: {e}")

    def _update_simulated_balance(self, asset: str, amount: float, strategy: str) -> None:
        """
        Actualiza el balance simulado de un activo para una estrategia
        
        Args:
            asset: Símbolo del activo
            amount: Cantidad a agregar (positivo) o restar (negativo)
            strategy: Nombre de la estrategia
        """

        current = self.simulated_balances[strategy].get(asset, 0.0)
        self.simulated_balances[strategy][asset] = max(0.0, current + amount)
        self._save_simulated_balances(strategy)

    def _init_simulated_orders(self) -> None:
        """
        Inicializa los archivos de órdenes simuladas para cada estrategia.
        Si los archivos existen, se leen y se borra su contenido.
        Luego, se rellenan con las órdenes actuales de la cuenta.
        """
        filename = self.simulated_orders_files[self.strategy]
        if os.path.exists(filename):
            # Leer y borrar el contenido del archivo
            with open(filename, 'r+') as f:
                    f.truncate(0)  # Borra el contenido del archivo

            # Obtener órdenes actuales de la cuenta
            all_orders = []
            for pair in self.trading_pairs:
                try:
                    orders = self.client.get_all_orders(symbol=pair, limit=50)
                    for order in orders:
                        if order['status'] == 'FILLED':
                            order_data = {
                                'symbol': order['symbol'],
                                'isBuyer': order['side'] == 'BUY',
                                'side': order['side'],
                                'type': ORDER_TYPE_MARKET,
                                'status': 'FILLED',
                                'price': float(order['price']),
                                'qty': float(order['executedQty']),
                                'quantity': float(order['executedQty']),
                                'time': str(datetime.fromtimestamp(order['time'] / 1000)),
                                'strategy': strategy
                            }
                            all_orders.append(order_data)
                except Exception as e:
                    logging.error(f"Error obteniendo órdenes para {pair}: {e}")

            # Guardar las órdenes en el archivo
            with open(filename, 'w') as f:
                json.dump(all_orders, f, indent=4)


    def _load_simulated_orders(self) -> None:
        """Carga órdenes simuladas desde archivos JSON por estrategia"""
        for strategy, filename in self.simulated_orders_files.items():
            if not os.path.exists(filename):
                self.simulated_orders[strategy] = []
                self._save_simulated_orders(strategy)
            else:
                try:
                    with open(filename, 'r') as f:
                        self.simulated_orders[strategy] = json.load(f)
                except Exception as e:
                    logging.error(f"Error cargando órdenes simuladas de {strategy}: {e}")
                    self.simulated_orders[strategy] = []

    def _save_simulated_orders(self, strategy: str) -> None:
        """
        Guarda órdenes simuladas en archivo JSON por estrategia
        
        Args:
            strategy: Nombre de la estrategia
        """
        try:
            with open(self.simulated_orders_files[strategy], 'w') as f:
                json.dump(self.simulated_orders[strategy], f, indent=4)
        except Exception as e:
            logging.error(f"Error guardando órdenes simuladas de {strategy}: {e}")

    def _save_simulated_order(self, order: Dict, strategy: str) -> None:
        """
        Guarda una nueva orden simulada para una estrategia específica
        
        Args:
            order: Diccionario con datos de la orden
            strategy: Nombre de la estrategia
        """
        self.simulated_orders[strategy].append(order)
        self._save_simulated_orders(strategy)

    @lru_cache(maxsize=32)
    def _get_available_assets(self) -> List[str]:
        """Obtiene lista de activos disponibles"""
        try:
            account = self.client.get_account()
            return [balance['asset'] for balance in account['balances'] 
                   if float(balance['free']) > 0 or float(balance['locked']) > 0]
        except Exception as e:
            logging.error(f"Error obteniendo activos: {e}")
            return ['BTC']

    def _generate_trading_pairs(self) -> List[str]:
        """Genera pares de trading válidos"""
        def check_pair(asset: str) -> Optional[str]:
            if asset != 'USDT':
                pair = f"{asset}USDT"
                try:
                    self.client.get_symbol_info(pair)
                    return pair
                except:
                    logging.warning(f"Par {pair} no disponible")
                    return None
                    
        with ThreadPoolExecutor() as executor:
            pairs = executor.map(check_pair, self.available_assets)
            valid_pairs = [p for p in pairs if p]
            
        return valid_pairs
    def get_historical_data(self, symbol: str, interval: str = '1m', limit: int = 1000) -> Optional[pd.DataFrame]:
        """
        Obtiene datos históricos de Binance
        
        Args:
            symbol: Par de trading (ej: 'BTCUSDT')
            interval: Intervalo de tiempo ('1m', '5m', '1h', etc)
            limit: Cantidad de velas a obtener
            
        Returns:
            DataFrame con datos históricos o None si hay error
        """
        try:
            klines = self.client.get_klines(
                symbol=symbol,
                interval=interval,
                limit=limit
            )

            #print(klines)
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 
                'ignore'
            ])

            #print(df.tail(10))
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            numeric_columns = ['open', 'high', 'low', 'close', 'volume', 
                             'number_of_trades', 'taker_buy_base_asset_volume',
                             'taker_buy_quote_asset_volume']
            df[numeric_columns] = df[numeric_columns].apply(pd.to_numeric)
            
            # Calcular volumen de venta restando volumen de compra del total
            df['taker_sell_base_asset_volume'] = df['volume'] - df['taker_buy_base_asset_volume']
            
            #print(df.tail(10))
            return df
            
        except Exception as e:
            logging.error(f"Error obteniendo datos históricos para {symbol}: {str(e)}")
            return None
        
    def analyze_market(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Realiza análisis técnico sobre los datos
        
        Args:
            df: DataFrame con datos históricos
            
        Returns:
            DataFrame con indicadores técnicos
        """
        numeric_columns = ['open', 'high', 'low', 'close', 'volume']
        df[numeric_columns] = df[numeric_columns].astype(float)

        df['SMA_10'] = ta.trend.sma_indicator(df['close'], window=10)
        df['SMA_20'] = ta.trend.sma_indicator(df['close'], window=20)
        df['EMA_50'] = ta.trend.ema_indicator(df['close'], window=50)
        df['RSI'] = ta.momentum.rsi(df['close'], window=14)
        macd = ta.trend.MACD(df['close'])
        df['MACD'] = macd.macd()
        df['MACD_signal'] = macd.macd_signal()
        bollinger = ta.volatility.BollingerBands(df['close'])
        df['BB_upper'] = bollinger.bollinger_hband()
        df['BB_lower'] = bollinger.bollinger_lband()
        df['BB_middle'] = bollinger.bollinger_mavg()
        df['volatility'] = df['close'].pct_change().rolling(window=20).std() * 100
        df['volatility_pct'] = df['volatility'] / df['close'] * 100
        df['volatility_pct_20'] = df['volatility_pct'].rolling(window=20).mean()
        df['volatility_pct_50'] = df['volatility_pct'].rolling(window=50).mean()
        df['volatility_pct_100'] = df['volatility_pct'].rolling(window=100).mean()
        buy_taker_columns = ['taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume']
        df['taker_buy_activity'] = df[buy_taker_columns[0]] + df[buy_taker_columns[1]]
        # Calculamos la fuerza del mercado comparando volumen de compra vs volumen total
        df['bullish_market_strength'] = (df['taker_buy_base_asset_volume'] / df['volume']) * 100
        # Media móvil de la fuerza del mercado para suavizar la señal
        df['bullish_market_strength_sma'] = df['bullish_market_strength'].rolling(window=20).mean()
        df['bearish_market_strength'] = (df['taker_sell_base_asset_volume'] / df['volume']) * 100
        df['bearish_market_strength_sma'] = df['bearish_market_strength'].rolling(window=20).mean()    

        return df


        
    def calculate_profit(self, current_price: float, quantity: float, pair: str) -> Optional[Tuple[float, float, float, float]]:
        """
        Calcula el beneficio actual para un par de trading
        
        Args:
            current_price: Precio actual del activo
            quantity: Cantidad de activos transaccionados
            pair: Par de trading (ej: 'BTCUSDT')
            
        Returns:
            Tupla con (beneficio_usd, porcentaje_beneficio, precio_actual, balance)
            o None si hay error
        """
        try:
            balance = self.get_account_balance(pair.replace('USDT', ''))

            if not self.positions[pair] or not self.entry_prices[pair]:
                return 0.0, 0.0, current_price, balance
                
            entry_price = self.entry_prices[pair]
            profit_pct = ((current_price - entry_price) / entry_price) * 100
            profit_usd = quantity * entry_price * (profit_pct / 100)
            
            logging.info(f"{pair} - Entrada: {entry_price:.8f} - Actual: {current_price:.8f}")
            logging.info(f"Beneficio: {profit_pct:.8f}% ({profit_usd:.8f} USDT)")
            
            return profit_usd, profit_pct, current_price, balance
            
        except Exception as e:
            logging.error(f"Error calculando beneficio (calculate_profit) para {pair}: {str(e)}")
            return None





    def get_account_balance(self, asset: str = 'USDT') -> float:
        """
        Obtiene el balance de un activo para una estrategia específica
        
        Args:
            asset: Símbolo del activo
            
        Returns:
            Balance disponible
        """
        try:
            # Usar operador ternario para simplificar la lógica
            return (
                self.simulated_balances[self.strategy].get(asset, 0.0) 
                if self.simulation_mode
                else float(self.client.get_asset_balance(asset=asset)['free'])
            )
        except Exception as e:
            logging.error(f"Error obteniendo balance de {asset} para {self.strategy}: {e}")
            return 0.0

    def place_market_order(self, symbol: str, side: str, quantity: float) -> Optional[Dict]:
        """
        Coloca una orden de mercado
        
        Args:
            symbol: Par de trading
            side: 'BUY' o 'SELL'
            quantity: Cantidad que sera transaccionada
            strategy: Nombre de la estrategia
            
        Returns:
            Diccionario con datos de la orden o None si hay error
        """
        try:
            
            ticker = self.client.get_symbol_ticker(symbol=symbol)
            current_price = float(ticker['price'])
            #formatted_qty = self.format_quantity(symbol, quantity, current_price, side)
            formatted_qty = quantity
            print(f"Colocando orden {side} para {symbol} con estrategia {self.strategy} con la cantidad {formatted_qty}")
            base_asset = symbol.replace('USDT', '')
            if not formatted_qty:
                return None

            
            order = {
                    'symbol': symbol,
                    'isBuyer': side == 'BUY',
                    'side': side,
                    'type': ORDER_TYPE_MARKET,
                    'status': 'FILLED',
                    'price': current_price,
                    'qty': formatted_qty,
                    'quantity': formatted_qty,
                    'time': str(datetime.now()),
                    'strategy': self.strategy
                }


            #Si no esta en modo simulacion, se ejecuta la orden en binance
            if not self.simulation_mode:
                try:
                    order = self.client.create_order(
                        symbol=symbol,
                        side=side,
                        type=ORDER_TYPE_MARKET,
                        quantity=formatted_qty
                    )
                    #return order_broker
                except Exception as e:
                    logging.error(f"Error al crear orden en Binance: {str(e)}")
                    if "insufficient balance" in str(e).lower():
                        logging.error("Balance insuficiente para ejecutar la orden")
                    elif "MIN_NOTIONAL" in str(e):
                        logging.error("La orden no cumple con el mínimo notional requerido")
                    elif "LOT_SIZE" in str(e):
                        logging.error("La cantidad no cumple con el tamaño de lote permitido")
                    return None
            
            self._save_simulated_order(order, self.strategy)
                
            # Actualizar balances simulados
            qty = float(formatted_qty)
            if side == 'BUY':
                    self._update_simulated_balance('USDT', -qty * current_price, self.strategy)
                    self._update_simulated_balance(base_asset, qty, self.strategy)
            else:
                    self._update_simulated_balance('USDT', qty * current_price, self.strategy)
                    self._update_simulated_balance(base_asset, -qty, self.strategy)

            logging.info(f"Orden {side} ({self.strategy}): {formatted_qty} {symbol} a {current_price}")
            return order

        except Exception as e:
            logging.error(f"Error en orden {side}: {e}")
            return None

    def place_short_market_order(self, symbol: str, side: str, quantity: float) -> Optional[Dict]:
        """
        Coloca una orden de mercado para posición corta
        
        Args:
            symbol: Par de trading
            side: 'SELL' para abrir corto o 'BUY' para cerrar corto
            quantity: Cantidad que sera transaccionada
            strategy: Nombre de la estrategia
            
        Returns:
            Diccionario con datos de la orden o None si hay error
        """
        try:
            ticker = self.client.get_symbol_ticker(symbol=symbol)
            current_price = float(ticker['price'])
            formatted_qty = self.format_quantity(symbol, quantity, current_price, side)
            print(f"Colocando orden corta {side} para {symbol} con estrategia {self.strategy} con la cantidad {formatted_qty}")
            base_asset = symbol.replace('USDT', '')
            if not formatted_qty:
                return None

            order = {
                    'symbol': symbol,
                    'isBuyer': side == 'BUY',
                    'side': side,
                    'type': ORDER_TYPE_MARKET,
                    'status': 'FILLED', 
                    'price': current_price,
                    'qty': formatted_qty,
                    'quantity': formatted_qty,
                    'time': str(datetime.now()),
                    'strategy': self.strategy,
                    'isShort': True
                }

            #Si no esta en modo simulacion, se ejecuta la orden en binance
            if not self.simulation_mode:
                try:
                    params = {'type': 'MARKET'}
                    if side == 'SELL':
                        # Abrir posición corta
                        order = self.client.create_margin_order(
                            symbol=symbol,
                            side=SIDE_SELL,
                            type=ORDER_TYPE_MARKET,
                            quantity=formatted_qty,
                            sideEffectType='MARGIN_BUY',
                            **params
                        )
                    else:
                        # Cerrar posición corta
                        order = self.client.create_margin_order(
                            symbol=symbol,
                            side=SIDE_BUY,
                            type=ORDER_TYPE_MARKET,
                            quantity=formatted_qty,
                            sideEffectType='AUTO_REPAY',
                            **params
                        )
                except Exception as e:
                    logging.error(f"Error al crear orden corta en Binance: {str(e)}")
                    if "insufficient balance" in str(e).lower():
                        logging.error("Balance insuficiente para ejecutar la orden")
                    elif "MIN_NOTIONAL" in str(e):
                        logging.error("La orden no cumple con el mínimo notional requerido")
                    elif "LOT_SIZE" in str(e):
                        logging.error("La cantidad no cumple con el tamaño de lote permitido")
                    return None

            self._save_simulated_order(order, self.strategy)
                
            # Actualizar balances simulados para posición corta
            qty = float(formatted_qty)
            if side == 'SELL':
                # Abrir corto
                self._update_simulated_balance('USDT', qty * current_price, self.strategy)
                self._update_simulated_balance(f"SHORT_{base_asset}", qty, self.strategy)
            else:
                # Cerrar corto
                self._update_simulated_balance('USDT', -qty * current_price, self.strategy)
                self._update_simulated_balance(f"SHORT_{base_asset}", -qty, self.strategy)

            logging.info(f"Orden corta {side} ({self.strategy}): {formatted_qty} {symbol} a {current_price}")
            return order

        except Exception as e:
            logging.error(f"Error en orden corta {side}: {e}")
            return None

    def calculate_position_size(self, pair: str, risk_percentage: float = 10.0) -> Optional[str]:
        """
        Calcula el tamaño de la posición
        
        Args:
            pair: Par de trading
            risk_percentage: Porcentaje de riesgo
            
        Returns:
            Cantidad formateada o None si hay error
        """
        try:
            balance = self.get_account_balance('USDT')
            current_price = float(self.client.get_symbol_ticker(symbol=pair)['price'])
            position_size = max(5.0, balance * risk_percentage) / current_price
            #return self.format_quantity(pair, position_size, current_price, side='BUY')
            return position_size
        except Exception as e:
            logging.error(f"Error calculando posición: {e}")
            return None
        
    def calculate_sell_size(self, pair: str, risk_percentage: float = 10.0, min_qty: float = 5.0) -> Optional[str]:
        """
        Calcula el tamaño de la posición
        
        Args:
            pair: Par de trading
            risk_percentage: Porcentaje de riesgo
            
        Returns:
            Cantidad formateada o None si hay error
        """
        try:
            balance = self.get_account_balance(pair.replace('USDT', ''))
            sell_size = balance * risk_percentage
            #return self.format_quantity(pair, position_size, current_price, side='BUY')
            return sell_size
        except Exception as e:
            logging.error(f"Error calculando posición: {e}")
            return None

    def format_quantity(self, pair: str, quantity: float, current_price: float, side: str = None) -> Optional[str]:
        """
        Formatea la cantidad según los límites del par y verifica balance disponible
        
        Args:
            pair: Par de trading
            quantity: Cantidad a formatear
            current_price: Precio actual
            side: Lado de la operación (BUY/SELL)
            
        Returns:
            Cantidad formateada o None si hay error
        """
        try:
            limits = self.get_symbol_limits(pair)
            if not limits:
                return None

            quantity = float(quantity)
            current_price = float(current_price)
            min_notional = float(limits['min_notional'])
            max_qty = float(limits['max_qty'])
            min_qty = float(limits['min_qty'])
            step_size = float(limits['step_size'])

            if quantity * current_price < min_notional:
                quantity = (min_notional / current_price)

            quantity = max(min(quantity, max_qty), min_qty)
            precision = int(round(-math.log(step_size, 10), 0))
            quantity = round(quantity - (quantity % step_size), precision)

            # Verificar balance disponible según el lado de la operación
            if side == 'BUY':
                usdt_balance = self.get_account_balance('USDT')
                if quantity * current_price > usdt_balance:
                    logging.error(f"Balance USDT insuficiente para comprar {quantity} {pair}")
                    return None
            elif side == 'SELL':
                base_asset = pair.replace('USDT', '')
                asset_balance = self.get_account_balance(base_asset)
                if quantity > asset_balance:
                    logging.error(f"Balance {base_asset} insuficiente para vender {quantity} {pair}")
                    return None

            return f'{quantity:.{precision}f}'

        except Exception as e:
            logging.error(f"Error formateando cantidad: {e}")
            return None





    def get_symbol_limits(self, pair: str) -> Optional[Dict[str, float]]:
        """
        Obtiene los límites de trading para un símbolo
        
        Args:
            pair: Par de trading
            
        Returns:
            Diccionario con límites o None si hay error
        """
        try:
            info = self.client.get_symbol_info(pair)
            filters = {f['filterType']: f for f in info['filters']}

            #print(filters)
            min_notional = float(filters.get('NOTIONAL', {'minNotional': '5.0'})['minNotional'])
            
            return {
                'min_qty': float(filters['LOT_SIZE']['minQty']),
                'max_qty': float(filters['LOT_SIZE']['maxQty']),
                'step_size': float(filters['LOT_SIZE']['stepSize']),
                'min_notional': min_notional
            }
        except Exception as e:
            logging.error(f"Error obteniendo límites para {pair}: {e}")
            return None
        
    def execute_trade_strategy(self) -> Tuple[float, float, float, float]:
        """
        Ejecuta estrategia de trading #1 basada en indicadores técnicos
        
        Returns:
            Tupla con (beneficio_total_usd, beneficio_promedio_pct, último_precio, balance_total)
        """
        results = []
        with ThreadPoolExecutor() as executor:
            futures = [executor.submit(self._execute_single_pair_strategy, pair) 
                      for pair in self.trading_pairs]
            results = [f.result() for f in futures if f.result()]

        if not results:
            return 0.0, 0.0, 0.0, 0.0
        
        #print("Resultados completos:", results)

        total_profit_usd = sum(r[0] for r in results)
        avg_profit_pct = sum(r[1] for r in results) / len(results)
        
        # Calcular balance total en la moneda base y en USD
        total_balance = sum(r[3] for r in results)
        
        # Desglose del cálculo del balance total en USD
        balances_usd = []
        for r in results:
            precio = r[2]
            balance = r[3] 
            balance_usd = precio * balance
            balances_usd.append(balance_usd)
            #print(f"Par: Precio={precio}, Balance={balance}, Balance USD={balance_usd}")
            
        total_balance_usd = sum(balances_usd)
        print(f"Balance total USD: {total_balance_usd}")

        return total_profit_usd, avg_profit_pct, total_balance, total_balance_usd
    

    def strategy_1(self, pair: str) -> Tuple[Optional[str], float]:
            """
            Determina la estrategia para un par específico y retorna el side y la cantidad.
            
            Args:
                pair: Par de trading
                
            Returns:
                side: 'BUY' o 'SELL' o None
                quantity: Cantidad a comprar o vender
            """
            try:
                df = self.get_historical_data(pair)
                if df is None or df.empty:
                    return None, 0.0
                    
                df = self.analyze_market(df)
                if df is None or df.empty:
                    return None, 0.0

                current_price = float(df.iloc[-1]['close'])
                sma_20 = df.iloc[-1]['SMA_20']
                rsi = df.iloc[-1]['RSI']
                bb_lower = df.iloc[-1]['BB_lower']
                bb_upper = df.iloc[-1]['BB_upper']
                # Media móvil de la fuerza del mercado para suavizar la señal
                bullish_strength = df.iloc[-1]['bullish_market_strength_sma']
                bearish_strength = df.iloc[-1]['bearish_market_strength_sma']

                # Inicializar quantity
                quantity = 0.0
                side = None

                # Definir el porcentaje de stop-loss
                stop_loss_pct = 0.05  # 5% de pérdida máxima permitida

                # Señal de compra: precio bajo + RSI bajo + cerca de BB inferior + fuerza alcista alta
                if (current_price < sma_20 and 
                    rsi < 30 and 
                    current_price <= bb_lower and 
                    bullish_strength > bearish_strength):
                    optimal_quantity = self.calculate_position_size(pair)
                    if optimal_quantity is not None:
                        quantity = self.format_quantity(pair, optimal_quantity, current_price, side='BUY')
                        side = 'BUY'
                elif self.positions[pair]:
                    # Verificar si el stop-loss está habilitado y si el precio actual ha caído por debajo del stop-loss
                    use_stop_loss = self.stop_loss_mode
                    entry_price = self.entry_prices[pair]
                    stop_loss_price = entry_price * (1 - stop_loss_pct)
                    
                    # Señal de venta por stop loss o condiciones técnicas + fuerza bajista alta
                    if use_stop_loss and current_price <= stop_loss_price:
                        quantity = self.get_account_balance(pair.replace('USDT', ''))
                        side = 'SELL'
                    elif (current_price > sma_20 and 
                          rsi > 70 and 
                          current_price >= bb_upper and
                          bearish_strength > bullish_strength):  # Fuerza de venta mayor que de compra
                        risk_percentage = 10.0
                        optimal_quantity = self.calculate_sell_size(pair, risk_percentage)
                        if optimal_quantity is not None:
                            quantity = self.format_quantity(pair, optimal_quantity, current_price, side='SELL')
                            side = 'SELL'

                return side, quantity

            except Exception as e:
                logging.error(f"Error en estrategia 1 para {pair}: {e}")
                return None, 0.0

    def ejecutar_operacion(self, side: str, pair: str, quantity: float) -> Optional[Dict]:
            """
            Efectúa la operación de compra o venta.
            
            Args:
                side: 'BUY' o 'SELL'
                pair: Par de trading
                quantity: Cantidad a comprar o vender
                
            Returns:
                Orden ejecutada o None si hay error
            """
            try:
                order = self.place_market_order(pair, side, quantity)
                if order:
                    if side == 'BUY':
                        self.entry_prices[pair] = float(order['price'])
                        self.positions[pair] = True
                    elif side == 'SELL':
                        balance = self.get_account_balance(pair.replace('USDT', ''))
                        print(f"Balance {pair.replace('USDT', '')}: {balance}")
                        if balance <= 0:
                            self.positions[pair] = False
                    return order
                else:
                    return None
            except Exception as e:
                logging.error(f"Error al ejecutar operación (ejecutar_operacion) {side} en {pair}: {e}")
                return None

    def _execute_single_pair_strategy(self, pair: str) -> Optional[Tuple[float, float, float, float]]:
            """
            Ejecuta estrategia #1 para un par específico usando indicadores técnicos
            
            Args:
                pair: Par de trading
                
            Returns:
                Tupla con resultados o None si hay error
            """
            try:
                side, quantity = self.executing_strategy(pair)
                if side and quantity > 0.0:
                    order = self.ejecutar_operacion(side, pair, quantity)

                # Recalcular el precio actual y el profit
                df = self.get_historical_data(pair, limit=1)
                current_price = float(df.iloc[-1]['close']) if df is not None and not df.empty else 0.0

                profit = self.calculate_profit(current_price, quantity, pair)
                return profit if profit else (0.0, 0.0, current_price, 0.0)
            except Exception as e:
                logging.error(f"Error en ejecución de estrategia (execute_single_pair_strategy) para {pair}: {e}")
                return None
    

    #Estrategia 2

    def _setup_rl_agents(self, re_load: bool = True) -> None:
        """Configura los agentes de RL para cada par de trading"""
        def setup_agent(pair: str) -> Tuple[str, Optional[Tuple[TradingEnv, RLTradingAgent]]]:
            try:
                df = self.get_historical_data(pair, interval=self.interval, limit=1000)
                print(df)
                if df is not None:
                    df = self.analyze_market(df)
                    df = df.dropna()
                    indicators = self.get_technical_indicators(pair)
                    #print(indicators)

                    balance_asset = self.get_account_balance(pair.replace('USDT', ''))
                    balance_usdt = self.get_account_balance('USDT')
                    env = TradingEnv(pair,df,technical_indicators=indicators, initial_balance_usd=balance_usdt, initial_balance_asset=balance_asset)
                    agent = RLTradingAgent(env, type_model='ppo')
                    
                    if re_load:
                        model_path = f'trading_model_{pair}_{self.interval}'
                        try:
                            agent.model.load(model_path)
                            logging.info(f"Modelo cargado para {pair}_{self.interval}")
                        except:
                            logging.info(f"No se encontró modelo existente para {pair}_{self.interval}")
                        
                    return pair, (env, agent)
                return pair, None
            except Exception as e:
                logging.error(f"Error configurando agente {pair}: {e}")
                return pair, None

        with ThreadPoolExecutor() as executor:
            results = executor.map(setup_agent, self.trading_pairs)
            
        for pair, result in results:
            if result:
                self.envs[pair], self.agents[pair] = result

    def train_agent(self, timesteps: int = 100000) -> None:
        """
        Entrena los agentes de RL
        
        Args:
            timesteps: Número de pasos de entrenamiento
        """
        def train_single_agent(pair: str) -> None:
            logging.info(f"Entrenando agente {pair}...")
            self.agents[pair].train(timesteps)
            model_path = f'trading_model_{pair}_{self.interval}'
            self.agents[pair].save(model_path)
            logging.info(f"Modelo guardado en {model_path}")

        with ThreadPoolExecutor() as executor:
            executor.map(train_single_agent, self.trading_pairs)

    def get_technical_indicators(self, pair):
        """Obtener indicadores técnicos para un par específico"""
        import json
        
        try:
            with open('pair_indicators.json', 'r') as f:
                pair_indicators = json.load(f)
            return pair_indicators.get(pair)
        except FileNotFoundError:
            # Si el archivo no existe, crear uno con los indicadores por defecto
            pair_indicators = {
                'BTCUSDT': ['close','high','low','open'],
                'ETHUSDT': ['close', 'high','low','open'], 
                'BNBUSDT': ['close','high','low','open'],
                'TRXUSDT': ['close','high','low','open'],
                'TROYUSDT': ['close','high','low','open']
            }
            
            with open('pair_indicators.json', 'w') as f:
                json.dump(pair_indicators, f, indent=4)
                
            return pair_indicators.get(pair)

        
    def _prepare_observation(self, row: pd.Series, symbol: str, indicators: List[str], window_size: int, current_price: float) -> Optional[np.ndarray]:
        """
        Prepara observación para el agente RL usando una ventana de datos históricos
        
        Args:
            row: Fila de datos actual
            symbol: Par de trading
            indicators: Lista de indicadores técnicos
            window_size: Tamaño de la ventana de datos históricos
        Returns:
            Array numpy con la observación o None si hay error
        """
        try:
            asset = symbol.replace('USDT', '')
            
            
            if row is None or row.empty:
                return None, 0.0
                
            # Obtener últimas n filas según window_size
            window_data = row.tail(window_size)
            #print(window_data)
            
            # Obtener datos técnicos para la ventana completa
            raw_obs = np.array([
                window_data[indicator].values  # Usar todos los valores de la ventana
                for indicator in indicators
            ])
            #print(raw_obs)

            # Normalizar cada punto de tiempo en la ventana
            scaled_obs = np.array([
                self.envs[symbol].scaler.transform(raw_obs[:, i].reshape(1, -1)).flatten()
                for i in range(raw_obs.shape[1])
            ]).flatten()
            
            # Añadir información de posición y balance
            asset_balance = self.get_account_balance(asset)
            usd_balance = self.get_account_balance('USDT')
            #current_price = row['close']
            current_total = usd_balance + (asset_balance * current_price)
            
            balance_info = np.array([
                asset_balance / max(self.envs[symbol].initial_balance_asset, 1e-8),
                usd_balance / max(self.envs[symbol].initial_balance_usd, 1e-8), 
                (current_total / max(self.envs[symbol].initial_total_balance, 1e-8)) - 1.0
            ])
            
            return np.concatenate([scaled_obs, balance_info]).reshape(1, -1).astype(np.float32)

        except Exception as e:
            logging.error(f"Error preparando observación para {symbol}: {str(e)}")
            return None

    


    def strategy_2(self, pair: str) -> Tuple[Optional[str], float]:
        """
        Determina la estrategia para un par específico usando RL y retorna el side y la cantidad.
        
        Args:
            pair: Par de trading
            
        Returns:
            side: 'BUY' o 'SELL' o None
            quantity: Cantidad a comprar o vender
        """
        try:
            side = None
            quantity = 0.0
            window_size = self.envs[pair].window_size

            df = self.get_historical_data(pair, limit=window_size*3)
            if df is None or df.empty:
                return None, 0.0
                
            df = self.analyze_market(df)
            if df is None or df.empty:
                return None, 0.0
            
            current_price = df.iloc[-1]['close']    

            indicators = self.get_technical_indicators(pair)
            #print(indicators)

            observation = self._prepare_observation(df, pair, indicators, window_size, current_price)
            if observation is None:
                return side, quantity

            action = self.agents[pair].predict(observation)
            if action[0][0] > 0.5:
                percent_quantity = action[0][1]
                optimal_quantity = self.calculate_position_size(pair, percent_quantity)
                
                if optimal_quantity is not None:
                    quantity = self.format_quantity(pair, optimal_quantity, current_price, side='BUY')
                    if quantity!=None:
                        quantity = float(quantity)
                        side = 'BUY'
                    else:
                        side = None
                        quantity = 0.0
                    
            elif action[0][0] < -0.5 and self.positions[pair]:
                #risk_percentage = 10.0
                percent_quantity = action[0][1]
                optimal_quantity = self.calculate_sell_size(pair, percent_quantity)
                
                if optimal_quantity is not None:
                    quantity = self.format_quantity(pair, optimal_quantity, current_price, side='SELL')
                    if quantity!=None:
                        quantity = float(quantity)
                        side = 'SELL'
                    else:
                        side = None
                        quantity = 0.0

            return side, quantity

        except Exception as e:
            logging.error(f"Error en estrategia 2 para {pair}: {e}")
            return side, quantity
        



    def strategy_3(self, data: dict) -> dict:
        """
        Implementa la estrategia 3 usando un modelo de lenguaje.
        
        Args:
            data: Diccionario con datos de precios e indicadores.
            
        Returns:
            Diccionario con la acción ('BUY', 'SELL', 'HOLD'), cantidad y argumento.
        """
        # Definir el prompt
        prompt = f"""
        Eres un trader profesional. Aquí tienes los datos de mercado:
        
        - Precio de cierre: {data['close']}
        - SMA 20: {data['SMA_20']}
        - RSI: {data['RSI']}
        - MACD: {data['MACD']}
        - Bollinger Bands: {data['BB_upper']}, {data['BB_lower']}
        
        Basado en estos datos, ¿deberías comprar, vender o mantener? 
        Indica la cantidad de transacción y proporciona un argumento para tu decisión.
        """

        # Realizar la solicitud al modelo
        response = self.client_llm.chat.completions.create(
            model="finance-llama3-8b",
            messages=[
                {"role": "system", "content": "Eres un trader profesional."},
                {"role": "user", "content": prompt}
            ]
        )

        # Procesar la respuesta
        decision = response.choices[0].message.content.strip()
        # Aquí puedes implementar lógica para extraer la acción, cantidad y argumento de la respuesta
        # Por ejemplo, podrías usar expresiones regulares o procesamiento de texto simple

        print("decision: ", decision)

        return {
            'action': 'BUY',  # Extraer de la respuesta
            'quantity': 10,   # Extraer de la respuesta
            'argument': decision  # Usar la respuesta completa como argumento
        }