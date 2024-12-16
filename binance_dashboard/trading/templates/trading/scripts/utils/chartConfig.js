import { getCookie } from '/static/scripts/utils/utils.js';

export async function saveChartConfiguration(chartConfig) {
    try {
        const saveConfigResponse = await fetch('/save_chart_config/', {
            method: 'POST', 
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify(chartConfig)
        });
        
        if (!saveConfigResponse.ok) {
            console.error('Error al guardar la configuración del gráfico');
        }
    } catch (error) {
        console.error('Error al guardar la configuración:', error);
    }
}

export function getChartConfig(currentSymbol, currentInterval, currentChartType) {
    return {
        currentSymbol: currentSymbol,
        currentInterval: currentInterval,
        currentChartType: currentChartType,
        showPredictionsLSTM: document.getElementById('showLSTM').checked,
        showPredictionsTimeGAN: document.getElementById('showTimeGAN').checked,
        showTrades: document.getElementById('showTrades').checked,
        showSimulation1: document.getElementById('showSimulation1').checked,
        showSimulation2: document.getElementById('showSimulation2').checked,
        showSimulation3: document.getElementById('showSimulation3').checked,
        showEMA: document.getElementById('showEMA').checked,
        showPSAR: document.getElementById('showPSAR').checked,
        showSMA: document.getElementById('showSMA').checked,
        showRSI: document.getElementById('showRSI').checked,
        showMACD: document.getElementById('showMACD').checked,
        showStochastic: document.getElementById('showStochastic').checked,  
        showOBV: document.getElementById('showOBV').checked,
        showAD: document.getElementById('showAD').checked,
        showADX: document.getElementById('showADX').checked,
        showATR: document.getElementById('showATR').checked,
        showPivot: document.getElementById('showPivot').checked,
        showFibonacci: document.getElementById('showFibonacci').checked,
        showBollinger: document.getElementById('showBollinger').checked,
        strategy1Active: document.querySelector('.toggle-strategy[data-target="strategy1"]').classList.contains('btn-active'),
        strategy2Active: document.querySelector('.toggle-strategy[data-target="strategy2"]').classList.contains('btn-active'),
        strategy3Active: document.querySelector('.toggle-strategy[data-target="strategy3"]').classList.contains('btn-active'),
        colors: {
            candleDown: '#ff0000', // Rojo brillante
            candleUp: '#00ff00', // Verde neón
            line: '#00ffff', // Cyan brillante
            volume: '#ff00ff', // Magenta brillante
            volume_buy: '#00ff00', // Verde neón
            volume_sell: '#ff0000', // Rojo brillante
            balance: '#ffff00', // Amarillo brillante
            strategy1Balance: '#00ff00', // Verde para balance estrategia 1
            strategy2Balance: '#ff1493', // Rosa para balance estrategia 2
            strategy3Balance: '#4169e1', // Azul real para balance estrategia 3
            prediction: '#39ff14', // Verde lima neón
            predictionLSTM: '#1aff1a', // Verde fluorescente      
            predictionTimeGAN: '#ff1493', // Rosa profundo   
            predictionBand: 'rgba(57, 255, 20, 0.1)',
            tradeBuy: '#7fff00', // Verde chartreuse
            tradeSell: '#ff4500', // Rojo naranja
            simulation1Buy: '#00ffff', // Cyan para compras simuladas
            simulation1Sell: '#ff69b4', // Rosa para ventas simuladas
            simulation2Buy: '#ffd700', // Dorado para compras simuladas 2
            simulation2Sell: '#9370db', // Púrpura medio para ventas simuladas 2
            simulation3Buy: '#98fb98', // Verde pálido para compras simuladas 3
            simulation3Sell: '#dda0dd', // Ciruela para ventas simuladas 3
            movingAverage: '#ff8c00', // Naranja oscuro
            rsi: '#ff69b4', // Rosa caliente
            macd: '#00bfff', // Azul cielo profundo
            bollinger: '#9400d3', // Violeta oscuro
            momentum: '#ff1493', // Rosa profundo
            ema: '#ffa500', // Naranja
            sma: '#32cd32', // Verde lima
            psar: '#4169e1', // Azul real
            stochastic: '#ff6347', // Tomate
            obv: '#87ceeb', // Azul cielo
            ad: '#dda0dd', // Ciruela
            adx: '#20b2aa', // Verde mar claro
            atr: '#f0e68c', // Caqui
            pivot: '#48d1cc', // Turquesa medio
            fibonacci: '#ffd700' // Oro
        },
        layout: {
            backgroundColor: '#1a1a1a', // Negro muy oscuro
            textColor: '#00ff00', // Verde neón para el texto
            gridColor: '#333333', // Gris muy oscuro
            height: 800,
            domains: {
                price: [0.3, 1],
                volume: [0, 0.2],
                balance: [0, 0.2],
                rsi: [0.2, 0.3],
                macd: [0.1, 0.2],
                momentum: [0.1, 0.2]
            },
            predictions: {
                opacity: 0.8,
                lineWidth: 2,
                bandOpacity: 0.2,
                showConfidenceBands: true,
                confidenceInterval: 0.95
            }
        }
    };
}