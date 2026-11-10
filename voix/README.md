# voix — voix de Jarvis

Écoute (reconnaissance) et synthèse vocale, entièrement locales (Vosk, Piper), aucun réseau sauf `prechauffe.py` (edge-tts).

## Fichiers clés
- `ecoute.py` — écoute continue/ponctuelle (mot d'activation, fenêtre d'ordre, diagnostic).
- `reveil.py` — veille basse consommation : « réveille-toi Jarvis » ou double claquement de mains.
- `piper_serveur.py` — synthèse vocale locale (modèle chargé une fois, un WAV par ligne reçue).
- `prechauffe.py` — pré-génère les phrases fréquentes (edge-tts) dans le cache.
- `models/` — modèles Vosk/Piper.

## Voir aussi
- [lib](../lib/README.md) — `voix.ps1`, `voix-naturelle.ps1`
- [CLAUDE.md](../CLAUDE.md)
- [INDEX](../INDEX.md)
