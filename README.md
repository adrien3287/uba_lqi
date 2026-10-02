# UBA Luftqualitätsindex (LQI)

HACS-fähige Custom Integration für die Luftqualitätsdaten des Umweltbundesamts.

## Funktionen

- Einrichtung per Config Flow
- Auswahl nahegelegener Luftmessstationen über den Home-Assistant-Standort oder manuelle Koordinaten
- Hauptsensor pro Station für den **UBA Luftqualitätsindex (LQI)**
- eigener **Karte (LQI)**-Sensor pro Station mit `latitude`/`longitude`; sein Zustand ist die numerische LQI-Stufe und kann direkt als Kartenlabel verwendet werden
- optionale Auswahl eines Home-Assistant-Bereichs/Raums bei der Einrichtung; alle erzeugten Stationsgeräte werden diesem Bereich vorgeschlagen
- zusätzliche Diagnose-Sensoren, standardmäßig deaktiviert:
  - numerischer LQI
  - Messbeginn / Messende
  - Entfernung
  - Datenvollständigkeit
  - Komponentensensoren für die von der API gelieferten Schadstoffe
- erweiterte Attribute am Hauptsensor mit Stationsdetails und den aktuellen Komponentenwerten

## Installation über HACS

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Q14siX&repository=uba_lqi&category=integration)

### Variante 1: Benutzerdefiniertes Repository

1. **HACS** öffnen
2. oben rechts auf die **drei Punkte** klicken
3. **Benutzerdefinierte Repositories** wählen
4. diese URL eintragen:
   `https://github.com/Q14siX/uba_lqi/`
5. als Kategorie **Integration** auswählen
6. Repository hinzufügen
7. nach **UBA Luftqualitätsindex (LQI)** suchen und installieren
8. Home Assistant neu starten

### Variante 2: Direkt über den HACS-Store

Wenn das Repository später offiziell im HACS-Standardkatalog gelistet ist, reicht:

1. **HACS → Integrationen** öffnen
2. nach **UBA Luftqualitätsindex (LQI)** suchen
3. Integration installieren
4. Home Assistant neu starten

> Hinweis: Die direkte Suche im normalen HACS-Store funktioniert erst dann, wenn das Repository offiziell im HACS-Katalog aufgenommen wurde. Ohne diese Aufnahme funktioniert die Installation weiterhin über **Benutzerdefinierte Repositories**.

## Manuelle Installation

1. den Ordner `custom_components/uba_lqi` in deine Home-Assistant-Installation kopieren
2. Home Assistant neu starten
3. unter **Einstellungen → Geräte & Dienste → Integration hinzufügen** nach **UBA Luftqualitätsindex (LQI)** suchen

## Einrichtung

1. Integration hinzufügen
2. Standortquelle wählen:
   - **Home-Assistant-Standort verwenden** oder
   - **manuelle Koordinaten** eingeben
3. Suchradius festlegen
4. gewünschte Stationen auswählen
5. Einrichtung abschließen

## Datenquelle

- UBA Air Data API / Luftqualität
- API-Doku: `https://luftqualitaet.api.bund.dev`
- Metadaten über `/meta/json`
- aktuelle Luftqualitätsdaten über `/airquality/json`


## Anzeige auf einer Home-Assistant-Karte

Für jede ausgewählte Station wird eine aktivierte Entität **Karte (LQI)** erzeugt. Sie besitzt numerische `latitude`- und `longitude`-Attribute und verwendet die LQI-Zahl als Zustand.

Beispiel:

```yaml
type: map
auto_fit: true
entities:
  - entity: sensor.DEINE_STATION_KARTE_LQI
    label_mode: state
```

Damit erscheint auf dem Marker direkt die aktuelle LQI-Zahl. Den tatsächlichen Entity-Namen wählst du aus den erzeugten **Karte (LQI)**-Entitäten aus.


## Geo-Location-Quelle für die Kartenansicht

Zusätzlich zu den Sensoren erzeugt die Integration pro ausgewählter Station eine `geo_location.*`-Entität mit der gemeinsamen Quelle `uba_lqi`.

Für die Karte reicht **eine einzige Quelle**. Es darf dabei kein `label_mode` gesetzt werden, damit Home Assistant das dynamische `entity_picture` der Station als Marker verwendet:

```yaml
type: map
auto_fit: true
cluster: false
geo_location_sources:
  - uba_lqi
```

Der Kartenmarker ist ein dynamisches SVG mit der **aktuellen LQI-Zahl** im Zentrum. Die Farbe folgt der LQI-Stufe; bei fehlenden Daten wird ein grauer Marker mit `?` angezeigt.

Die `geo_location.*`-Entität verwendet den **numerischen LQI selbst als Zustand**. Dadurch zeigt ein Klick auf den Kartenmarker im normalen Home-Assistant-Mehr-Info-Dialog direkt den aktuellen LQI samt Verlauf/History an, statt nur die Entfernung zur Station.

Zusätzliche Attribute sind unter anderem `lqi_label`, Stationsname, Koordinaten, Entfernung sowie Messbeginn und Messende. Neue Stationen, die später über die Integrationsoptionen ausgewählt werden, erscheinen automatisch über dieselbe Quelle.
