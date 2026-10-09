# Changelog

Alle nennenswerten Änderungen. Versionen folgen [Semantic Versioning](https://semver.org/lang/de/).

## 0.1.0

Erste Version.

- Ein Button je Plattform: MakerWorld, Printables, Cults3D und Thingiverse. Die Karte färbt sich in der Farbe der gewählten Plattform.
- MakerWorld über die öffentlichen Sitemaps, Printables über die öffentliche GraphQL-API, Cults3D und Thingiverse über ihre offiziellen APIs mit Schlüssel bzw. Token.
- Vorschaubild, Titel und Ersteller, soweit die Plattform sie liefert; Links öffnen direkt die Modellseite.
- Fehlende Zugänge grauen den jeweiligen Button aus statt die Seite zu stören.
- Härtung: Links und Bilder nur zu bekannten Hosts, strikte Content-Security-Policy ohne Inline-Code, Schutz-Header, Ratenbegrenzung pro IP, begrenzte Antwortgrößen, Container ohne Root, read-only und ohne Capabilities.
- Docker-Image (amd64) unter `ghcr.io/schnuecks/print-roulette`.
