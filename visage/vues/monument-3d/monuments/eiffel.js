// Tour Eiffel en géométrie procédurale : quatre arêtes courbes, treillis en X, arcs, trois plates-formes, flèche. Unités ~ mètres.
const HAUTEUR = 300;

function demiLargeur(y) {
  const t = 1 - y / HAUTEUR;
  return 3 + 59 * Math.pow(Math.max(t, 0), 2.3);
}

export const eiffel = {
  id: "eiffel",
  nom: "Tour Eiffel",
  hauteur: 324,
  camera: { position: [300, 200, 380], cible: [0, 140, 0] },
  construire(THREE) {
    const g = new THREE.Group();
    const matFer = new THREE.LineBasicMaterial({ color: 0xc8a27a });
    const matFerDoux = new THREE.LineBasicMaterial({ color: 0x8a6d52 });
    const matPlate = new THREE.MeshStandardMaterial({ color: 0x9c7a58, roughness: 0.7, metalness: 0.35 });
    const matSol = new THREE.MeshStandardMaterial({ color: 0x0b1118, roughness: 1, metalness: 0 });

    const NIVEAUX = 26;
    const ys = [];
    for (let i = 0; i <= NIVEAUX; i++) ys.push((HAUTEUR * i) / NIVEAUX);
    const coins = (y) => {
      const w = demiLargeur(y);
      return [[-w, y, -w], [w, y, -w], [w, y, w], [-w, y, w]];
    };

    // Arêtes (quatre montants courbes), anneaux horizontaux et croisillons en X sur chaque face
    const pts = [];
    for (let i = 0; i < NIVEAUX; i++) {
      const a = coins(ys[i]);
      const b = coins(ys[i + 1]);
      for (let k = 0; k < 4; k++) {
        const k2 = (k + 1) % 4;
        pts.push(...a[k], ...b[k]);                       // montant
        pts.push(...a[k], ...a[k2]);                      // anneau
        pts.push(...a[k], ...b[k2], ...a[k2], ...b[k]);   // croisillon en X sur la face
      }
    }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.Float32BufferAttribute(pts, 3));
    g.add(new THREE.LineSegments(geo, matFer));

    // Doublement des montants (épaisseur visuelle)
    const pts2 = [];
    for (let i = 0; i < NIVEAUX; i++) {
      const a = coins(ys[i]);
      const b = coins(ys[i + 1]);
      for (let k = 0; k < 4; k++) {
        const e = 0.9;
        const dx = a[k][0] > 0 ? -e : e;
        const dz = a[k][2] > 0 ? -e : e;
        pts2.push(a[k][0] + dx, a[k][1], a[k][2] + dz, b[k][0] + dx, b[k][1], b[k][2] + dz);
      }
    }
    const geo2 = new THREE.BufferGeometry();
    geo2.setAttribute("position", new THREE.Float32BufferAttribute(pts2, 3));
    g.add(new THREE.LineSegments(geo2, matFerDoux));

    // Grands arcs entre les pieds (quatre demi-tores)
    const w0 = demiLargeur(0);
    const arcGeo = new THREE.TorusGeometry(w0 * 0.62, 1.1, 6, 36, Math.PI);
    for (let k = 0; k < 4; k++) {
      const arc = new THREE.Mesh(arcGeo, matPlate);
      arc.position.y = 4;
      if (k === 0) arc.position.z = -w0;
      if (k === 1) arc.position.z = w0;
      if (k === 2) { arc.position.x = -w0; arc.rotation.y = Math.PI / 2; }
      if (k === 3) { arc.position.x = w0; arc.rotation.y = Math.PI / 2; }
      g.add(arc);
    }

    // Plates-formes (1er étage ~57 m, 2e ~115 m, sommet ~276 m)
    const etage = (y, epaisseur) => {
      const w = demiLargeur(y) + 1.5;
      const m = new THREE.Mesh(new THREE.BoxGeometry(w * 2, epaisseur, w * 2), matPlate);
      m.position.y = y;
      g.add(m);
    };
    etage(57, 4);
    etage(115, 3);
    etage(276, 3);

    // Flèche et antenne
    const fleche = new THREE.Mesh(new THREE.CylinderGeometry(0.6, 2.4, 48, 10), matPlate);
    fleche.position.y = 276 + 24;
    g.add(fleche);

    // Sol : disque sombre et repères discrets
    const sol = new THREE.Mesh(new THREE.CircleGeometry(520, 72), matSol);
    sol.rotation.x = -Math.PI / 2;
    sol.position.y = -0.2;
    g.add(sol);
    const grille = new THREE.GridHelper(1000, 40, 0x1d3a4d, 0x10202c);
    grille.position.y = 0;
    g.add(grille);
    return g;
  },
};
