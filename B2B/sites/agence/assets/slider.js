// Interaction signature (curseur avant/après) et révélation des titres, numéros et photos au défilement.
// Sans ce script : le curseur reste à 50 %, tout le reste du contenu est déjà visible (voir style.css).
(() => {
  const curseur = document.getElementById("aa-curseur");
  const bloc = document.getElementById("demo-aa");
  if (curseur && bloc) {
    const maj = () => bloc.style.setProperty("--p", curseur.value + "%");
    curseur.addEventListener("input", maj);
    maj();
  }

  if (matchMedia("(prefers-reduced-motion: reduce)").matches) return;

  const phrase = document.querySelector(".phrase-geante");
  if (phrase) {
    const mots = phrase.textContent.trim().split(/\s+/);
    phrase.innerHTML = mots.map((m, i) => `<span class="mot" style="transition-delay:${i * 45}ms">${m}</span>`).join(" ");
  }

  if (!("IntersectionObserver" in window)) return;
  const cibles = document.querySelectorAll(".titre-anime, .num-contour, .photo-cadre, .solution-phrases li, .ex, .faq details, .phrase-geante");
  if (!cibles.length) return;
  const obs = new IntersectionObserver((entrees) => {
    for (const en of entrees) {
      if (en.isIntersecting) { en.target.classList.add("voir"); obs.unobserve(en.target); }
    }
  }, { threshold: 0.2, rootMargin: "0px 0px -10% 0px" });
  cibles.forEach((c) => obs.observe(c));
})();
