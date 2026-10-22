// Registre des monuments : chacun est construit en géométrie procédurale simple (aucun modèle téléchargé).
import { eiffel } from "./eiffel.js";

export const MONUMENTS = { eiffel };

export function trouverMonument(id) {
  return MONUMENTS[id] || MONUMENTS.eiffel;
}
