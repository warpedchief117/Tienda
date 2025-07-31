
document.addEventListener("DOMContentLoaded", () => {
  const form = document.querySelector("form");
  const btn = document.getElementById("btn-submit");

  if (!form || !btn) return;

  const btnText = btn.querySelector("span");
  const spinner = document.getElementById("btn-spinner");

  form.addEventListener("submit", () => {
    // Desactiva el botón
    btn.disabled = true;

    // Cambia el texto
    btnText.textContent = "Registrando...";

    // Muestra el spinner
    if (spinner) {
      spinner.style.display = "inline-block";
    }
  });
});
