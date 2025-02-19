document.addEventListener("DOMContentLoaded", function () {
    const menuToggle = document.getElementById("menu-toggle");
    const menu = document.querySelector(".navbar ul");

    menuToggle.addEventListener("click", function () {
        menu.classList.toggle("active");
    });
});
