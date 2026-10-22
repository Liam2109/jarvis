// Barre de widgets flottante, menu (burger / touche M) et panneaux Configuration + Capacités (lecture seule).
// Chargé par visage/index.html et visage/pilotage.html. JS vanilla, aucun appel réseau externe (seulement les routes locales de Jarvis, avec le même jeton), aucun eval,
// aucun innerHTML : tout texte venant des fichiers (qui sont des DONNÉES) est posé avec textContent.
(function () {
  "use strict";
  const TOKEN = typeof K !== "undefined" ? K : (window.K || "");

  // ---------- Petits outils partagés (utilisés aussi par pilotage.js) ----------
  function h(tag, props, ...enfants) {
    const e = document.createElement(tag);
    if (props) {
      for (const cle of Object.keys(props)) {
        const v = props[cle];
        if (cle === "class") e.className = v;
        else if (cle === "on") { for (const ev of Object.keys(v)) e.addEventListener(ev, v[ev]); }
        else if (v !== false && v !== null && v !== undefined) e.setAttribute(cle, String(v));
      }
    }
    for (const c of enfants.flat(Infinity)) {
      if (c === null || c === undefined || c === false) continue;
      e.append(typeof c === "object" ? c : String(c));
    }
    return e;
  }
  async function lire(chemin) {
    const r = await fetch(chemin + (chemin.indexOf("?") >= 0 ? "&" : "?") + "k=" + encodeURIComponent(TOKEN), { cache: "no-store" });
    if (!r.ok) throw new Error("HTTP " + r.status);
    return r.json();
  }
  async function poster(chemin, corps) {
    const r = await fetch(chemin, { method: "POST", headers: { "X-Jarvis-Token": TOKEN, "Content-Type": "application/json" }, body: JSON.stringify(corps || {}) });
    return r.json();
  }
  window.JarvisUI = { h, lire, poster, jeton: TOKEN };

  // ---------- Style (thème sombre de Jarvis ; variables de la page si elles existent) ----------
  const css = `
  .wbar { position: fixed; left: 50%; bottom: 14px; transform: translateX(-50%); z-index: 95; display: flex; gap: 8px; align-items: center; padding: 8px 12px; border-radius: 999px;
          background: rgba(8, 19, 30, .92); border: 1px solid var(--ligne-forte, rgba(79,210,255,.5)); box-shadow: 0 6px 30px rgba(0,0,0,.55); font-family: var(--titre, "Segoe UI", system-ui, sans-serif); }
  .wbtn { position: relative; border-radius: 999px; padding: 7px 16px; border: 1px solid var(--ligne, rgba(79,210,255,.2)); background: rgba(12, 26, 40, .9); color: var(--texte, #c6e4f2); cursor: pointer; font: 13px/1 var(--titre, "Segoe UI", system-ui, sans-serif); letter-spacing: .06em; }
  .wbtn:hover:not([disabled]) { background: rgba(79, 210, 255, .18); }
  .wbtn[aria-pressed="true"] { background: var(--accent, #4fd2ff); color: #04121c; border-color: var(--accent, #4fd2ff); font-weight: 600; }
  .wbtn[disabled] { opacity: .35; cursor: not-allowed; }
  .wpop { position: fixed; z-index: 96; min-width: 190px; padding: 8px; border-radius: 14px; background: rgba(8, 19, 30, .97); border: 1px solid var(--ligne-forte, rgba(79,210,255,.5)); box-shadow: 0 8px 30px rgba(0,0,0,.6); }
  .wpop button { display: block; width: 100%; text-align: left; margin: 2px 0; }
  .wburger { position: fixed; left: 14px; bottom: 14px; z-index: 97; width: 44px; height: 44px; border-radius: 50%; padding: 0; font-size: 20px; }
  .wmenu { position: fixed; left: 14px; bottom: 66px; z-index: 97; padding: 8px; border-radius: 14px; background: rgba(8, 19, 30, .97); border: 1px solid var(--ligne-forte, rgba(79,210,255,.5)); min-width: 220px; box-shadow: 0 8px 30px rgba(0,0,0,.6); }
  .wmenu button { display: block; width: 100%; text-align: left; margin: 3px 0; border-radius: 10px; }
  .wpanneau { position: fixed; inset: 8vh 12vw; z-index: 98; overflow: auto; padding: 22px 28px; border-radius: 16px; background: rgba(6, 13, 21, .985); border: 1px solid var(--ligne-forte, rgba(79,210,255,.5)); color: var(--texte, #c6e4f2); font-family: var(--titre, "Segoe UI", system-ui, sans-serif); }
  .wpanneau h2 { margin: 0 0 6px; color: var(--accent, #4fd2ff); letter-spacing: .12em; text-transform: uppercase; font-size: 16px; }
  .wpanneau h3 { margin: 18px 0 6px; color: var(--doux, #7f9fb2); font-size: 13px; letter-spacing: .14em; text-transform: uppercase; }
  .wpanneau .note { color: var(--doux, #7f9fb2); font-size: 13px; margin: 0 0 8px; }
  .wpanneau .rang { display: flex; justify-content: space-between; gap: 12px; padding: 5px 0; border-bottom: 1px dashed rgba(79,210,255,.13); font-size: 14px; overflow-wrap: anywhere; }
  .wpanneau .oui { color: #6dffb4; } .wpanneau .non { color: var(--doux, #7f9fb2); }
  .wpanneau .fermer { position: absolute; top: 14px; right: 18px; }
  body.pilotage-on #soustitres { bottom: 84px; }
  `;
  document.head.append(h("style", null, css));

  // ---------- État et affichage ----------
  const etat = { menu: false, panneau: null, pop: null, widgets: null };
  const boutons = {};

  function conversationOuverte() {
    if (window.JarvisConv && typeof window.JarvisConv.ouverte === "function") return !!window.JarvisConv.ouverte();
    return !document.body.classList.contains("conv-ferme");
  }
  function basculerConversation() {
    if (window.JarvisConv && typeof window.JarvisConv.basculer === "function") window.JarvisConv.basculer();
    else if (typeof window.basculerConv === "function") window.basculerConv();      // le bouton « Conv. » et la touche C existants
    majBoutons();
  }
  function majBoutons() {
    const w = etat.widgets || {};
    boutons.micro.setAttribute("aria-pressed", String(w.micro_actif !== false));
    boutons.micro.setAttribute("title", w.micro_actif === false ? "Jarvis est en sourdine : cliquer pour le réactiver" : "Jarvis écoute : cliquer pour le mettre en sourdine");
    boutons.conv.setAttribute("aria-pressed", String(conversationOuverte()));
    boutons.musique.setAttribute("aria-pressed", String(!w.musique_coupee));
    boutons.musique.setAttribute("title", w.musique_coupee ? "Musique coupée : cliquer pour la remettre" : "Musique active : cliquer pour la couper");
    boutons.dossier.setAttribute("aria-pressed", String(!!etat.pop));
  }
  async function rafraichir() {
    if (document.hidden) return;
    try { etat.widgets = await lire("/pilotage-widgets"); majBoutons(); } catch (e) { /* Jarvis arrêté ou Pilotage désactivé */ }
  }
  async function agir(corps) {
    try { const r = await poster("/pilotage-widget", corps); if (!r.ok && r.texte) annoncer(r.texte); } catch (e) { annoncer("Jarvis ne répond pas."); }
    rafraichir();
  }
  let minuteurAnnonce = null;
  function annoncer(texte) {
    let a = document.getElementById("wannonce");
    if (!a) { a = h("div", { id: "wannonce", class: "wpop", style: "left:50%;transform:translateX(-50%);bottom:76px;" }); document.body.append(a); }
    a.textContent = texte;
    if (minuteurAnnonce) clearTimeout(minuteurAnnonce);
    minuteurAnnonce = setTimeout(() => { a.remove(); }, 3500);
  }

  function fermerPop() { if (etat.pop) { etat.pop.remove(); etat.pop = null; } }
  function ouvrirDossiers() {
    if (etat.pop) { fermerPop(); majBoutons(); return; }
    const noms = (etat.widgets && etat.widgets.dossiers) || [];
    const pop = h("div", { class: "wpop", style: "left:50%;transform:translateX(-50%);bottom:76px;" },
      noms.length ? noms.map((n) => h("button", { class: "wbtn", on: { click: () => { fermerPop(); agir({ widget: "dossier", nom: n }); } } }, n)) : h("span", { class: "note" }, "Aucun dossier autorisé."));
    document.body.append(pop); etat.pop = pop; majBoutons();
  }

  // ---------- Panneaux en lecture seule ----------
  function fermerPanneau() { if (etat.panneau) { etat.panneau.remove(); etat.panneau = null; } }
  function ouvrirPanneau(titre, note, contenu) {
    fermerPanneau();
    const p = h("section", { class: "wpanneau", role: "dialog", "aria-label": titre },
      h("button", { class: "wbtn fermer", on: { click: fermerPanneau } }, "Fermer"), h("h2", null, titre), h("p", { class: "note" }, note), contenu);
    document.body.append(p); etat.panneau = p;
  }
  async function panneauConfiguration() {
    let d; try { d = await lire("/pilotage-donnees"); } catch (e) { annoncer("Données indisponibles."); return; }
    const rangs = (d.config || []).map((o) => h("div", { class: "rang" }, h("span", null, o.nom), h("b", { class: o.etat === "oui" ? "oui" : "non" }, o.etat)));
    ouvrirPanneau("Configuration", "Lecture seule : seul l'état des options est affiché (oui / non), jamais une clé, un jeton, un chemin ni un mot de passe. Pour changer une option, modifiez config.local.json.", rangs.length ? rangs : h("p", { class: "note" }, "Aucune option."));
  }
  async function panneauCapacites() {
    let d; try { d = await lire("/pilotage-donnees"); } catch (e) { annoncer("Données indisponibles."); return; }
    const c = d.capacites || {};
    const bloc = (titre, brut, actif) => { const liste = Array.isArray(brut) ? brut : []; return [h("h3", null, titre + " (" + liste.length + ")" + (actif === false ? " · désactivés" : "")),
      liste.length ? liste.map((x) => h("div", { class: "rang" }, h("span", null, x.nom + (x.description ? " — " + x.description : "")), h("b", null, x.etat))) : h("p", { class: "note" }, "Aucun.")]; };
    ouvrirPanneau("Capacités", "Ce que Jarvis a installé : skills, presets et vues, avec leur état.", [bloc("Skills", c.skills), bloc("Presets", c.presets, c.presets_actif), bloc("Vues", c.vues, c.vues_actif)]);
  }

  // ---------- Menu ----------
  let menu = null;
  function fermerMenu() { if (menu) { menu.remove(); menu = null; } etat.menu = false; boutons.burger.setAttribute("aria-pressed", "false"); }
  function basculerMenu() {
    if (etat.menu) { fermerMenu(); return; }
    fermerPop(); etat.menu = true; boutons.burger.setAttribute("aria-pressed", "true");
    const item = (libelle, fn) => h("button", { class: "wbtn", on: { click: () => { fermerMenu(); fn(); } } }, libelle);
    menu = h("nav", { class: "wmenu", "aria-label": "Menu" },
      item("Accueil", () => { window.location.href = "/?k=" + encodeURIComponent(TOKEN); }),
      item("Workspace · Pilotage", () => { window.location.href = "/pilotage?k=" + encodeURIComponent(TOKEN); }),
      item("Configuration (lecture seule)", panneauConfiguration),
      item("Capacités", panneauCapacites));
    document.body.append(menu);
  }
  function fermerTout() { fermerMenu(); fermerPanneau(); fermerPop(); majBoutons(); }

  // ---------- Construction ----------
  boutons.burger = h("button", { class: "wbtn wburger", title: "Menu (touche M)", "aria-label": "Menu", "aria-pressed": "false", on: { click: basculerMenu } }, "☰");
  boutons.micro = h("button", { class: "wbtn", "aria-pressed": "true", on: { click: () => agir({ widget: "micro", etat: !(etat.widgets && etat.widgets.micro_actif !== false) }) } }, "Micro");
  boutons.conv = h("button", { class: "wbtn", "aria-pressed": "true", title: "Ouvrir / fermer la conversation (touche C)", on: { click: basculerConversation } }, "Conversation");
  boutons.dossier = h("button", { class: "wbtn", "aria-pressed": "false", title: "Ouvrir un dossier autorisé", on: { click: ouvrirDossiers } }, "Dossier");
  boutons.musique = h("button", { class: "wbtn", "aria-pressed": "true", on: { click: () => agir({ widget: "musique", coupee: !(etat.widgets && etat.widgets.musique_coupee) }) } }, "Musique");
  boutons.partage = h("button", { class: "wbtn", disabled: "disabled", title: "pas branché", "aria-label": "Partage d'écran (pas branché)" }, "Écran");
  boutons.camera = h("button", { class: "wbtn", disabled: "disabled", title: "pas branché", "aria-label": "Caméra (pas branchée)" }, "Caméra");
  const barre = h("div", { class: "wbar", id: "wbar", role: "toolbar", "aria-label": "Widgets" }, boutons.micro, boutons.conv, boutons.dossier, boutons.musique, boutons.partage, boutons.camera);
  document.body.append(boutons.burger, barre);
  document.body.classList.add("pilotage-on");

  // Échap ferme d'abord le menu / un panneau / la liste des dossiers, SANS déclencher le comportement habituel (fermer la vue, sinon réduire la fenêtre).
  // Touche M : menu. (Phase de capture : passe avant les écouteurs de la page.)
  window.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && (etat.menu || etat.panneau || etat.pop)) { fermerTout(); e.preventDefault(); e.stopImmediatePropagation(); return; }
    const cible = (e.target && e.target.tagName) || "";
    if ((e.key === "m" || e.key === "M") && !e.ctrlKey && !e.altKey && !e.metaKey && !/^(INPUT|TEXTAREA|SELECT)$/.test(cible)) basculerMenu();
  }, true);

  majBoutons();
  rafraichir();
  setInterval(rafraichir, 2000);
  window.JarvisWidgets = { basculerMenu, fermerTout, majBoutons, etat };
})();
