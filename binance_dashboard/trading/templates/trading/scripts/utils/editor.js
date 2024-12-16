
let editor = ace.edit("editor");
editor.setTheme("ace/theme/monokai");
editor.session.setMode("ace/mode/python");
editor.setOptions({
    fontSize: "12pt",
    enableBasicAutocompletion: true,
    enableSnippets: true,
    enableLiveAutocompletion: true
});




// Funciones del explorador de archivos
export function loadFileTree() {
    fetch('/get_file_tree/')
        .then(response => response.json())
        .then(data => {
            const fileTree = document.querySelector('.file-tree');
            fileTree.innerHTML = generateFileTreeHTML(data);
            addFileTreeListeners();
        })
        .catch(error => console.error('Error loading file tree:', error));
}


export function generateFileTreeHTML(item, level = 0) {
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
export function addFileTreeListeners() {
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


        
 export function showContextMenu(e, item) {
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
export function updateBotOutput() {
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