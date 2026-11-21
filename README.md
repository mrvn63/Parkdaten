# Parkdaten-Sammler Zürich und Basel

Dieses Repository speichert automatisch alle 10 Minuten die aktuelle Belegung der Parkhäuser in Zürich und Basel. Es läuft gratis auf GitHub Actions, ohne eigenen Computer oder Server.

## Datenquellen

| Stadt | Quelle | Lizenz |
|---|---|---|
| Zürich | Parkleitsystem Stadt Zürich, RSS-Feed `pls-zh.ch/plsFeed/rss` | CC0 (frei nutzbar) |
| Basel | Open Data Basel-Stadt, Datensatz 100088 | Offen, Quelle muss genannt werden |

## Ablage der Daten

```
data/
  zuerich/2026-11.csv   eine Datei pro Monat
  zuerich/last.json     interne Hilfsdatei gegen doppelte Messungen
  basel/2026-11.csv
  basel/last.json
```

Spalten: `collected_utc` (Zeitpunkt des Abrufs), `source_utc` (Zeitstempel der Quelle), `id`, `name`, `status`, `free` (freie Plätze), bei Basel zusätzlich `total` (Kapazität).

## Hinweise

- Das Repository sollte **öffentlich** sein. Dann sind die GitHub-Actions-Minuten unbegrenzt gratis. Bei einem privaten Repository würden die Gratis-Minuten für einen 10-Minuten-Takt nicht reichen.
- GitHub startet geplante Läufe manchmal einige Minuten zu spät. Für unsere Zwecke ist das kein Problem.
- Fällt eine Quelle aus, wird die andere trotzdem gespeichert.
