// Workspace « Pilotage » : Aperçu, Initiatives, Missions, Tâches, Analytics. JS vanilla, aucun appel réseau externe, aucun eval.
// Tout texte venant des fichiers (initiatives, tâches, candidatures, missions...) est une DONNÉE : posé avec textContent (via h()), jamais avec innerHTML.
// Les boutons Approuver / Rejeter / Plus tard envoient POST /pilotage-action : Jarvis appelle alors les MÊMES fonctions que les commandes Discord.
(function () {
  "use strict";
  const UI = window.JarvisUI;
  const h = UI.h;
  const SVG = "http://www.w3.org/2000/svg";
  const SECTIONS = [["apercu", "Aperçu"], ["initiatives", "Initiatives"], ["missions", "Missions"], ["taches", "Tâches"], ["analytics", "Analytics"]];
  let derniere = null;
  let conversationOuverte = true;

  function age(heures) {
    if (!(heures >= 1)) return "à l'instant";
    if (heures < 48) return "il y a " + Math.floor(heures) + " h";
    return "il y a " + Math.floor(heures / 24) + " j";
  }
  function remplacer(id, ...noeuds) {
    const e = document.getElementById(id);
    if (e) e.replaceChildren(...noeuds.flat(Infinity).filter((n) => n !== null && n !== undefined && n !== false));
  }
  function carteInfo(titre, valeur, detail) {
    return h("div", { class: "info" }, h("span", { class: "lib" }, titre), h("b", null, valeur), detail ? h("small", null, detail) : null);
  }
  function annoncer(texte, ok) {
    const t = document.getElementById("toast");
    if (!t) return;
    t.textContent = texte;
    t.className = "toast visible " + (ok ? "ok" : "ko");
    setTimeout(() => { t.className = "toast"; }, 4000);
  }

  // ---------- Aperçu ----------
  function rendreApercu(d) {
    const a = d.apercu || {};
    remplacer("zone-apercu",
      h("div", { class: "grille" },
        carteInfo("Voix", a.voix_active ? "Active" : "Coupée", a.voix_active ? "le micro est autorisé (voix_actif)" : "aucune détection vocale (voix_actif = non)"),
        carteInfo("Jarvis", a.sourdine ? "En sourdine" : (a.mode_jeu ? "Mode jeu" : "Actif"), a.sourdine ? "il n'exécute aucune commande" : ""),
        carteInfo("À traiter", String(a.initiatives_a_traiter || 0), "initiative(s) en attente de ton arbitrage"),
        carteInfo("Dernière revue de nuit", a.derniere_revue_initiatives || "—", "leçons : " + (a.derniere_revue_lecons || "—"))),
      h("h3", null, "Veilles"),
      h("ul", { class: "liste" }, (a.veilles || []).map((v) => h("li", null, h("span", { class: v.actif ? "pastille on" : "pastille" }), v.nom, " · ", v.actif ? "active" : "désactivée"))));
  }

  // ---------- Initiatives ----------
  async function agir(id, action) {
    try {
      const r = await UI.poster("/pilotage-action", { action, id });
      annoncer(r.texte || (r.ok ? "Fait." : "Refusé."), !!r.ok);
    } catch (e) { annoncer("Jarvis ne répond pas.", false); }
    charger();
  }
  function carteInitiative(i, avecDetail) {
    const detail = h("div", { class: "detail", hidden: "hidden" },
      h("div", null, "Numéro : " + i.id), h("div", null, "Source : " + i.source), h("div", null, "Statut : " + i.statut), h("div", null, "Type : " + i.type));
    const boutons = i.statut === "en_attente" ? h("div", { class: "actions" },
      h("button", { class: "btn principal", on: { click: () => agir(i.id, "approuver") } }, "Approuver"),
      h("button", { class: "btn", on: { click: () => agir(i.id, "rejeter") } }, "Rejeter"),
      h("button", { class: "btn", on: { click: () => agir(i.id, "plus_tard") } }, "Plus tard")) : h("div", { class: "actions" }, h("span", { class: "etiquette" }, "Oubliée (plus de 4 jours sans réponse)"));
    const voir = avecDetail ? h("button", { class: "lien", on: { click: () => { if (detail.hasAttribute("hidden")) detail.removeAttribute("hidden"); else detail.setAttribute("hidden", "hidden"); } } }, "Voir l'initiative") : null;
    return h("article", { class: "carte " + (i.urgence === "haute" ? "urgente" : "normale"), id: "init-" + i.id },
      h("div", { class: "barre" }),
      h("div", { class: "contenu" },
        h("div", { class: "ligne" }, h("span", { class: "etiquette" }, i.type_libelle), i.urgence === "haute" ? h("span", { class: "etiquette urgent" }, "Urgente") : null, h("span", { class: "age" }, age(i.age_heures))),
        h("h3", null, i.titre), h("p", null, i.raison), boutons, voir, detail));
  }
  function rendreInitiatives(d) {
    const ini = d.initiatives || { en_attente: [], maintenance: [], a_traiter: 0 };
    remplacer("zone-initiatives",
      h("header", { class: "entete" }, h("h2", null, "Ce qui mérite ton arbitrage"), h("span", { class: "badge" }, ini.a_traiter + " à traiter")),
      h("h3", null, "En attente"),
      ini.en_attente.length ? ini.en_attente.map((i) => carteInitiative(i, false)) : h("p", { class: "vide" }, "Rien à arbitrer pour le moment."),
      h("h3", null, "Maintenance"),
      ini.maintenance.length ? ini.maintenance.map((i) => carteInitiative(i, true)) : h("p", { class: "vide" }, "Aucune initiative oubliée ni promotion de leçon."));
  }

  // ---------- Missions, tâches ----------
  function rendreMissions(d) {
    const m = d.missions || [];
    remplacer("zone-missions", h("h2", null, "Missions de l'agent de développement"), h("p", { class: "note" }, "Lecture seule."),
      m.length ? m.map((x) => h("article", { class: "carte normale" }, h("div", { class: "barre" }), h("div", { class: "contenu" },
        h("div", { class: "ligne" }, h("span", { class: "etiquette" }, "Tâche " + x.id), h("span", { class: "etiquette" }, x.statut), h("span", { class: "age" }, x.nuit)), h("p", null, x.texte), x.raison ? h("p", { class: "note" }, x.raison) : null))) : h("p", { class: "vide" }, "Aucune mission."));
  }
  function rendreTaches(d) {
    const t = d.taches || { todo: [], candidatures: [] };
    remplacer("zone-taches", h("h2", null, "Tâches"), h("p", { class: "note" }, "Lecture seule."),
      h("div", { class: "deux" },
        h("section", null, h("h3", null, "To-do"), t.todo.length ? h("ul", { class: "liste" }, t.todo.map((x) => h("li", { class: x.fait ? "fait" : "" }, (x.fait ? "☑ " : "☐ ") + x.texte))) : h("p", { class: "vide" }, "Aucune tâche.")),
        h("section", null, h("h3", null, "Candidatures"), t.candidatures.length ? h("ul", { class: "liste" }, t.candidatures.map((c) => h("li", null, h("b", null, c.entreprise), " — " + c.poste + " · ", h("span", { class: "etiquette" }, c.statut), " " + c.date))) : h("p", { class: "vide" }, "Aucune candidature suivie."))));
  }

  // ---------- Analytics (SVG local) ----------
  function courbe(points) {
    const L = 360, H = 90, m = 6;
    const vs = points.map((p) => p.valeur), mini = Math.min(...vs), maxi = Math.max(...vs), ecart = maxi - mini || 1;
    const x = (i) => m + (points.length === 1 ? 0 : (i * (L - 2 * m)) / (points.length - 1));
    const y = (v) => H - m - ((v - mini) * (H - 2 * m)) / ecart;
    const svg = document.createElementNS(SVG, "svg");
    svg.setAttribute("viewBox", "0 0 " + L + " " + H); svg.setAttribute("class", "courbe"); svg.setAttribute("role", "img");
    const ligne = document.createElementNS(SVG, "polyline");
    ligne.setAttribute("points", points.map((p, i) => x(i).toFixed(1) + "," + y(p.valeur).toFixed(1)).join(" "));
    ligne.setAttribute("fill", "none"); ligne.setAttribute("stroke", "#4fd2ff"); ligne.setAttribute("stroke-width", "2");
    svg.append(ligne);
    points.forEach((p, i) => { const c = document.createElementNS(SVG, "circle"); c.setAttribute("cx", x(i).toFixed(1)); c.setAttribute("cy", y(p.valeur).toFixed(1)); c.setAttribute("r", "2.5"); c.setAttribute("fill", "#9be9ff"); svg.append(c); });
    return svg;
  }
  function rendreAnalytics(d) {
    const s = (d.analytics && d.analytics.series) || [];
    remplacer("zone-analytics", h("h2", null, "Analytics du SaaS"), h("p", { class: "note" }, "Relevés locaux, lecture seule."),
      s.length ? h("div", { class: "grille" }, s.map((x) => {
        const der = x.points[x.points.length - 1];
        return h("div", { class: "info large" }, h("span", { class: "lib" }, x.nom), h("b", null, String(der.valeur)), h("small", null, der.date),
          x.points.length > 1 ? courbe(x.points) : h("small", null, "pas assez de relevés pour un graphique"));
      })) : h("p", { class: "vide" }, "Aucun relevé SaaS."));
  }

  // ---------- Conversation (panneau latéral qui s'ouvre et se ferme, comme le bouton Conv. de l'accueil) ----------
  function rendreConversation(d) {
    const c = d.conversation || [];
    remplacer("zone-conversation", h("h3", null, "Conversation"), c.length ? c.map((m) => h("div", { class: "msg " + (m.role === "liam" ? "liam" : "jarvis") }, h("b", null, m.role === "liam" ? "Vous" : "Jarvis"), " " + m.texte)) : h("p", { class: "vide" }, "Rien de dit pour le moment."));
    const z = document.getElementById("zone-conversation"); if (z) { if (conversationOuverte) z.removeAttribute("hidden"); else z.setAttribute("hidden", "hidden"); }
  }
  window.JarvisConv = {
    ouverte: () => conversationOuverte,
    basculer: () => { conversationOuverte = !conversationOuverte; if (derniere) rendreConversation(derniere); },
  };

  // ---------- Ensemble ----------
  function rendre(d) {
    derniere = d;
    rendreApercu(d); rendreInitiatives(d); rendreMissions(d); rendreTaches(d); rendreAnalytics(d); rendreConversation(d);
    const b = document.getElementById("badge-nav");
    if (b) b.textContent = String(((d.initiatives && d.initiatives.a_traiter) || 0));
  }
  async function charger() {
    try { rendre(await UI.lire("/pilotage-donnees")); } catch (e) { annoncer("Données indisponibles.", false); }
  }
  function montrer(id) {
    for (const [cle] of SECTIONS) {
      const p = document.getElementById("zone-" + cle), n = document.getElementById("nav-" + cle);
      if (p) { if (cle === id) p.removeAttribute("hidden"); else p.setAttribute("hidden", "hidden"); }
      if (n) n.setAttribute("aria-current", cle === id ? "page" : "false");
    }
  }
  function init() {
    remplacer("nav-liste", SECTIONS.map(([cle, nom]) => h("button", { class: "nav", id: "nav-" + cle, on: { click: () => montrer(cle) } }, nom, cle === "initiatives" ? h("span", { class: "badge", id: "badge-nav" }, "0") : null)));
    montrer("initiatives");
    charger();
    setInterval(() => { if (!document.hidden) charger(); }, 4000);
    window.addEventListener("keydown", (e) => { if (e.key === "Escape") UI.poster("/reduire", {}); });      // (le menu, s'il est ouvert, a déjà capté Échap)
  }
  window.Pilotage = { rendre, init, montrer, age, agir };
})();
