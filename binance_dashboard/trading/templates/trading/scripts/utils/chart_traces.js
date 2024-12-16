import { calculateBollingerBands, calculateMomentum, calculateRSI, calculateMACD, calculateEMA, calculateStochastic, calculateATR, calculateADX, calculateOBV, calculatePivotPoints, calculateFibonacciLevels, calculateMovingAverage } from '/static/scripts/utils/tecnical_indicators.js';

        // Función para crear trace de balance para una estrategia
export function createStrategyBalanceTrace(balanceChartData, filteredData, name, color) {
            if (filteredData.length > 0) {
                const trace = {
                    x: filteredData.map(item => item.timestamp),
                    y: filteredData.map(item => item.total_balance_usd),
                    type: 'scatter',
                    mode: 'lines', 
                    name: name,
                    line: {
                        color: color,
                        width: 2
                    }
                };
                balanceChartData.push(trace);
                return trace;
            }
            return null;
        }

export async function addPredictionTraces(chartConfig, minTime, traces) {
            if (chartConfig.showPredictionsLSTM) {
                // Obtener predicciones LSTM
                const predResponse = await fetch(`/get_predictions/${chartConfig.currentSymbol}/${chartConfig.currentInterval}/`);
                const predData = await predResponse.json();

                const predictions = (predData.predictions || []).filter(p => {
                    //console.log(p);
                    const timestamp = new Date(p.timestamp).getTime();
                    return timestamp >= minTime;
                });
                //console.log(predictions);
                
                if (predictions.length > 0) {
                    traces.push({
                        x: predictions.map(p => p.timestamp),
                        y: predictions.map(p => p.value),
                        type: 'scatter',
                        mode: 'lines+markers', 
                        name: 'Predicción LSTM',
                        line: {
                            color: chartConfig.colors.prediction,
                            dash: 'dot'
                        },
                        marker: {
                            color: chartConfig.colors.prediction
                        },
                        yaxis: 'y1'
                    });
                }
            }

            if (chartConfig.showPredictionsTimeGAN) {
                // Obtener predicciones TimeGAN
                const predResponseTimeGAN = await fetch(`/get_predictions/${chartConfig.currentSymbol}/${chartConfig.currentInterval}/`);
                const predDataTimeGAN = await predResponseTimeGAN.json();

                const predictionsTimeGAN = (predDataTimeGAN.predictions || []).filter(p => {
                    //console.log(p);
                    const timestamp = new Date(p.timestamp).getTime();
                    return timestamp >= minTime;
                });
                
                if (predictionsTimeGAN.length > 0) {
                    traces.push({
                        x: predictionsTimeGAN.map(p => p.timestamp),
                        y: predictionsTimeGAN.map(p => p.value),
                        type: 'scatter',
                        mode: 'lines+markers',
                        name: 'Predicción TimeGAN',
                        line: {
                            color: chartConfig.colors.predictionTimeGAN,
                            dash: 'dot'
                        },
                        marker: {
                            color: chartConfig.colors.predictionTimeGAN
                        },
                        yaxis: 'y1'
                    });
                }
            }
            //console.log(traces);
        }


export function addIndicatorTraces(chartConfig, data, traces) {
            // Agregar EMA
            if (chartConfig.showEMA) {
                const ema = calculateEMA(data.close, 20);
                traces.push({
                    x: data.timestamps_local,
                    y: ema,
                    type: 'scatter',
                    mode: 'lines', 
                    name: 'EMA',
                    line: {
                        color: chartConfig.colors.ema,
                        width: 2
                    },
                    yaxis: 'y1'
                });
            }

            // Agregar SMA
            if (chartConfig.showSMA) {
                const sma = calculateMovingAverage(data.close, 20);
                traces.push({
                    x: data.timestamps_local,
                    y: sma,
                    type: 'scatter',
                    mode: 'lines',
                    name: 'SMA',
                    line: {
                        color: chartConfig.colors.sma,
                        width: 2
                    },
                    yaxis: 'y1'
                });
            }

            // Agregar Stochastic
            if (chartConfig.showStochastic) {
                const stoch = calculateStochastic(data.high, data.low, data.close, 14, 3);
                traces.push({
                    x: data.timestamps_local,
                    y: stoch.k,
                    type: 'scatter',
                    mode: 'lines',
                    name: 'Stochastic %K',
                    line: {
                        color: chartConfig.colors.stochastic,
                        width: 2
                    },
                    yaxis: 'y4'
                },
                {
                    x: data.timestamps_local,
                    y: stoch.d,
                    type: 'scatter', 
                    mode: 'lines',
                    name: 'Stochastic %D',
                    line: {
                        color: chartConfig.colors.stochastic,
                        width: 2,
                        dash: 'dash'
                    },
                    yaxis: 'y4'
                });
            }

            // Agregar OBV
            if (chartConfig.showOBV) {
                const obv = calculateOBV(data.close, data.volume);
                traces.push({
                    x: data.timestamps_local,
                    y: obv,
                    type: 'scatter',
                    mode: 'lines',
                    name: 'OBV',
                    line: {
                        color: chartConfig.colors.obv,
                        width: 2
                    },
                    yaxis: 'y5'
                });
            }

            // Agregar ADX
            if (chartConfig.showADX) {
                const adx = calculateADX(data.high, data.low, data.close, 14);
                traces.push({
                    x: data.timestamps_local,
                    y: adx,
                    type: 'scatter',
                    mode: 'lines',
                    name: 'ADX',
                    line: {
                        color: chartConfig.colors.adx,
                        width: 2
                    },
                    yaxis: 'y4'
                });
            }

            // Agregar ATR
            if (chartConfig.showATR) {
                const atr = calculateATR(data.high, data.low, data.close, 14);
                traces.push({
                    x: data.timestamps_local,
                    y: atr,
                    type: 'scatter',
                    mode: 'lines',
                    name: 'ATR',
                    line: {
                        color: chartConfig.colors.atr,
                        width: 2
                    },
                    yaxis: 'y5'
                });
            }

            // Agregar Pivot Points
            if (chartConfig.showPivot) {
                const pivots = calculatePivotPoints(data.high, data.low, data.close);
                traces.push({
                    x: data.timestamps_local,
                    y: pivots.pp,
                    type: 'scatter',
                    mode: 'lines',
                    name: 'Pivot Point',
                    line: {
                        color: chartConfig.colors.pivot,
                        width: 2
                    },
                    yaxis: 'y1'
                });
            }

            // Agregar Fibonacci
            if (chartConfig.showFibonacci) {
                const fib = calculateFibonacciLevels(data.high, data.low);
                Object.entries(fib).forEach(([level, values]) => {
                    traces.push({
                        x: data.timestamps_local,
                        y: Array(data.timestamps_local.length).fill(values),
                        type: 'scatter',
                        mode: 'lines',
                        name: `Fib ${level}`,
                        line: {
                            color: chartConfig.colors.fibonacci,
                            width: 1,
                            dash: 'dot'
                        },
                        yaxis: 'y1'
                    });
                });
            }

            // Agregar RSI
            if (chartConfig.showRSI) {
                const rsi = calculateRSI(data.close, 14);
                traces.push({
                    x: data.timestamps_local,
                    y: rsi,
                    type: 'scatter',
                    mode: 'lines',
                    name: 'RSI',
                    line: {
                        color: chartConfig.colors.rsi,
                        width: 2
                    },
                    yaxis: 'y4'
                });
            }

            // Agregar MACD
            if (chartConfig.showMACD) {
                const macdData = calculateMACD(data.close);
                traces.push({
                    x: data.timestamps_local,
                    y: macdData.macd,
                    type: 'scatter',
                    mode: 'lines',
                    name: 'MACD',
                    line: {
                        color: chartConfig.colors.macd,
                        width: 2
                    },
                    yaxis: 'y5'
                });
            }

            // Agregar Bollinger Bands
            if (chartConfig.showBollinger) {
                const bollingerBands = calculateBollingerBands(data.close, 20, 2);
                traces.push({
                    x: data.timestamps_local,
                    y: bollingerBands.upper,
                    type: 'scatter',
                    mode: 'lines',
                    name: 'Bollinger Superior',
                    line: {
                        color: chartConfig.colors.bollinger,
                        width: 1,
                        dash: 'dash'
                    },
                    yaxis: 'y1'
                },
                {
                    x: data.timestamps_local,
                    y: bollingerBands.lower,
                    type: 'scatter',
                    mode: 'lines',
                    name: 'Bollinger Inferior',
                    line: {
                        color: chartConfig.colors.bollinger,
                        width: 1,
                        dash: 'dash'
                    },
                    yaxis: 'y1'
                });
            }
        }