document.addEventListener("DOMContentLoaded", function () {
  const sidebar = document.getElementById("sidebar");
  const toggle = document.getElementById("sidebar-toggle");
  const tab = document.getElementById("sidebar-tab");
  const icon = document.getElementById("tab-icon");
  const body = document.body;

  if (!sidebar || !toggle || !tab || !icon) {
    console.warn("❌ Sidebar: elementos no encontrados");
    return;
  }

  console.log("✅ Sidebar inicializado");

  // Restaurar estado fijado
  if (localStorage.getItem("sidebarPinned") === "true") {
    sidebar.classList.add("pinned");
    body.classList.add("sidebar-open");
    icon.classList.replace("fa-chevron-right", "fa-chevron-left");
  }

  // Botón hamburguesa (móvil)
  toggle.addEventListener("click", () => {
    sidebar.classList.toggle("open");
  });

  // Cierre automático al hacer clic en un enlace (solo móvil)
  if (window.innerWidth < 768) {
    const links = sidebar.querySelectorAll("a");
    links.forEach((link) => {
      link.addEventListener("click", () => {
        sidebar.classList.remove("open");
      });
    });
  }

  // Botón de anclaje (escritorio)
  tab.addEventListener("click", (e) => {
    e.stopPropagation();
    const pinned = sidebar.classList.toggle("pinned");
    body.classList.toggle("sidebar-open", pinned);
    icon.classList.toggle("fa-chevron-left", pinned);
    icon.classList.toggle("fa-chevron-right", !pinned);
    localStorage.setItem("sidebarPinned", pinned);
  });
});


