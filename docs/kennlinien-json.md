# Kennlinien als JSON – Grundlagen ab Firmware 0.1.33

Ab 0.1.34: [benannte Profile und Umschaltung](kennlinien-profile.md). Die folgenden Befehle ohne Profilname ersetzen weiterhin den ganzen aktiven Satz.

Dieser Stand führt austauschbare Kennlinien, Prüfung und dauerhafte Flash-Speicherung ein. Übertragung erfolgt über die vorhandene Telnet- oder USB-CDC-Shell. Ein USB-Laufwerk ist noch nicht enthalten; das folgt in Schritt 2. Flash-Aufteilung und WLAN-Zugangsdaten bleiben bestehen.

## Start und Prüfung

Nach Build/Flash bleibt zunächst der bisherige Kennliniensatz aktiv. Auf dem Pico:

```
hamlab curves status
```

`source: builtin` bedeutet eingebaute Standardkennlinien, `source: flash` bedeutet geladener Import. `storage_error: 0` bedeutet erfolgreich initialisierte Speicherung. Nach einem fehlenden oder ungültigen gespeicherten Datensatz verwendet der Boot die Standardkennlinien; ein ungültiger Datensatz wird als Fehler gemeldet. Die Auswahl der Rücklauf-Frequenz erfolgt weiterhin über `hamlab calibration`, ohne automatische Frequenzermittlung.

Am PC, im Projektverzeichnis:

```
python3 tools/powermeter_curves.py validate docs/calibration/curves-v0.1.32.json
python3 tools/powermeter_curves.py status
python3 tools/powermeter_curves.py import docs/calibration/curves-v0.1.32.json
```

Das letzte Kommando überträgt und prüft auf dem Pico, aktiviert und speichert aber nichts. Es entfernt anschließend den Übertragungspuffer. Kein ICOM, Scope oder Sender wird angesprochen.

## Speichern und nach Neustart prüfen

```
python3 tools/powermeter_curves.py import docs/calibration/curves-v0.1.32.json --save
python3 tools/powermeter_curves.py status
```

Dann den Pico neu starten und erneut `status` ausführen: `source` muss `flash` sein. Die mitgelieferte JSON-Datei enthält genau die bisherigen Standardstützstellen aus 0.1.32, deshalb sollten sich die Messwerte durch diesen ersten Test nicht ändern. Bei erfolgreichem Import werden Peak-Hold und letzte Messung zurückgesetzt.

Aktiven Satz sichern:

```
python3 tools/powermeter_curves.py export --output meine-kennlinien.json
```

Bestehende Ausgabedateien werden nicht überschrieben. Andere Pico-IP: `--host IP` vor dem Unterkommando. Über USB, ohne gleichzeitig geöffnetes Terminal:

```
python3 tools/powermeter_curves.py --serial /dev/ttyACM1 status
python3 tools/powermeter_curves.py --serial /dev/ttyACM1 import meine-kennlinien.json --save
```

USB benötigt `pyserial`. Der Gerätepfad ist an den eigenen Rechner anzupassen.

## Format und Grenzen

Die Beispieldatei ist die vollständige Vorlage. `schema_version` ist 1. Es müssen alle vier Kurven gemeinsam vorhanden sein:

| id | Eingang | Frequenz Hz | reference | master |
| --- | --- | ---: | --- | --- |
| forward | A0-A3 | 7031670 | scope_vpp_sine_50ohm | scope |
| reverse_7mhz | A1-A3 | 7100000 | reversed_coupler_scope_vpp_50ohm | scope |
| reverse_50mhz | A1-A3 | 50100000 | reversed_coupler_scope_vpp_50ohm | scope |
| current | A2-A3 | 7100000 | a0_master_50ohm | A0 |

Jede Kurve hat zusätzlich `load_ohms: 50` und `points: [[Spannung_in_V, Leistung_in_W], ...]`. In Schritt 1 sind die IDs, Eingänge, Frequenzen und Referenzen fest. Neue Frequenzen erfordern eine spätere Erweiterung der Auswertelogik.

Je Kurve 2–24 Punkte; Spannung 0–3,3 V, Leistung größer 0 bis 150 W. Spannungen müssen streng steigen, Leistungen dürfen gleich bleiben, aber nicht fallen. Gleiche Wattwerte ermöglichen die bisherigen Plateau-/Randstützstellen. Keine Extrapolation außerhalb der importierten Spannungsgrenzen. Die 150-W-Formatgrenze ist kein Nachweis einer Kalibrierung bis 150 W und hebt ADC-Eingangsgrenzen nicht auf.

Das PC-Werkzeug entfernt unnötige Leerzeichen. Der Pico akzeptiert maximal 4096 JSON-Bytes; auch die normalisierte Exportdarstellung muss in diese Grenze passen. Fehlende, unbekannte oder doppelte Felder sowie ungültige Zahlen werden zurückgewiesen. Importierte Werte bleiben empirische Kalibrierungen; Import allein verbessert weder Genauigkeit noch Frequenzabdeckung. Die Grafiken im Projekt zeigen die eingebauten Standardkennlinien, nicht einen später individuell importierten Flash-Satz.

## Ablauf auf dem Pico

`hamlab curves begin <Bytes>`, wiederholtes `chunk <Hexblock>`, `check`, dann `import`. Das PC-Werkzeug übernimmt diese Schritte in kurzen Blöcken. `check` prüft ausschließlich. `import` prüft erneut, speichert den vollständigen Satz als einen Settings/NVS-Datensatz mit Prüfsumme und aktiviert erst nach erfolgreichem Speichern. Ein fehlgeschlagener Schreibvorgang lässt den aktiven Satz unverändert. Ein bereits gespeicherter identischer Satz wird nicht erneut geschrieben.

`hamlab curves abort` verwirft eine begonnene Übertragung. Nach einem abgebrochenen PC-Transfer gegebenenfalls dieses Kommando ausführen. Nur eine Übertragung gleichzeitig; `export` ist während einer begonnenen Übertragung gesperrt. Der Puffer überlebt keinen Neustart. 0.1.33 speichert unter `hamlab_curves/bank`; 0.1.34 liest diesen Satz als Legacy und speichert neue aktive Sätze unter `hamlab_profiles/active`, getrennt von den WLAN-Settings. USB-Dateisystem bleibt in diesem Stand aus.

## Prüfung dieses Pakets

```
python3 tools/test_powermeter_curves.py
python3 -m unittest discover -s tools -p 'test_*.py'
```

Der erste Test kompiliert den tatsächlichen C-Parser und Speicherbaustein mit GCC und einem simulierten Settings-Backend. Geprüft werden JSON-Fehler, Reihenfolge/Grenzen, Prüfsumme, verlustfreier Export/Import, Interpolation ohne Extrapolation, Übertragungsprüfung, Schreibfehler und Speicherung. Das ersetzt keinen Zephyr-Build, Flash-Test oder Neustarttest auf dem Pico. Für 0.1.33 wurden hier keine Zephyr-Binaries gebaut. Der zusätzliche dauerhafte RAM-Bedarf der Kennlinienverwaltung beträgt ungefähr 7,3 KiB; den tatsächlichen Gesamtverbrauch zeigt der lokale Build.
