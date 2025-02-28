// Asegúrate de que fft.js esté disponible



// Calcula las Bandas de Bollinger, que son indicadores de volatilidad que crean bandas superior e inferior 
// alrededor de una media móvil, útiles para identificar sobrecompra/sobreventa
export function calculateBollingerBands(prices, period = 20, stdDev = 2) {
    // Calcular media móvil
    const sma = prices.map((_, i) => {
        if (i < period - 1) return null;
        const slice = prices.slice(i - period + 1, i + 1);
        return slice.reduce((a, b) => a + b) / period;
    });

    // Calcular desviación estándar
    const stdDevs = prices.map((_, i) => {
        if (i < period - 1) return null;
        const slice = prices.slice(i - period + 1, i + 1);
        const mean = sma[i];
        const squaredDiffs = slice.map(x => Math.pow(x - mean, 2));
        const variance = squaredDiffs.reduce((a, b) => a + b) / period;
        return Math.sqrt(variance);
    });

    // Calcular bandas superior e inferior
    const upper = sma.map((mean, i) => 
        mean === null ? null : mean + (stdDevs[i] * stdDev)
    );
    const lower = sma.map((mean, i) => 
        mean === null ? null : mean - (stdDevs[i] * stdDev)
    );

    return { upper, lower };
}

// Calcula el Momentum, que mide la velocidad del cambio en los precios
// comparando el precio actual con el precio de n períodos atrás
export function calculateMomentum(prices, period = 10) {
    return prices.map((price, i) => {
        if (i < period) return null;
        return price - prices[i - period];
    });
}

// Calcula la Media Móvil Simple (SMA), que suaviza los datos de precios
// para identificar tendencias
export function calculateMovingAverage(data, period) {
    let movingAverage = [];
    for (let i = 0; i < data.length; i++) {
        if (i < period - 1) {
            movingAverage.push(null);
        } else {
            const sum = data.slice(i - period + 1, i + 1).reduce((a, b) => a + b, 0);
            movingAverage.push(sum / period);
        }
    }
    return movingAverage;
}

// Calcula el Índice de Fuerza Relativa (RSI), un indicador de momentum que mide
// la velocidad y magnitud de los movimientos direccionales de precios
export function calculateRSI(data, period) {
    let rsi = [];
    let gains = 0;
    let losses = 0;
    for (let i = 1; i < data.length; i++) {
        const change = data[i] - data[i - 1];
        if (change > 0) {
            gains += change;
        } else {
            losses -= change;
        }
        if (i >= period) {
            const avgGain = gains / period;
            const avgLoss = losses / period;
            const rs = avgGain / avgLoss;
            rsi.push(100 - (100 / (1 + rs)));
            gains = 0;
            losses = 0;
        } else {
            rsi.push(null);
        }
    }
    return rsi;
}

// Calcula el MACD (Moving Average Convergence Divergence), que muestra la relación
// entre dos medias móviles exponenciales de diferentes períodos
export function calculateMACD(data, shortPeriod = 12, longPeriod = 26, signalPeriod = 9) {
    const shortEMA = calculateEMA(data, shortPeriod);
    const longEMA = calculateEMA(data, longPeriod);
    const macd = shortEMA.map((val, index) => val - longEMA[index]);
    const signal = calculateEMA(macd, signalPeriod);
    return { macd, signal };
}

// Calcula la Media Móvil Exponencial (EMA), que da más peso a los datos recientes
// que a los datos antiguos
export function calculateEMA(data, period) {
    const k = 2 / (period + 1);
    let emaArray = [data[0]];
    for (let i = 1; i < data.length; i++) {
        emaArray.push(data[i] * k + emaArray[i - 1] * (1 - k));
    }
    return emaArray;
}

// Calcula el Oscilador Estocástico, que compara el precio de cierre actual
// con el rango de precios durante un período específico
export function calculateStochastic(high, low, close, period, smoothK) {
    let k = [];
    let d = [];
    
    for (let i = 0; i < close.length; i++) {
        if (i < period - 1) {
            k.push(null);
            continue;
        }
        
        const highSlice = high.slice(i - period + 1, i + 1);
        const lowSlice = low.slice(i - period + 1, i + 1);
        const highestHigh = Math.max(...highSlice);
        const lowestLow = Math.min(...lowSlice);
        
        const currentK = ((close[i] - lowestLow) / (highestHigh - lowestLow)) * 100;
        k.push(currentK);
    }
    
    // Calcular %D como SMA de %K
    d = calculateMovingAverage(k.filter(x => x !== null), smoothK);
    
    return { k, d };
}

// Calcula el Balance de Volumen (OBV), que relaciona el volumen con los cambios
// de precio para confirmar tendencias
export function calculateOBV(close, volume) {
    let obv = [0];
    for (let i = 1; i < close.length; i++) {
        if (close[i] > close[i - 1]) {
            obv.push(obv[i - 1] + volume[i]);
        } else if (close[i] < close[i - 1]) {
            obv.push(obv[i - 1] - volume[i]);
        } else {
            obv.push(obv[i - 1]);
        }
    }
    return obv;
}

// Calcula el Índice Direccional Medio (ADX), que mide la fuerza de una tendencia
// independientemente de su dirección
export function calculateADX(high, low, close, period) {
    let tr = [0];
    let plusDM = [0];
    let minusDM = [0];
    
    // Calcular TR y DM
    for (let i = 1; i < close.length; i++) {
        tr.push(Math.max(
            high[i] - low[i],
            Math.abs(high[i] - close[i - 1]),
            Math.abs(low[i] - close[i - 1])
        ));
        
        plusDM.push(high[i] - high[i - 1] > low[i - 1] - low[i] ?
            Math.max(high[i] - high[i - 1], 0) : 0);
        
        minusDM.push(low[i - 1] - low[i] > high[i] - high[i - 1] ?
            Math.max(low[i - 1] - low[i], 0) : 0);
    }
    
    // Calcular medias móviles suavizadas
    const trMA = calculateEMA(tr, period);
    const plusDMMA = calculateEMA(plusDM, period);
    const minusDMMA = calculateEMA(minusDM, period);
    
    // Calcular DI
    const plusDI = plusDMMA.map((val, i) => (val / trMA[i]) * 100);
    const minusDI = minusDMMA.map((val, i) => (val / trMA[i]) * 100);
    
    // Calcular DX y ADX
    const dx = plusDI.map((val, i) => 
        Math.abs(plusDI[i] - minusDI[i]) / (plusDI[i] + minusDI[i]) * 100
    );
    
    return calculateEMA(dx, period);
}

// Calcula el Rango Verdadero Medio (ATR), que mide la volatilidad del mercado
export function calculateATR(high, low, close, period) {
    let tr = [high[0] - low[0]];
    
    for (let i = 1; i < close.length; i++) {
        tr.push(Math.max(
            high[i] - low[i],
            Math.abs(high[i] - close[i - 1]),
            Math.abs(low[i] - close[i - 1])
        ));
    }
    
    return calculateEMA(tr, period);
}

// Calcula los Puntos Pivot, niveles de soporte y resistencia basados en los
// precios alto, bajo y de cierre del período anterior
export function calculatePivotPoints(high, low, close) {
    const pp = close.map((c, i) => (high[i] + low[i] + c) / 3);
    return { pp };
}

// Calcula los niveles de Fibonacci, utilizados para identificar posibles
// niveles de soporte, resistencia y objetivos de precio
export function calculateFibonacciLevels(high, low) {
    const diff = Math.max(...high) - Math.min(...low);
    return {
        '0': Math.min(...low),
        '0.236': Math.min(...low) + diff * 0.236,
        '0.382': Math.min(...low) + diff * 0.382,
        '0.5': Math.min(...low) + diff * 0.5,
        '0.618': Math.min(...low) + diff * 0.618,
        '0.786': Math.min(...low) + diff * 0.786,
        '1': Math.max(...high)
    };
}