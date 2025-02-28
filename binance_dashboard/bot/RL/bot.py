from typing import Optional, Tuple
import logging

class RLBot:
    def calculate_profit(self, current_price: float, quantity: float, pair: str) -> Optional[Tuple[float, float, float, float]]:
        try:
            if quantity is None or current_price is None:
                logging.error("La cantidad o precio actual no pueden ser None")
                return None
                
            balance = self.get_account_balance(pair.replace('USDT', ''))

            if not self.positions[pair] or not self.entry_prices[pair]:
                return 0.0, 0.0, current_price, balance
                
            entry_price = float(self.entry_prices[pair])  # Convert to float
            if entry_price == 0:  # Avoid division by zero
                return 0.0, 0.0, current_price, balance
                
            profit_pct = ((current_price - entry_price) / entry_price) * 100
            profit_usd = quantity * entry_price * (profit_pct / 100)
            
            return profit_usd, profit_pct, current_price, balance
            
        except Exception as e:
            logging.error(f"Error calculando beneficio para {pair}: {str(e)}")
            return None