# -*- coding: utf-8 -*-

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import os

from sklearn.preprocessing import MinMaxScaler
#buena
import logging

from binance.client import Client
from binance.exceptions import BinanceAPIException
from datetime import datetime

import tensorflow as tf
from tensorflow.keras import backend as K
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.optimizers import Adam

# Configurar TensorFlow para usar ejecución eager
tf.compat.v1.enable_eager_execution()
K.clear_session()

class BinanceView:
    def __init__(self):
        
        
        self.api_key = 'akOyfC3602O1NAnRHqMCItE6Z7R5phRTr2e33pKKigzHUP3TNtq1u6Nixh8Z6I9J'
        self.api_secret = 'UyywNH3aUIpCsIUw4u2Zedy5p7hQ0EHKtSAJzPAEh1XR3x0iYzMVhpFpkCzMJb4N'
        self.client = Client(self.api_key, self.api_secret)
    
    def get_binance_data(self, symbol, interval='1m', limit=1000):
        """Obtener datos de Binance por minuto"""
        klines = self.client.get_klines(symbol=symbol, interval=interval, limit=limit)
        dates = [datetime.fromtimestamp(entry[0] / 1000).strftime('%Y-%m-%d %H:%M:%S') for entry in klines]
        
        # Obtener datos OHLCV
        opens = [float(entry[1]) for entry in klines]
        highs = [float(entry[2]) for entry in klines]
        lows = [float(entry[3]) for entry in klines]
        closes = [float(entry[4]) for entry in klines]
        volumes = [float(entry[5]) for entry in klines]
        
        data = pd.DataFrame({
            'Open': opens,
            'High': highs,
            'Low': lows,
            'Close': closes,
            'Volume': volumes
        }, index=dates)
        
        return data
    
        
    def get_account_info(self):
        try:
            account = self.client.get_account()
            total_balance_usd = 0
            balances = []
            
            for balance in account['balances']:
                if float(balance['free']) > 0 or float(balance['locked']) > 0:
                    asset = balance['asset']
                    free = float(balance['free'])
                    locked = float(balance['locked'])
                    
                    # Calcular valor en USD
                    if asset != 'USDT':
                        try:
                            price = float(self.client.get_symbol_ticker(symbol=f"{asset}USDT")['price'])
                        except:
                            price = 0
                    else:
                        price = 1
                        
                    total_asset = free + locked
                    asset_value_usd = total_asset * price
                    total_balance_usd += asset_value_usd
                    
                    balances.append({
                        'asset': asset,
                        'free': free,
                        'locked': locked,
                        'usd_value': asset_value_usd
                    })
            
            return {
                'balances': balances,
                'total_balance_usd': total_balance_usd
            }
        except BinanceAPIException as e:
            return {'error': str(e)}

class LSTMPredictor:
    def __init__(self, lookback=60, model_path='model_weights.h5', features=['Close']):
        self.lookback = lookback
        self.model_path = model_path
        self.scaler = MinMaxScaler(feature_range=(0, 1))
        self.logger = logging.getLogger(__name__)
        self.predictions = []
        self.features = features
        
        # Cargar modelo si existe
        if os.path.exists(self.model_path):
            print("Se encontró modelo")
            try:
                print("Cargando modelo")
                # Limpiar sesión antes de cargar el modelo
                K.clear_session()
                self.model = load_model(self.model_path, compile=False)
                self.model.compile(optimizer=Adam(learning_rate=0.001), loss='mean_squared_error')
                self.logger.info("Modelo cargado exitosamente")
            except Exception as e:
                self.logger.error(f"Error cargando modelo: {str(e)}")
        else:
            print("No se encontró modelo")
            self.model = None   

    def create_model(self, input_shape):
        """Crear el modelo LSTM"""
        model = Sequential([
            LSTM(units=50, return_sequences=True, input_shape=input_shape),
            Dropout(0.2),
            LSTM(units=50, return_sequences=True),
            Dropout(0.2),
            LSTM(units=50),
            Dropout(0.2),
            Dense(units=len(self.features))
        ])
        
        model.compile(optimizer=Adam(learning_rate=0.001), loss='mean_squared_error')
        return model

    def prepare_data(self, data):
        """Preparar los datos para el entrenamiento"""
        try:
            # Seleccionar features
            if isinstance(data, pd.DataFrame):
                data = data[self.features].values
            
            # Normalizar los datos
            scaled_data = self.scaler.fit_transform(data)
            
            X, y = [], []
            for i in range(self.lookback, len(scaled_data)):
                X.append(scaled_data[i-self.lookback:i])
                y.append(scaled_data[i])
            
            return np.array(X), np.array(y)
            
        except Exception as e:
            self.logger.error(f"Error preparando datos: {str(e)}")
            raise

    def train(self, data, epochs=50, batch_size=32, validation_split=0.1):
        """Entrenar el modelo"""
        try:
            # Preparar datos
            X, y = self.prepare_data(data)
            
            # Crear modelo si no existe
            if self.model is None:
                print("Creando modelo")
                self.model = self.create_model(input_shape=(X.shape[1], X.shape[2]))
            
            # Entrenar modelo
            history = self.model.fit(
                X, y,
                epochs=epochs,
                batch_size=batch_size,
                validation_split=validation_split,
                verbose=1
            )
            
            # Guardar pesos del modelo
            self.model.save(self.model_path)
            self.logger.info("Modelo guardado exitosamente")
            
            return history
            
        except Exception as e:
            self.logger.error(f"Error entrenando modelo: {str(e)}")
            raise

    def predict(self, data):
        """Hacer predicciones"""
        try:
            if self.model is None:
                raise ValueError("El modelo debe ser entrenado antes de hacer predicciones")
            
            # Preparar datos para predicción
            if isinstance(data, pd.DataFrame):
                data = data[self.features].values
                
            if len(data) < self.lookback:
                raise ValueError(f"Se necesitan al menos {self.lookback} puntos de datos para la predicción")
            
            # Tomar los últimos lookback puntos
            last_sequence = data[-self.lookback:]
            
            # Normalizar
            scaled_sequence = self.scaler.transform(last_sequence)
            
            # Reshape para el modelo
            X = np.array([scaled_sequence])
            
            # Hacer predicción
            scaled_prediction = self.model.predict(X)
            
            # Desnormalizar
            prediction = self.scaler.inverse_transform(scaled_prediction)
            
            return prediction[0]
            
        except Exception as e:
            self.logger.error(f"Error haciendo predicción: {str(e)}")
            raise

    def evaluate(self, test_data):
        """Evaluar el modelo con datos de prueba"""
        try:
            X_test, y_test = self.prepare_data(test_data)
            score = self.model.evaluate(X_test, y_test, verbose=0)
            return score
            
        except Exception as e:
            self.logger.error(f"Error evaluando modelo: {str(e)}")
            raise


def run_prediction_loop(symbol, interval):
    """Ejecutar predicciones en tiempo real"""
    try:
        binance_view = BinanceView()
        # Usar todas las características OHLCV
        predictor = LSTMPredictor(lookback=60, model_path='{}_{}_model_weights.h5'.format(symbol, interval), features=['Open', 'High', 'Low', 'Close', 'Volume'])
        
        while True:
            # Obtener datos más recientes usando BinanceView
            data = binance_view.get_binance_data(symbol, interval)
            
            # Entrenar modelo con nuevos datos
            predictor.train(data, epochs=5)
            
            # Hacer predicción
            last_60_minutes = data[-60:]
            predictions = predictor.predict(last_60_minutes)

            # Guardar predicción con timestamp
            next_minute = datetime.now() + timedelta(minutes=1)
            prediction_data = {
                'timestamp': next_minute.strftime('%Y-%m-%d %H:%M:%S'),
                'value': float(predictions[3])  # Usar el valor de Close
            }
            
            # Guardar predicción en archivo JSON
            try:
                with open('{}_{}_predictions.json'.format(symbol,interval), 'r') as f:
                    predictions_list = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                predictions_list = []
            
            predictions_list.append(prediction_data)
            
            with open('{}_{}_predictions.json'.format(symbol,interval), 'w') as f:
                json.dump(predictions_list, f)
            
            print(f"Predicción para el siguiente minuto: {predictions[3]:.2f}")
            
            # Esperar 1 minuto
            import time
            time.sleep(60)
            
    except Exception as e:
        print(f"Error: {str(e)}")
        

# Leer el archivo JSON
with open('C:/Users/eduar/PycharmProjects/FinArt/binance_dashboard/bot/forecasting/chart_config.json') as f:
    data = json.load(f)

# Extraer los valores de currentSymbol y currentInterval
symbol = data['currentSymbol']
interval = data['currentInterval']

print("El simbolo es:", symbol)
print("El intervalo es:", interval)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_prediction_loop(symbol, interval)
    
    
    
##Final