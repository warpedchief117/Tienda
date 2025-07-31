let lastScrollTop = 0;
const navbar = document.querySelector("nav");

window.addEventListener("scroll", function () {
  const scrollTop = window.pageYOffset || document.documentElement.scrollTop;

  if (scrollTop > lastScrollTop) {
    navbar.style.transform = "translateY(-100%)";
    navbar.style.transition = "transform 0.3s ease-in-out";
  } else {
    navbar.style.transform = "translateY(0)";
    navbar.style.transition = "transform 0.3s ease-in-out";
  }

  lastScrollTop = scrollTop <= 0 ? 0 : scrollTop;
});
