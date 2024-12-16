import logging 



single_asset = ['BTC']

try:
    with open(f'training_balances_{single_asset[0]}USDT.txt', 'r') as f:
        lines = f.readlines()
        # Extraer balance inicial de la primera línea
        balance_inicial = float(lines[0].split(': ')[1].strip())
        print(balance_inicial)
        
                # Encontrar el máximo balance final
        balances = [float(line.split('Balance = ')[1].split(',')[0]) 
                   for line in lines[1:]]
        balance_final = max(balances)
        print(balance_final)
        # Calcular variación porcentual
        variacion_porcentual = ((balance_final/balance_inicial)-1)*100
        print(variacion_porcentual)
except Exception as e:
    logging.error(f"Error leyendo archivo de balances: {str(e)}")