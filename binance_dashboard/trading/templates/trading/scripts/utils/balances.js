
export async function getStrategyBalanceData() {
    let strategy1BalanceData = [], strategy2BalanceData = [], strategy3BalanceData = [];
    
    if (document.querySelector('.toggle-strategy[data-target="strategy1"]').classList.contains('btn-active')) {
        const strategy1Response = await fetch('/get_strategy_trading_history/1');
        strategy1BalanceData = await strategy1Response.json();
        console.log("strategy1BalanceData:", strategy1BalanceData);
    }

    if (document.querySelector('.toggle-strategy[data-target="strategy2"]').classList.contains('btn-active')) {
        const strategy2Response = await fetch('/get_strategy_trading_history/2');
        strategy2BalanceData = await strategy2Response.json();
        console.log("strategy2BalanceData:", strategy2BalanceData);
    }

    if (document.querySelector('.toggle-strategy[data-target="strategy3"]').classList.contains('btn-active')) {
        const strategy3Response = await fetch('/get_strategy_trading_history/3');
        strategy3BalanceData = await strategy3Response.json();
        console.log("strategy3BalanceData:", strategy3BalanceData);
    }

    return { strategy1BalanceData, strategy2BalanceData, strategy3BalanceData };
}

// Función para filtrar datos de balance por rango de tiempo
export function filterBalanceDataByTimeRange(balanceData, minTime, maxTime) {
    return balanceData.filter(item => {
        const timestamp = new Date(item.timestamp);
        return timestamp >= minTime && timestamp <= maxTime;
    });
}

export function updateTotalBalance() {
    fetch('/get_total_balance_usd/')
        .then(response => response.json())
        .then(async data => {
            // Actualizar el balance total
            document.querySelector('.total-balance-usd').textContent = `$${data.total_balance_usd.toFixed(2)}`;
            
            const tbody = document.querySelector('table.table tbody');
            
            // Obtener estados de los botones de estrategia
            const strategy1Active = document.querySelector('.toggle-strategy[data-target="strategy1"]')?.classList.contains('btn-active');
            const strategy2Active = document.querySelector('.toggle-strategy[data-target="strategy2"]')?.classList.contains('btn-active');
            
            // Obtener datos de simulación si las estrategias están activas
            let sim1Data = null;
            let sim2Data = null;
            
            if (strategy1Active) {
                try {
                    const response_1 = await fetch('/get_balance_simulation/1/');
                    sim1Data = await response_1.json();
                    //console.log("simulationData strategy 1: ", sim1Data);
                    // Actualizar el título de la columna con el balance total
                    const strategy1Header = document.querySelector('span.strategy1-header');
                    if (strategy1Header) {
                        console.log("strategy1Header: ", strategy1Header);
                        strategy1Header.textContent = `estrategia 1 ($${sim1Data.total_balance_usd.toFixed(2)})`;
                    }
                } catch (error) {
                    console.error('Error al obtener los balances de simulación 1:', error);
                }
            }
            
            if (strategy2Active) {
                try {
                    const response_2 = await fetch('/get_balance_simulation/2/');
                    sim2Data = await response_2.json();
                    //console.log("simulationData strategy 2: ", sim2Data);
                    // Actualizar el título de la columna con el balance total
                    const strategy2Header = document.querySelector('span.strategy2-header');
                    if (strategy2Header) {
                        console.log("strategy2Header: ", strategy2Header);
                        strategy2Header.textContent = `estrategia 2 ($${sim2Data.total_balance_usd.toFixed(2)})`;
                    }
                } catch (error) {
                    console.error('Error al obtener los balances de simulación 2:', error);
                }
            }
            
            // Actualizar filas existentes o crear nuevas si es necesario
            data.balances.forEach((balance, index) => {
                let tr = tbody.children[index];
                if (!tr) {
                    tr = document.createElement('tr');
                    tbody.appendChild(tr);
                }
                
                // Obtener datos de simulación para este activo
                const sim1Balance = sim1Data?.balances[index];
                const sim2Balance = sim2Data?.balances[index];
                
                tr.innerHTML = `
                    <td>
                        <span class="text-primary">"${balance.asset}"</span>
                        <br>
                        <span class="text-info">${balance.current_price}</span>
                    </td>
                    <td>
                        <span class="text-success amount">${balance.free}</span>
                        <span class="text-success usd d-none">$${(balance.free * balance.current_price).toFixed(2)}</span>
                    </td>
                    <td>
                        <span class="text-warning amount">${balance.locked}</span>
                        <span class="text-warning usd d-none">$${(balance.locked * balance.current_price).toFixed(2)}</span>
                    </td>
                    <td class="strategy1-balance">
                        ${sim1Balance ? `
                            <span class="text-info">${sim1Balance.amount}</span>
                            <br>
                            <span class="text-info">$${sim1Balance.usd_value.toFixed(2)}</span>
                        ` : '<span class="text-info">-</span>'}
                    </td>
                    <td class="strategy2-balance">
                        ${sim2Balance ? `
                            <span class="text-info">${sim2Balance.amount}</span>
                            <br>
                            <span class="text-info">$${sim2Balance.usd_value.toFixed(2)}</span>
                        ` : '<span class="text-info">-</span>'}
                    </td>
                    <td><span class="text-info">-</span></td>
                `;
            });
            
            // Eliminar filas sobrantes si hay menos balances que antes
            while (tbody.children.length > data.balances.length) {
                tbody.removeChild(tbody.lastChild);
            }
        })
        .catch(error => console.error('Error al obtener los balances:', error));
}
