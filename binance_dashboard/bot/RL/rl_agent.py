from stable_baselines3 import PPO, A2C
from stable_baselines3.common.vec_env import DummyVecEnv
from stable_baselines3.common.callbacks import CheckpointCallback
import numpy as np


class RLTradingAgent:
    def __init__(self, env, type_model):
        self.env = DummyVecEnv([lambda: env])
        self.symbol = self.env.envs[0].pair
        self.type_model = type_model

        # Configuración mejorada del modelo con learning rate dinámico
        initial_lr = 1e-3  # Learning rate inicial más alto
        if type_model == 'ppo':
        # Modelo PPO
            self.model = PPO(
                'MlpPolicy',
                self.env,
                learning_rate=lambda remaining_progress: initial_lr * (1 - remaining_progress), # Learning rate dinámico
                n_steps=4096,  # Aumentado para mejor exploración
                batch_size=256, # Batch size más grande para mejor estabilidad
                n_epochs=20,    # Más épocas por actualización
                gamma=0.995,    # Horizonte temporal más largo
                gae_lambda=0.98, # Mayor énfasis en recompensas a largo plazo
                clip_range=0.3,  # Rango de recorte más amplio
                clip_range_vf=0.3, # Recorte del valor también
                ent_coef=0.02,   # Mayor exploración
                vf_coef=0.7,     # Mayor énfasis en la estimación de valor
                max_grad_norm=1.0, # Gradientes menos restringidos
                use_sde=True,     # Exploración con ruido estado-dependiente
                sde_sample_freq=4, # Frecuencia de muestreo SDE
                target_kl=0.015,   # Control más estricto de divergencia KL
                tensorboard_log=f"./tensorboard_log/{self.symbol}/ppo/",
                verbose=1
            )
        elif type_model == 'a2c':
            # Modelo A2C
            self.model = A2C(
                'MlpPolicy',
                self.env,
                learning_rate=lambda remaining_progress: initial_lr * (1 - remaining_progress),
                n_steps=4096,
                gamma=0.995,
                gae_lambda=0.98,
                ent_coef=0.02,
                vf_coef=0.7,
                max_grad_norm=1.0,
                use_sde=True,
                sde_sample_freq=4,
                tensorboard_log=f"./tensorboard_log/{self.symbol}/a2c/",
                verbose=1
            )

    def train(self, total_timesteps=100000):
        """Entrenar el agente con checkpoints y registrar balances"""
        checkpoint_callback = CheckpointCallback(
            save_freq=1000,
            save_path=f'./model_checkpoints/{self.symbol}/',
            name_prefix=f'trading_model_{self.symbol}'
        )

        # Obtener balance inicial
        #initial_balance = self.env.envs[0].initial_balance_usd + (self.env.envs[0].initial_balance_asset * self.env.envs[0].initial_price)
        initial_balance = self.env.envs[0].initial_total_balance
        # Crear archivo de registro de balances
        with open(f'training_balances_{self.symbol}.txt', 'w') as f:
            f.write(f"Balance inicial para {self.symbol}: {initial_balance:.2f}\n")

        try:
            # Entrenar modelo hasta lograr un cambio superior al 5%
            epoch = 0
            max_change = -float('inf')
            
            while max_change <= 5.0 and epoch < 10:
                self.model.learn(
                    total_timesteps=total_timesteps,
                    callback=checkpoint_callback,
                    reset_num_timesteps=False
                )
                
                # Calcular y registrar balance actual
                current_price = self.env.envs[0].df['close'].iloc[self.env.envs[0].current_step]
                current_balance = self.env.envs[0].balance_usd + (self.env.envs[0].balance_asset * current_price)
                change_pct = ((current_balance/initial_balance)-1)*100
                
                max_change = max(max_change, change_pct)
                
                with open(f'training_balances_{self.symbol}.txt', 'a') as f:
                    f.write(f"Época {epoch}: Balance = {current_balance:.2f}, Cambio = {change_pct:.2f}%\n")
                
                epoch += 1

            if max_change > 0.1:
                print(f"Entrenamiento completado. Se alcanzó un cambio de {max_change:.2f}%")
            else:
                print(f"Se alcanzó el máximo de épocas sin lograr un cambio superior al 5%")

        except Exception as e:
            print(f"Error durante el entrenamiento de {self.symbol}: {str(e)}")
            raise e

    def save(self, path):
        """Guardar el modelo"""
        self.model.save(f"{path}_{self.symbol}")

    def load(self, path):
        """Cargar un modelo guardado"""
        if self.type_model == 'ppo':
            self.model = PPO.load(f"{path}_{self.symbol}")
        elif self.type_model == 'a2c':
            self.model = A2C.load(f"{path}_{self.symbol}")

    def predict(self, observation):
        """Predecir la siguiente acción"""
        action, _ = self.model.predict(observation)
        return action