# Changelog

Alle nennenswerten Änderungen. Versionen folgen [Semantic Versioning](https://semver.org/lang/de/).

## Unveröffentlicht

- Docker-Image auch für arm64 (z. B. Raspberry Pi).
- `PUBLIC_URL` ist jetzt optional: Ohne Angabe nimmt die App die Adresse aus der Anfrage (`Host`, hinter einem Proxy `X-Forwarded-Host`/`-Proto`). Vorher zeigte das Vorschaubild ohne `PUBLIC_URL` auf roulette.hessis.eu. Nur einfache Hostnamen werden übernommen.
- Der User-Agent nennt ohne `PUBLIC_URL` die Projektseite statt roulette.hessis.eu.
- Tests mit der Standardbibliothek (`python -m unittest`), die CI führt sie bei jedem Pull Request aus.
- Kommentare und Meldungen im Code auf Englisch, passend zur Dokumentation.

## 0.3.1

- Die Seite gibt es in sechs Sprachen: Deutsch, Englisch, Französisch, Spanisch, Italienisch und Niederländisch. Vorgabe ist die Browsersprache, sonst Englisch; die Wahl oben rechts merkt sich der Browser.
- Fehlermeldungen kommen vom Server als Code und erscheinen in der gewählten Sprache.
- Saubere Zeilenumbrüche in Titel, Hinweisen und Footer, keine einzelnen Wörter mehr allein in der letzten Zeile.
- Statische Dateien werden nur noch mit fest hinterlegten Dateitypen ausgeliefert, unbekannte Endungen ergeben 404 (Hinweis aus CodeQL).

## 0.3.0

- Eigenes Logo: Glücksrad in den Plattformfarben mit goldener Nabe, auch als Favicon und App-Icon.
- Edlere Schrift: Playfair Display für Überschriften, Rad und Buttons, Manrope für Text; goldener Schriftzug.
- Schriften liegen lokal auf dem Server, die Seite lädt keine Schriften von Dritten.
- Neues Vorschaubild für geteilte Links.
- README auf Englisch und Deutsch mit Screenshots, Einstellungen und Hinweisen zu den Zugängen.
- Lizenz: GNU AGPL 3.0 oder später. Der Footer verlinkt auf den Quellcode (`SOURCE_URL`, leer blendet den Link aus).

## 0.2.0

- Glücksrad in den Plattformfarben: Drehen wählt eine zufällige Plattform, Segmente und Buttons wählen gezielt.
- Filter „Nur kostenlose Modelle“ und „NSFW ausblenden“ (Standard an) für Printables, Cults3D und Thingiverse; MakerWorld zeigt einen Hinweis, weil die Sitemap keine Angaben liefert.
- Verlauf der letzten zwölf Würfe im Browser, Leertaste würfelt erneut.
- Cults3D würfelt jetzt aus zufälligen Wochen seit 2014 statt nur aus den neuesten 50.000 Modellen.
- Der erste Wurf auf Printables und Thingiverse wartet nicht mehr auf die tägliche Suche nach der höchsten Modell-ID.
- Favicon und Vorschaubild für geteilte Links; Animationen ruhen bei „Bewegung reduzieren“.

## 0.1.0

Erste Version.

- Ein Button je Plattform: MakerWorld, Printables, Cults3D und Thingiverse. Die Karte färbt sich in der Farbe der gewählten Plattform.
- MakerWorld über die öffentlichen Sitemaps, Printables über die öffentliche GraphQL-API, Cults3D und Thingiverse über ihre offiziellen APIs mit Schlüssel bzw. Token.
- Vorschaubild, Titel und Ersteller, soweit die Plattform sie liefert; Links öffnen direkt die Modellseite.
- Fehlende Zugänge grauen den jeweiligen Button aus statt die Seite zu stören.
- Härtung: Links und Bilder nur zu bekannten Hosts, strikte Content-Security-Policy ohne Inline-Code, Schutz-Header, Ratenbegrenzung pro IP, begrenzte Antwortgrößen, Container ohne Root, read-only und ohne Capabilities.
- Docker-Image (amd64) unter `ghcr.io/schnuecks/print-roulette`.
