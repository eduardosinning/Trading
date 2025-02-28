import { getCookie } from '/static/scripts/utils/utils.js';



// Función que crea y maneja una terminal interactiva en la interfaz
// Parámetros:
// - terminalHistory: Array que almacena el historial de comandos
// - historyIndex: Índice para navegar el historial
export function createTerminalInput(terminalHistory, historyIndex) {
    // Obtiene el elemento contenedor de la terminal
    const terminal = document.getElementById('botOutput');
    
    // Crea la línea de input con el prompt
    const inputLine = document.createElement('div');
    inputLine.className = 'terminal-input-line';
    inputLine.innerHTML = `
        <span class="terminal-prompt">$ </span>
        <input type="text" class="terminal-input" placeholder="Escribe un comando...">
    `;
    terminal.appendChild(inputLine);
    
    const input = inputLine.querySelector('.terminal-input');
    let currentDirectory = '';
    
    // Maneja los eventos del teclado en el input
    input.addEventListener('keydown', async (e) => {
        if (e.key === 'Enter') {
            const command = input.value.trim();
            if (command) {
                // Agrega el comando al historial
                terminalHistory.push(command);
                historyIndex = terminalHistory.length;
                
                // Muestra el comando ejecutado en la terminal
                const cmdLine = document.createElement('div');
                cmdLine.className = 'terminal-line';
                cmdLine.textContent = `$ ${command}`;
                terminal.insertBefore(cmdLine, inputLine);
                
                // Deshabilita el input mientras procesa el comando
                input.disabled = true;
                
                try {
                    // Envía el comando al servidor para su ejecución
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
                    
                    // Maneja el comando clear limpiando la terminal
                    if (data.clear) {
                        terminal.innerHTML = '';
                        terminal.appendChild(inputLine);
                    } else {
                        // Muestra la salida del comando si existe
                        if (data.output) {
                            const outputLine = document.createElement('div');
                            outputLine.className = 'terminal-line' + (data.error ? ' error' : '');
                            outputLine.textContent = data.output;
                            terminal.insertBefore(outputLine, inputLine);
                        }
                    }
                    
                    // Actualiza el directorio actual si cambió (comando cd)
                    if (data.current_directory !== undefined) {
                        currentDirectory = data.current_directory;
                        const prompt = inputLine.querySelector('.terminal-prompt');
                        prompt.textContent = currentDirectory ? `${currentDirectory}$ ` : '$ ';
                    }
                    
                } catch (error) {
                    // Maneja errores de conexión
                    console.error('Error:', error);
                    const errorLine = document.createElement('div');
                    errorLine.className = 'terminal-line error';
                    errorLine.textContent = 'Error de conexión';
                    terminal.insertBefore(errorLine, inputLine);
                }
                
                // Restaura el input a su estado inicial
                input.value = '';
                input.disabled = false;
                input.focus();
                
                // Hace scroll al final de la terminal
                terminal.scrollTop = terminal.scrollHeight;
            }
        } else if (e.key === 'ArrowUp') {
            // Navega hacia atrás en el historial de comandos
            e.preventDefault();
            if (historyIndex > 0) {
                historyIndex--;
                input.value = terminalHistory[historyIndex];
            }
        } else if (e.key === 'ArrowDown') {
            // Navega hacia adelante en el historial de comandos
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
    
    // Enfoca el input al crear la terminal
    input.focus();
}