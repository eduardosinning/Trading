import { getCookie } from '/static/scripts/utils/utils.js';



export function createTerminalInput(terminalHistory, historyIndex) {
    const terminal = document.getElementById('botOutput');
    const inputLine = document.createElement('div');
    inputLine.className = 'terminal-input-line';
    inputLine.innerHTML = `
        <span class="terminal-prompt">$ </span>
        <input type="text" class="terminal-input" placeholder="Escribe un comando...">
    `;
    terminal.appendChild(inputLine);
    
    const input = inputLine.querySelector('.terminal-input');
    let currentDirectory = '';
    
    input.addEventListener('keydown', async (e) => {
        if (e.key === 'Enter') {
            const command = input.value.trim();
            if (command) {
                // Agregar comando al historial
                terminalHistory.push(command);
                historyIndex = terminalHistory.length;
                
                // Mostrar comando ejecutado
                const cmdLine = document.createElement('div');
                cmdLine.className = 'terminal-line';
                cmdLine.textContent = `$ ${command}`;
                terminal.insertBefore(cmdLine, inputLine);
                
                // Deshabilitar input mientras se ejecuta
                input.disabled = true;
                
                try {
                    const response = await fetch('/execute-terminal-command/', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': getCookie('csrftoken')
                        },
                        body: JSON.stringify({ 
                            command: command,
                            current_directory: currentDirectory 
                        })
                    });
                    
                    const data = await response.json();
                    
                    // Manejar comando clear
                    if (data.clear) {
                        terminal.innerHTML = '';
                        terminal.appendChild(inputLine);
                    } else {
                        // Mostrar salida si existe
                        if (data.output) {
                            const outputLine = document.createElement('div');
                            outputLine.className = 'terminal-line' + (data.error ? ' error' : '');
                            outputLine.textContent = data.output;
                            terminal.insertBefore(outputLine, inputLine);
                        }
                    }
                    
                    // Actualizar directorio actual para cd
                    if (data.current_directory !== undefined) {
                        currentDirectory = data.current_directory;
                        // Actualizar el prompt con el directorio actual
                        const prompt = inputLine.querySelector('.terminal-prompt');
                        prompt.textContent = currentDirectory ? `${currentDirectory}$ ` : '$ ';
                    }
                    
                } catch (error) {
                    console.error('Error:', error);
                    const errorLine = document.createElement('div');
                    errorLine.className = 'terminal-line error';
                    errorLine.textContent = 'Error de conexión';
                    terminal.insertBefore(errorLine, inputLine);
                }
                
                // Limpiar y habilitar input
                input.value = '';
                input.disabled = false;
                input.focus();
                
                // Scroll al fondo
                terminal.scrollTop = terminal.scrollHeight;
            }
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            if (historyIndex > 0) {
                historyIndex--;
                input.value = terminalHistory[historyIndex];
            }
        } else if (e.key === 'ArrowDown') {
            e.preventDefault();
            if (historyIndex < terminalHistory.length - 1) {
                historyIndex++;
                input.value = terminalHistory[historyIndex];
            } else {
                historyIndex = terminalHistory.length;
                input.value = '';
            }
        }
    });
    
    input.focus();
}