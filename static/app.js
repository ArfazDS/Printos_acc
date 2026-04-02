document.addEventListener("DOMContentLoaded", () => {
    const themeToggle = document.getElementById("theme-toggle");
    
    // Check local storage for theme preference
    const currentTheme = localStorage.getItem("theme");
    if (currentTheme) {
        document.documentElement.setAttribute("data-theme", currentTheme);
        updateIcon(currentTheme);
    } else {
        // Check system preference
        const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
        if (prefersDark) {
            document.documentElement.setAttribute("data-theme", "dark");
            updateIcon("dark");
        }
    }

    if (themeToggle) {
        themeToggle.addEventListener("click", () => {
            let theme = document.documentElement.getAttribute("data-theme");
            let targetTheme = "light";
            
            if (theme === "light" || !theme) {
                targetTheme = "dark";
            }
            
            document.documentElement.setAttribute("data-theme", targetTheme);
            localStorage.setItem("theme", targetTheme);
            updateIcon(targetTheme);
        });
    }

    function updateIcon(theme) {
        if (!themeToggle) return;
        if (theme === "dark") {
            themeToggle.innerHTML = "☀️"; // Show sun to toggle light
        } else {
            themeToggle.innerHTML = "🌙"; // Show moon to toggle dark
        }
    }
});
