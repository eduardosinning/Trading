// Función para manejar la minimización/maximización de divs
export function setupMinimizeButtons() {
    // Manejar botones de minimizar
    document.querySelectorAll('.minimize-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            const targetId = btn.getAttribute('data-target');
            const targetContent = document.getElementById(targetId);
            
            if (targetContent.style.display === 'none') {
                // Maximizar
                targetContent.style.display = 'block';
                btn.innerHTML = '<i class="fas fa-minus"></i>';
                localStorage.setItem(`section-${targetId}-state`, 'maximized');
            } else {
                // Minimizar
                targetContent.style.display = 'none';
                btn.innerHTML = '<i class="fas fa-plus"></i>';
                localStorage.setItem(`section-${targetId}-state`, 'minimized');
            }
        });
    });

    // Manejar botones de maximizar
    document.querySelectorAll('.maximize-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            const targetId = btn.getAttribute('data-target');
            const targetContent = document.getElementById(targetId);
            const card = targetContent.closest('.card');
            
            if (card.classList.contains('maximized')) {
                // Restaurar tamaño
                card.classList.remove('maximized');
                btn.innerHTML = '<i class="fas fa-expand"></i>';
            } else {
                // Maximizar
                card.classList.add('maximized');
                btn.innerHTML = '<i class="fas fa-compress"></i>';
            }
        });
    });
}

// Función para restaurar el estado de las secciones
export function restoreSectionStates() {
    document.querySelectorAll('.minimize-btn').forEach(btn => {
        const targetId = btn.getAttribute('data-target');
        const targetContent = document.getElementById(targetId);
        const savedState = localStorage.getItem(`section-${targetId}-state`);
        
        if (savedState === 'minimized') {
            targetContent.style.display = 'none';
            btn.innerHTML = '<i class="fas fa-plus"></i>';
        }
    });
}