// --- Drag & Drop con animaciones reales ---
document.querySelectorAll('.producto-card').forEach(card => {
  card.setAttribute('draggable', 'true');

  card.addEventListener('dragstart', e => {
    e.dataTransfer.setData('producto', card.dataset.producto);
    e.dataTransfer.setData('origen', card.dataset.origen);

    // Animación visual al iniciar drag
    card.classList.add('ring-4', 'ring-blue-400', 'scale-105', 'shadow-xl', 'transition', 'duration-300');
  });

  card.addEventListener('dragend', () => {
    card.classList.remove('ring-4', 'ring-blue-400', 'scale-105', 'shadow-xl');
  });
});

document.querySelectorAll('.dropzone').forEach(zone => {
  zone.addEventListener('dragover', e => {
    e.preventDefault();
    zone.classList.add('ring-4', 'ring-blue-400', 'shadow-lg', 'transition', 'duration-300');
  });

  zone.addEventListener('dragleave', () => {
    zone.classList.remove('ring-4', 'ring-blue-400', 'shadow-lg');
  });

  zone.addEventListener('drop', e => {
    e.preventDefault();
    zone.classList.remove('ring-4', 'ring-blue-400', 'shadow-lg');

    const producto = e.dataTransfer.getData('producto');
    const origen = e.dataTransfer.getData('origen');
    const destino = zone.dataset.destino; // siempre el contenedor

    console.log("DROP EVENT:", { producto, origen, destino }); // debug

    if (!producto || !origen || !destino) {
      console.warn("Faltan datos, no se abre el modal");
      return;
    }

    if (Number(origen) === Number(destino)) {
      console.warn("Misma columna, no se abre el modal");
      return;
    }

    abrirFormularioTransferencia(producto, origen, destino);
  });
});


// --- Modal ---
function abrirFormularioTransferencia(producto, origen, destino) {
  const modal = document.getElementById('transferenciaModal');
  const content = document.getElementById('transferenciaContent');

  modal.classList.remove('hidden');
  content.classList.remove('animate-fadeOut');
  content.classList.add('animate-fadeIn');

  document.getElementById('producto_id').value = producto;
  document.getElementById('origen_id').value = origen;
  document.getElementById('destino_id').value = destino;
}

function cerrarModal() {
  const modal = document.getElementById('transferenciaModal');
  const content = document.getElementById('transferenciaContent');

  content.classList.remove('animate-fadeIn');
  content.classList.add('animate-fadeOut');

  setTimeout(() => {
    modal.classList.add('hidden');
    content.classList.remove('animate-fadeOut');
  }, 300); // coincide con duración de animación
}

// --- Confirmación AJAX ---
async function confirmarTransferencia(event) {
  event.preventDefault(); // evitar submit normal

  const form = document.querySelector('#transferenciaModal form');
  const formData = new FormData(form);

  try {
    const response = await fetch(form.action, {
      method: 'POST',
      body: formData,
      headers: { 'X-Requested-With': 'XMLHttpRequest' }
    });

    const result = await response.json();

    if (result.success) {
      const productoId = result.producto_id;
      const origenId = result.origen_id;
      const destinoId = result.destino_id;

      // Si el backend dice que se debe eliminar la card del origen
      if (result.remove_card) {
        const cardOrigen = document.querySelector(
          `.producto-card[data-producto="${productoId}"][data-origen="${origenId}"]`
        );
        if (cardOrigen) cardOrigen.remove();
      }

      // Si el destino no tenía card, crearla
      if (result.add_card) {
        const zoneDestino = document.querySelector(`.dropzone[data-destino="${destinoId}"]`);
        if (zoneDestino) {
          const nuevaCard = document.createElement('div');
          nuevaCard.className = 'producto-card bg-white rounded-lg shadow p-4 mb-2';
          nuevaCard.dataset.producto = productoId;
          nuevaCard.dataset.origen = destinoId;
          nuevaCard.textContent = result.producto_nombre + " (x" + result.cantidad + ")";
          zoneDestino.appendChild(nuevaCard);
        }
      }

      cerrarModal();
      alert("✅ Transferencia realizada correctamente.");
    } else {
      alert("❌ Error: " + result.errors.join(", "));
    }
  } catch (err) {
    console.error(err);
    alert("❌ Error inesperado en la transferencia.");
  }
}
