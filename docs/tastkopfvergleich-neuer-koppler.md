> Historischer Versuchsaufbau vom 6.10.2026: Stromkoppler vorübergehend an A0. Aktuell liegt er an A2; dieses Skript liest weiterhin A0 und vergleicht damit bei heutiger Belegung den Richtkoppler. Aktuellen Stromkoppler-Abgleich mit [powermeter_align_current.py](abgleich-a2-auf-a0.md) aufnehmen.

# Neuer Stromkoppler: Tastkopfvergleich ohne Scope-Abfrage

Ein neuer Koppler mit einem Stromtransformator wurde an A0 angeschlossen. Erster gemeldeter Wert: etwa **0,533 V bei 100 % ICOM-Stellung**. Diese Spannung ist kein Wattreferenzwert. Die alten Vorlauf-/SWR-Kennlinien gehören zum alten Koppler und sind nach dem Hardwarewechsel für diesen Eingang **nicht gültig**. Das Testskript ignoriert deshalb alle Watt-/SWR-Ableitungen der Firmware und liest die tatsächlichen ADC-Spannungen.

Ziel: gleicher Sender, gleiche Frequenz/Last/Kabel/Position, zwei Durchläufe mit unterschiedlichen Tastkopfzuständen. Keine Scope-Kommandos; der Tastkopf wirkt nur als zusätzlich angeschlossene Last. Der Versuch prüft die Änderung des Detektorsignals, nicht automatisch absolute Leistung oder Rückwirkungsfreiheit.

## Start

Voraussetzungen wie bei bisherigen ICOM-Tests: Python mit `pyserial`, USB-CI-V 19200 Baud, CW, vorhandenes RTS-CW-Keying/Break-in, Tuner aus. Pico `192.168.178.98:8080`, gültiges A0−A3; A3 Masse. Passend belastbare 50-Ω-Dummyload. A1 muss für diesen Test nicht gültig sein, soweit die HTTP-Messung A0 normal liefert.

```bash
python3 tools/powermeter_probe_test.py sweep --plan
python3 tools/powermeter_probe_test.py sweep
```

Erster Befehl: nur Plan, kein Gerätezugriff. Zweiter: Verbindungskontrolle ohne Sendebefehle oder Einstellungsschreibzugriffe. RTS/DTR werden beim Öffnen des Ports deaktiviert.

Bei Bedarf `--port /dev/serial/by-id/...-if00-port0` und `--pico ADRESSE` ergänzen. Baud bleibt 19200.

## Zwei Messläufe

Frequenz **7,1 MHz** ist Standard; explizit setzen, damit beide Läufe vergleichbar bleiben. `--levels 1:100:1` fährt jeden ganzen Prozentwert einschließlich 1 und 100. 100 Punkte, drei Abfragen je Punkt, eine Sekunde Einschwingzeit und fünf Sekunden RX-Pause: ungefähr 12–15 Minuten je Lauf, abhängig von WLAN/CI-V. Keine Dauerträger-Messung über die ganze Reihe.

**Ohne Tastkopf**:

```bash
python3 tools/powermeter_probe_test.py sweep --run \
  --probe without --frequency 7100000 --levels 1:100:1 \
  --settle 1 --pause 5 --samples 3 \
  --notes 'Neuer Stromkoppler; 50 Ohm; Scope-Tastkopf abgezogen' \
  --output koppler_ohne.csv
```

Warten bis der Lauf beendet und der Sender wieder auf RX ist. Tastkopf an genau die vorgesehene Messstelle anschließen, Tastkopffaktor/Masseanschluss nicht zwischen Einzelpunkten ändern.

**Mit Tastkopf**:

```bash
python3 tools/powermeter_probe_test.py sweep --run \
  --probe with --frequency 7100000 --levels 1:100:1 \
  --settle 1 --pause 5 --samples 3 \
  --notes 'Neuer Stromkoppler; 50 Ohm; Scope-Tastkopf 1:10 angeschlossen' \
  --output koppler_mit.csv
```

Für einen kurzen Ersttest in **beiden** Kommandos `--levels 1,5,10,20,50,100` verwenden, jeweils neue Dateinamen. Kopplerposition, Last, Kabel und Versorgung unverändert lassen. Nicht während TX umstecken.

Jeder Lauf erfasst vor dem Senden einen eigenen Ruhewert (CSV-Zeile 0 %). Frequenz-/Leistungsstellung werden per CI-V zurückgelesen. Nach jedem Punkt wird RX angefordert. Zeitlimit standardmäßig 8 s pro Sendefenster; bei Ablauf wird der Punkt verworfen. Bei Fehler/Abbruch bleibt der bisherige CSV-Inhalt erhalten, RTS wird deaktiviert, RX und Wiederherstellung ursprünglicher Frequenz/Leistungsstellung werden versucht. Software-Cleanup ersetzt keine unabhängige Hardwareabschaltung.

Vorhandene CSVs werden nicht überschrieben. Beenden mit Ctrl+C. Scope wird weder abgefragt noch eingestellt. ICOM-Indikatorwerte PO/ALC/VD/ID/SWR werden zusätzlich protokolliert; sie sind keine kalibrierte Leistungsreferenz.

## Auswertung

```bash
python3 tools/powermeter_probe_test.py compare \
  --without koppler_ohne.csv --with-probe koppler_mit.csv \
  --output koppler_vergleich.csv
```

Für Grafik zusätzlich `--plot`; gegebenenfalls vorher `python3 -m pip install matplotlib`. Erzeugt dann `koppler_vergleich.png` mit beiden Spannungskennlinien und prozentualer Änderung.

Vergleich paart identische Frequenz, Leistungsstellung und CI-V-Rohstellung. Unvollständige oder unterschiedlich geplante Reihen werden abgelehnt, nicht stillschweigend gekürzt. Bei erneuter Analyse neuen Ausgabedateinamen wählen.

CSV enthält die Differenz **mit minus ohne**, relativ zur Ohne-Reihe. Positives Vorzeichen bedeutet höhere Detektorspannung mit Tastkopf. Zusätzlich wird der jeweilige Ruheoffset abgezogen und erneut verglichen. Bei zu kleiner Bezugsspannung gegenüber beobachteter Streuung wird kein Prozentwert ausgegeben. Das ist eine Plausibilitätsregel, keine qualifizierte Nachweisgrenze.

Die Grafik-Fehlerbalken zeigen Standardabweichung der Abfragen innerhalb eines Punkts, nicht die Gesamtmessunsicherheit. Rohwertlisten und ADC-Bereichslisten erlauben Kontrolle der Autorange; Rohwerte aus unterschiedlichen Bereichen dürfen nicht direkt verglichen werden.

**Spannungsänderung ist kein prozentualer Wattfehler.** Zum Zeitpunkt dieses Versuchs war die neue Detektorkennlinie noch unbekannt. Ein Stromkoppler liefert ohne Kenntnis von Last und Phase keine allgemeine Wirkleistungsmessung. Auch ein reiner Stromabgriff schließt tatsächliche Laständerung durch den Tastkopf und eine Senderreaktion nicht aus.

Optional den Ohne-Lauf ein drittes Mal wiederholen (`koppler_ohne_wiederholung.csv`, `--probe without`) und mit der Mit-Reihe vergleichen. So lässt sich erkennen, ob Erwärmung oder Drift zwischen den Läufen den Tastkopfeffekt überlagern. Messreihen, Anschlussnotizen und Grafik gemeinsam aufbewahren.

## Offline-Prüfung

```bash
python3 tools/test_powermeter_probe_test.py
```

Simulierte Geräte prüfen Plan/Lesemodus, Sweep, Mittelwerte, CSV, Fehlerabbruch, Zeitlimit, RX/Wiederherstellung und Vergleich. Kein realer Sendetest in der Entwicklungsumgebung. Der damalige Versuch erforderte keinen Firmware-Wechsel; die heutige Belegung ist in der Bedienungsanleitung dokumentiert.
