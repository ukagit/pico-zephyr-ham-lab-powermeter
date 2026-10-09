# Benannte Kennlinienprofile – Firmware 0.1.34

Bis zu acht benannte Profile liegen im Flash. Die Auswahl erfolgt einzeln für `forward`, `reverse_7mhz`, `reverse_50mhz` und `current`. Ein Wechsel von `current` verändert ausschließlich A2; A0 und die SWR-Kurven behalten ihre Auswahl. Gewählte Kurven und Profilnamen werden gemeinsam als aktiver Satz gespeichert und nach Neustart geladen. Hold und letzte Messung werden beim erfolgreichen Umschalten zurückgesetzt.

## Firmware aktualisieren

Paket im bestehenden Projektverzeichnis mit `tar -xf` entpacken. Wie bisher:

```
west build -b rpi_pico/rp2040/w -S cdc-acm-console . -d build -p always
./tools/flash_openocd.sh
```

Der gültige gespeicherte Satz aus 0.1.33 wird unverändert geladen. Er erscheint zunächst bei allen vier Kurven als `legacy` und bleibt später wieder auswählbar. Das Update schreibt beim Start keinen neuen Kennliniensatz. WLAN-Zugangsdaten und Flash-Partitionen bleiben bestehen. Für diesen Stand wurden keine vorgebauten Zephyr-Binaries erstellt.

## Erste Probe mit den vorhandenen Kurven

Am PC:

```
python3 tools/powermeter_curves.py export --output current_original.json
python3 tools/powermeter_curves.py import current_original.json --profile current_original --save
python3 tools/powermeter_curves.py list
```

Import mit `--profile NAME --save` speichert ein Profil, aktiviert es jedoch nicht. Import mit `--profile NAME` ohne `--save` bleibt ein reiner Prüflauf. Der Profilname wird als Kommandoargument vergeben, nicht als zusätzliches JSON-Feld. Bestehende Ausgabedateien beim Export werden nicht überschrieben.

Nun auf dem Pico:

```
hamlab curves list
hamlab curves select current current_original
hamlab curves status
```

`current [current_original]` bestätigt die Auswahl. Nach Neustart muss diese Auswahl erhalten bleiben. Weil dieser Probelauf dieselben Stützstellen verwendet, sollten die Messwerte gleich bleiben.

Alternativ per PC:

```
python3 tools/powermeter_curves.py select current current_original
```

`--host IP` oder `--serial /dev/ttyACM1` vor dem Unterkommando ändern die Verbindung. Standard ist Telnet zu 192.168.178.98.

## Weiteren Messfühler verwenden

1. Den vollständigen aktiven Satz exportieren und die Datei unter einem neuen Namen kopieren.
2. Im Objekt mit `id: current` die `points` durch die gemessene A2-Kennlinie dieses Fühlers ersetzen. Alle anderen Kurven und Metadaten beibehalten.
3. Offline prüfen, als neues Profil speichern und anschließend auswählen.

Beispiel für eine selbst erstellte Datei `current_100watt.json`:

```
python3 tools/powermeter_curves.py validate current_100watt.json
python3 tools/powermeter_curves.py import current_100watt.json --profile current_100watt --save
```

Danach:

```
hamlab curves select current current_100watt
```

Diese Beispieldatei ist nicht enthalten, weil für den Namen keine neue Kalibrierung erfunden werden soll. Ein Profilname wie `current_100watt` erweitert die Messgrenze nicht: die tatsächlichen Stützstellen bestimmen den Bereich. Die eingebaute A2-Kurve endet weiterhin bei etwa 83,35 W.

Jedes Profil enthält in diesem ersten Stand einen vollständigen Satz von vier Kurven im bisherigen Schema 1. Beim Auswählen wird daraus nur die angegebene Kurve übernommen. Damit sind Fühlerwechsel möglich, ohne das JSON-Format aus 0.1.33 zu ändern. Die bestehenden Frequenzen und Referenzen bleiben fest; neue Frequenzen oder ein anderes Referenzverfahren erfordern eine spätere Erweiterung.

## Zurückschalten und Profile ersetzen

```
hamlab curves select current legacy
hamlab curves select current builtin
```

`legacy` ist nur vorhanden, wenn ein gültiger Satz aus 0.1.33 gespeichert war. `builtin` verwendet die eingebauten Standardstützstellen. Beide sind zusätzlich zu den acht eigenen Profilen verfügbar. `legacy` bewahrt den ursprünglichen 0.1.33-Satz; spätere Importe ohne Profilname ändern ihn nicht.

Eigene Namen: 1–23 Zeichen, Buchstaben, Ziffern, `_` und `-`. Groß-/Kleinschreibung wird unterschieden. `builtin`, `legacy`, `imported` und `active` sind reserviert.

Ein unter demselben Namen gespeichertes Profil kann ersetzt werden, solange keine aktive Kurve dieses Profil verwendet. Zuerst alle entsprechenden Rollen auf `builtin`, `legacy` oder ein anderes Profil schalten, dann erneut importieren. Acht Plätze; keine Löschfunktion in diesem Stand. Vorhandene Namen lassen sich wiederverwenden.

Import ohne `--profile` mit `--save` bleibt möglich: er ersetzt und aktiviert den ganzen Satz und bezeichnet die Auswahl als `imported`. Bereits gespeicherte eigene Profile bleiben erhalten. Die Namen `legacy` und `imported` sind Herkunftsbezeichnungen im Status; nur `legacy` ist zusätzlich als ursprünglicher Satz auswählbar.

## Fehler und Grenzen

Ungültige Profile, unbekannte Namen und Flash-Schreibfehler verändern den aktiven Satz nicht. Während einer begonnenen Übertragung ist Umschalten gesperrt; gegebenenfalls `hamlab curves abort` verwenden. Alle bisherigen Punkte-, Spannungs-, Leistungs- und JSON-Größengrenzen gelten weiter. Auch eine Mischung ausgewählter Kurven muss als vollständiger JSON-Satz in 4096 Bytes exportierbar bleiben.

Jeder aktive Satz enthält die ausgewählten Kurven selbst und ihre Namen. Nach Neustart müssen dafür nicht alle Profile in den RAM geladen werden. Beschädigte gespeicherte Datensätze werden zurückgewiesen und `storage_error` meldet den Fehler. Bei beschädigter aktiver Auswahl fällt der Boot auf einen gültigen alten 0.1.33-Satz oder die Standardkurven zurück. Profile sind Kalibrierdaten, kein Beleg einer absoluten Genauigkeit. Ein gewechselter Messfühler muss am richtigen Eingang angeschlossen und für Frequenz, Aufbau und Referenz passend kalibriert sein.

JSON-API `hamlab meter` / HTTP-State ergänzt `curve_profiles` mit den vier Namen. Web-/OLED-Leistungsanzeige nutzt unmittelbar die ausgewählte Kurve. A2 bleibt die zusätzliche 50-Ohm-Anzeige und ersetzt weder A0-Hauptanzeige noch SWR.

## Verifikation

18 Offline-Tests bestehen, darunter der tatsächliche C-Parser/Speicherbaustein mit simuliertem Settings-Backend: Migration aus 0.1.33, Profilimport ohne Aktivierung, Auswahl, Neustart, Schreibfehler, belegte Profile, acht Plätze, Rückkehr zu Standard/Legacy und der PC-Übertragungsablauf. C-Bausteine werden mit `-Wall -Wextra -Werror` kompiliert. Der lokale Zephyr-Build und Hardwaretest stehen noch aus.

Kennlinienverwaltung benötigt nun ungefähr 9,1 KiB statische Daten insgesamt. Die Profile selbst liegen im Flash; zusätzlich gibt es RAM-Puffer für Transfer, Prüfung und Speichern. Den tatsächlichen RAM-Verbrauch zeigt der Build. USB-Massenspeicher folgt weiterhin separat.
