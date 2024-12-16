import gym
from gym import spaces
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler


class TradingEnv(gym.Env):
    def __init__(self, pair, df, technical_indicators=None, initial_balance_usd=10000, initial_balance_asset=0, window_size=10):
        super(TradingEnv, self).__init__()
        # Establecer indicadores técnicos por defecto si no se proporcionan
        self.technical_indicators = technical_indicators if technical_indicators else [
            'close', 'SMA_20', 'EMA_50', 'RSI', 'MACD', 'BB_upper', 'BB_lower', 
            'BB_middle', 'volatility', 'volatility_pct', 'volatility_pct_20', 
            'volatility_pct_50', 'volatility_pct_100', 'taker_buy_activity'
        ]
        
        # Preprocesar y limpiar datos
        self.df = self._prepare_data(df)
        self.pair = pair
        self.window_size = window_size
        
        # Balances iniciales y actuales
        self.initial_balance_usd = initial_balance_usd
        self.initial_balance_asset = initial_balance_asset
        self.balance_usd = initial_balance_usd
        self.balance_asset = initial_balance_asset
        # Fee por transacción
        self.fee = 0.00075  # 0.075%
        
        # Calcular balance total inicial
        self.initial_price = self.df['close'].iloc[self.window_size]
        self.initial_total_balance = initial_balance_usd + (initial_balance_asset * self.initial_price)
        
        self.current_step = 0

        # Definir espacios
        self.action_space = spaces.Box(
            low=np.array([-1, 0]),  # [acción (-1 venta, 0 hold, 1 compra), cantidad]
            high=np.array([1, 1]),  # cantidad normalizada entre 0 y 1
            shape=(2,),
            dtype=np.float32
        )

        # Espacio de observación normalizado para ventana de tiempo completa
        observation_dim = (len(self.technical_indicators) * window_size) + 3  # Multiplicar por window_size para incluir toda la ventana
        self.observation_space = spaces.Box(
            low=-10,
            high=10,
            shape=(observation_dim,),
            dtype=np.float32
        )

        # Inicializar scaler
        self.scaler = StandardScaler()
        self._fit_scaler()

    def _prepare_data(self, df):
        """Preprocesar y limpiar datos"""
        # Rellenar valores NaN
        df = df.fillna(method='ffill')
        df = df.fillna(method='bfill')

        # Asegurarse de que todas las columnas sean numéricas
        for col in self.technical_indicators:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        return df

    def _fit_scaler(self):
        """Ajustar el scaler a los datos"""
        data_to_scale = np.column_stack([
            self.df[indicator] for indicator in self.technical_indicators
        ])
        self.scaler.fit(data_to_scale)

    def _get_observation(self):
        """Obtener el estado actual normalizado considerando la ventana de tiempo"""
        if self.current_step < self.window_size:
            return None
            
        # Obtener datos de la ventana actual
        window_data = self.df.iloc[self.current_step - self.window_size + 1:self.current_step + 1]
        #print(window_data)
        
        # Obtener datos técnicos para la ventana
        raw_obs = np.array([
            window_data[indicator].values  # Usar toda la ventana de datos
            for indicator in self.technical_indicators
        ])
        #print(raw_obs)

        # Normalizar cada punto de tiempo en la ventana
        scaled_obs = np.array([
            self.scaler.transform(raw_obs[:, i].reshape(1, -1)).flatten()
            for i in range(raw_obs.shape[1])
        ]).flatten()
        #print(scaled_obs)


        current_price = window_data['close'].iloc[-1]
        current_total_balance = self.balance_usd + (self.balance_asset * current_price)
        
        # Añadir información de balance y posición
        balance_info = np.array([
            self.balance_asset / max(self.initial_balance_asset, 1e-8),
            self.balance_usd / max(self.initial_balance_usd, 1e-8),
            (current_total_balance / max(self.initial_total_balance, 1e-8)) - 1.0
        ])

        return np.concatenate([scaled_obs, balance_info]).astype(np.float32)

    def step(self, action):
        """Ejecutar un paso en el ambiente"""
        done = False
        self.current_step += 1

        if self.current_step >= len(self.df) - 1:
            done = True

        action_type = action[0]  # -1 a 1
        quantity = action[1]     # 0 a 1

        reward = self._calculate_reward(action_type, quantity)
        obs = self._get_observation()

        current_price = self.df['close'].iloc[self.current_step]
        current_total_balance = self.balance_usd + (self.balance_asset * current_price)
        
        info = {
            'balance_usd': self.balance_usd,
            'balance_asset': self.balance_asset,
            'total_balance': current_total_balance,
            'initial_total_balance': self.initial_total_balance,
            'balance_change': current_total_balance - self.initial_total_balance,
            'step': self.current_step
        }

        return obs, reward, done, info

    def _calculate_reward(self, action_type, quantity):
        """Calcular recompensa basada en cambio de balance total"""
        current_price = self.df['close'].iloc[self.current_step]
        prev_total_balance = self.balance_usd + (self.balance_asset * current_price)
        
        # Convertir cantidad normalizada a cantidad real
        if action_type > 0.5:  # Compra
            max_asset_to_buy = self.balance_usd / (current_price * (1 + self.fee))
            actual_quantity = quantity * max_asset_to_buy
            
            if self.balance_usd >= actual_quantity * current_price * (1 + self.fee):
                cost = actual_quantity * current_price * (1 + self.fee)
                self.balance_usd -= cost
                self.balance_asset += actual_quantity
                
        elif action_type < -0.5:  # Venta
            actual_quantity = quantity * self.balance_asset
            
            if self.balance_asset >= actual_quantity:
                revenue = actual_quantity * current_price * (1 - self.fee)
                self.balance_usd += revenue
                self.balance_asset -= actual_quantity

        # Calcular nuevo balance total y retornar diferencia como recompensa
        new_total_balance = self.balance_usd + (self.balance_asset * current_price)
        reward = (new_total_balance - prev_total_balance) / self.initial_total_balance
        
        return reward

    def reset(self):
        """Reiniciar el ambiente"""
        self.current_step = self.window_size  # Empezar después de la ventana inicial
        self.balance_usd = self.initial_balance_usd
        self.balance_asset = self.initial_balance_asset
        
        initial_price = self.df['close'].iloc[0]
        self.initial_total_balance = self.initial_balance_usd + (self.initial_balance_asset * initial_price)
        
        return self._get_observation()