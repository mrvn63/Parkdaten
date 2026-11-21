"""
Sammelt die aktuelle Belegung der Parkhäuser in Zürich und Basel
und hängt sie an CSV-Dateien an (eine Datei pro Stadt und Monat).

Quellen (offene Daten):
- Zürich: Parkleitsystem Stadt Zürich, RSS-Feed, Lizenz CC0
  https://www.pls-zh.ch/plsFeed/rss
- Basel: Open Data Basel-Stadt, Datensatz 100088, Quelle angeben
  https://data.bs.ch/explore/dataset/100088/

Braucht nur die Python-Standardbibliothek (keine Installation nötig).
"""

import csv
import json
import os
import re
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

ZUERICH_URL = "https://www.pls-zh.ch/plsFeed/rss"
BASEL_URL = "https://data.bs.ch/api/explore/v2.1/catalog/datasets/100088/exports/json"

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
USER_AGENT = "parkdaten-sammler/1.0 (privates Lernprojekt, offene Daten)"

ZUERICH_FIELDS = ["collected_utc", "source_utc", "id", "name", "status", "free"]
BASEL_FIELDS = ["collected_utc", "source_utc", "id", "name", "status", "free", "total"]


def fetch(url, retries=3, timeout=30):
    """Lädt eine URL und versucht es bei Fehlern bis zu 3-mal."""
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except Exception as e:  # Netzwerkfehler, Timeout, HTTP-Fehler
            last_error = e
            time.sleep(5 * attempt)
    raise RuntimeError(f"Abruf fehlgeschlagen: {url} ({last_error})")


def parse_zuerich(xml_bytes, collected_utc):
    """Liest den RSS-Feed. Beschreibung hat die Form 'open /  163'."""
    root = ET.fromstring(xml_bytes)
    dc = "{http://purl.org/dc/elements/1.1/}"
    rows = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        desc = (item.findtext("description") or "").strip()
        source = (item.findtext(f"{dc}date") or item.findtext("pubDate") or "").strip()

        m = re.search(r"pid=([^&]+)", link)
        pid = m.group(1) if m else title

        status, free = desc, ""
        if "/" in desc:
            status, free = [p.strip() for p in desc.split("/", 1)]
        free = free if re.fullmatch(r"-?\d+", free) else ""

        rows.append({
            "collected_utc": collected_utc,
            "source_utc": source,
            "id": pid,
            "name": title,
            "status": status,
            "free": free,
        })
    return rows


def _first(record, *keys):
    """Gibt den ersten vorhandenen Wert aus mehreren möglichen Feldnamen zurück."""
    for k in keys:
        if k in record and record[k] not in (None, ""):
            return record[k]
    return ""


def parse_basel(json_bytes, collected_utc):
    """Liest den JSON-Export. Feldnamen werden robust erkannt."""
    data = json.loads(json_bytes)
    if isinstance(data, dict):  # falls die API ein Objekt mit 'results' liefert
        data = data.get("results", [])
    if data:
        print("basel: Felder im Export:", ", ".join(sorted(data[0].keys())))
    rows = []
    for r in data:
        rows.append({
            "collected_utc": collected_utc,
            # Falls kein Zeitstempel erkannt wird, gilt der Abrufzeitpunkt
            "source_utc": _first(r, "published", "publikationszeit", "zeitstempel") or collected_utc,
            "id": _first(r, "id2", "id", "name"),
            "name": _first(r, "title", "titel", "name"),
            "status": _first(r, "status", "state"),
            "free": _first(r, "free", "anzahl_frei", "frei"),
            "total": _first(r, "total", "total_platze", "total_plaetze"),
        })
    return rows


def load_last(city):
    """Letzter gespeicherter Quell-Zeitstempel pro Parkhaus (gegen Duplikate)."""
    path = os.path.join(DATA_DIR, city, "last.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_rows(city, rows, fields):
    """Hängt nur neue Messungen an data/<stadt>/<JJJJ-MM>.csv an."""
    os.makedirs(os.path.join(DATA_DIR, city), exist_ok=True)
    last = load_last(city)
    new_rows = [r for r in rows if r["source_utc"] and last.get(r["id"]) != r["source_utc"]]

    month = datetime.now(timezone.utc).strftime("%Y-%m")
    path = os.path.join(DATA_DIR, city, f"{month}.csv")
    write_header = not os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        if write_header:
            w.writeheader()
        w.writerows(new_rows)

    for r in new_rows:
        last[r["id"]] = r["source_utc"]
    with open(os.path.join(DATA_DIR, city, "last.json"), "w", encoding="utf-8") as f:
        json.dump(last, f, ensure_ascii=False, indent=0, sort_keys=True)
    return len(new_rows), len(rows)


def main():
    collected_utc = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    ok = 0
    for city, url, parser, fields in [
        ("zuerich", ZUERICH_URL, parse_zuerich, ZUERICH_FIELDS),
        ("basel", BASEL_URL, parse_basel, BASEL_FIELDS),
    ]:
        try:
            rows = parser(fetch(url), collected_utc)
            new, total = save_rows(city, rows, fields)
            print(f"{city}: {total} Parkhäuser gelesen, {new} neue Messungen gespeichert")
            ok += 1
        except Exception as e:
            print(f"{city}: FEHLER {e}", file=sys.stderr)
    # Nur als Fehler melden, wenn beide Quellen ausgefallen sind
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
