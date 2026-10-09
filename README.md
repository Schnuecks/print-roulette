# Print Roulette

Kleine Webseite: ein Button je Plattform, ein Klick liefert ein zufälliges 3D-Modell mit Link.

Quellen: MakerWorld, Printables, Cults3D, Thingiverse. Keine Datenbank, kein Login, nichts wird gespeichert.

## Quellen und Zugänge

| Quelle | Woher | Zugang |
|---|---|---|
| MakerWorld | öffentliche Sitemaps, nur Titel + Link | keiner |
| Printables | öffentliche GraphQL-API, Zufalls-ID | keiner |
| Cults3D | offizielle GraphQL-API | `CULTS_USER` + `CULTS_API_KEY` (Schlüssel unter cults3d.com/en/api/keys) |
| Thingiverse | offizielle REST-API, Zufalls-ID | `THINGIVERSE_TOKEN` (App-Token unter thingiverse.com/developers) |

Jede Variable kann auch als `NAME_FILE` auf eine Datei zeigen (Docker-Secrets). Fehlt der Zugang, ist der Button ausgegraut.

## Starten

```bash
docker compose up -d --build
```

Danach auf http://localhost:8080. Ohne Docker: `python app.py`.

Weitere Einstellungen: `MW_LANG` (Sprache der MakerWorld-Links, Standard `en`), `USER_AGENT`, `CULTS_MAX_OFFSET`.
