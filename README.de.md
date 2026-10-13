<p align="center"><img src="static/logo.svg" width="96" alt="Print Roulette"></p>

# Print Roulette

[English](README.md) · **Deutsch**

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white" alt="Python 3.12">
  <img src="https://img.shields.io/badge/dependencies-none-4C9A2A" alt="Keine Abhängigkeiten">
  <a href="https://github.com/Schnuecks/print-roulette/pkgs/container/print-roulette"><img src="https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white" alt="Docker ready"></a>
  <img src="https://img.shields.io/badge/platform-amd64%20%7C%20arm64-E4572E" alt="Plattform amd64 | arm64">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-AGPL--3.0-4C9A2A" alt="Lizenz AGPL-3.0"></a>
  <img src="https://img.shields.io/badge/maintained-yes-4C9A2A" alt="Gepflegt">
</p>

Dreh am Rad und entdeck einen zufälligen 3D-Druck. Print Roulette wählt ein Modell von
**MakerWorld**, **Printables**, **Cults3D** oder **Thingiverse** und verlinkt direkt auf
dessen Seite. Für die Abende, an denen du etwas drucken willst, aber nicht weißt, was.

<p align="center">
  <img src="docs/screenshots/desktop-dark.png" width="640" alt="Print Roulette mit Glücksrad, Treffer und Verlauf">
  &nbsp;
  <img src="docs/screenshots/mobile-light.png" width="200" alt="Print Roulette auf dem Handy im hellen Modus">
</p>

## Funktionen

- **Glücksrad** in den Plattformfarben: drehen für eine zufällige Plattform, oder per Klick
  auf ein Segment oder einen Button gezielt auf einer Plattform würfeln
- **Vorschaubild, Titel und Ersteller,** soweit die Plattform sie liefert; jeder Treffer
  verlinkt auf die Originalseite des Modells
- **Filter** für nur kostenlose Modelle und zum Ausblenden von NSFW-Inhalten (standardmäßig an)
- **Verlauf** der letzten zwölf Würfe, nur im eigenen Browser gespeichert
- **Tastatur:** die Leertaste würfelt noch mal wie zuletzt
- **Sechs Sprachen:** Deutsch, Englisch, Französisch, Spanisch, Italienisch und Niederländisch;
  vorgegeben ist die Browsersprache, die Wahl merkt sich der Browser
- **Keine Datenbank, kein Login, kein Tracking:** auf dem Server wird nichts gespeichert
- **Hell und dunkel,** funktioniert auf dem Handy, beachtet „Bewegung reduzieren“
- **Kleiner Container:** nur Standardbibliothek, läuft ohne Root mit schreibgeschütztem
  Dateisystem und eingebautem Healthcheck

## Plattformen

| Plattform | Quelle | Zugang | Filter kostenlos | Filter NSFW |
|---|---|---|---|---|
| MakerWorld | öffentliche Sitemaps, nur Titel und Link | keiner | – | – |
| Printables | öffentliche GraphQL-API, zufällige Modell-ID | keiner | ✓ | ✓ |
| Cults3D | offizielle GraphQL-API, zufällige Woche seit 2014 | Nickname + API-Schlüssel | ✓ | ✓ |
| Thingiverse | offizielle REST-API, zufällige Modell-ID | App-Token | immer kostenlos | ✓ |

Plattformen ohne Zugang sind ausgegraut und fehlen auf dem Rad. Die Sitemaps von MakerWorld
enthalten weder Preis noch NSFW-Kennzeichen, deshalb sagt die Ergebniskarte dort, wenn ein
Filter nicht greift.

## Schnellstart

```yaml
services:
  print-roulette:
    image: ghcr.io/schnuecks/print-roulette:latest
    container_name: print-roulette
    restart: unless-stopped
    read_only: true
    cap_drop: [ALL]
    ports:
      - "8080:8080"
    environment:
      # PUBLIC_URL: https://roulette.example.com   # optional, sonst aus der Anfrage
      CULTS_USER: dein-cults-nickname
      CULTS_API_KEY_FILE: /run/secrets/cults_api_key
      THINGIVERSE_TOKEN_FILE: /run/secrets/thingiverse_token
    secrets:
      - cults_api_key
      - thingiverse_token

secrets:
  cults_api_key:
    file: ./secrets/cults_api_key.txt
  thingiverse_token:
    file: ./secrets/thingiverse_token.txt
```

```bash
docker compose up -d
```

Danach http://localhost:8080 öffnen. Ohne Docker: `python app.py` (Python 3.12, keine Pakete
nötig).

### Zugänge besorgen

- **Cults3D:** unter [cults3d.com/en/api/keys](https://cults3d.com/en/api/keys) einen
  schreibgeschützten API-Schlüssel anlegen. Der Benutzername ist dein Cults-Nickname.
- **Thingiverse:** unter [thingiverse.com/developers](https://www.thingiverse.com/developers)
  eine App vom Typ „Web App“ anlegen und deren *App Token* verwenden.

**Hinter einem Reverse Proxy mit eigenen Fehlerseiten** (z. B. einer Traefik-Middleware
`errors`) nimm `/api/` davon aus. Die Seite liest die JSON-Fehlerantworten der API, um
Meldungen in der gewählten Sprache anzuzeigen. Bei Traefik geht das mit einem zweiten Router
für `PathPrefix(`/api/`)` ohne die Fehler-Middleware.

Docker-Secrets werden mit den Rechten der Datei auf dem Host eingebunden. Kann der Container
sie nicht lesen, starte ihn mit deinem Benutzer (`user: "1000:1000"`) oder mach die Dateien
lesbar.

## Einstellungen

Jede Variable mit einem Zugang kann auch als `NAME_FILE` auf eine Datei zeigen.

| Variable | Standard | Bedeutung |
|---|---|---|
| `PORT` | `8080` | Port im Container |
| `PUBLIC_URL` | – (aus der Anfrage) | Öffentliche Adresse für das Vorschaubild geteilter Links. Leer: wird aus der Anfrage genommen (`Host`, hinter einem Proxy `X-Forwarded-Host`/`-Proto`) |
| `CULTS_USER`, `CULTS_API_KEY` | – | Zugang zu Cults3D |
| `THINGIVERSE_TOKEN` | – | App-Token für Thingiverse |
| `MW_LANG` | `en` | Sprache der MakerWorld-Links (`en`, `de`, …) |
| `RATE_PER_MINUTE` | `30` | Würfe pro IP und Minute |
| `TRUST_PROXY` | `1` | Clients nach `X-Forwarded-For` zählen (hinter einem Reverse Proxy); ohne Proxy `0` |
| `USER_AGENT` | `PrintRoulette/<Version> (+PUBLIC_URL oder Projekt-URL)` | User-Agent für Anfragen an die Plattformen |
| `SOURCE_URL` | `https://github.com/Schnuecks/print-roulette` | Link auf den Quellcode im Footer; leer blendet ihn aus |
| `PRINTABLES_MAX_ID`, `THINGIVERSE_MAX_ID` | eingebaut | Startwert für die höchste Modell-ID; die App tastet einmal am Tag nach oben |

## Rücksicht auf die Plattformen

- MakerWorld: Der Sitemap-Index wird höchstens einmal am Tag geladen, Sitemap-Seiten werden
  zwischengespeichert.
- Cults3D: höchstens ein API-Aufruf alle drei Minuten, die Treffer liegen in einem Vorrat,
  weit unter dem Tageslimit.
- Printables und Thingiverse: eine Anfrage pro Wurf, dazu eine kurze tägliche Suche nach
  neuen IDs.
- Jede Anfrage gibt sich mit einem ehrlichen User-Agent zu erkennen.

## Sicherheit

- Links und Bilder erreichen den Browser nur, wenn sie HTTPS nutzen und auf bekannte Hosts
  der vier Plattformen zeigen.
- Strikte Content-Security-Policy ohne Inline-Code, dazu die üblichen Schutz-Header.
- Ratenbegrenzung pro IP, Antworten der Plattformen sind auf 8 MB begrenzt, Fehlerdetails
  bleiben im Log.
- Schriften und Icons kommen vom eigenen Server, die Seite lädt außer den Vorschaubildern der
  Plattformen nichts von Dritten.
- Die CI prüft den Code mit Ruff (inklusive Sicherheitsregeln) und scannt das Image mit Trivy.

Was sich in einer Version geändert hat, steht im [CHANGELOG](CHANGELOG.md).

## Wie es entsteht

Print Roulette entsteht mit Unterstützung eines KI-Assistenten. Funktionen und Verhalten lege
ich fest, prüfe die Änderungen und teste sie auf meinem eigenen Server. Veröffentlicht wird
nur, was die automatischen Prüfungen besteht: die Tests und ein Sicherheitsscan des Container-
Images.

## Unterstützen

Print Roulette ist kostenlos und bleibt es. Wenn es dir einen schönen Druck beschert hat, kannst
du mir einen Kaffee auf Ko-fi ausgeben; das hält das Projekt am Laufen. Danke!

<p>
  <a href="https://ko-fi.com/schnuecks"><img src="https://ko-fi.com/img/githubbutton_sm.svg" alt="Support me on Ko-fi"></a>
</p>

## Rückmeldungen

Fehler und Ideen sind als [Issue auf GitHub](https://github.com/Schnuecks/print-roulette/issues)
willkommen. Sicherheitsprobleme bitte vertraulich melden, siehe [SECURITY.md](SECURITY.md).

## Lizenz

Copyright (C) 2026 Schnuecks

Print Roulette ist freie Software unter der
[GNU Affero General Public License, Version 3 oder später](LICENSE)
(AGPL-3.0-or-later). Du darfst es nutzen, verändern und weitergeben.

Gibst du eine veränderte Fassung weiter oder bietest sie anderen über ein Netzwerk zur
Nutzung an, musst du ihnen den Quellcode deiner Fassung unter derselben Lizenz
zugänglich machen. Der Link „Quellcode auf GitHub“ im Footer erfüllt das für diese
Fassung; bei einer eigenen Fassung richte ihn mit `SOURCE_URL` auf deinen Quellcode.

Das Programm wird ohne jede Gewährleistung bereitgestellt. Einzelheiten stehen in der
[Lizenz](LICENSE). Die Schriften Playfair Display und Manrope in `static/fonts/` stehen
unter der SIL Open Font License (siehe die Dateien `OFL-*.txt` dort); Print Roulette liefert
sie selbst aus, die Seite lädt keine Schriften von Google oder anderen Servern.

Print Roulette ist ein unabhängiges Hobbyprojekt und gehört nicht zu MakerWorld,
Printables, Cults3D oder Thingiverse. Modelle und Bilder gehören den jeweiligen Plattformen
und Erstellern.
