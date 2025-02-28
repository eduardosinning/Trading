import gym
from gym import spaces
import numpy as np
from bot import TradingBot
import logging
from stable_baselines3 import PPO
import time

class IndicadoresEnv(gym.Env):
    def __init__(self, indicadores_posibles, single_asset, tiempo_limite=None):
        super(IndicadoresEnv, self).__init__()
        self.indicadores_posibles = indicadores_posibles
        self.action_space = spaces.MultiDiscrete([len(indicadores_posibles)] * 6)
        self.observation_space = spaces.Box(low=0, high=1, shape=(len(indicadores_posibles),), dtype=np.float32)
        self.state = None
        self.single_asset = single_asset
        self.bot = TradingBot(single_asset=self.single_asset, simulation_mode=True, estrategia='strategy2', re_load=False)
        self.tiempo_limite = tiempo_limite
        self.tiempo_inicio = None
        self.reset()

    def reset(self):
        self.state = np.random.rand(len(self.indicadores_posibles))
        self.tiempo_inicio = time.time()
        return self.state

    def step(self, action):
        # Verificar si se excedió el tiempo límite
        if self.tiempo_limite and (time.time() - self.tiempo_inicio) > self.tiempo_limite:
            return self.state, -100, True, {'tiempo_excedido': True}

        # Seleccionar indicadores basados en la acción
        seleccionados = [self.indicadores_posibles[i] for i in action]
        
        # Guardar indicadores seleccionados en pair_indicators.json
        import json
        try:
            with open('pair_indicators.json', 'r') as f:
                pair_indicators = json.load(f)
            
            # Actualizar los indicadores para el par BTC-USDT
            pair_indicators[f'{self.single_asset[0]}USDT'] = seleccionados
            
            with open('pair_indicators.json', 'w') as f:
                json.dump(pair_indicators, f, indent=4)
        except Exception as e:
            logging.error(f"Error guardando indicadores: {str(e)}")

        if not self.bot.agents:
            logging.error("No se pudo configurar ningún agente de trading")
            return self.state, -100, True, {}
        
        self.bot.train_agent(timesteps=1000)
        
        # Leer archivo de balances
        try:
            with open(f'training_balances_{self.single_asset[0]}USDT.txt', 'r') as f:
                lines = f.readlines()
                balance_inicial = float(lines[0].split(': ')[1].strip())
                balances = [float(line.split('Balance = ')[1].split(',')[0]) 
                           for line in lines[1:]]
                balance_final = max(balances)
                variacion_porcentual = ((balance_final/balance_inicial)-1)*100
        except Exception as e:
            logging.error(f"Error leyendo archivo de balances: {str(e)}")
            return self.state, -100, True, {}
        
        reward = variacion_porcentual
        self.state = np.random.rand(len(self.indicadores_posibles))
        done = True
        
        return self.state, reward, done, {}

    def render(self, mode='human'):
        pass

class AgenteIndicadores:
    def __init__(self, indicadores_posibles, single_asset, tiempo_limite=None):
        self.env = IndicadoresEnv(indicadores_posibles, single_asset, tiempo_limite)
        self.model = PPO("MlpPolicy", self.env, verbose=1)
        self.tiempo_limite = tiempo_limite
        
    def entrenar(self, total_timesteps=10000):
        tiempo_inicio = time.time()
        while True:
            if self.tiempo_limite and (time.time() - tiempo_inicio) > self.tiempo_limite:
                logging.info("Tiempo límite de entrenamiento alcanzado")
                break
            self.model.learn(total_timesteps=min(1000, total_timesteps))
            total_timesteps -= 1000
            if total_timesteps <= 0:
                break
        
    def guardar_modelo(self, ruta):
        self.model.save(ruta)
        
    def cargar_modelo(self, ruta):
        self.model = PPO.load(ruta, env=self.env)
        
    def encontrar_mejores_indicadores(self, n_episodios=10):
        mejores_indicadores = None
        mejor_rendimiento = float('-inf')
        tiempo_inicio = time.time()
        
        for _ in range(n_episodios):
            if self.tiempo_limite and (time.time() - tiempo_inicio) > self.tiempo_limite:
                logging.info("Tiempo límite de búsqueda alcanzado")
                break
                
            obs = self.env.reset()
            done = False
            while not done:
                action, _ = self.model.predict(obs)
                obs, reward, done, info = self.env.step(action)
                
                if 'tiempo_excedido' in info:
                    return mejores_indicadores, mejor_rendimiento
                
                if reward > mejor_rendimiento:
                    mejor_rendimiento = reward
                    mejores_indicadores = [self.env.indicadores_posibles[i] for i in action]
                    
        return mejores_indicadores, mejor_rendimiento

def ejecutar_busqueda_indicadores(indicadores_posibles, single_asset, timesteps_entrenamiento=30, n_episodios=10, tiempo_limite_segundos=10000):
    """
    Ejecuta la búsqueda de los mejores indicadores técnicos
    
    Args:
        indicadores_posibles: Lista de indicadores disponibles
        single_asset: Lista con el activo a operar
        timesteps_entrenamiento: Pasos de entrenamiento para el agente
        n_episodios: Número de episodios para buscar mejores indicadores
        tiempo_limite_segundos: Tiempo límite en segundos para la búsqueda
        
    Returns:
        tuple: Mejores indicadores encontrados y su rendimiento
    """
    agente = AgenteIndicadores(indicadores_posibles, single_asset, tiempo_limite_segundos)
    
    if timesteps_entrenamiento > 0:
        agente.entrenar(timesteps_entrenamiento)
        agente.guardar_modelo(f"{single_asset[0]}_modelo_encuentra_indicadores.zip")
    else:
        agente.cargar_modelo(f"{single_asset[0]}_modelo_encuentra_indicadores.zip")
        
    mejores_indicadores, rendimiento = agente.encontrar_mejores_indicadores(n_episodios)
    
    logging.info(f"Mejores indicadores encontrados: {mejores_indicadores}")
    logging.info(f"Rendimiento obtenido: {rendimiento}%")
    
    return mejores_indicadores, rendimiento