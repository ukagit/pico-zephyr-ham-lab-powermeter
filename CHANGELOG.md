## Dokumentation zu 0.1.49 – 9.10.2026
- README und Bedienung auf fünf OLED-Ansichten, A2-Profile, Voltmeter und AP aktualisiert.
- Boot-Auswahl über GP21, offener AP, WPA2-Alternative, WHD-Kanalfix und synchrone Treiberrückgabe dokumentiert.
- AP-Verbindungen mit Ubuntu/MacBook und wiederholte Moduswechsel getestet; iPhone-Verbindung offen.
- Firmware bleibt 0.1.49.

## Dokumentation zu 0.1.32 – 6.10.2026
- README und Bedienung vollständig auf aktuellen Aufbau mit A0/A1/A2 und Akku GP28 aktualisiert.
- Messhistorie, Tastkopfeinfluss, A0-Master-Abgleich, Grenzen und obere Plateaus dokumentiert.
- Kennliniengrafik/PDF/CSV umfassen alle vier aktiven Kurven; Plotwerkzeug liest beide Header.
- Testwerkzeuge und GitHub-Vorbereitung aktualisiert; Firmware unverändert.

## 0.1.32
- A2-Kennlinie aus gepaarten A0-Master-Messungen vom 6.10.2026, 7,1 MHz / 50 Ω.
- 1 % mangels gültiger A0-Referenz ausgeschlossen; 90/100-%-Punkte gepoolt, beobachtete Randstreuung begrenzt berücksichtigt.
- Vorlauf/Rücklauf/SWR unverändert; Zusatzwert als auf A0 abgeglichen gekennzeichnet.

## Werkzeuge nach 0.1.31
- Automatischer A0-Master/A2-Abgleich mit gepaarten Messungen und Gültigkeitskennzeichnung.
- Scope-Kalibrierwerkzeug akzeptiert den zusätzlichen ADS1115-Kanal.
- Firmware bleibt 0.1.31.

## 0.1.31
- Akku von ADS1115 A2 auf Pico GP28/ADC2 verlegt.
- Separater Stromkoppler A2−A3 mit Autorange und 7,1-MHz/50-Ω-Kennlinie, JSON, Web-/OLED-Vollansicht.
- Richtkoppler-Kennlinien und SWR unverändert.

# Änderungen

## PC-Werkzeug: neuer Koppler, 2026-10-06

- Sweep 1–100 % mit ICOM-RTS und A0-Rohspannungen, ohne Scopezugriff.
- Ruhewert, Mehrfachabfragen und ADC-Autorange protokolliert.
- Offlinevergleich ohne/mit Tastkopf, optionale Grafik; keine Wattinterpretation der alten Kennlinie.
- Firmware bleibt 0.1.30.

## Dokumentationslieferung zu 0.1.30 – 2026-10-06

- Aktuelle Leistungsbeschreibung, Bedienung, Anschlüsse, API und Messgrenzen.
- Messverfahren, Aufbauabhängigkeit, 1N4148-Korrektur und verworfene Nullpunktschätzung dokumentiert.
- Werkzeugübersicht, GitHub-Anleitung, Kennliniengrafik und exportierte aktive Stützstellen.
- Alte README als historischer Zwischenstand erhalten; keine Firmwareänderung.

## 0.1.30

- SWR ~1 als blaue Annahmemarke im farbigen Web-Balken; gemessen weiß, Hold gelb.

## 0.1.29

- Lineare Kleinleistungs-Schätzung entfernt; ~1 ausschließlich als Anzeigeannahme.
- API-SWR unter Rücklaufgrenze bleibt ungültig/null; keine Annahmewerte in Hold oder letzter Messung.

## 0.1.28

- Vorübergehende lineare Schätzung unter erster Rücklaufstützstelle. In 0.1.29 verworfen.

## 0.1.25–0.1.27

- Deutliche SWR-Warnungen, ruhige Anzeige bei fehlender HF und kleinem unbestimmtem Rücklauf.

## 0.1.24

- Rücklaufkurven 7,1 und 50,1 MHz aus umgedrehtem Koppler, gemittelten Zeitbasis-Wiederholungen und monoton gepoolten Plateaus.
- Rücklaufkurvenauswahl im RAM; numerisches SWR bei fehlender Vorlauf-Frequenzkurve gesperrt.

## 0.1.23

- Automatische Scope-Zeitbasis/V-div-Vorgaben, Planmodus und mehrere Zeitbasis-Wiederholungen.

## 0.1.22

- tools/powermeter_series.sh: Frequenz- und Leistungsreihe mit 25/50 Ohm, eine manuelle Scope-Skalierung pro Durchgang.
- Reine Verbindungskontrolle ohne --run; Plan vorab geprüft, keine vorhandenen Dateien überschrieben, Stop beim ersten Messfehler.
- Firmware-Messverhalten und Kennlinien unverändert gegenüber 0.1.21.

## 0.1.21

- Vorlaufkennlinie ab 1.2544 W: neue 1–4-%-Punkte, 5–20 % aus vollständiger 20-V/div-Reihe, höhere alte Punkte weiterhin vorläufig.
- OLED-Kompakt unter 10 W mit Nachkommastelle.
- Rücklaufkennlinie unverändert; kleine Vorlaufleistung aktiviert kein unkalibriertes SWR.

## 0.1.20

- Kalibrierskript: bis zu drei Pico-Leseversuche bei Messfehler/HTTP 409/503 oder Verbindungsfehler, 200-ms-Abstand.
- HTTP-Status und measurement_error/Kanalfehler werden ausgegeben.
- Leseversuche beachten dieselbe TX-Deadline; ungültige Punkte werden verworfen.
- Firmware-Messalgorithmus und Kennlinien unverändert gegenüber 0.1.19.

## 0.1.19

- meter/status: laufender ADC-Snapshot, keine zusätzliche ADC-Messung, 250-ms-Sperrwartezeit.
- Shell-JSON-Puffer statisch mit eigener Sperre statt 3 KiB auf dem 4-KiB-Telnet-Stack.
- Kalibrierwerkzeuge: --load-ohms 25|50, getrennte Last-/Vorlauf-/Rücklaufreferenz.
- Frequenzreihe mit bestätigten 25 Ohm ausgewertet; Kennlinien unverändert.

## 0.1.18

- DDS/ATT/Frequenz/Sweep vollständig aus aktivem Firmwarecode und HTTP/Shell entfernt.
- Sweep-Puffer und Thread entfernt; Encoder steuert OLED-Seiten.
- Info: Batterieeingang, separate vorläufige Vor-/Rücklaufkalibrierung; kein erfundener DDS-Frequenzwert im State.
- tools/powermeter_frequency_test.py: kurze 50-Ohm-CW-Frequenzprüfung auf Icom-Bändern, gemeinsame CSV mit Abweichung zur 7-MHz-Kurve.

## 0.1.17

- OLED-Kompakt: kleine W-Einheit, große ganzzahlige Watt und SWR mit einer Nachkommastelle in gemeinsamer Zeile.
- Balken/Hold unverändert; Fußzeile zeigt Max-Hold in Watt.

## 0.1.16

- OLED-Wattzahl vollständig unter dem gelben Bereich ab Pixelzeile 18.
- Balken Zeilen 44–51, Hold-Markierung 43–53, gemeinsame Fußzeile MAX-Watt / SWR ab 56.
- Autoscale in der kleinen Kopfzeile.
- Spannungsteiler-Hinweis auf der Akkuseite entfernt.

## 0.1.15

- Stackbedarf des HTTP-JSON-Aufbaus reduziert: Antwort und gesperrte Zwischenpuffer statisch.
- JSON-Antwortpuffer 3072 Byte; Schutz gegen abgeschnittene Antworten.
- OLED-Thread 3072 statt 2048 Byte Stack für verschachtelte Formatierung.
- Ungenutztes meter_cal_hz entfernt.
- Ursache des gemeldeten Hardwarehängers noch nicht durch Stackmessung bestätigt.

## 0.1.14

- Letzte Messung: NTP-Zeit, Watt und zeitgleich erfasster SWR (null bei ungültigem SWR).
- OLED: große Wattzahl, Autoscale-Balken 10/20/50/100/150 W und 3-s-Hold.
- GP19/20/21: Kompakt/Voll/Batterie, gegen Masse, Pull-ups und 30-ms-Entprellung.
- DDS-Pinansteuerung entfernt, damit Tasterpins ausschließlich Eingänge sind.
- A2-A3: Akkumessung alle 2 s, ±4.096 V, Faktor 2 für 10k/10k-Teiler.

## 0.1.13

- SWR-Balken grün/gelb/rot mit aktuellem Wert und Peak in Voll-/Kompaktansicht.

## 0.1.12

- swr/power Shell-Kommandos ohne zusätzliche ADC-Messung, Sperrwartezeit begrenzt.
- Messkennlinien unverändert.

## 0.1.11

- Vorläufige separate Rücklaufkurve aus 25-Ohm-Messreihe, Tuner aus.
- SWR, 3-s-SWR-Peak, Web/OLED; keine Extrapolation nahe Untergrund.
- Finale gemeinsame Vor-/Rücklaufkalibrierung weiterhin geplant.

## 0.1.10

- Web-Polling 200 ms mit Cache-State statt zusätzlicher ADC-Messung.
- Messschleife beschleunigt; OLED-Refresh separat begrenzt.

## 0.1.9

- NTP-UTC in separatem Firmwaremodul; Messzeit und zugehörige Leistung in JSON.
- Web zeigt letzte kalibrierte Leistungsmessung mit Pico-NTP-Zeit, Europe/Berlin.
- Kleiner Max-Hold-Text in Kompaktansicht.

## 0.1.8

- Max-Hold nach 3 s nach unten aktualisieren; Autoscale folgt.
- Kompakt-Headline, Vollansicht-Link, letzte gültige Abfrage mit Browserdatum/-zeit.

## 0.1.7

- Kompaktansicht auf Watt und Balken mit Skala reduziert.
- Max-Hold-Reset per Doppelklick auf den kompakten Balken.

## 0.1.6

- Max-Hold-Marke direkt im Leistungsbalken, beschriftete Skala.
- Autoscale-Endwerte 10,20,50,100,150 W anhand Leistung und gehaltenem Peak.
- Kennlinie und Messung unverändert.

## 0.1.5

- Firmware Peak-Hold mit Web-Reset, Leistung auf OLED und Web.
- SWR-Peak-Anzeige vorbereitet, Werte weiterhin null.
- DDS-/ATT-Infos aus Anzeigen entfernt. Unterbereich-Messnotizen aufgenommen.
- Kennlinie unverändert bis Scope-Referenzen für 1..5% vorliegen.

## 0.1.4

- Vorläufige Vorlaufkennlinie bei 7.031670 MHz, 4..92.16 W; keine Extrapolation.
- Web Voll-/Kompaktansicht mit Watt, ADC-Rohdaten, Status und Fehleranzeige.
- OLED Vorlauf-Watt, hamlab power und JSON power. Rücklauf/SWR bleiben unkalibriert.
- Hosttests bestanden; Zephyr Build/Flash beim Anwender erforderlich.

# Powermeter Versionsübersicht

## 0.1.3
- ADS1115 A0-A3 Vorlauf, A1-A3 Rücklauf mit AutoRange je Kanal.
- Signierte Rohwerte, Spannungen und Bereiche über Shell/API/Web.
- OLED zeigt Differenzspannungen.
- Alte AD8307-Leistungs-/SWR-/Sweep-Funktionen gesperrt.
- ADC-Verhalten mit simulierten Registern geprüft; Hardwaretest ausstehend.

## 0.1.2
- Gemeinsamen GPIO-I²C-Bus auf GP0 SDA / GP1 SCL verschoben.
- UART0 für diese Pins deaktiviert; USB CDC bleibt Konsole.
- Bestehende SSD1306-Ansteuerung übernommen.
- WLAN und Telnet laut Rückmeldung in 0.1.1 funktionsfähig.
- Build und OLED-Hardwaretest für 0.1.2 ausstehend.

## 0.1.1
- RP2040-Linkerfehler z_impl_sys_rand_get: Timer-RNG für Inbetriebnahme aktiviert.
- Kein kryptografischer RNG; dauerhafte Entropielösung noch offen.
- Erneuter Build und Hardwaretest ausstehend.

## 0.1.0
- Eigenständige Projektkopie aus HamLab 0.3.7.
- Pico-W-Board RP2040, Overlay und OpenOCD-Target angepasst.
- Settings/NVS auf letzten 64 KiB des 2-MiB-Flashs.
- Projektkennung, Webtitel und TCP-Banner umbenannt.
- Netzwerk, USB-Shell und bestehende Gerätefunktionen übernommen.
- A2/A3 noch nicht implementiert; Build/Hardwaretest ausstehend.
