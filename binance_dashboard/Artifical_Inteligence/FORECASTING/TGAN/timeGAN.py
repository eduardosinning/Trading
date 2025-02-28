import numpy as np
import torch
import torch.nn as nn
from torch import optim
import torch.nn.functional as F
#from torch.utils.data import DataLoader
#from binance_dashboard.bot.forecasting.TGAN.utils import random_generator
#from binance_dashboard.bot.forecasting.TGAN.utils import extract_time
import matplotlib.pyplot as plt
import pandas as pd

class Time_GAN_module(nn.Module):
    """
    Módulo TimeGAN adaptado para predicción de precios de Binance
    """
    def __init__(self, input_size, output_size, hidden_dim, n_layers, activation=torch.sigmoid, rnn_type="gru"):
        super(Time_GAN_module, self).__init__()

        self.hidden_dim = hidden_dim
        self.n_layers = n_layers
        self.sigma = activation
        self.rnn_type = rnn_type

        if self.rnn_type == "gru":
            self.rnn = nn.GRU(input_size, hidden_dim, n_layers, batch_first=True)
        elif self.rnn_type == "rnn":
            self.rnn = nn.RNN(input_size, hidden_dim, n_layers, batch_first=True)
        elif self.rnn_type == "lstm":
            self.rnn = nn.LSTM(input_size, hidden_dim, n_layers, batch_first=True)
            
        self.fc = nn.Linear(hidden_dim, output_size)
        
    def forward(self, x):
        batch_size = x.size(0)

        if self.rnn_type in ["rnn", "gru"]:
            hidden = self.init_hidden(batch_size)
        elif self.rnn_type == "lstm":
            h0 = torch.zeros(self.n_layers, batch_size, self.hidden_dim).float()
            c0 = torch.zeros(self.n_layers, batch_size, self.hidden_dim).float()
            hidden = (h0, c0)

        out, hidden = self.rnn(x, hidden)
        out = out.contiguous().view(-1, self.hidden_dim)
        out = self.fc(out)
        
        if self.sigma == nn.Identity:
            return nn.Identity()(out)
            
        out = self.sigma(out)
        return out, hidden
    
    def init_hidden(self, batch_size):
        hidden = torch.zeros(self.n_layers, batch_size, self.hidden_dim)
        return hidden

def prepare_binance_data(df, window_size=10):
    """
    Prepara los datos de Binance para el entrenamiento
    """
    # Seleccionar features relevantes
    features = ['open', 'high', 'low', 'close']
    data = df[features].values
    
    # Crear ventanas deslizantes
    X, y = [], []
    for i in range(len(data) - window_size*2):
        X.append(data[i:i+window_size])
        y.append(data[i+window_size:i+window_size*2, 3]) # Solo close price
        
    return np.array(X), np.array(y)

def train_timegan_binance(df, parameters,symbol,interval):
    """
    Entrena TimeGAN con datos de Binance
    
    Args:
        df: DataFrame con datos OHLC de Binance
        parameters: Diccionario con parámetros de entrenamiento
    """
    # Preparar datos
    X, y = prepare_binance_data(df)
    
    # Configurar dimensiones
    input_dim = 4  # OHLC
    output_dim = 1 # Solo close
    seq_len = 10   # 10 minutos
    
    # Intentar cargar modelos guardados
    generator_path = f'{symbol}_{interval}_TGAN_generator.pth'
    discriminator_path = f'{symbol}_{interval}_TGAN_discriminator.pth'
    
    if os.path.exists(generator_path) and os.path.exists(discriminator_path):
        # Cargar modelos existentes
        generator = Time_GAN_module(input_size=input_dim, output_size=output_dim,
                                  hidden_dim=parameters['hidden_dim'],
                                  n_layers=parameters['num_layers'])
        generator.load_state_dict(torch.load(generator_path))
        
        discriminator = Time_GAN_module(input_size=output_dim, output_size=1,
                                      hidden_dim=parameters['hidden_dim'],
                                      n_layers=parameters['num_layers'])
        discriminator.load_state_dict(torch.load(discriminator_path))
        print("Modelos cargados exitosamente")
    else:
        # Crear nuevos modelos
        generator = Time_GAN_module(input_size=input_dim, output_size=output_dim,
                                  hidden_dim=parameters['hidden_dim'],
                                  n_layers=parameters['num_layers'])
        discriminator = Time_GAN_module(input_size=output_dim, output_size=1,
                                      hidden_dim=parameters['hidden_dim'],
                                      n_layers=parameters['num_layers'])
        print("Creando nuevos modelos")
    
    # Optimizadores
    g_optimizer = optim.Adam(generator.parameters(), lr=0.001)
    d_optimizer = optim.Adam(discriminator.parameters(), lr=0.001)
    
    # Entrenamiento
    for epoch in range(parameters['epoch']):
        for i in range(0, len(X), parameters['batch_size']):
            batch_X = torch.FloatTensor(X[i:i+parameters['batch_size']])
            batch_y = torch.FloatTensor(y[i:i+parameters['batch_size']])
            
            # Entrenar discriminador
            d_optimizer.zero_grad()
            pred_y = generator(batch_X)[0]
            d_real = discriminator(batch_y.unsqueeze(-1))[0]
            d_fake = discriminator(pred_y.detach().unsqueeze(-1))[0]
            
            d_loss = -torch.mean(torch.log(d_real + 1e-8) + torch.log(1 - d_fake + 1e-8))
            d_loss.backward()
            d_optimizer.step()
            
            # Entrenar generador
            g_optimizer.zero_grad() 
            pred_y = generator(batch_X)[0]
            d_fake = discriminator(pred_y.unsqueeze(-1))[0]
            
            g_loss = -torch.mean(torch.log(d_fake + 1e-8))
            g_loss.backward()
            g_optimizer.step()
            
        if epoch % 10 == 0:
            print(f'Epoch {epoch}: G_loss={g_loss.item():.4f}, D_loss={d_loss.item():.4f}')
    
    # Guardar modelos entrenados
    torch.save(generator.state_dict(), generator_path)
    torch.save(discriminator.state_dict(), discriminator_path)
    print("Modelos guardados exitosamente")
            
    return generator

def predict_next_window(generator, last_window):
    """
    Genera predicción para los próximos 10 minutos
    
    Args:
        generator: Modelo entrenado
        last_window: Últimos 10 minutos de datos OHLC
    """
    with torch.no_grad():
        x = torch.FloatTensor(last_window).unsqueeze(0)
        pred = generator(x)[0].numpy()
    return pred


from dotenv import load_dotenv
from binance.client import Client
from binance.exceptions import BinanceAPIException
from datetime import datetime, timedelta
import json
import logging
import time
import os
load_dotenv()


class BinanceView:
    def __init__(self):
        self.api_key = os.getenv('BINANCE_API_KEY')
        self.api_secret = os.getenv('BINANCE_SECRET_KEY')
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

def run_prediction_loop(symbol, interval):
    """Ejecutar predicciones en tiempo real con TimeGAN"""
    try:
        # Parámetros del modelo TimeGAN
        parameters = {
            'hidden_dim': 128,      # Dimensión de capa oculta
            'num_layers': 4,       # Número de capas RNN
            'batch_size': 320,      # Tamaño del batch
            'epoch': 100000,          # Épocas de entrenamiento
            'window_size': 10      # Ventana de tiempo para predicción
        }
        
        binance_view = BinanceView()
        
        while True:
            # Obtener datos más recientes
            df = binance_view.get_binance_data(symbol, interval)
            df.columns = ['open', 'high', 'low', 'close', 'volume']
            df = df[['open', 'high', 'low', 'close']]  # Solo usamos OHLC
            print(df)
            # Entrenar modelo
            generator = train_timegan_binance(df, parameters,symbol,interval)
            
            # Obtener última ventana para predicción
            last_window = df[-parameters['window_size']:].values
            predictions = predict_next_window(generator, last_window)
            print(predictions)
            
            # Guardar predicción
            next_minute = datetime.now() + timedelta(minutes=1)
            prediction_data = {
                'timestamp': next_minute.strftime('%Y-%m-%d %H:%M:%S'),
                'value': predictions[-1].item()  # Convertir a escalar Python nativo
            }
            
            # Guardar en archivo JSON
            filename = f'{symbol}_{interval}_TGAN_predictions.json'
            try:
                with open(filename, 'r') as f:
                    predictions_list = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                predictions_list = []
            
            predictions_list.append(prediction_data)
            
            with open(filename, 'w') as f:
                json.dump(predictions_list, f)
            
            print(f"Predicción TimeGAN para el siguiente minuto: {float(predictions[-1]):.2f}")
            
            # Esperar intervalo
            time.sleep(60)
            
    except Exception as e:
        print(f"Error en TimeGAN: {str(e)}")
        logging.error(f"Error en TimeGAN: {str(e)}")

# Configuración inicial
with open('C:/Users/eduar/PycharmProjects/FinArt/binance_dashboard/bot/forecasting/chart_config.json') as f:
    data = json.load(f)

symbol = data['currentSymbol']
interval = data['currentInterval']

print("Símbolo:", symbol)
print("Intervalo:", interval)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_prediction_loop(symbol, interval)
    