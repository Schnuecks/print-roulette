'use strict';

/* Translations of the page, in six languages.
   Order of choice: saved choice, otherwise the browser language, otherwise English. */

const LANGUAGES = {
  de: 'Deutsch',
  en: 'English',
  fr: 'Français',
  es: 'Español',
  it: 'Italiano',
  nl: 'Nederlands',
};
const DEFAULT_LANG = 'en';
const LANG_KEY = 'pr-lang';

const STRINGS = {
  de: {
    spin: 'Drehen',
    spinAria: 'Rad drehen und zufällige Plattform wählen',
    wheelTitle: 'Rad mit den Plattformen',
    directAria: 'Plattform direkt wählen',
    free: 'Nur kostenlose Modelle',
    safe: 'NSFW ausblenden',
    start: 'Dreh am Rad oder wähl eine Plattform.',
    spinning: 'Das Rad dreht sich…',
    rollingOn: 'Würfle auf {name}…',
    by: 'von {creator}',
    opens: 'öffnet auf {source}',
    noFilterPrice: '{name} liefert keine Preise, der Filter greift hier nicht.',
    noFilterNsfw: '{name} kennzeichnet keine NSFW-Inhalte, der Filter greift hier nicht.',
    noFilterBoth: '{name} liefert weder Preise noch NSFW-Kennzeichen, die Filter greifen hier nicht.',
    hint: 'Leertaste: noch mal würfeln',
    historyTitle: 'Zuletzt gewürfelt',
    historyClear: 'Verlauf leeren',
    footer1: 'Unabhängiges Hobbyprojekt.',
    footer2: 'Modelle und Bilder gehören den jeweiligen Plattformen und Erstellern.',
    source: 'Quellcode auf GitHub',
    unknownSource: 'Unbekannte Plattform',
    notConfigured: '{name} ist auf diesem Server nicht eingerichtet.',
    unavailable: '{name} antwortet gerade nicht. Versuch es gleich noch mal.',
    rateLimit: 'Zu viele Würfe, warte einen Moment.',
    busy: 'Gerade würfeln sehr viele gleichzeitig. Versuch es gleich noch mal.',
    invalidLink: 'Ungültiger Link',
    noPlatform: 'Keine Plattform verfügbar',
    error: 'Fehler: {msg}',
    language: 'Sprache',
    untitled: 'Ohne Titel',
  },
  en: {
    spin: 'Spin',
    spinAria: 'Spin the wheel and pick a random platform',
    wheelTitle: 'Wheel with the platforms',
    directAria: 'Pick a platform directly',
    free: 'Free models only',
    safe: 'Hide NSFW',
    start: 'Spin the wheel or pick a platform.',
    spinning: 'The wheel is spinning…',
    rollingOn: 'Rolling on {name}…',
    by: 'by {creator}',
    opens: 'opens on {source}',
    noFilterPrice: '{name} has no prices, so the filter can’t apply here.',
    noFilterNsfw: '{name} doesn’t mark NSFW content, so the filter can’t apply here.',
    noFilterBoth: '{name} has no prices or NSFW marks, so the filters can’t apply here.',
    hint: 'Space bar: roll again',
    historyTitle: 'Recently rolled',
    historyClear: 'Clear history',
    footer1: 'Independent hobby project.',
    footer2: 'Models and images belong to their platforms and creators.',
    source: 'Source code on GitHub',
    unknownSource: 'Unknown platform',
    notConfigured: '{name} isn’t set up on this server.',
    unavailable: '{name} isn’t responding right now. Try again in a moment.',
    rateLimit: 'Too many rolls, wait a moment.',
    busy: 'Lots of people are rolling right now. Try again in a moment.',
    invalidLink: 'Invalid link',
    noPlatform: 'No platform available',
    error: 'Error: {msg}',
    language: 'Language',
    untitled: 'Untitled',
  },
  fr: {
    spin: 'Tourner',
    spinAria: 'Faire tourner la roue et choisir une plateforme au hasard',
    wheelTitle: 'Roue des plateformes',
    directAria: 'Choisir directement une plateforme',
    free: 'Modèles gratuits uniquement',
    safe: 'Masquer le contenu NSFW',
    start: 'Fais tourner la roue ou choisis une plateforme.',
    spinning: 'La roue tourne…',
    rollingOn: 'Tirage sur {name}…',
    by: 'par {creator}',
    opens: 's’ouvre sur {source}',
    noFilterPrice: '{name} n’indique pas de prix, le filtre ne s’applique pas ici.',
    noFilterNsfw: '{name} ne signale pas le contenu NSFW, le filtre ne s’applique pas ici.',
    noFilterBoth: '{name} n’indique ni prix ni contenu NSFW, les filtres ne s’appliquent pas ici.',
    hint: 'Barre d’espace : relancer',
    historyTitle: 'Derniers tirages',
    historyClear: 'Effacer l’historique',
    footer1: 'Projet amateur indépendant.',
    footer2: 'Les modèles et les images appartiennent à leurs plateformes et à leurs créateurs.',
    source: 'Code source sur GitHub',
    unknownSource: 'Plateforme inconnue',
    notConfigured: '{name} n’est pas configuré sur ce serveur.',
    unavailable: '{name} ne répond pas pour le moment. Réessaie dans un instant.',
    rateLimit: 'Trop de tirages, patiente un instant.',
    busy: 'Beaucoup de monde fait tourner la roue en ce moment. Réessaie dans un instant.',
    invalidLink: 'Lien invalide',
    noPlatform: 'Aucune plateforme disponible',
    error: 'Erreur : {msg}',
    language: 'Langue',
    untitled: 'Sans titre',
  },
  es: {
    spin: 'Girar',
    spinAria: 'Girar la ruleta y elegir una plataforma al azar',
    wheelTitle: 'Ruleta con las plataformas',
    directAria: 'Elegir una plataforma directamente',
    free: 'Solo modelos gratuitos',
    safe: 'Ocultar contenido NSFW',
    start: 'Gira la ruleta o elige una plataforma.',
    spinning: 'La ruleta está girando…',
    rollingOn: 'Buscando en {name}…',
    by: 'de {creator}',
    opens: 'se abre en {source}',
    noFilterPrice: '{name} no indica precios, así que el filtro no se aplica aquí.',
    noFilterNsfw: '{name} no marca el contenido NSFW, así que el filtro no se aplica aquí.',
    noFilterBoth: '{name} no indica precios ni contenido NSFW, así que los filtros no se aplican aquí.',
    hint: 'Barra espaciadora: volver a girar',
    historyTitle: 'Últimas tiradas',
    historyClear: 'Borrar historial',
    footer1: 'Proyecto personal independiente.',
    footer2: 'Los modelos y las imágenes pertenecen a sus plataformas y creadores.',
    source: 'Código fuente en GitHub',
    unknownSource: 'Plataforma desconocida',
    notConfigured: '{name} no está configurado en este servidor.',
    unavailable: '{name} no responde ahora mismo. Inténtalo de nuevo en un momento.',
    rateLimit: 'Demasiadas tiradas, espera un momento.',
    busy: 'Ahora mismo hay muchas tiradas a la vez. Inténtalo de nuevo en un momento.',
    invalidLink: 'Enlace no válido',
    noPlatform: 'No hay ninguna plataforma disponible',
    error: 'Error: {msg}',
    language: 'Idioma',
    untitled: 'Sin título',
  },
  it: {
    spin: 'Gira',
    spinAria: 'Gira la ruota e scegli una piattaforma a caso',
    wheelTitle: 'Ruota con le piattaforme',
    directAria: 'Scegli direttamente una piattaforma',
    free: 'Solo modelli gratuiti',
    safe: 'Nascondi contenuti NSFW',
    start: 'Gira la ruota o scegli una piattaforma.',
    spinning: 'La ruota sta girando…',
    rollingOn: 'Estrazione su {name}…',
    by: 'di {creator}',
    opens: 'si apre su {source}',
    noFilterPrice: '{name} non indica i prezzi, quindi il filtro qui non vale.',
    noFilterNsfw: '{name} non segnala i contenuti NSFW, quindi il filtro qui non vale.',
    noFilterBoth: '{name} non indica né prezzi né contenuti NSFW, quindi i filtri qui non valgono.',
    hint: 'Barra spaziatrice: gira di nuovo',
    historyTitle: 'Ultime estrazioni',
    historyClear: 'Cancella cronologia',
    footer1: 'Progetto amatoriale indipendente.',
    footer2: 'Modelli e immagini appartengono alle rispettive piattaforme e ai loro autori.',
    source: 'Codice sorgente su GitHub',
    unknownSource: 'Piattaforma sconosciuta',
    notConfigured: '{name} non è configurato su questo server.',
    unavailable: '{name} non risponde al momento. Riprova tra poco.',
    rateLimit: 'Troppe estrazioni, aspetta un attimo.',
    busy: 'In questo momento molti stanno girando la ruota. Riprova tra poco.',
    invalidLink: 'Link non valido',
    noPlatform: 'Nessuna piattaforma disponibile',
    error: 'Errore: {msg}',
    language: 'Lingua',
    untitled: 'Senza titolo',
  },
  nl: {
    spin: 'Draaien',
    spinAria: 'Draai aan het rad en kies een willekeurig platform',
    wheelTitle: 'Rad met de platforms',
    directAria: 'Kies direct een platform',
    free: 'Alleen gratis modellen',
    safe: 'NSFW verbergen',
    start: 'Draai aan het rad of kies een platform.',
    spinning: 'Het rad draait…',
    rollingOn: 'Zoeken op {name}…',
    by: 'door {creator}',
    opens: 'opent op {source}',
    noFilterPrice: '{name} geeft geen prijzen, dus het filter werkt hier niet.',
    noFilterNsfw: '{name} markeert geen NSFW-inhoud, dus het filter werkt hier niet.',
    noFilterBoth: '{name} geeft geen prijzen en markeert geen NSFW-inhoud, dus de filters werken hier niet.',
    hint: 'Spatiebalk: nog een keer draaien',
    historyTitle: 'Laatst gedraaid',
    historyClear: 'Geschiedenis wissen',
    footer1: 'Onafhankelijk hobbyproject.',
    footer2: 'Modellen en afbeeldingen zijn van de platforms en hun makers.',
    source: 'Broncode op GitHub',
    unknownSource: 'Onbekend platform',
    notConfigured: '{name} is op deze server niet ingesteld.',
    unavailable: '{name} reageert nu niet. Probeer het zo opnieuw.',
    rateLimit: 'Te vaak gedraaid, wacht even.',
    busy: 'Er draaien nu heel veel mensen tegelijk. Probeer het zo opnieuw.',
    invalidLink: 'Ongeldige link',
    noPlatform: 'Geen platform beschikbaar',
    error: 'Fout: {msg}',
    language: 'Taal',
    untitled: 'Zonder titel',
  },
};

function detectLang() {
  try {
    const saved = localStorage.getItem(LANG_KEY);
    if (saved && STRINGS[saved]) return saved;
  } catch (e) { /* private mode or blocked */ }
  for (const l of navigator.languages || [navigator.language || '']) {
    const code = String(l).slice(0, 2).toLowerCase();
    if (STRINGS[code]) return code;
  }
  return DEFAULT_LANG;
}

let lang = detectLang();

function t(key, vars) {
  const text = (STRINGS[lang] && STRINGS[lang][key]) || STRINGS[DEFAULT_LANG][key] || key;
  return text.replace(/\{(\w+)\}/g, (_, k) => (vars && vars[k] != null ? String(vars[k]) : ''));
}

// Sets all fixed texts of the page: data-i18n for text, data-i18n-<attr> for attributes
function applyStatic() {
  document.documentElement.lang = lang;
  document.querySelectorAll('[data-i18n]').forEach(n => { n.textContent = t(n.dataset.i18n); });
  for (const attr of ['aria-label', 'title']) {
    document.querySelectorAll(`[data-i18n-${attr}]`).forEach(n => n.setAttribute(attr, t(n.getAttribute(`data-i18n-${attr}`))));
  }
}

function setLang(code) {
  if (!STRINGS[code]) return;
  lang = code;
  try { localStorage.setItem(LANG_KEY, code); } catch (e) { /* not important */ }
  applyStatic();
}
