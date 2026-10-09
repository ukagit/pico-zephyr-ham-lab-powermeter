> Historischer Zwischenstand. Aktuell: [Bedienung](bedienung.md), [Kalibrierung](messung-und-kalibrierung.md), [Werkzeuge](testwerkzeuge.md).

# Automatische Kalibrierung, erster Test

Firmware bleibt 0.1.3. Neue PC-Tools: tools/powermeter_calibrate.py und
korrigiertes tools/icom7300_read.py (Port-Endung -port0, 19200 Baud).

Voraussetzungen:
- IC-7300: CW, BK-IN aktiv, USB Keying (CW)=RTS, USB SEND=OFF,
  USB Keying (RTTY)=OFF. Andere CAT-Programme geschlossen.
- HF-Ausgang an ausreichend belastbarer 50-Ohm-Dummyload.
- SDS CH1 misst direkt die Lastspannung mit geeignetem Tastkopf;
  Tastkopf-Faktor korrekt, DC-Kopplung, vollständiger Sinus, laufende Aufnahme.
- Keine über Messpunkte gemischten Average-Daten: zuerst Normal-Erfassung nutzen.
- sds status liefert bereits skalierte Voltwerte. Kein weiterer Faktor im Tool.
- Pico 192.168.178.98:8080 liefert gültige A0-A3/A1-A3-Werte.

```bash
python3 -m pip install pyserial
python3 tools/powermeter_calibrate.py
```
Ohne --run werden nur Abfragen ausgeführt. Dabei kein HF-Signal erforderlich.
RTS/DTR werden vor dem Öffnen auf inaktiv gesetzt; USB-Treiber können beim Öffnen
kurze Leitungsimpulse erzeugen. Ersten Verbindungscheck vor Aktivieren USB-CW testen.

Für einen einzelnen kurzen Sendetest anschließend USB Keying(CW)=RTS einstellen:

```bash
python3 tools/powermeter_calibrate.py --run --levels 5 --frequency 7031670 --output cal_test_5pct.csv
```

Scope-Vertikalskalierung vorher auf kleine Leistung anpassen. Die Referenz ist
Vpp²/(8*50); gilt für sauberen Sinus und tatsächliche 50-Ohm-Last.
RF-Prozent ist nur der Icom-Stellwert. Icom-Meter bleiben Rohwerte.
ADC wird automatisch umgeschaltet. Kalibriert wird hier nur der Vorlauf;
Rücklaufspannung an Dummyload ist kein bekannter Rücklauf-Leistungspunkt.

Bei erfolgreichem Test z.B. --levels 5,10,20,30,50,70,100; Scope-Skalierung muss
über den gesamten Bereich passende Referenzmessungen erlauben. Erst später starten.

Jeder Punkt: maximal 8 s Tastung, 5 s Pause. Hintergrundtimer lässt RTS los;
bei Fehler/Strg+C werden RTS deaktiviert und RX angefordert. Frequenz und
Leistungseinstellung werden nach Ende wiederhergestellt. Bei USB-Verlust,
Programmabsturz oder fehlender BK-IN-Funktion ist softwareseitiges Abschalten
nicht garantiert; lokalen manuellen Abbruch verfügbar halten.

Ausgabe CSV wird nicht überschrieben. Fehlerpunkte werden verworfen;
bereits vollständige Punkte bleiben erhalten. Scope/ADC/Icom werden nacheinander
während des konstanten Trägers abgefragt, nicht exakt gleichzeitig.
Unit-/Parser-Tests bestanden; realer automatischer Sendetest noch ausstehend.

## RTS-Anpassung

CW-Tastung verwendet standardmäßig RTS, passend zur vorhandenen Icom-Einstellung.
--key-line rts explizit; optional --key-line dtr. Icom-Einstellungen nicht ändern.
USB SEND darf nicht dieselbe Leitung wie USB CW Keying benutzen.
Timer, Fehlerabbruch und Abschluss geben die gewählte Leitung frei.
