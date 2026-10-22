// Vue « horloge » : un seul minuteur, une seule racine, tout est retiré par hide().
let racine = null;
let minuteur = null;
const reglages = { secondes: true, h12: false };

function dessiner() {
  if (!racine) return;
  const d = new Date();
  const opts = { hour: "2-digit", minute: "2-digit", hour12: reglages.h12 };
  if (reglages.secondes) opts.second = "2-digit";
  racine.querySelector(".h").textContent = d.toLocaleTimeString("fr-FR", opts);
  racine.querySelector(".d").textContent = d.toLocaleDateString("fr-FR", { weekday: "long", day: "numeric", month: "long", year: "numeric" });
}

function creerRacine() {
  const r = document.createElement("div");
  r.id = "vue-horloge";
  r.style.cssText = "position:fixed;inset:0;z-index:50;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:2vh;background:#04070c;color:#eefbff;font-family:'Cascadia Mono',Consolas,monospace;";
  const h = document.createElement("div");
  h.className = "h";
  h.style.cssText = "font-size:min(18vw,30vh);letter-spacing:.06em;text-shadow:0 0 3vh rgba(79,210,255,.35);";
  const d = document.createElement("div");
  d.className = "d";
  d.style.cssText = "font-size:min(3vw,5vh);color:#7f9fb2;letter-spacing:.14em;text-transform:uppercase;";
  const aide = document.createElement("div");
  aide.textContent = "Échap pour fermer";
  aide.style.cssText = "position:absolute;bottom:3vh;font-size:max(12px,1.4vh);color:#4d6b7d;letter-spacing:.2em;text-transform:uppercase;";
  r.append(h, d, aide);
  return r;
}

export default {
  show(params) {
    if (params && typeof params.secondes === "boolean") reglages.secondes = params.secondes;
    if (params && typeof params.h12 === "boolean") reglages.h12 = params.h12;
    if (!racine) {
      racine = creerRacine();
      document.body.appendChild(racine);
      minuteur = setInterval(dessiner, 1000);
    }
    dessiner();
  },
  hide() {
    if (minuteur !== null) { clearInterval(minuteur); minuteur = null; }
    if (racine) { racine.remove(); racine = null; }
  },
  command(cmd, params) {
    if (cmd === "secondes") reglages.secondes = !(params && params.actif === false);
    else if (cmd === "format") reglages.h12 = !!(params && params.h12);
    dessiner();
  },
};
