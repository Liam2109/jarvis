// Vue « monuments 3D » : three.js local (import map de la page), OrbitControls local, géométrie procédurale (registre monuments/).
// Idempotent : show() deux fois ne crée qu'une scène. hide() arrête l'animation, retire les écouteurs, libère la mémoire GPU et le DOM.
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { trouverMonument } from "./monuments/index.js";

let etat = null;

function fermerDemande() {
  window.dispatchEvent(new CustomEvent("jarvis-vue-fermer"));
}

function creerRacine() {
  const r = document.createElement("div");
  r.id = "vue-monument-3d";
  r.style.cssText = "position:fixed;inset:0;z-index:50;background:#04070c;overflow:hidden;font-family:'Segoe UI',system-ui,sans-serif;";
  const titre = document.createElement("div");
  titre.className = "titre";
  titre.style.cssText = "position:absolute;top:3vh;left:50%;transform:translateX(-50%);color:#9be9ff;letter-spacing:.4em;text-transform:uppercase;font-size:max(14px,2vh);pointer-events:none;text-shadow:0 0 2vh rgba(79,210,255,.4);";
  const aide = document.createElement("div");
  aide.textContent = "Clic gauche : tourner · Molette : zoom · Clic droit : déplacer · Échap : fermer";
  aide.style.cssText = "position:absolute;top:3vh;right:2vw;color:#4d6b7d;font-size:max(11px,1.3vh);letter-spacing:.12em;pointer-events:none;text-align:right;max-width:30vw;";
  const bouton = document.createElement("button");
  bouton.textContent = "Fermer";
  bouton.style.cssText = "position:absolute;top:3vh;left:2vw;background:rgba(8,20,32,.85);color:#d8f4ff;border:1px solid rgba(79,210,255,.5);padding:.5em 1.4em;letter-spacing:.15em;text-transform:uppercase;cursor:pointer;";
  bouton.addEventListener("click", fermerDemande);
  r.append(titre, aide, bouton);
  return { racine: r, titre, bouton };
}

function liberer(objet) {
  objet.traverse((o) => {
    if (o.geometry) o.geometry.dispose();
    const m = o.material;
    if (m) (Array.isArray(m) ? m : [m]).forEach((x) => x.dispose());
  });
}

function placerCamera(cam, ctrl, monument) {
  cam.position.set(...monument.camera.position);
  ctrl.target.set(...monument.camera.cible);
  ctrl.update();
}

function chargerMonument(id) {
  const m = trouverMonument(id);
  if (etat.groupe) { etat.scene.remove(etat.groupe); liberer(etat.groupe); }
  etat.monument = m;
  etat.groupe = m.construire(THREE);
  etat.scene.add(etat.groupe);
  etat.titre.textContent = m.nom;
  placerCamera(etat.camera, etat.controles, m);
}

function monter(params) {
  const { racine, titre, bouton } = creerRacine();
  document.body.appendChild(racine);
  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.setClearColor(0x04070c, 1);
  racine.insertBefore(renderer.domElement, racine.firstChild);
  const scene = new THREE.Scene();
  scene.fog = new THREE.Fog(0x04070c, 700, 1800);
  scene.add(new THREE.HemisphereLight(0xbfe6ff, 0x1a1410, 0.9));
  const soleil = new THREE.DirectionalLight(0xfff1dd, 0.9);
  soleil.position.set(250, 400, 200);
  scene.add(soleil);
  const camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 1, 4000);
  const controles = new OrbitControls(camera, renderer.domElement);
  controles.enableDamping = true;
  controles.dampingFactor = 0.08;
  controles.minDistance = 60;
  controles.maxDistance = 1400;
  controles.maxPolarAngle = Math.PI * 0.495;
  controles.screenSpacePanning = true;
  controles.autoRotateSpeed = 0.6;

  etat = { racine, titre, bouton, renderer, scene, camera, controles, groupe: null, monument: null, raf: 0, onResize: null };
  etat.onResize = () => {
    renderer.setSize(window.innerWidth, window.innerHeight);
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
  };
  window.addEventListener("resize", etat.onResize);
  const boucle = () => {
    if (!etat) return;
    etat.raf = requestAnimationFrame(boucle);
    if (!document.hidden) {
      controles.update();
      renderer.render(scene, camera);
    }
  };
  chargerMonument((params && params.monument) || "eiffel");
  boucle();
}

export default {
  show(params) {
    if (!etat) monter(params);
    else if (params && params.monument) chargerMonument(params.monument);
  },
  hide() {
    if (!etat) return;
    const e = etat;
    etat = null;
    cancelAnimationFrame(e.raf);
    window.removeEventListener("resize", e.onResize);
    e.bouton.removeEventListener("click", fermerDemande);
    e.controles.dispose();
    if (e.groupe) liberer(e.groupe);
    e.scene.clear();
    e.renderer.dispose();
    e.renderer.forceContextLoss();
    e.racine.remove();
  },
  command(cmd, params) {
    if (!etat) return;
    if (cmd === "monument" && params && params.monument) chargerMonument(params.monument);
    else if (cmd === "recentrer") placerCamera(etat.camera, etat.controles, etat.monument);
    else if (cmd === "rotation") etat.controles.autoRotate = !(params && params.actif === false);
  },
};
