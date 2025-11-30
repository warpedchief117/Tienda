document.addEventListener("DOMContentLoaded", function () {
  // ============================
  // Mostrar etiqueta
  // ============================
  window.mostrarEtiqueta = function (button) {
    const url = button.getAttribute("data-url");
    const productoId = button.getAttribute("data-id");
    const ubicacionId = button.getAttribute("data-ubicacion");
    const contenedor = document.getElementById(`etiqueta-${productoId}-${ubicacionId}`);
    const img = document.getElementById(`img-${productoId}-${ubicacionId}`);

    if (contenedor.style.display === "block") {
      contenedor.style.display = "none";
      return;
    }

    fetch(url)
      .then(res => {
        if (!res.ok) throw new Error("No se pudo cargar la etiqueta");
        return res.json();
      })
      .then(data => {
        if (data.imagen) {
          img.src = `data:image/png;base64,${data.imagen}`;
          contenedor.style.display = "block";
        } else {
          img.alt = "Etiqueta no disponible";
        }
      })
      .catch(err => {
        img.alt = "Error al cargar la etiqueta";
        console.error(err);
      });
  };

  // ============================
  // Imprimir etiqueta
  // ============================
  window.imprimirEtiqueta = function (productoId, ubicacionId) {
    const img = document.getElementById(`img-${productoId}-${ubicacionId}`);
    const ventana = window.open('', '_blank');
    ventana.document.write(`
      <html>
        <head>
          <title>Etiqueta</title>
          <style>
            body { margin: 0; display: flex; justify-content: center; align-items: center; height: 100vh; }
            img { max-width: 100%; max-height: 100%; }
          </style>
        </head>
        <body>
          <img src="${img.src}" />
          <script>
            window.onload = function() {
              window.print();
              window.onafterprint = function() { window.close(); };
            };
          <\/script>
        </body>
      </html>
    `);
    ventana.document.close();
  };

  // ============================
  // Descargar etiqueta
  // ============================
  window.descargarEtiqueta = function (productoId, ubicacionId) {
    const img = document.getElementById(`img-${productoId}-${ubicacionId}`);
    const enlace = document.createElement('a');
    enlace.href = img.src;
    enlace.download = `etiqueta_producto_${productoId}_${ubicacionId}.png`;
    document.body.appendChild(enlace);
    enlace.click();
    document.body.removeChild(enlace);
  };

  // ============================
  // Buscador con animación
  // ============================
  const buscador = document.getElementById("buscador");
  if (buscador) {
    buscador.addEventListener("input", function () {
      let filtro = this.value.toLowerCase();
      let cards = document.querySelectorAll(".producto-card");

      cards.forEach(card => {
        let nombre = card.getAttribute("data-nombre").toLowerCase();
        let descripcion = card.getAttribute("data-descripcion").toLowerCase();
        let categoria = card.getAttribute("data-categoria").toLowerCase();
        let temporada = card.getAttribute("data-temporada").toLowerCase();

        if (
          nombre.includes(filtro) ||
          descripcion.includes(filtro) ||
          categoria.includes(filtro) ||
          temporada.includes(filtro)
        ) {
          card.style.display = "block";
          card.classList.add("animate-fadeIn");
          card.classList.remove("animate-fadeOut");
        } else {
          card.classList.add("animate-fadeOut");
          setTimeout(() => {
            card.style.display = "none";
          }, 300); // espera la animación
        }
      });
    });
  }
});
