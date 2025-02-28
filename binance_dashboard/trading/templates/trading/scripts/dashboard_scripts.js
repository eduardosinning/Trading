import { escapeHtml, getCookie } from '/static/scripts/utils/utils.js';

import { executeStrategy1, executeStrategy2, stopStrategy } from '/static/scripts/utils/execute_strategies.js';

import { getStrategyBalanceData, filterBalanceDataByTimeRange , updateTotalBalance} from '/static/scripts/utils/balances.js';

import { setupMinimizeButtons, restoreSectionStates } from '/static/scripts/utils/max_min_buttons.js';
import { addIndicatorTraces, addPredictionTraces, createStrategyBalanceTrace } from '/static/scripts/utils/chart_traces.js';
import { createTerminalInput } from '/static/scripts/utils/terminal.js';
import { getChartConfig, saveChartConfiguration } from '/static/scripts/utils/chartConfig.js';


/**
 * Calcula las magnitudes de la Transformada de Fourier de un array de precios.
 * @param {number[]} prices - Array de precios de cierre.
 * @returns {number[]} - Array de magnitudes de la Transformada de Fourier.
 */
async function calculateFourierMagnitudes(prices) {
    try {
        console.log("prices: ", prices);
        const response = await fetch('/calculate_fourier/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({ prices: prices })
        });

        const data = await response.json();
        //console.log("data: ", data);
        const sinusoids = data.sinusoids;
        const fundamental_freqs = data.fundamental_freqs;
        //console.log("sinusoids: ", sinusoids);
        //console.log("fundamental_freqs: ", fundamental_freqs);
        return [sinusoids, fundamental_freqs];
    } catch (error) {
        console.error('Error calculating Fourier magnitudes:', error);
        return [];
    }
}

// Variables globales
let editor = ace.edit("editor");
editor.setTheme("ace/theme/monokai");
editor.session.setMode("ace/mode/python");
editor.setOptions({
    fontSize: "12pt",
    enableBasicAutocompletion: true,
    enableSnippets: true,
    enableLiveAutocompletion: true
});

let currentChartType = localStorage.getItem('currentChartType') || 'candlestick';
let currentInterval = localStorage.getItem('currentInterval') || '1m';
let currentSymbol = localStorage.getItem('currentSymbol') || document.getElementById('symbolSelector').value || 'BTCUSDT';
let isBotRunning = localStorage.getItem('isBotRunning') === 'true' || false;

let traces = [];
let chartDataPrompt = '';
let terminalHistory = [];

let historyIndex = -1;


// Funciones del explorador de archivos
function loadFileTree() {
    fetch('/get_file_tree/')
        .then(response => response.json())
        .then(data => {
            const fileTree = document.querySelector('.file-tree');
            fileTree.innerHTML = generateFileTreeHTML(data);
            addFileTreeListeners();
        })
        .catch(error => console.error('Error loading file tree:', error));
}


function generateFileTreeHTML(item, level = 0) {
    if (typeof item === 'string') {
        return `
            <div class="file-tree-item" draggable="true" data-path="${item}">
                <div class="item-content">
                    <i class="fas fa-file-alt"></i> <!-- Cambiado el ícono -->
                    ${item.split('/').pop()}
                </div>
                <button class="delete-btn" title="Eliminar">
                    <i class="fas fa-trash-alt"></i>
                </button>
            </div>
        `;
    }

    let html = '';    
    
    Object.entries(item).forEach(([name, content]) => {
        if (content.type === 'directory') {
            // Asegúrate de que cada directorio tenga un atributo 'path'
            const directoryPath = content.path || name; // Usa 'name' como fallback si 'path' no está definido
            html += `
                <div class="folder">
                    <div class="file-tree-item folder-item" data-path="${directoryPath}">
                        <div class="item-content">
                            <i class="fas fa-folder toggle-folder"></i>
                            ${name}
                        </div>
                        <button class="delete-btn" title="Eliminar">
                            <i class="fas fa-trash-alt"></i>
                        </button>
                    </div>
                    <div class="folder-content" data-folder="${directoryPath}" style="display: none;">
                        ${generateFileTreeHTML(content.content, level + 1)}
                    </div>
                </div>
            `;
        } else if (content.type === 'file') {
            html += `
                <div class="file-tree-item" draggable="true" data-path="${content.path}">
                    <div class="item-content">
                        <i class="fas fa-file-alt"></i>
                        ${name}
                    </div>
                    <button class="delete-btn" title="Eliminar">
                        <i class="fas fa-trash-alt"></i>
                    </button>
                </div>
            `;
        }
    });


    return html;
}
function addFileTreeListeners() {
    document.querySelectorAll('.file-tree-item').forEach(item => {
        const itemContent = item.querySelector('.item-content');
        const deleteBtn = item.querySelector('.delete-btn');

        if (item.querySelector('i').classList.contains('fa-file-alt')) {
            itemContent.addEventListener('click', () => {
                // Cargar archivo en el editor
                fetch(`/get_file_content/?path=${item.dataset.path}`)
                    .then(response => response.text())
                    .then(content => {
                        editor.setValue(content, -1);
                        document.getElementById('currentPath').value = item.dataset.path;
                    })
                    .catch(error => console.error('Error loading file:', error));
            });
        }

        // Listener para el botón de eliminar
        deleteBtn.addEventListener('click', async (e) => {
            e.stopPropagation(); // Evitar que el click se propague al item
            
            if (confirm('¿Estás seguro de que quieres eliminar este elemento?')) {
                try {
                    const response = await fetch('/delete-file-or-folder/', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': getCookie('csrftoken')
                        },
                        body: JSON.stringify({
                            path: item.dataset.path
                        })
                    });
                    
                    const data = await response.json();
                    if (data.success) {
                        loadFileTree();
                        // Si el archivo eliminado es el actual en el editor, limpiar el editor
                        if (document.getElementById('currentPath').value === item.dataset.path) {
                            editor.setValue('');
                            document.getElementById('currentPath').value = '';
                        }
                    } else {
                        alert('Error al eliminar: ' + data.error);
                    }
                } catch (error) {
                    console.error('Error:', error);
                    alert('Error al eliminar el elemento');
                }
            }
        });

        // Drag start
        item.addEventListener('dragstart', (e) => {
            e.dataTransfer.setData('text/plain', e.target.dataset.path);
            e.target.classList.add('dragging');
        });

        // Drag end
        item.addEventListener('dragend', (e) => {
            e.target.classList.remove('dragging');
        });

        // Agregar listener para clic derecho
        item.addEventListener('contextmenu', (e) => {
            showContextMenu(e, item);
        });
    });

    // Listeners para folders
    document.querySelectorAll('.folder-content').forEach(folder => {
        folder.addEventListener('dragover', (e) => {
            e.preventDefault();
            e.currentTarget.classList.add('drag-over');
        });

        folder.addEventListener('dragleave', (e) => {
            e.currentTarget.classList.remove('drag-over');
        });

        folder.addEventListener('drop', async (e) => {
            e.preventDefault();
            e.currentTarget.classList.remove('drag-over');
            
            const sourcePath = e.dataTransfer.getData('text/plain');
            const targetPath = e.currentTarget.dataset.folder;
            try {
                const response = await fetch('/move-file/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken')
                    },
                    body: JSON.stringify({
                        sourcePath: sourcePath,
                        targetPath: targetPath
                    })
                });

                const data = await response.json();
                if (data.success) {
                    loadFileTree(); // Recargar el árbol de archivos
                } else {
                    alert('Error moving file: ' + data.error);
                }
            } catch (error) {
                console.error('Error:', error);
                alert('Error moving file');
            }
        });
    });

    // Agregar listener para expandir/colapsar carpetas
    document.querySelectorAll('.toggle-folder').forEach(icon => {
        icon.addEventListener('click', (e) => {
            e.stopPropagation();
            const folderContent = icon.closest('.folder').querySelector('.folder-content');
            if (folderContent.style.display === 'none') {
                folderContent.style.display = 'block';
                icon.classList.remove('fa-folder');
                icon.classList.add('fa-folder-open');
            } else {
                folderContent.style.display = 'none';
                icon.classList.remove('fa-folder-open');
                icon.classList.add('fa-folder');
            }
        });
    });
}


        
function showContextMenu(e, item) {
    e.preventDefault();
    
    // Eliminar menú contextual existente si hay uno
    const existingMenu = document.querySelector('.context-menu');
    if (existingMenu) {
        existingMenu.remove();
    }
    
    // Crear nuevo menú contextual
    const contextMenu = document.createElement('div');
    contextMenu.className = 'context-menu';
    contextMenu.style.position = 'fixed';
    contextMenu.style.left = `${e.pageX}px`;
    contextMenu.style.top = `${e.pageY}px`;
    
    const deleteButton = document.createElement('div');
    deleteButton.className = 'context-menu-item';
    deleteButton.innerHTML = '<i class="fas fa-trash-alt"></i> Eliminar';
    deleteButton.onclick = async () => {
        if (confirm('¿Estás seguro de que quieres eliminar este elemento?')) {
            try {
                const response = await fetch('/delete-file-or-folder/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken')
                    },
                    body: JSON.stringify({
                        path: item.dataset.path
                    })
                });
                
                const data = await response.json();
                if (data.success) {
                    loadFileTree();
                    // Si el archivo eliminado es el actual en el editor, limpiar el editor
                    if (document.getElementById('currentPath').value === item.dataset.path) {
                        editor.setValue('');
                        document.getElementById('currentPath').value = '';
                    }
                } else {
                    alert('Error al eliminar: ' + data.error);
                }
            } catch (error) {
                console.error('Error:', error);
                alert('Error al eliminar el elemento');
            }
        }
        contextMenu.remove();
    };
    
    contextMenu.appendChild(deleteButton);
    document.body.appendChild(contextMenu);
    
    // Cerrar menú al hacer clic fuera
    document.addEventListener('click', function closeMenu(e) {
        if (!contextMenu.contains(e.target)) {
            contextMenu.remove();
            document.removeEventListener('click', closeMenu);
        }
    });
}



// Funciones del terminal
function updateBotOutput() {
    if (!isBotRunning) return;

    fetch('/get_bot_output/')
        .then(response => response.text())
        .then(data => {
            const terminal = document.getElementById('botOutput');
            // Mantener el input al final
            const inputLine = terminal.querySelector('.terminal-input-line');
            terminal.innerHTML = data;
            if (inputLine) {
                terminal.appendChild(inputLine);
            }
            if (terminal.scrollHeight - terminal.scrollTop <= terminal.clientHeight + 100) {
                terminal.scrollTop = terminal.scrollHeight;
            }
        })
        .catch(error => {
            console.error('Error updating bot output:', error);
            clearInterval(window.botOutputInterval);
            updateRunButton(false);
        });
}


// Funciones del gráfico
async function updateChart() {
    try {
        const chartConfig = getChartConfig(currentSymbol, currentInterval, currentChartType);
        const limit = document.getElementById('limitInput').value || 100;
        
        const [response, saveConfigResult] = await Promise.all([
            fetch(`/get_klines/${chartConfig.currentSymbol}/${chartConfig.currentInterval}/${limit}`),
            saveChartConfiguration(chartConfig)
        ]);
        const data = await response.json();
        
        let minTime, maxTime;
        if (data && data.timestamps_local && data.timestamps_local.length > 0) {
            const dates = data.timestamps_local.map(timestamp => new Date(timestamp));
            dates.sort((a, b) => a - b);
            minTime = dates[0];
            maxTime = dates[dates.length - 1];
        }

        const trace1 = {
            x: data.timestamps_local,
            y: currentChartType === 'line' ? data.close : undefined,
            close: currentChartType === 'candlestick' ? data.close : undefined,
            decreasing: currentChartType === 'candlestick' ? {line: {color: chartConfig.colors.candleDown}} : undefined,
            increasing: currentChartType === 'candlestick' ? {line: {color: chartConfig.colors.candleUp}} : undefined,
            line: currentChartType === 'line' ? {color: chartConfig.colors.line} : {color: chartConfig.colors.line},
            type: currentChartType === 'candlestick' ? 'candlestick' : 'scatter',
            mode: currentChartType === 'line' ? 'lines' : undefined,
            name: 'Precio',
            xaxis: 'x',
            yaxis: 'y1'
        };
        
        if (currentChartType === 'candlestick') {
            trace1.high = data.high;
            trace1.low = data.low;
            trace1.open = data.open;
        }
        
        const traceVolume = {
            x: data.timestamps_local,
            y: data.volume,
            type: 'bar',
            name: 'Volumen',
            marker: {
                color: chartConfig.colors.volume
            },
            yaxis: 'y2'
        };

        const traceVolume_buy = {
            x: data.timestamps_local,
            y: data.taker_buy_base_asset_volume,
            type: 'bar',
            name: 'Volumen Compras',
            marker: {
                color: chartConfig.colors.volume_buy
            },
            yaxis: 'y2'
        };

        // Calcular las magnitudes de Fourier
        async function createFourierTraces(data, traces) {
            const selectedWave = document.getElementById('waveSelector').value;
            const selectedSeries = document.getElementById('timeSeriesSelector').value;
            //console.log("selectedSeries: ", selectedSeries);
            const selectedData = data[selectedSeries];
            //console.log("selectedData: ", selectedData);
            const result = await calculateFourierMagnitudes(selectedData);
            const sinusoids = result[0];
            const fundamental_freqs = result[1];
            //console.log("sinusoids: ", sinusoids);
            //console.log("fundamental_freqs: ", fundamental_freqs);

            if (selectedWave === 'wave') {
                // Agregar trazas de sinusoides de Fourier
                const traceFourier1 = {
                    x: data.timestamps_local,
                    y: sinusoids[0],
                    type: 'scatter',
                    mode: 'lines',
                    name: 'Sinusoide 1',
                    line: {
                        color: chartConfig.colors.fourier1 || '#ff7f0e'
                    },
                    yaxis: 'y3'
                };

                const traceFourier2 = {
                    x: data.timestamps_local,
                    y: sinusoids[1],
                    type: 'scatter',
                    mode: 'lines',
                    name: 'Sinusoide 2',
                    line: {
                        color: chartConfig.colors.fourier2 || '#2ca02c'
                    },
                    yaxis: 'y3'
                };

                const traceFourier3 = {
                    x: data.timestamps_local,
                    y: sinusoids[2],
                    type: 'scatter',
                    mode: 'lines',
                    name: 'Sinusoide 3',
                    line: {
                        color: chartConfig.colors.fourier3 || '#1f77b4'
                    },
                    yaxis: 'y3'
                };

                traces.push(traceFourier1);
                traces.push(traceFourier2); 
                traces.push(traceFourier3);
            } else if (selectedWave === 'limits') {
                // Calcular el punto medio vertical
                const midPoint = Math.max(...selectedData) / 2;

                // Definir colores para los límites
                const num_limits = document.getElementById('fourierValue').value;
                const limitColors = Array.from({length: num_limits}, (_, i) => {
                    const hue = (i * 360 / num_limits);
                    return `hsl(${hue}, 100%, 50%)`;
                });
                
                // Ordenar índices de mayor a menor
                const sorted_indices = [...fundamental_freqs].sort((a, b) => b - a);
                
                // Generar secuencia Fibonacci hasta num_limits
                const fibonacci = [1, 1];
                for(let i = 2; i < num_limits; i++) {
                    fibonacci[i] = fibonacci[i-1] + fibonacci[i-2];
                }
                
                // Tomar elementos en posiciones Fibonacci
                const fundamental_freqs2 = fibonacci.slice(3, 3+num_limits).map(pos => sorted_indices[pos-1]);
                console.log("fibonacci: ", fibonacci);
                console.log("length: ", fibonacci.length);
                console.log("fundamental_freqs (posiciones Fibonacci): ", fundamental_freqs2);

                // Crear líneas horizontales para cada magnitud
                for (let i = 0; i < 3+num_limits; i++) {
                    const magnitude = fundamental_freqs2[i];
                    
                    // Línea superior
                    const upperTrace = {
                        x: data.timestamps_local,
                        y: Array(data.timestamps_local.length).fill(midPoint + magnitude),
                        type: 'scatter',
                        mode: 'lines',
                        name: `Límite Superior ${i+1}`,
                        line: {
                            color: limitColors[i],
                            dash: 'dash'
                        },
                        yaxis: 'y3'
                    };

                    // Línea inferior
                    const lowerTrace = {
                        x: data.timestamps_local,
                        y: Array(data.timestamps_local.length).fill(midPoint - magnitude),
                        type: 'scatter',
                        mode: 'lines',
                        name: `Límite Inferior ${i+1}`,
                        line: {
                            color: limitColors[i],
                            dash: 'dash'
                        },
                        yaxis: 'y3'
                    };

                    traces.push(upperTrace);
                    traces.push(lowerTrace);
                }
            }
        }

        traces = [trace1, traceVolume, traceVolume_buy];
        
        await Promise.all([
            addRealTradeSimulation(chartConfig, minTime, maxTime, traces),
            addSimulationTradesTraces(chartConfig, minTime, maxTime, traces),
            addPredictionTraces(chartConfig, minTime, traces)
        ]);

        addIndicatorTraces(chartConfig, data, traces);
        if (document.getElementById('showFourier').checked) {
            await createFourierTraces(data, traces);
        }

        const layout = {
            plot_bgcolor: chartConfig.layout.backgroundColor,
            paper_bgcolor: chartConfig.layout.backgroundColor,
            title: {
                text: `Intervalo: ${currentInterval}`,
                font: {
                    color: chartConfig.layout.textColor,
                    size: 16
                },
                y: 0.9
            },
            xaxis: {
                gridcolor: chartConfig.layout.gridColor,
                title: 'Tiempo',
                color: chartConfig.layout.textColor,
                domain: [0, 1]
            },
            yaxis: {
                gridcolor: chartConfig.layout.gridColor,
                title: 'Precio',
                color: chartConfig.layout.textColor,
                domain: chartConfig.layout.domains.price,
                side: 'left'
            },
            yaxis2: {
                title: 'Volumen',
                color: chartConfig.layout.textColor,
                domain: chartConfig.layout.domains.volume,
                side: 'right',
                showgrid: true
            },
            yaxis3: { // Definir un nuevo eje para las magnitudes de Fourier
                title: 'Fourier',
                color: chartConfig.layout.textColor,
                domain: [0.7, 1], // Ajusta el dominio según sea necesario
                side: 'right',
                overlaying: 'y'
            },
            yaxis4: {
                title: 'Osciladores',
                color: chartConfig.layout.textColor,
                domain: chartConfig.layout.domains.rsi,
                side: 'left',
                overlaying: 'y'
            },
            yaxis5: {
                title: 'Indicadores',
                color: chartConfig.layout.textColor,
                domain: chartConfig.layout.domains.macd,
                side: 'right',
                overlaying: 'y'
            },
            legend: {
                x: 0,
                y: 1,
                orientation: 'h',
                xanchor: 'left',
                yanchor: 'bottom',
                font: {color: chartConfig.layout.textColor}
            },
            height: chartConfig.layout.height,
            margin: {
                t: 70,
                b: 50
            }
        };

        await Plotly.newPlot('priceChart', traces, layout, {displayModeBar: false});

        // Obtener datos de balance y esperar a que se completen todas las solicitudes
        const [balanceResponse, strategyBalanceData] = await Promise.all([
            fetch('/get_trading_history/'),
            getStrategyBalanceData()
        ]);

        const balanceData = await balanceResponse.json();
        const filteredBalanceData = filterBalanceDataByTimeRange(balanceData, minTime, maxTime);

        const traceBalance = {
            x: filteredBalanceData.map(item => item.timestamp),
            y: filteredBalanceData.map(item => item.total_balance_usd),
            type: 'scatter',
            mode: 'lines',
            name: 'Balance Real',
            line: {
                color: chartConfig.colors.balance,
                width: 2
            }
        };

        const balanceChartData = [traceBalance];
        const balanceLayout = {
            title: 'Histórico de Balance',
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0)',
            font: {
                color: '#ffffff'
            },
            xaxis: {
                title: 'Fecha',
                gridcolor: '#444444'
            },
            yaxis: {
                title: 'Balance (USD)',
                gridcolor: '#444444'
            },
            showlegend: true,
            legend: {
                x: 0,
                y: 1,
                orientation: 'h',
                bgcolor: 'rgba(0,0,0,0)'
            }
        };

        await Plotly.newPlot('balanceChart', balanceChartData, balanceLayout, {displayModeBar: false});

        // Agregar líneas de balance de estrategias y actualizar gráfico
        addStrategyBalanceLines(chartConfig, balanceChartData, 
            strategyBalanceData.strategy1BalanceData,
            strategyBalanceData.strategy2BalanceData, 
            strategyBalanceData.strategy3BalanceData,
            minTime, maxTime);

        await Plotly.redraw('balanceChart');
        const numPoints = 25;


        
        // Agregar event listener para el botón de extracción
        document.getElementById('extractDataButton').onclick = function() {

            console.log('Extrayendo datos para el prompt');
            // Extraer datos para el prompt
            chartDataPrompt = extractChartDataPrompt(traces, data, chartConfig, numPoints);
            console.log('Prompt generado:', chartDataPrompt);
            addMessage(chartDataPrompt, true);
            //chartDataPrompt = '';
            //addMessage(chartDataPrompt, true);
        };

    } catch (error) {
        console.error('Error updating chart:', error);
    }
}

// Función para extraer datos del gráfico y generar prompt
function extractChartDataPrompt(traces, data, chartConfig, numPoints) {
    // Obtener la cantidad de puntos del input
    let prompt = `Análisis del mercado para ${chartConfig.currentSymbol} en intervalo ${chartConfig.currentInterval}:\n\n`;
    
    // Datos de precio
    prompt += `Precios (últimos ${numPoints} puntos):\n`;
    prompt += `Timestamps: ${data.timestamps_local.slice(-numPoints).join(', ')}\n`;
    prompt += `Open: ${data.open.slice(-numPoints).join(', ')}\n`;
    prompt += `High: ${data.high.slice(-numPoints).join(', ')}\n`;
    prompt += `Low: ${data.low.slice(-numPoints).join(', ')}\n`;
    prompt += `Close: ${data.close.slice(-numPoints).join(', ')}\n\n`;

    // Datos de volumen
    prompt += `Volumen (últimos ${numPoints} puntos):\n`;
    prompt += `Total: ${data.volume.slice(-numPoints).join(', ')}\n`;
    prompt += `Compras: ${data.taker_buy_base_asset_volume.slice(-numPoints).join(', ')}\n\n`;

    // Indicadores técnicos activos y sus valores
    let hasActiveIndicators = false;
    let indicatorsPrompt = '';
    
    traces.forEach(trace => {
        if (trace.name) {
            if (chartConfig.showRSI && trace.name.includes('RSI')) {
                indicatorsPrompt += `RSI: ${trace.y.slice(-numPoints).join(', ')}\n`;
                hasActiveIndicators = true;
            }
            if (chartConfig.showMACD) {
                if (trace.name === 'MACD') {
                    indicatorsPrompt += `MACD: ${trace.y.slice(-numPoints).join(', ')}\n`;
                    hasActiveIndicators = true;
                }
            }
            if (chartConfig.showBollinger) {
                if (trace.name === 'Bollinger Superior') {
                    indicatorsPrompt += `Bollinger Superior: ${trace.y.slice(-numPoints).join(', ')}\n`;
                    hasActiveIndicators = true;
                }
                if (trace.name === 'Bollinger Inferior') {
                    indicatorsPrompt += `Bollinger Inferior: ${trace.y.slice(-numPoints).join(', ')}\n`;
                    hasActiveIndicators = true;
                }
            }
            if (chartConfig.showEMA && trace.name.includes('EMA')) {
                indicatorsPrompt += `EMA: ${trace.y.slice(-numPoints).join(', ')}\n`;
                hasActiveIndicators = true;
            }
            if (chartConfig.showSMA && trace.name.includes('SMA')) {
                indicatorsPrompt += `SMA: ${trace.y.slice(-numPoints).join(', ')}\n`;
                hasActiveIndicators = true;
            }
            if (chartConfig.showOBV && trace.name === 'OBV') {
                indicatorsPrompt += `OBV: ${trace.y.slice(-numPoints).join(', ')}\n`;
                hasActiveIndicators = true;
            }
            if (chartConfig.showADX && trace.name === 'ADX') {
                indicatorsPrompt += `ADX: ${trace.y.slice(-numPoints).join(', ')}\n`;
                hasActiveIndicators = true;
            }
            if (chartConfig.showATR && trace.name === 'ATR') {
                indicatorsPrompt += `ATR: ${trace.y.slice(-numPoints).join(', ')}\n`;
                hasActiveIndicators = true;
            }
            if (chartConfig.showPivot && trace.name === 'Pivot Point') {
                indicatorsPrompt += `${trace.name}: ${trace.y.slice(-numPoints).join(', ')}\n`;
                hasActiveIndicators = true;
            }
        }
    });

    if (hasActiveIndicators) {
        prompt += `Indicadores activos y sus valores (últimos ${numPoints} puntos):\n`;
        prompt += indicatorsPrompt;
    }
    
    // Predicciones activas
    const prediccionesActivas = [];
    if (chartConfig.showPredictionsLSTM) {
        traces.forEach(trace => {
            if (trace.name === 'Predicción LSTM') {
                prediccionesActivas.push({
                    nombre: 'LSTM',
                    valores: trace.y.slice(-numPoints).join(', ')
                });
            }
        });
    }
    if (chartConfig.showPredictionsTimeGAN) {
        traces.forEach(trace => {
            if (trace.name === 'Predicción TimeGAN') {
                prediccionesActivas.push({
                    nombre: 'TimeGAN', 
                    valores: trace.y.slice(-numPoints).join(', ')
                });
            }
        });
    }

    if (prediccionesActivas.length > 0) {
        prompt += `\nPredicciones activas y sus valores (últimos ${numPoints} puntos):\n`;
        prediccionesActivas.forEach(prediccion => {
            prompt += `- ${prediccion.nombre}: ${prediccion.valores}\n`;
        });
    }

    return prompt;
}


// Función para agregar líneas de balance de estrategias
function addStrategyBalanceLines(chartConfig, balanceChartData, strategy1BalanceData, strategy2BalanceData, strategy3BalanceData, minTime, maxTime) {
            if (chartConfig.strategy1Active) {
                const filteredStrategy1BalanceData = filterBalanceDataByTimeRange(strategy1BalanceData, minTime, maxTime);
                createStrategyBalanceTrace(balanceChartData,
                    filteredStrategy1BalanceData,
                    'Balance Estrategia 1',
                    chartConfig.colors.strategy1Balance
                );
            }

            if (chartConfig.strategy2Active) {
                const filteredStrategy2BalanceData = filterBalanceDataByTimeRange(strategy2BalanceData, minTime, maxTime);
                createStrategyBalanceTrace(balanceChartData,
                    filteredStrategy2BalanceData, 
                    'Balance Estrategia 2',
                    chartConfig.colors.strategy2Balance
                );
            }

            if (chartConfig.strategy3Active) {
                const filteredStrategy3BalanceData = filterBalanceDataByTimeRange(strategy3BalanceData, minTime, maxTime);
                createStrategyBalanceTrace(balanceChartData,
                    filteredStrategy3BalanceData,
                    'Balance Estrategia 3', 
                    chartConfig.colors.strategy3Balance
                );
            }
        }

async function addRealTradeSimulation(chartConfig, minTime,maxTime, traces) {
    if (chartConfig.showTrades) {
        // Obtener transacciones si el checkbox está marcado
        let tradesData = [];
        const type_transaccion = 'real';
        const tradesResponse = await fetch(`/get_trades/${chartConfig.currentSymbol}/${type_transaccion}/`);
        tradesData = await tradesResponse.json();

        // Filtrar trades dentro del rango de tiempo visible
        const filteredTrades = tradesData.filter(trade => {
            const tradeTime = new Date(trade.time);
            return tradeTime >= minTime && tradeTime <= maxTime;
        });

        const buyTrades = filteredTrades.filter(trade => trade.isBuyer === true);
        const sellTrades = filteredTrades.filter(trade => trade.isBuyer === false);

        if (buyTrades.length > 0) {
            const traceBuys = {
                x: buyTrades.map(trade => trade.time),
                y: buyTrades.map(trade => trade.price),
                type: 'scatter',
                mode: 'markers+text',
                name: 'Compras',
                text: buyTrades.map(trade => `▲<br>Cantidad: ${trade.qty}<br>Precio: $${trade.price}<br>Total: $${(trade.qty * trade.price).toFixed(2)}`),
                textposition: 'bottom center',
                marker: {
                    color: chartConfig.colors.tradeBuy,
                    size: 16,
                    symbol: 'triangle-up'
                },
                yaxis: 'y1'
            };
            traces.push(traceBuys);
        }

        if (sellTrades.length > 0) {
            const traceSells = {
                x: sellTrades.map(trade => trade.time),
                y: sellTrades.map(trade => trade.price),
                type: 'scatter',
                mode: 'markers+text',
                name: 'Ventas',
                text: sellTrades.map(trade => `▼<br>Cantidad: ${trade.qty}<br>Precio: $${trade.price}<br>Total: $${(trade.qty * trade.price).toFixed(2)}`),
                textposition: 'top center',
                marker: {
                    color: chartConfig.colors.tradeSell,
                    size: 16,
                    symbol: 'triangle-down'
                },
                yaxis: 'y1'
            };
            traces.push(traceSells);
        }
    }
}

// Función para agregar trazas de simulación
async function addSimulationTradesTraces(chartConfig, minTime, maxTime, traces) {
            const simulationConfigs = [
                {show: chartConfig.showSimulation1, type: 'estrategia_1', buyColor: chartConfig.colors.simulation1Buy, sellColor: chartConfig.colors.simulation1Sell, name: 'Simulación 1'},
                {show: chartConfig.showSimulation2, type: 'estrategia_2', buyColor: chartConfig.colors.simulation2Buy, sellColor: chartConfig.colors.simulation2Sell, name: 'Simulación 2'}, 
                {show: chartConfig.showSimulation3, type: 'estrategia_3', buyColor: chartConfig.colors.simulation3Buy, sellColor: chartConfig.colors.simulation3Sell, name: 'Simulación 3'}
            ];

            for (const config of simulationConfigs) {
                if (config.show) {
                    let simulationTradesData = [];
                    const simulationTradesResponse = await fetch(`/get_trades/${chartConfig.currentSymbol}/${config.type}/`);
                    simulationTradesData = await simulationTradesResponse.json();

                    const filteredSimulationTrades = simulationTradesData.filter(trade => {
                        const tradeTime = new Date(trade.time);
                        return tradeTime >= minTime && tradeTime <= maxTime;
                    });

                    const buySimulationTrades = filteredSimulationTrades.filter(trade => trade.isBuyer === true);
                    const sellSimulationTrades = filteredSimulationTrades.filter(trade => trade.isBuyer === false);

                    if (buySimulationTrades.length > 0) {
                        const traceSimulationBuys = {
                            x: buySimulationTrades.map(trade => trade.time),
                            y: buySimulationTrades.map(trade => trade.price),
                            type: 'scatter',
                            mode: 'markers+text',
                            name: `Compras ${config.name}`,
                            text: buySimulationTrades.map(trade => `▲<br>Cantidad: ${trade.qty}<br>Precio: $${trade.price}<br>Total: $${(trade.qty * trade.price).toFixed(2)}`),
                            textposition: 'bottom center',
                            marker: {
                                color: config.buyColor,
                                size: 16,
                                symbol: 'triangle-up'
                            },
                            yaxis: 'y1'
                        };
                        traces.push(traceSimulationBuys);
                    }

                    if (sellSimulationTrades.length > 0) {
                        const traceSimulationSells = {
                            x: sellSimulationTrades.map(trade => trade.time),
                            y: sellSimulationTrades.map(trade => trade.price),
                            type: 'scatter',
                            mode: 'markers+text',
                            name: `Ventas ${config.name}`,
                            text: sellSimulationTrades.map(trade => `▼<br>Cantidad: ${trade.qty}<br>Precio: $${trade.price}<br>Total: $${(trade.qty * trade.price).toFixed(2)}`),
                            textposition: 'top center',
                            marker: {
                                color: config.sellColor,
                                size: 16,
                                symbol: 'triangle-down'
                            },
                            yaxis: 'y1'
                        };
                        traces.push(traceSimulationSells);
                    }
                }
            }
        }


// Función para alternar la visibilidad de los valores en USD
function toggleUSDVisibility() {
    const usdElements = document.querySelectorAll('.usd');
    usdElements.forEach(element => {
            element.classList.toggle('d-none');
        });
}

// Configurar el editor y los botones flotantes
//let editor = ace.edit("editor");

    // Funciones para el Chat GPT
function addMessage(content, isUser = false) {
    const messagesContainer = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${isUser ? 'user' : 'assistant'}`;
    
        // Formatear el contenido si contiene bloques de código
        const formattedContent = formatMessageContent(content);
        
        messageDiv.innerHTML = `
            ${formattedContent}
            <div class="message-time">${new Date().toLocaleTimeString()}</div>
        `;
        
        messagesContainer.appendChild(messageDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        
        // Agregar listeners para los botones de copiar
        messageDiv.querySelectorAll('.copy-button').forEach(button => {
            button.addEventListener('click', () => {
                const codeBlock = button.nextElementSibling;
                navigator.clipboard.writeText(codeBlock.textContent);
                button.textContent = '¡Copiado!';
                setTimeout(() => button.textContent = 'Copiar', 2000);
            });
        });

        return formattedContent;
    }

function formatMessageContent(content) {
    return content.replace(/```(\w+)?\n([\s\S]*?)```/g, (match, language, code) => `
        <button class="copy-button">Copiar</button>
        <pre class="code-block-chat ${language || ''}">${escapeHtml(code.trim())}</pre>
    `);
}



// Event Listeners
document.addEventListener('DOMContentLoaded', function() {
    // Referencias a elementos del DOM
    const elements = {
        floatingButton: document.getElementById('floatingButton'),
        sendToChatButton: document.getElementById('sendToChat'), 
        editSelectionButton: document.getElementById('editSelection'),
        chatMessages: document.getElementById('chatMessages'),
        editorElement: document.getElementById('editor'),
        chatInput: document.getElementById('chatInput'),
        sendButton: document.getElementById('sendChat')
    };

    // Funciones de utilidad
    const createChatMessage = (selectedText, chatMessages) => {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message user-message';

        const codeContainer = document.createElement('div');
        codeContainer.style.position = 'relative';

        const deleteButton = document.createElement('button');
        deleteButton.innerHTML = '<i class="fas fa-times"></i>';
        Object.assign(deleteButton.style, {
            position: 'absolute',
            top: '5px',
            left: '5px',
            background: 'transparent',
            border: 'none',
            color: '#ff6b6b',
            cursor: 'pointer'
        });
        deleteButton.onclick = () => messageDiv.remove();

        const codeBlock = document.createElement('pre');
        codeBlock.className = 'code-block-chat';
        Object.assign(codeBlock.style, {
            backgroundColor: '#1a1a1a',
            color: '#d4d4d4',
            fontFamily: "'Fira Code', monospace",
            padding: '1rem',
            borderRadius: '4px',
            border: '1px solid #333'
        });
        codeBlock.textContent = selectedText;

        codeContainer.append(deleteButton, codeBlock);
        messageDiv.appendChild(codeContainer);
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    };

    const handleSendToChat = () => {
        const selectedText = editor.getSelectedText();
        if (selectedText.trim()) {
            createChatMessage(selectedText, elements.chatMessages);
            elements.floatingButton.style.display = 'none';
        }
    };

    const handleEditSelection = () => {
        const selectedText = editor.getSelectedText();
        if (selectedText.trim()) {
            alert(`Editar: ${selectedText}`);
            elements.floatingButton.style.display = 'none';
        }
    };

    const adjustFloatingButtonPosition = () => {
        const selectedText = editor.getSelectedText();
        if (selectedText.trim()) {
            const range = editor.getSelectionRange();
            const startPos = editor.renderer.textToScreenCoordinates(range.start.row, range.start.column);
            const editorRect = elements.editorElement.getBoundingClientRect();

            Object.assign(elements.floatingButton.style, {
                position: 'absolute',
                top: `${startPos.pageY - editorRect.top - 40}px`,
                left: `${startPos.pageX - editorRect.left + 400}px`,
                display: 'block',
                zIndex: '1000'
            });
        } else {
            elements.floatingButton.style.display = 'none';
        }
    };

    const hideFloatingButton = (e) => {
        if (!elements.editorElement.contains(e.target) && !elements.floatingButton.contains(e.target)) {
            elements.floatingButton.style.display = 'none';
        }
    };

    // Event Listeners
    elements.sendToChatButton?.addEventListener('click', handleSendToChat);
    elements.editSelectionButton?.addEventListener('click', handleEditSelection);
    document.addEventListener('click', hideFloatingButton);

    elements.sendButton.addEventListener('click', () => sendMessage(elements.chatInput));

    elements.chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage(elements.chatInput);
        }
    });

    elements.chatInput.addEventListener('input', () => {
        elements.chatInput.style.height = 'auto';
        elements.chatInput.style.height = `${Math.min(elements.chatInput.scrollHeight, 150)}px`;
    });

    editor.getSession().selection.on('changeSelection', adjustFloatingButtonPosition);



    async function sendMessage(chatInput) {
        const type = 'trading';
        const message = chatInput.value.trim();
        const terminalOutput = document.getElementById('botOutput').textContent.trim().substring(1);
        const editorContent = editor.getSelectedText().trim();
        
        if (!message) return;

        // Estructurar el mensaje para ChatGPT
        const user_chat = {
            message: message,
            editor_code: editorContent || null,
            terminal_output: terminalOutput.length > 10 ? terminalOutput : null,
            type: type,
            chart_data: chartDataPrompt
        };

        // Agregar mensaje del usuario
        addMessage(message, true);
        chatInput.value = '';

        if (terminalOutput && terminalOutput.length > 10) {
            addMessage(terminalOutput, false);
            type = 'terminal';
        }

        console.log(user_chat);

        try {
            const response = await fetch('/local_llm_chat/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify(user_chat)
            }); 

            const data = await response.json();
            if (data.success) {
                addMessage(data.response);
            } else {
                addMessage('Error: ' + data.error);
            }
        } catch (error) {
            console.error('Error:', error);
            addMessage('Error de conexión con el servidor');
        }
    }

    // Llamar a la función al cargar la página
    updateTotalBalance();
    // Actualizar cada minuto (60000 milisegundos)
    setInterval(updateTotalBalance, 60000);
    setupChartEventListeners();

    // Configurar botones de estrategia con estado guardado
    setupStrategyButtons();
    
    // Cargar árbol de archivos inicial
    loadFileTree();
    
    // Iniciar actualización periódica del terminal
    setInterval(updateBotOutput, 5000);
    
    // Iniciar gráfico con configuración guardada
    updateChart();
    setInterval(updateChart, 60000);


    // Agregar evento de clic a los botones de alternancia
    const toggleButtons = document.querySelectorAll('.toggle-usd');
    toggleButtons.forEach(button => {
        button.addEventListener('click', toggleUSDVisibility);
    });


    setupFileControls();

    // Botón Run/Stop
    const runBotBtn = document.getElementById('runBot');
    runBotBtn.addEventListener('click', () => {
        const currentFile = document.getElementById('currentPath').value;
        
        if (!currentFile && !isBotRunning) {
            alert('Por favor, selecciona un archivo para ejecutar');
            return;
        }
        
        const endpoint = isBotRunning ? '/stop_bot/' : '/run_bot/';
        
        fetch(endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                current_file: currentFile
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                updateRunButton(!isBotRunning, runBotBtn);
                
                if (!isBotRunning) {
                    // Bot detenido
                    clearInterval(window.botOutputInterval);
                    alert('Script detenido');
                } else {
                    // Bot iniciado
                    alert('Script iniciado');
                    updateBotOutput();
                    window.botOutputInterval = setInterval(updateBotOutput, 5000);
                }
            } else {
                alert(`Error: ${data.error}`);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error de conexión');
        });
    });

    // Verificar estado inicial del bot
    fetch('/bot_status/')
        .then(response => response.json())
        .then(data => {
            updateRunButton(data.is_running,runBotBtn);
        })
        .catch(error => console.error('Error checking bot status:', error));

    // Agregar input al terminal
    createTerminalInput(terminalHistory, historyIndex);
    // Configurar botones de minimizar/maximizar
    setupMinimizeButtons();
    // Restaurar estados guardados
    restoreSectionStates();



});



function setupFileControls() {
    // Botones de control
    document.getElementById('clearTerminal').addEventListener('click', () => {
        document.getElementById('botOutput').textContent = '';
    });

    document.getElementById('scrollToBottom').addEventListener('click', () => {
        const terminal = document.getElementById('botOutput');
        terminal.scrollTop = terminal.scrollHeight;
    });

    // Botón New File
    document.getElementById('newFile').addEventListener('click', () => {
        document.getElementById('newItemModalLabel').textContent = 'New File';
        document.getElementById('newItemType').value = 'file';
        document.getElementById('newItemName').placeholder = 'Enter file name (e.g., script.py)';
        new bootstrap.Modal(document.getElementById('newItemModal')).show();
    });

    // Botón New Folder
    document.getElementById('newFolder').addEventListener('click', () => {
        document.getElementById('newItemModalLabel').textContent = 'New Folder';
        document.getElementById('newItemType').value = 'folder';
        document.getElementById('newItemName').placeholder = 'Enter folder name';
        new bootstrap.Modal(document.getElementById('newItemModal')).show();
    });

    // Botón Create en el modal
    document.getElementById('createNewItem').addEventListener('click', () => {
        const name = document.getElementById('newItemName').value;
        const type = document.getElementById('newItemType').value;
        const currentPath = document.getElementById('currentPath').value || '';
        console.log(currentPath);

        fetch('/create_file_or_folder/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                name: name,
                type: type,
                path: currentPath
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                loadFileTree();  // Recargar árbol de archivos
                bootstrap.Modal.getInstance(document.getElementById('newItemModal')).hide();
                document.getElementById('newItemName').value = '';  // Limpiar input
            } else {
                alert('Error: ' + data.error);
            }
        })
        .catch(error => console.error('Error:', error));
    });

    // Botón Save Code (corregido)
    document.getElementById('saveCode').addEventListener('click', () => {
        const content = editor.getValue();
        const path = document.getElementById('currentPath').value;
        
        if (!path) {
            alert('Please select a file to save');
            return;
        }

        fetch('/save_bot_code/', {  // URL corregida
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                file_name: path,
                content: content
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('File saved successfully!');
            } else {
                alert('Error saving file: ' + data.error);
            }
        })
        .catch(error => console.error('Error:', error));
    });
}
function setupStrategyButtons() {
    // Inicialización de event listeners
    const strategy1Button = document.querySelector('.toggle-strategy[data-target="strategy1"]');
    const strategy2Button = document.querySelector('.toggle-strategy[data-target="strategy2"]');
    const strategy3Button = document.querySelector('.toggle-strategy[data-target="strategy3"]');

    // Agregar estilos CSS para el botón activo
    const style = document.createElement('style');
    style.textContent = `
        .btn-active {
            background-color: #28a745 !important;
            color: white !important;
            border-color: #45a049 !important;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2) !important;
        }
    `;
    document.head.appendChild(style);

    // Objeto para mantener el estado de las estrategias
    const strategyStates = {
        strategy1: localStorage.getItem('strategy1State') === 'true',
        strategy2: localStorage.getItem('strategy2State') === 'true', 
        strategy3: localStorage.getItem('strategy3State') === 'true'
    };

    // Restaurar estados visuales iniciales
    if (strategyStates.strategy1 && strategy1Button) {
        strategy1Button.classList.add('btn-active');
    }
    if (strategyStates.strategy2 && strategy2Button) {
        strategy2Button.classList.add('btn-active');
    }
    if (strategyStates.strategy3 && strategy3Button) {
        strategy3Button.classList.add('btn-active');
    }

    if (strategy1Button) {
        strategy1Button.addEventListener('click', async () => {
            if (!strategyStates.strategy1) {
                strategy1Button.classList.add('btn-active');
                strategyStates.strategy1 = true;
                localStorage.setItem('strategy1State', 'true');
                try {
                    await executeStrategy1();
                    await updateTotalBalance();
                    alert('Estrategia 1 activada correctamente');
                } catch (error) {
                    console.error('Error al ejecutar estrategia 1:', error);
                    strategy1Button.classList.remove('btn-active');
                    strategyStates.strategy1 = false;
                    localStorage.setItem('strategy1State', 'false');
                    alert('Error al activar estrategia 1: ' + error.message);
                }
            } else {
                try {
                    await stopStrategy(1);
                    await updateTotalBalance();
                    strategy1Button.classList.remove('btn-active');
                    strategyStates.strategy1 = false;
                    localStorage.setItem('strategy1State', 'false');
                } catch (error) {
                    console.error('Error al detener estrategia 1:', error);
                }
            }
        });
    }

    if (strategy2Button) {
        strategy2Button.addEventListener('click', async () => {
            if (!strategyStates.strategy2) {
                strategy2Button.classList.add('btn-active');
                strategyStates.strategy2 = true;
                localStorage.setItem('strategy2State', 'true');
                try {
                    await executeStrategy2();
                    await updateTotalBalance();
                    alert('Estrategia 2 activada correctamente');
                } catch (error) {
                    console.error('Error al ejecutar estrategia 2:', error);
                    strategy2Button.classList.remove('btn-active');
                    strategyStates.strategy2 = false;
                    localStorage.setItem('strategy2State', 'false');
                    alert('Error al activar estrategia 2: ' + error.message);
                }
            } else {
                try {
                    await stopStrategy(2);
                    await updateTotalBalance();
                    strategy2Button.classList.remove('btn-active');
                    strategyStates.strategy2 = false;
                    localStorage.setItem('strategy2State', 'false');
                } catch (error) {
                    console.error('Error al detener estrategia 2:', error);
                }
            }
        });
    }

    if (strategy3Button) {
        strategy3Button.addEventListener('click', async () => {
            if (!strategyStates.strategy3) {
                strategy3Button.classList.add('btn-active');
                strategyStates.strategy3 = true;
                localStorage.setItem('strategy3State', 'true');
                try {
                    await executeStrategy3();
                    await updateTotalBalance();
                    alert('Estrategia 3 activada correctamente');
                } catch (error) {
                    console.error('Error al ejecutar estrategia 3:', error);
                    strategy3Button.classList.remove('btn-active');
                    strategyStates.strategy3 = false;
                    localStorage.setItem('strategy3State', 'false');
                    alert('Error al activar estrategia 3: ' + error.message);
                }
            } else {
                try {
                    await stopStrategy(3);
                    await updateTotalBalance();
                    strategy3Button.classList.remove('btn-active');
                    strategyStates.strategy3 = false;
                    localStorage.setItem('strategy3State', 'false');
                } catch (error) {
                    console.error('Error al detener estrategia 3:', error);
                }
            }
        });
    }
}



function updateRunButton(isRunning, runBotBtn) {
    if (isRunning) {
        runBotBtn.innerHTML = '<i class="fas fa-stop"></i> Stop';
        runBotBtn.classList.add('btn-danger');
        runBotBtn.classList.remove('btn-modern');
    } else {
        runBotBtn.innerHTML = '<i class="fas fa-play"></i> Run';
        runBotBtn.classList.remove('btn-danger');
        runBotBtn.classList.add('btn-modern');
    }
    isBotRunning = isRunning;
    // Guardar estado del botón
    localStorage.setItem('botRunningState', isRunning);
}

function setupChartEventListeners() {
    // Variable para controlar el tiempo entre actualizaciones
    let updateTimeout = null;

    // Función para ejecutar updateChart con debounce
    const debouncedUpdateChart = () => {
        if (updateTimeout) {
            clearTimeout(updateTimeout);
        }
        updateTimeout = setTimeout(() => {
            updateChart();
        }, 300); // Espera 300ms antes de ejecutar
    };

    // Cargar estados guardados y configurar listeners para checkboxes
    ['showLSTM', 'showTimeGAN', 'showRSI', 'showMACD', 'showBollinger', 'showTrades', 
    'showSimulation1', 'showSimulation2', 'showSimulation3', 'showEMA','showSMA', 'showPSAR', 'showStochastic', 
    'showOBV', 'showADX', 'showATR', 'showPivot', 'showFibonacci', 'showFourier'].forEach(id => {
        const checkbox = document.getElementById(id);
        // Cargar estado guardado
        const savedState = localStorage.getItem(id);
        if (savedState !== null) {
            checkbox.checked = savedState === 'true';
        }
        // Agregar listener y guardar estado
        checkbox.addEventListener('change', (e) => {
            localStorage.setItem(id, e.target.checked);
            debouncedUpdateChart();
        });
    });

    // Configurar limit input
    const limitInput = document.getElementById('limitInput');
    const savedLimit = localStorage.getItem('limitInput');
    if (savedLimit) {
        limitInput.value = savedLimit;
    }
    limitInput.addEventListener('input', (e) => {
        localStorage.setItem('limitInput', e.target.value);
        debouncedUpdateChart();
    });

    // Configurar interval buttons
    document.querySelectorAll('[data-interval]').forEach(button => {
        button.addEventListener('click', () => {
            currentInterval = button.dataset.interval;
            localStorage.setItem('currentInterval', currentInterval);
            debouncedUpdateChart();
        });
    });
    
    // Configurar chart type buttons
    document.querySelectorAll('[data-chart-type]').forEach(button => {
        button.addEventListener('click', () => {
            currentChartType = button.dataset.chartType;
            localStorage.setItem('currentChartType', currentChartType);
            debouncedUpdateChart();
        });
    });

    // Configurar symbol selector
    const symbolSelector = document.getElementById('symbolSelector');
    const savedSymbol = localStorage.getItem('currentSymbol');
    if (savedSymbol) {
        symbolSelector.value = savedSymbol;
        currentSymbol = savedSymbol;
    }
    symbolSelector.addEventListener('change', (e) => {
        currentSymbol = e.target.value;
        localStorage.setItem('currentSymbol', currentSymbol);
        debouncedUpdateChart();
    });

    // Configurar toggle all indicators
    const toggleAllCheckbox = document.getElementById('toggleAllIndicators');
    const indicatorCheckboxes = document.querySelectorAll('.indicator-checkbox');
    
    const savedToggleAll = localStorage.getItem('toggleAllIndicators');
    if (savedToggleAll !== null) {
        toggleAllCheckbox.checked = savedToggleAll === 'true';
    }

    toggleAllCheckbox.addEventListener('change', function() {
        localStorage.setItem('toggleAllIndicators', toggleAllCheckbox.checked);
        indicatorCheckboxes.forEach(checkbox => {
            checkbox.checked = toggleAllCheckbox.checked;
            localStorage.setItem(checkbox.id, toggleAllCheckbox.checked);
        });
    });

}
