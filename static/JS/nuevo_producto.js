document.addEventListener("DOMContentLoaded", () => {
  const form = document.querySelector("form");
  const codigoInput = document.getElementById("id_codigo_barras");

  const nombreInput = document.getElementById("id_nombre");
  const descripcionInput = document.getElementById("id_descripcion");
  const mayoreoInput = document.getElementById("id_precio_mayoreo");
  const menudeoInput = document.getElementById("id_precio_menudeo");
  const docenaInput = document.getElementById("id_precio_docena");
  const tipoCodigoInput = document.getElementById("id_tipo_codigo");
  const duenioSelect = document.getElementById("id_dueño");
  const categoriaPadreSelect = document.getElementById("id_categoria_padre");
  const subcategoriaSelect = document.getElementById("id_subcategoria");
  const atributosContainer = document.getElementById("atributos-container");
  const ubicacionSelect = document.getElementById("id_ubicacion");
  const submitBtn = document.getElementById("submit-btn");

  // Evitar submit al presionar Enter en código de barras: disparar búsqueda
  codigoInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      buscarYCompletar(codigoInput.value);
    }
  });

  // También buscar al perder foco o cambiar
  codigoInput.addEventListener("change", () => buscarYCompletar(codigoInput.value));
  codigoInput.addEventListener("blur", () => {
    if (!nombreInput.value && codigoInput.value) buscarYCompletar(codigoInput.value);
  });

  // Protección extra: si nombre está vacío al enviar, intentar buscar antes
  form.addEventListener("submit", async (e) => {
    if (!nombreInput.value && codigoInput.value) {
      e.preventDefault();
      await buscarYCompletar(codigoInput.value);
      if (nombreInput.value) form.submit();
    }
  });

  async function buscarYCompletar(codigo) {
    if (!codigo) return;
    codigoInput.classList.add("opacity-50");

    try {
      const url = `/inventario/buscar_producto/?codigo=${encodeURIComponent(codigo)}`;
      const resp = await fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();

      if (!data.existe) {
        alert("Producto no encontrado por código de barras.");
        return;
      }

      // Llenar campos principales
      nombreInput.value = data.nombre || "";
      descripcionInput.value = data.descripcion || "";
      mayoreoInput.value = data.precio_mayoreo ?? "";
      menudeoInput.value = data.precio_menudeo ?? "";
      docenaInput.value = data.precio_docena ?? "";
      tipoCodigoInput.value = data.tipo_codigo ?? "";

      if (duenioSelect && data.dueño_id) {
        duenioSelect.value = String(data.dueño_id);
      }
      if (categoriaPadreSelect && data.categoria_padre_id) {
        categoriaPadreSelect.value = String(data.categoria_padre_id);
      }

      if (subcategoriaSelect) {
        subcategoriaSelect.innerHTML = "";
        const subData = document.querySelectorAll("#subcategorias-data div");
        subData.forEach((sub) => {
          if (String(sub.dataset.padre) === String(data.categoria_padre_id)) {
            const opt = document.createElement("option");
            opt.value = sub.dataset.id;
            opt.textContent = sub.dataset.nombre;
            subcategoriaSelect.appendChild(opt);
          }
        });
        if (data.subcategoria_id) {
          subcategoriaSelect.value = String(data.subcategoria_id);
        }
      }

      renderAtributos(data.atributos);

      setReadOnlyTrue([
        nombreInput,
        descripcionInput,
        mayoreoInput,
        menudeoInput,
        docenaInput,
        duenioSelect,
        categoriaPadreSelect,
        subcategoriaSelect,
      ]);

      // Guardar producto_id en un hidden para usarlo en la verificación
      let hiddenId = document.getElementById("id_producto_id");
      if (!hiddenId) {
        hiddenId = document.createElement("input");
        hiddenId.type = "hidden";
        hiddenId.id = "id_producto_id";
        hiddenId.name = "producto_id";
        form.appendChild(hiddenId);
      }
      hiddenId.value = data.producto_id;

      // Verificar inventario si ya hay ubicación seleccionada
      if (ubicacionSelect && ubicacionSelect.value) {
        verificarInventario(data.producto_id, ubicacionSelect.value);
      }

      const cantInput = document.getElementById("id_cantidad_inicial");
      if (cantInput) cantInput.focus();
    } catch (err) {
      console.error("Error buscando producto:", err);
      alert("Ocurrió un error al buscar el producto.");
    } finally {
      codigoInput.classList.remove("opacity-50");
    }
  }

async function verificarInventario(productoId, ubicacionId) {
  if (!productoId || !ubicacionId) return;
  try {
    const url = `/inventario/verificar_inventario/?producto=${productoId}&ubicacion=${ubicacionId}`;
    const resp = await fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();

  if (data.existe) {
    // Producto ya existe en esa ubicación → Agregar inventario
    form.action = `/inventario/agregar_inventario/${productoId}/${ubicacionId}/`;
    submitBtn.textContent = "Agregar inventario";

    // Cambiar a verde
    submitBtn.classList.replace("bg-red-600", "bg-green-600");
    submitBtn.classList.replace("hover:bg-red-700", "hover:bg-green-700");
  } else {
    // Producto no existe en esa ubicación → Registrar producto nuevo
    form.action = `/inventario/nuevo_producto/`;
    submitBtn.textContent = "Registrar producto";

    // Cambiar a rojo
    submitBtn.classList.replace("bg-green-600", "bg-red-600");
    submitBtn.classList.replace("hover:bg-green-700", "hover:bg-red-700");
  }


  } catch (err) {
    console.error("Error verificando inventario:", err);
  }
}

// Listener para cuando cambie la ubicación
ubicacionSelect?.addEventListener("change", () => {
  const productoId = document.getElementById("id_producto_id")?.value;
  if (productoId) {
    verificarInventario(productoId, ubicacionSelect.value);
  }
});


  function renderAtributos(atributos = []) {
    atributosContainer.innerHTML = "";
    atributos.forEach((attr) => {
      const wrapper = document.createElement("div");
      wrapper.className = "mb-2";
      const label = document.createElement("label");
      label.className = "block font-semibold mb-1";
      label.textContent = attr.nombre;

      const input = document.createElement("input");
      input.type = "text";
      input.className = "form-control bg-gray-100";
      input.value = attr.valor || "";
      input.readOnly = true;

      wrapper.appendChild(label);
      wrapper.appendChild(input);
      atributosContainer.appendChild(wrapper);
    });
  }

  function setReadOnlyTrue(elements) {
    elements.forEach((el) => {
      if (!el) return;
      if (el.tagName === "SELECT") {
        el.disabled = true;
        el.classList.add("bg-gray-100");
      } else {
        el.setAttribute("readonly", "true");
        el.classList.add("bg-gray-100");
      }
    });
  }
});
