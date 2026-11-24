// Rendu d'un skit stick-stage (tamtree-ai/stick-stage, MIT, cloné dans Videos\outils\stick-stage, hors git) pour l'agent videos-creation.
// 2 onglets Chrome au plus (serveur à 5,9 Go de RAM). Lancé par rendu_stickstage.py depuis le dossier de l'outil :
//   npx tsx <ce fichier> <skitId> <sortie.mp4>
import path from "node:path";
import { fileURLToPath } from "node:url";
import { remotionBackend } from "../outils/stick-stage/src/node";

const OUTIL = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../outils/stick-stage");
const [id, out] = process.argv.slice(2);
if (!id || !out) { console.error("usage : stickstage-rendu.mts <skitId> <sortie.mp4>"); process.exit(2); }
const t0 = Date.now();
await remotionBackend({ entryPoint: path.join(OUTIL, "src/app/index.ts") }).renderSkit(id, path.resolve(out), { concurrency: 2, onProgress: () => undefined });
console.log(`rendu ${id} en ${((Date.now() - t0) / 1000).toFixed(1)} s`);
