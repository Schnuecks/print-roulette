# Print Roulette

Kleine Webseite mit Glücksrad: Dreh am Rad oder wähl eine Plattform direkt und bekomm ein zufälliges 3D-Modell mit Link.

Quellen: MakerWorld, Printables, Cults3D, Thingiverse. Keine Datenbank, kein Login, nichts wird gespeichert.

## Quellen und Zugänge

| Quelle | Woher | Zugang |
|---|---|---|
| MakerWorld | öffentliche Sitemaps, nur Titel + Link | keiner |
| Printables | öffentliche GraphQL-API, Zufalls-ID | keiner |
| Cults3D | offizielle GraphQL-API | `CULTS_USER` + `CULTS_API_KEY` (Schlüssel unter cults3d.com/en/api/keys) |
| Thingiverse | offizielle REST-API, Zufalls-ID | `THINGIVERSE_TOKEN` (App-Token unter thingiverse.com/developers) |

Jede Variable kann auch als `NAME_FILE` auf eine Datei zeigen (Docker-Secrets). Fehlt der Zugang, ist der Button ausgegraut.

## Bedienung

- **Rad drehen:** wählt zufällig eine Plattform und dann ein Modell. Ein Klick auf ein Segment oder einen Plattform-Button würfelt gezielt dort.
- **Leertaste:** würfelt noch mal wie zuletzt.
- **Filter:** „Nur kostenlose Modelle“ und „NSFW ausblenden“ (Standard an). Printables, Cults3D und Thingiverse liefern die nötigen Angaben, MakerWorld nicht; dort weist die Karte darauf hin.
- **Verlauf:** die letzten zwölf Würfe, nur im eigenen Browser gespeichert.

## Starten

Fertiges Image: `ghcr.io/schnuecks/print-roulette` (Tags je Version, z. B. `0.2.0` und `0.2`, sowie `latest`). Oder selbst bauen:

```bash
docker compose up -d --build
```

Danach auf http://localhost:8080. Ohne Docker: `python app.py`.

Weitere Einstellungen: `MW_LANG` (Sprache der MakerWorld-Links, Standard `en`), `PUBLIC_URL` (für das Vorschaubild geteilter Links, Standard `https://roulette.hessis.eu`), `USER_AGENT`.

## Sicherheit

- Der Browser bekommt nur Links und Bilder auf bekannte Hosts der vier Plattformen, alles andere wird verworfen.
- Strikte Content-Security-Policy ohne Inline-Code, dazu die üblichen Schutz-Header.
- Ratenbegrenzung pro IP (`RATE_PER_MINUTE`, Standard 30 Würfe pro Minute). Hinter einem Proxy zählt `X-Forwarded-For` (`TRUST_PROXY=1`), ohne Proxy auf `0` setzen.
- Antworten der Plattformen sind auf 8 MB begrenzt, Fehlertexte gehen nur ins Log, nicht an den Browser.
- Der Container läuft ohne Root, read-only und ohne Capabilities. CI prüft mit Ruff (inkl. Sicherheitsregeln) und scannt das Image mit Trivy.
