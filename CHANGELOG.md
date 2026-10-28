# Changelog

Alle nennenswerten Änderungen. Versionen folgen [Semantic Versioning](https://semver.org/lang/de/).

## 0.6.1

- pip ist nicht mehr im Docker-Image. Die App braucht es zur Laufzeit nicht, und die darin mitgelieferten Pakete (urllib3, msgpack, setuptools) lösten Funde im Image-Scan aus.

## 0.6.0

- MakerWorld zeigt jetzt Vorschaubild und Ersteller, und beide Filter (kostenlos, NSFW) greifen auch dort. Die Details kommen pro Wurf aus der Modell-API von MakerWorld, das Modell selbst weiter zufällig aus den Sitemaps.
- Cults3D: Jeder API-Aufruf holt Modelle aus fünf zufälligen Wochen statt aus einer, und ein gezeigtes Modell verlässt den Vorrat. Würfe hintereinander zeigen dadurch nicht mehr fast dasselbe. Die Zahl der API-Aufrufe bleibt gleich.
- Eine Fehlermeldung erscheint erst, wenn das Rad stehen bleibt; vorher waren die Knöpfe schon während der Drehung wieder frei.
- Beschreibung und Linkvorschau der Seite auf Englisch, passend zur Standardsprache.
- Das Docker-Image bringt einen eigenen `HEALTHCHECK` mit (fragt `/healthz` ab).

## 0.5.2

Nach dem ZAP-Baseline-Scan (keine echte Lücke, nur Härtung):

- Content-Security-Policy: Bilder nur noch von den Bild-Hosts der Plattformen statt von jeder HTTPS-Adresse.
- Neuer Header `Cross-Origin-Embedder-Policy: credentialless`; die Vorschaubilder fremder Hosts laden weiter.
- `.zap/rules.tsv` blendet die Fehlalarme des Scans aus (fehlende `Sec-Fetch-*` in ZAPs Anfragen, Cache-Hinweise, Wörter in JavaScript-Kommentaren).

## 0.5.1

Härtung nach einem Security-Review:

- Ratenbegrenzung hinter einem Proxy: Die Client-Adresse ist jetzt der Eintrag von hinten in `X-Forwarded-For`, den der eigene Proxy gesetzt hat (`TRUSTED_PROXY_HOPS`, Standard 1). Vorne angehängte Werte des Clients zählen nicht mehr.
- **`TRUST_PROXY` ist jetzt standardmäßig `0`.** Hinter einem Reverse Proxy muss `TRUST_PROXY=1` gesetzt werden, sonst zählen alle Besucher als ein Client.
- Höchstens `MAX_ROLLS` Würfe gleichzeitig (Standard 8), weitere bekommen sofort eine kurze Meldung in der gewählten Sprache.
- Kürzere Zeitlimits für Anfragen an die Plattformen (8 s, ein Wurf höchstens 20 s).
- Cults3D: Nur eine Anfrage füllt den Vorrat gleichzeitig, auch ein leerer Vorrat wird höchstens alle 15 s nachgefüllt, nach Fehlern pausiert das Nachfüllen zwei Minuten.
- Ohne `PUBLIC_URL` wird die Startseite mit `Cache-Control: private` ausgeliefert, damit geteilte Caches keine fremde Adresse im Vorschaubild behalten.
- Basis-Image per Digest und GitHub Actions per Commit-SHA festgelegt; Dependabot hält beides aktuell.

## 0.5.0

- Python 3.15 im Docker-Image (vorher 3.13); die CI testet ebenfalls mit 3.15.
- README: kurzer Abschnitt, wie das Projekt entsteht.

## 0.4.0

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
