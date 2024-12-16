import { getCookie } from '/static/scripts/utils/utils.js';

export async function executeStrategy1() {
    try {
        const response = await fetch('/execute_strategy_1/', {
            method: 'POST'
        });
        const data = await response.json();
        
        if (data.success) {
            console.log('Estrategia 1 ejecutada con éxito:', data.output);
        } else {
            console.error('Error al ejecutar la estrategia 1:', data.error);
        }
    } catch (error) {
        console.error('Error en la solicitud:', error);
    }
}

export async function executeStrategy2() {
    try {
        const response = await fetch('/execute_strategy_2/', {
            method: 'POST'
        });
        const data = await response.json();
        
        if (data.success) {
            console.log('Estrategia 2 ejecutada con éxito:', data.output);
        } else {
            console.error('Error al ejecutar la estrategia 2:', data.error);
        }
    } catch (error) {
        console.error('Error en la solicitud:', error);
    }
}

export async function stopStrategy(strategyNumber) {
    try {
        const response = await fetch(`/stop_strategy_${strategyNumber}/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            }
        });
        const data = await response.json();
        
        if (!data.success) {
            console.error(`Error al detener estrategia ${strategyNumber}:`, data.error);
            throw new Error(data.error);
        }
        
        // Notificar al usuario
        alert(`Estrategia ${strategyNumber} detenida correctamente`);
    } catch (error) {
        console.error(`Error al detener estrategia ${strategyNumber}:`, error);
        alert(`Error al detener estrategia ${strategyNumber}: ${error.message}`);
        throw error;
    }
}