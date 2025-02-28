from stable_baselines3 import PPO
from IndicadoresEnv import IndicadoresEnv, AgenteIndicadores, ejecutar_busqueda_indicadores


single_asset =  ['ETH']
# Crear el entorno
indicadores_posibles = ['close','high','low','open','SMA_20', 'SMA_10', 'RSI', 'MACD', 'BB_upper','BB_lower','BB_middle','volatility','volatility_pct','volatility_pct_20','volatility_pct_50','volatility_pct_100']
mejores_indicadores, rendimiento = ejecutar_busqueda_indicadores(indicadores_posibles, single_asset, timesteps_entrenamiento=0, n_episodios=10)

print(f"Mejores indicadores encontrados: {mejores_indicadores}")
print(f"Rendimiento obtenido: {rendimiento}%")