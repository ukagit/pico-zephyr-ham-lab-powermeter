# Messung, Kalibrierung und Erkenntnisse

Stand: Firmware 0.1.32, 6. Oktober 2026. Die Aussagen beziehen sich auf den tatsächlich gemessenen Laboraufbau; keine zertifizierte Leistungsmessung.

## Messkette

IC-7300 → kurzes 50-Ω-Kabel → Richtkoppler mit zwei 1N4148-Detektoren → 50-Ω-Kabel → Dummyload. Eingesetzt wurde unter anderem eine kommerzielle 600-W-Dummyload mit angegebenem Bereich 0–3 GHz. Die Nennangabe ersetzt keinen Nachweis ihrer Anpassung einschließlich Kabel und Stecker.

ADS1115 misst A0−A3 (Vorlauf) und A1−A3 (Rücklauf); A3 liegt an Masse. Detektor-Gleichspannungen gelangen über den realen Teiler zum ADC. Zusätzlich angeschlossenes Analogmessgerät und dessen Einstellwiderstand belasten den Detektor. Seine Einstellung blieb fest; beobachtete Änderungen um 0,01 V wurden nicht separat korrigiert. Das ist kein Nachweis, dass ihr relativer Fehler bei kleinen Spannungen vernachlässigbar ist.

Siglent SDS1202X-E, Tastkopf 1:10, misst HF-Spannung am Lastanschluss beziehungsweise später am Kopplerausgang. Die Werte des `sds`-CLI enthalten bereits den eingestellten Tastkopffaktor. Messposition, Kabel, Last und Tastkopfanschluss sind Teile der Referenzkette und müssen im Protokoll festgehalten werden.

## Aktueller Aufbau mit zwei Kopplern

Der Richtkoppler bleibt für Vorlauf A0 und Rücklauf A1 angeschlossen. Seit 0.1.31 misst A2−A3 zusätzlich den neuen Koppler mit einem Stromtransformator. A3 bleibt Masse. Die Akkumessung wurde auf GP28 verlegt. Die zusätzliche Strommessung ersetzt keinen Richtkoppler und wird nicht in die SWR-Berechnung eingesetzt.

Der Stromkoppler wurde zuerst vorübergehend an A0 untersucht. Für diesen Versuch waren die alten A0-Wattwerte unbrauchbar; die Vergleichsprogramme werteten deshalb nur ADC-Spannungen aus. Danach folgte eine eigene Scope-Referenzkurve und schließlich der aktuelle Abgleich auf den wieder angeschlossenen A0-Richtkoppler. Diese drei Schritte liefern unterschiedliche Aussagen und dürfen nicht miteinander vermischt werden.

## Referenz aus HF-Spannung

Für einen Sinus und eine rein ohmsche Last gilt:

`Vrms = Vpp / (2 · √2)` und `P = Vpp² / (8 · R)`.

Bei 50 Ω: `reference_w = Vpp² / 400`. Beispiel: 188 Vss ergeben 88,36 W. Es wird das Vpp-Verfahren beibehalten, nicht zwischen Vpp- und RMS-Referenz gewechselt. RMS dient zusätzlich zur Plausibilitätskontrolle: `RMS · 2√2 / Vpp` liegt für einen idealen Sinus bei 1.

Für ideal ohmsche 25 Ω bezogen auf 50 Ω: Reflexionsfaktor −1/3, SWR 2. Lastleistung `Vpp²/200`, Vorlaufleistung `9·Vpp²/1600`, Rücklaufleistung `Vpp²/1600`. Das sind Modellwerte für die HF-Messstelle, nicht allein durch eine DC-Widerstandsmessung garantierte Referenzen. Ein vorgeschaltetes Kabel verändert Phase und Messbedingungen; Verluste sind in diesen Formeln nicht korrigiert.

Wichtig: CSV `reference_w` ist die zugeordnete **Vorlaufreferenz**, `load_w` die Lastleistung. Bei 25 Ω ist `reverse_reference_w` die modellierte Reflexionsleistung.

## Ablauf der Vorlaufkalibrierung

1. IC-7300 in CW, Tuner aus, 19200 Baud, vorhandenes USB-CW-Keying über RTS beibehalten.
2. Scope mit korrekt eingestelltem Tastkopffaktor und vollständigem, unverzerrtem Signal betreiben.
3. Sendeleistungsstufen einstellen; Prozentwerte sind Stellgrößen, keine Wattreferenz.
4. HF-Spannung, ADS-Spannungen/Bereiche und ICOM-Anzeigen während desselben kurzen Sendefensters erfassen.
5. Kleine Leistungen mit geeigneter kleinerer V/div-Skala, große Leistungen mit größerer Skala erfassen; später Zeitbasis/V-div über CLI automatisiert setzen.
6. CSV-Daten prüfen; nur geeignete Reihen in Stützstellen übernehmen.

Der fehlende Detektorteiler führte zunächst zu Spannungen über der zulässigen ADC-Versorgung. Die damaligen hohen Leistungswerte dürfen nicht als gültige Detektorkalibrierung verwendet werden. Der nachträglich eingebaute halbierende Teiler änderte die Kennlinie. Die aktive Tabelle verwendet ADC-seitige Werte des geteilten Aufbaus.

Vorlaufkurve: 16 Stützstellen, 7,03167 MHz, 1,2544–92,16 W. Kleine 1–4-%-Stufen wurden ergänzt, geeignete 20-V/div-Punkte übernommen; höhere frühere Punkte bleiben vorläufig. Zwischen Stützstellen wird linear interpoliert. Keine Nullstützstelle, keine Fortführung auf 150 W.

## Rücklaufkalibrierung mit umgedrehtem Koppler

Die frühe Rücklaufreihe mit 25 Ω war begrenzt und wurde durch die neue umgedrehte 50-Ω-Messung ersetzt.

Für diese Messung wurde der Koppler **physisch umgedreht**, die ADC-Zuordnung blieb unverändert. Kalibrierpaar deshalb **`reverse_v` gegen `reference_w`**. Das CSV-Feld `reverse_reference_w` bleibt an 50 Ω null und darf für diese Detektorkalibrierung nicht benutzt werden.

Am 6. Oktober wurden je Frequenz 15 Leistungsstufen von 1 bis 100 % und drei Zeitbasiseinstellungen aufgenommen: 45 Datensätze bei 7,1 MHz und 45 bei 50,1 MHz. Pro Stufe wurden Spannung und Leistung arithmetisch über die drei Wiederholungen gemittelt. Gleiche oder fallende obere Leistungsmittel wurden durch gewichtetes Zusammenfassen benachbarter Punkte monoton gemacht; kein künstlicher Anstieg auf einem Plateau.

- 7,1 MHz: 90/100 % zusammengefasst; 14 aktive Stützstellen, 1,3456–88,99 W.
- 50,1 MHz: 80/90 % gepoolt; 14 aktive Stützstellen, 1,1096–70,56 W.

Gemittelte Endpunkte begrenzen die Tabelle. Einzelmessungen am Endpunkt können außerhalb liegen. Tabelle und Herkunft: [Rücklaufbericht](ruecklauf-0.1.24.md), Originalreihen in [calibration](calibration/).

Die Kombination Vorlauf 7,03167 MHz / Rücklauf 7,1 MHz wird vorläufig verwendet. Für 50,1 MHz fehlt die passende Vorlaufkurve; numerisches SWR ist dort gesperrt. Das bedeutet nicht, dass bereits alle Frequenzmessungen als Kurven eingebaut wären.

## Unterer Bereich und 1N4148

Die Detektoren wurden zunächst fälschlich als Schottky bezeichnet. Tatsächlich sind 1N4148 eingebaut. Unsere empirisch erfassten Stützstellen ändern sich durch diese Korrektur nicht. Eine Diode besitzt keine scharfe universelle Spannungsschwelle; Empfindlichkeit hängt von HF-Spannung, Diodenkennlinie, Auskopplung und Last am Detektor ab.

Ein FY6900-Test mit maximal etwa 13 Vss an 50 Ω (0,4225 W bei Sinus) zeigte keinen erkennbaren Detektorunterschied gegenüber ohne Signal. Das liefert **keine** Kalibrierstützstelle, keinen genauen Empfindlichkeitsgrenzwert und keinen Beweis, dass allein die Diode Ursache ist.

Die lineare Nullpunktfortführung von Version 0.1.28 machte kleine Restspannungen zu scheinbar genauen SWR-Werten. Sie wurde wieder entfernt. Aktuell wird unter erster Rücklaufstützstelle **~1 als Anzeigeannahme** genutzt, nicht numerisch gemessen oder gespeichert.

Beispielreihe bei 50-Ω-Last, 7-MHz-Aufbau:

| Einstellung | Vorlauf W | Rücklaufspannung | Frühere Nullpunktschätzung SWR |
|---|---:|---:|---:|
| 5 % | 4,1775 | 6,4062 mV | 1,492 |
| 20 % | 17,7972 | 10,2422 mV | 1,275 |
| 50 % | 49,4909 | 15,0781 mV | 1,193 |
| Ohne Senden | nicht kalibriert | 0,4922 mV | kein gültiges SWR |

Diese SWR-Zahlen sind **verworfen**, keine Referenz für die Last. Ruheoffset ist klein gegenüber dem Signalrest und erklärt dessen Anstieg nicht allein. Echte Reflexion, Kopplerrestsignal und Detektoreffekte lassen sich daraus nicht sicher trennen.

## Stromkoppler: Tastkopfeinfluss und Scope-Kurve

Hypothese: Ein reiner Stromabgriff mit einem Transformator könnte im vorhandenen Aufbau weniger empfindlich auf die zusätzliche Tastkopfkapazität reagieren. Er benötigt keinen Abgleich zwischen Strom- und Spannungspfad zur Richtungstrennung. Das macht ihn einfacher, aber nicht grundsätzlich rückwirkungsfrei oder für beliebige Lasten genauer.

Die Messungen bei 7,1 MHz zeigten:

- Im ersten dichten Vergleich lagen Änderungen ab 20 % meist unter 1 % der Detektorspannung; kleine Stufen waren empfindlicher gegenüber zeitlichen Veränderungen und Ruhewerten.
- Beim späteren Vergleich der Scope-Messreihe mit dem Ohne-Scope-Lauf lagen die Spannungsunterschiede bei 3–100 % unter etwa 0,9 %. Bei 1/2 % waren die Abweichungen größer; die Punkte stammten aus einem früheren Teillauf. Ein kurzer erneuter Vergleich bestätigte diese größeren Abweichungen nicht in derselben Höhe.
- Das unterstützt eine geringere Empfindlichkeit des untersuchten Aufbaus bei 7,1 MHz. Es ist kein Nachweis absoluter Wattgenauigkeit und kein Beweis für das Verhalten bei 50 MHz oder Fehlanpassung.

Ein Tastkopf kann tatsächliche Last und tatsächlichen Strom verändern. Auch ein richtiger Stromsensor muss diese reale Veränderung anzeigen. Sensor-Rückwirkung, Senderreaktion und Zeitdrift müssen von einem reinen Anzeigefehler unterschieden werden. Für weitere Vergleiche ist eine Folge ohne–mit–ohne Tastkopf aussagekräftiger als nur zwei zeitlich getrennte Läufe.

Die zunächst erfasste Stromkoppler-Scope-Kurve kombinierte zwei Teilläufe, je drei Zeitbasen pro Stufe. 90/100 % wurden gepoolt; oberer Bezug etwa 88,36 W. Diese Kurve war in 0.1.31 aktiv, ist seit 0.1.32 aber durch den A0-Master-Abgleich ersetzt. Unterschiedliche Referenzbedingungen erklären, warum beide Wattanzeigen zuvor voneinander abwichen; ein Abgleich ist keine nachträgliche absolute Validierung.

## Aktueller A2-Abgleich mit A0 als Master

Auf Wunsch wird A0 als gemeinsame Referenz verwendet. Bei unverändertem Aufbau, 7,1 MHz und 50 Ω ohne Scope wurden 16 ICOM-Stufen von 1–100 % mit jeweils drei gemeinsamen Pico-Abfragen aufgenommen. Jede Abfrage enthält A0-Spannung, die daraus berechnete A0-Wattzahl und A2-Spannung. Der ADS1115 wandelt die Eingänge nacheinander, nicht zeitgleich; die Werte gehören zum selben kurzen Sendefenster.

Verwendete Zuordnung: **A2-Detektorspannung → A0-Masterleistung**. Die ICOM-Prozentstellung ist keine Wattreferenz. Das Skript setzt keine Kennlinie selbstständig in der Firmware.

| Stufe | A2-Mittelspannung | A0-Masterleistung | Behandlung |
|---|---:|---:|---|
| RF OFF | −0,253 mV | keine gültige Leistung | Ruhewert, kein Wattstützpunkt |
| 1 % | 0,0106302 V | keine gültige Leistung | A0 unter seiner Kennlinie, ausgeschlossen |
| 2 % | 0,0197136 V | 1,4943 W | untere gültige Stützstelle |
| 20 % | 0,3216979 V | 16,6786 W | reguläre Stützstelle |
| 50 % | 0,4796042 V | 47,2225 W | reguläre Stützstelle |
| 90 % | 0,5584375 V | 83,0575 W | mit 100 % zusammengefasst |
| 100 % | 0,5586042 V | 83,6348 W | mit 90 % zusammengefasst |

Die beiden oberen Mittelspannungen liegen nur rund 0,167 mV auseinander, während die Streuung je Stufe etwa 1,35–1,43 mV beträgt. Eine steile Interpolation dazwischen würde Rauschen verstärken. Daher gemeinsamer Endpunkt **0,5585208 V / 83,3462 W**. Das Plateau kann 90/100 % nicht zuverlässig unterscheiden; es beweist nicht allein eine Detektorsättigung.

Begrenzte konstante Randbereiche umfassen die tatsächlich beobachteten Einzelspannungen bei 2 % und im oberen Plateau: gesamter Bereich **0,0196875–0,5600625 V**. Es wird nicht außerhalb dieser Grenzen extrapoliert. Rohspannung bleibt auch bei ungültiger Wattableitung sichtbar.

Ergebnis: gemittelte A2-Anzeige ist auf A0 abgestimmt. Der Abgleich übernimmt die Unsicherheit und Aufbaueinflüsse der A0-Kurve. Er liefert weder eine unabhängig genauere Leistungsmessung noch eine Kalibrierung bis 150 W. Einzelanzeigen schwanken weiter, insbesondere im steileren oberen Kurvenbereich.

Vollständige Messung: [Abgleich-CSV](calibration/abgleich-a2-auf-a0-7mhz.csv). Aktive A2-Stützstellen: [CSV](calibration/stromkoppler-a0-master-v0.1.32.csv), `src/current_calibration.h`. Details: [Abgleich-Ergebnis](abgleich-ergebnis-v0.1.32.md).

## Leistung aus reinem Strom: Voraussetzung

Für eine bekannte ohmsche Last am Messort gilt `P = Irms² · R`. Ein auf 50 Ω abgeglichener Stromkoppler kann dafür eine praktische Wattanzeige liefern. Bei einer komplexen Last benötigt die allgemeine Wirkleistung dagegen Spannung, Strom und deren Phasenbeziehung. Auf einem fehlangepassten Kabel hängt der lokale Strom außerdem von Messposition und stehender Welle ab.

Deshalb bleiben die Aufgaben getrennt: Richtkoppler für Vorlauf/Rücklauf/SWR; Stromkoppler als zusätzliche 50-Ω-Anzeige. Ein DC-gemessener Lastwiderstand allein bestätigt keine ideale HF-Last über den gesamten Frequenzbereich.

## Was wir gelernt haben

- **Messaufbau ist Teil der Kalibrierung.** Kabelwechsel, Tastkopfposition, Masseanschluss und zusätzliche Kapazität können Messbedingungen und tatsächliche Last verändern.
- Der 1:10-Tastkopf ist kein rückwirkungsfreier Beobachter. Ein Vergleich bei 51 MHz ergab ungefähr 66 W ohne und 57 W mit Tastkopf in der damaligen Anzeige. Bei 7 MHz war der Einfluss kleiner. Diese Werte zeigen Aufbaueinfluss, nicht dessen eindeutige Ursache oder eine unabhängige absolute Referenz.
- Ein kurzer direkter Spitze-/Masseanschluss verbesserte die reproduzierbare Scope-Anbindung gegenüber längeren Anschlüssen. Auch danach war die Rückwirkung nicht ausgeschlossen.
- Scope-Zeitbasis und V/div müssen zum Signal passen. Bei kleiner Aussteuerung sinkt die Aussagekraft; Abschneiden des Sinus macht Vpp unbrauchbar. Wiederholungen über Zeitbasen helfen, sind aber kein unabhängiger Genauigkeitsnachweis.
- PGA-Autorange und erlaubte Eingangsspannung sind verschiedene Grenzen. ±6,144 V Messbereich gestattet keine 6 V an einem mit 3,3 V versorgten ADC.
- Tuner muss für definierte Lastvergleiche aus sein; ein falscher Lastschalter machte frühe 25-/50-Ω-Vergleiche unbrauchbar.
- Große und kleine Detektorsignale benötigen eigene Stützstellen. Eine hohe ADC-Auflösung ersetzt keine Detektorempfindlichkeit.
- Kopplerkompensation hängt vom Aufbau ab. Kopierte Kapazitätswerte sind keine universelle Korrektur; nach Hardwareänderungen erneut prüfen und gegebenenfalls kalibrieren.
- Gute Wiederholbarkeit im Bereich 1–30 W bedeutet nicht automatisch absolute Genauigkeit <5 %. Bisher fehlt eine unabhängige, ausreichend bekannte HF-Leistungsreferenz; weder ±5 % noch ±15 % sind zugesichert.

## Stand und sinnvolle nächste Schritte

Das Gerät ist als praktischer Laborindikator für den unveränderten Aufbau nutzbar. Numerische Anzeige nur innerhalb der Tabellen; ~1 ist eine qualitative Annahme. Zielbereich 10–150 W und Frequenzbereich etwa 1–51 MHz sind nicht vollständig kalibriert umgesetzt.

Weitere Arbeit nach Bedarf: passende Vorlauf-Frequenzkurven, unabhängige Referenz, empfindlichere Rücklaufdetektion, erneute Kurvenaufnahme nach Hardwarewechsel. Vorherige Messungen bleiben dokumentiert; kein unnötiges Wiederholen der ganzen Reihe nur wegen einer falschen Diodenbezeichnung.

## Messdateien zum Stromkoppler

| Datei | Einordnung |
|---|---|
| [koppler_vergleich.csv](calibration/koppler_vergleich.csv) | Früher dichter Ohne-/Mit-Tastkopfvergleich, Stromkoppler damals an A0 |
| [stromkoppler_7mhz_scope.csv](calibration/stromkoppler_7mhz_scope.csv) | Erster Scope-Teillauf, 1/2 % vollständig, bei 3 % abgebrochen |
| [stromkoppler_7mhz_scope_teil2.csv](calibration/stromkoppler_7mhz_scope_teil2.csv) | Fortsetzung 3–100 %; ersetzt den unvollständigen 3-%-Punkt |
| [stromkoppler_7mhz_ohne_scope.csv](calibration/stromkoppler_7mhz_ohne_scope.csv) | Vergleichslauf ohne Scope-Tastkopf, noch Stromkoppler an A0 |
| [stromkoppler-7mhz-stuetzstellen.csv](calibration/stromkoppler-7mhz-stuetzstellen.csv) | Frühere Scope-basierte Stromkopplerkurve von 0.1.31, heute ersetzt |
| [abgleich-a2-auf-a0-7mhz.csv](calibration/abgleich-a2-auf-a0-7mhz.csv) | Aktueller gepaarter A0/A2-Abgleich, A0 ist Master |
| [stromkoppler-a0-master-v0.1.32.csv](calibration/stromkoppler-a0-master-v0.1.32.csv) | Aktive A2-Stützstellen einschließlich begrenzter Randstücke |
| [firmware-v0.1.32-kennlinien.csv](calibration/firmware-v0.1.32-kennlinien.csv) | Alle vier aktiven Kurven, direkt aus Firmware-Headern exportiert |

Die Original-CSVs bleiben unverändert. Frühere Daten gelten für ihre dokumentierte Verdrahtung und Referenz; aktuelle aktive Kennlinien stehen ausschließlich in den beiden Headern und dem daraus erzeugten Gesamtexport.

## Quellen und Messdateien

- [DK4SX: Richtkoppler und Kompensation](https://dk4sx.darc.de/swr.htm)
- [DK9MAT: Aufbau mit Kompensationshinweisen](https://dk9mat.darc.de/qro-pa/25.html)
- [DJ0ABR: Richtkoppler und Messauskopplung](https://projects.dj0abr.de/doku.php?id=de:pwrswr:pwrswr_dir)
- [DL6GL: Richtkopplermessungen mit VNWA](https://dl6gl.de/messungen-an-richtkopplern-mit-dem-vnwa.html)
- [DL6GL: Tandem-Match, Strom- und Spannungstransformatoren](https://dl6gl.de/digitales-swr-powermeter-mit-pep-anzeige/2-tandem-match-koppler.html)
- [Tektronix: Rückwirkung von Oszilloskop-Tastköpfen](https://www.tek.com/en/documents/application-note/how-oscilloscope-probes-affect-your-measurement)
- [Carobbi/Millanta: Circuit Loading in Radio-Frequency Current Measurements](https://www.researchgate.net/publication/220408955_Circuit_Loading_in_Radio-Frequency_Current_Measurements_The_Insertion_Impedance_of_the_Transformer_Probes)
- [1N4148-Datenblatt](https://assets.nexperia.com/documents/data-sheet/1N4148_1N4448.pdf)

Die Quellen geben Hintergrund, keine nachträgliche Validierung unserer Leistungsmessung. Aktive Stützstellen: `src/power_calibration.h` und `src/current_calibration.h`, [CSV](calibration/firmware-v0.1.32-kennlinien.csv), [Grafik](images/powermeter-kennlinien-v0.1.32.png).
