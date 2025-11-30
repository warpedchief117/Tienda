// ===============================
// Reportes: carga dinámica de subcategorías y animación de cards
// ===============================
const form = document.getElementById('form-reportes');
const apiUrl = form.dataset.apiUrl || '/inventario/api/categorias/';

const categoriaSelect = document.getElementById('categoria');
const subSelect = document.getElementById('subcategoria');

let categoriasCache = null;

// 🔧 Función para cargar subcategorías según la categoría seleccionada
async function cargarSubcategorias(categoriaId, filtroSub = null) {
  if (!categoriaId) {
    subSelect.innerHTML = '<option value="">Todas</option>';
    return;
  }

  subSelect.innerHTML = '<option value="">Cargando...</option>';

  try {
    if (!categoriasCache) {
      const resp = await fetch(apiUrl, { headers: { "X-Requested-With": "XMLHttpRequest" } });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      categoriasCache = await resp.json();
    }

    const categoria = categoriasCache.categorias_padre.find(
      c => String(c.id) === String(categoriaId)
    );

    let html = '<option value="">Todas</option>';
    if (categoria && categoria.subcategorias) {
      categoria.subcategorias.forEach(sub => {
        html += `<option value="${sub.id}">${sub.nombre}</option>`;
      });
    }
    subSelect.innerHTML = html;

    // ✅ Mantener seleccionada la subcategoría filtrada
    if (filtroSub) {
      const option = subSelect.querySelector(`option[value="${filtroSub}"]`);
      if (option) option.selected = true;
    }
  } catch (err) {
    console.error('Error cargando subcategorías:', err);
    subSelect.innerHTML = '<option value="">Error al cargar</option>';
  }
}

// 📌 Evento al cambiar categoría
categoriaSelect.addEventListener('change', function () {
  cargarSubcategorias(this.value);
});

// 🎨 Animación suave de las cards
function animarCards() {
  const cards = document.querySelectorAll('#cards-container .card');
  cards.forEach((card, i) => {
    setTimeout(() => {
      card.classList.remove('opacity-0', 'translate-y-4');
    }, i * 120); // efecto escalonado
  });
}

// 🚀 Al cargar la página
document.addEventListener('DOMContentLoaded', () => {
  // Recuperar subcategoría seleccionada desde dataset
  const filtroSub = subSelect.dataset.selected || "";
  if (categoriaSelect.value) {
    cargarSubcategorias(categoriaSelect.value, filtroSub);
  }

  // Disparar animación inicial de las cards
  animarCards();
});

// 🔄 Animar cards después de enviar el formulario
form.addEventListener('submit', () => {
  setTimeout(animarCards, 400);
});

// ===============================
// Botón de PDF: ya está en el template como <a href="...">
// No necesita JS extra porque abre en otra pestaña con los filtros incluidos.
// ===============================
