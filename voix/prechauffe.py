"""Pré-synthèse (edge-tts) des phrases fréquentes de Jarvis : python prechauffe.py items.json
items.json = [{"voix": "...", "texte": "...", "cible": "chemin.mp3", "rate": "-4%", "pitch": "-2Hz", "volume": "+0%"}, ...]. Écrit chaque fichier en .part puis le renomme (jamais de fichier à moitié écrit dans le cache)."""
import asyncio, json, os, sys
import edge_tts

async def main():
    items = json.load(open(sys.argv[1], encoding="utf-8"))
    for it in items:
        cible = it["cible"]
        if os.path.exists(cible) and os.path.getsize(cible) > 500:
            continue
        os.makedirs(os.path.dirname(cible), exist_ok=True)
        part = cible + ".part"
        try:
            await edge_tts.Communicate(it["texte"], it["voix"], rate=it.get("rate", "+0%"), volume=it.get("volume", "+0%"), pitch=it.get("pitch", "+0Hz")).save(part)
            if os.path.getsize(part) > 500:
                os.replace(part, cible)
        except Exception:
            pass
        finally:
            try:
                if os.path.exists(part): os.remove(part)
            except Exception:
                pass

asyncio.run(main())
