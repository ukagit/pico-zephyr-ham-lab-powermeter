# Bedienung und Anschlüsse – Firmware 0.1.49

## Hardware

| Funktion | Anschluss |
|---|---|
| Pico | Raspberry Pi Pico W, RP2040; `rpi_pico/rp2040/w` |
| GPIO-I²C | GP0 SDA / GP1 SCL, gemeinsame Masse, Pull-ups nach 3,3 V |
| ADC | ADS1115, Adresse `0x48` |
| OLED | SSD1306, 128×64, Adresse `0x3c` |
| Vorlauf | A0−A3 |
| Rücklauf | A1−A3 |
| Referenz | A3 an Masse |
| Stromkoppler | A2−A3, eigener Detektorausgang |
| Akku | GP28 / Pico ADC2, Spannungsteiler 10 kΩ / 10 kΩ, Faktor 2 |
| Encoder | GP15 CLK / GP14 DT / GP13 Taster |
| OLED Kompakt / Voll / Akku | Taster GP19 / GP20 / GP21 gegen Masse |

GP0/GP1 sind nicht die GP16/GP17 des ursprünglichen HamLab. UART0 ist deaktiviert, die Shell läuft über USB CDC ACM. Detektoren: 1N4148. Der tatsächlich eingebaute halbierende Detektorteiler ist bereits in den ADC-seitigen Kalibrierwerten enthalten; keinen weiteren Faktor 2 auf die Kennlinien anwenden.

ADS1115-Autorange verwendet ±256 / 512 / 1024 / 2048 / 4096 / 6144 mV, getrennt für Vorlauf, Rücklauf und Stromkoppler. Ein größerer PGA-Bereich erlaubt **keine Spannung oberhalb der ADC-Versorgung**. A0 bis A3 müssen im zulässigen Versorgungsspannungsbereich bleiben. Ein Differenzeingang ersetzt keine galvanische Trennung.

Akku: eine Lithiumzelle, nominal 3,7 V. Akku+ → 10 kΩ → GP28 → 10 kΩ → GND; Akku−, A3 und ADC-GND gemeinsam. Nicht direkt an GP28 anschließen; Eingang maximal 3,3 V. Bei abgeschalteter Elektronik Rückspeisung über den Messeingang vermeiden. Anzeige ist Spannung, keine Ladezustandsmessung oder Schutzschaltung. `1800 mAh` ist eine Konfigurationsangabe, kein gemessener Kapazitätswert. Ein offener GP28-Eingang kann schweben. Der interne Pico-ADC misst mit 12 Bit und nominell 3300 mV Referenz, etwa alle zwei Sekunden. Die Referenztoleranz beeinflusst den Spannungswert; bei Bedarf `vref-mv` im Board-Overlay an die gemessene ADC-Versorgung anpassen.

## Build und Flash

Siehe [Schnellstart](../README.md#schnellstart). `tools/flash_openocd.sh` flasht `build/zephyr/zephyr.hex` über CMSIS-DAP mit RP2040-Target. `OPENOCD_ROOT` und `ZEPHYR_ROOT` lassen sich an den lokalen Installationspfad anpassen. Beim Build RAM/Flash-Verbrauch beachten: RP2040 hat begrenzte RAM-Reserve. Settings/NVS belegt die letzten 64 KiB des 2-MiB-Flashs ab `0x1f0000`.

Ein Firmware-Neuflash ist kein Ersatz für ein Backup von Zugangsdaten; vollständiges Löschen des Flashs entfernt die Settings. Normaler Start verbindet mit gespeicherten WLAN-Daten. Taste 3 / GP21 beim Start gedrückt wählt stattdessen den offenen AP. [Netzwerk-Anleitung](netzwerk-ap.md).

## USB, WLAN und Telnet

```bash
ls -l /dev/serial/by-id/
python3 -m serial.tools.miniterm /dev/ttyACM1 115200
```

`ttyACM1` ist ein Beispiel; richtigen Zephyr-CDC-Port wählen. Kein Benutzer-/Passwort-Login. In der Shell:

```text
wifi cred add -h
# Zugangsdaten gemäß der Hilfe dieser Zephyr-Version speichern
wifi_stored
network_status
net iface
```

Die WLAN-Befehlssyntax bewusst über die lokale Hilfe prüfen. `network_status` zeigt Verbindungszustand, Versuche, Fehler und Ports. DHCP vergibt die Adresse. Telnet: `telnet <IP> 23`. HTTP: `http://<IP>:8080/`. Keine Portweiterleitung ins Internet.

## Powermeter-Shell

| Befehl | Wirkung |
|---|---|
| `hamlab info` | Version, Board, Eingänge und Kalibrierstatus |
| `hamlab meter` | Letzter laufender Messwert als JSON; löst keine zusätzliche ADC-Wandlung aus |
| `hamlab status` | Aktueller vollständiger JSON-Zustand |
| `hamlab power` | Vorlauf-/Rücklaufleistung und Gültigkeit |
| `hamlab swr` | SWR, Peak und Qualitätsgrund |
| `hamlab calibration` | Gewählte Rücklaufkennlinie |
| `hamlab calibration 7100000` | Rücklaufkurve 7,1 MHz, Standard nach Neustart |
| `hamlab calibration 50100000` | Rücklaufkurve 50,1 MHz; numerisches SWR gesperrt |

Kurvenauswahl verändert weder Senderfrequenz noch Vorlaufkennlinie. Sie ist nur im RAM gespeichert und setzt die gehaltenen Werte zurück. Es gibt keine aktiven `hamlab freq`, `att` oder `sweep` mehr. Sperrwartezeiten der Shell-Abfragen sind begrenzt; bei Busy erneut abfragen.

## Webanzeigen

Vollansicht `/`: A0-Vorlaufwatt, Rohspannungen, ADC-Bereiche, Rücklauf, SWR, Max-Hold, letzter Zeitstempel sowie zusätzlicher A2-Stromkopplerwert und GP28-Akkuspannung. Der Stromkoppler wird als auf A0 abgeglichen bei 7,1 MHz / 50 Ω gekennzeichnet; bei oberem Plateau erscheint ein eigener Hinweis. Kompaktansicht `/compact`: große Wattzahl, Leistungs-/SWR-Balken und reduzierte Informationen; Link zur Vollansicht.

Leistungsbalken: grüne Füllung aktuell, gelbe Marke Max-Hold. Autoscale 10/20/50/100/150 W berücksichtigt aktuellen und gehaltenen Wert. Höhere Werte verschieben Hold sofort, nach etwa 3 s darf der gehaltene Wert wieder sinken. Peak-Reset per Schaltfläche in der Vollansicht oder Doppelklick auf den Leistungsbalken der Kompaktansicht.

SWR-Farbhintergrund: grün 1–1,5, gelb 1,5–2, rot ab 2; Skala bis 3+. Gemessene Marke weiß, Max-Hold gelb. Bei **~1** bleibt der Farbbalken sichtbar und zeigt eine **blaue Marke am Anfang**; der Wert ist angenommen, nicht quantitativ gemessen. Diese Farben sind Orientierung, keine Schutzabschaltung.

| Zustand | Anzeige und Bedeutung |
|---|---|
| Gültige Vor-/Rücklaufwerte | Numerisches SWR, weiße Marke |
| Rücklauf unter erster Stützstelle, geeigneter Vorlauf/Standardkurve | `~1`, blau; Annahme ohne nachgewiesene SWR-Obergrenze |
| Kein ausreichender Vorlauf oder Vorlauf außerhalb der Tabelle | `--`, neutraler Balken ohne Marke |
| Gültiges SWR > 3 | Deutlicher roter Hinweis und Marke am rechten Rand |
| Rücklauf über Messbereich / Rücklaufleistung ≥ Vorlauf | Deutlicher Hinweis; kein erfundener Zahlenwert |
| ADC-Fehler oder Übersteuerung | Messfehlerhinweis |
| Fehlende passende Vorlauf-Frequenzkalibrierung | Hinweis statt numerischem SWR |

Ein offener Ausgang wird nicht sicher erkannt. Ein ungültiger Zahlenwert beweist nicht automatisch SWR > 3. `~1` wird nicht als numerischer SWR in Hold oder letzter Messung gespeichert.

Web fragt den laufenden Zustand ungefähr alle 200 ms ab; Messung und OLED laufen unabhängig. Messschleife enthält etwa 100 ms Pause plus ADC-Zeit, OLED etwa 400 ms. Das sind Zielintervalle, keine garantierte Anzeigelatenz.

## OLED und Taster

Nach dem zehnsekündigen Netzwerkhinweis startet die Messanzeige. Fünf Ansichten: A0 kompakt, Vollansicht, Akku, A2-Leistung und A2-Voltmeter. GP19 wechselt A0 kompakt → A2-Leistung → A2-Voltmeter → A0 kompakt. GP20 wählt Details, GP21 im laufenden Betrieb Akku. Encoder-Drehen durchläuft alle fünf Ansichten; Encoder-Taster die drei ursprünglichen Ansichten. Taster gegen Masse, interne Pull-ups, etwa 30 ms Entprellung. Das monochrome OLED kennzeichnet geschätztes SWR als ~1 textlich. A2-Leistung zeigt mW/W und dBm; A2-Voltmeter misst 1:1 ohne externen Spannungsteiler.

## Zeitstempel

NTP im Pico: `pool.ntp.org` und `time.cloudflare.com`. Startversuch nach etwa 10 s, Fehlerwiederholung etwa alle 30 s, Erneuerung stündlich. DNS und UDP 123 erforderlich. Nach 24 h ohne Synchronisierung gilt die Uhr als nicht synchronisiert.

Zeit gehört zur letzten gültigen Vorlaufmessung mit verfügbarer NTP-Zeit; der SWR gehört zu derselben Erfassung oder ist `null`. Browser zeigt Europe/Berlin, API UTC als Unix-Millisekunden. Ohne HF bleibt der letzte Datensatz stehen. Speicherung nur RAM: kein dauerhaftes Messprotokoll nach Neustart. Automatische Messreihen auf dem PC schreiben eigene CSV-Zeitstempel.

## JSON-API

| Methode / Pfad | Verwendung |
|---|---|
| `GET /api/v1/info` | Version und Kalibrierinformationen |
| `GET /api/v1/state` | Laufender Snapshot für Web/Monitoring |
| `GET /api/v1/measure` | Frische Messung für Kalibrierwerkzeuge; kann Busy/Fehler melden |
| `POST /api/v1/peak/reset` | Leistungs- und SWR-Hold zurücksetzen |

```bash
curl http://192.168.178.98:8080/api/v1/state
curl -X POST http://192.168.178.98:8080/api/v1/peak/reset
```

`channels` enthält drei Kanäle: `forward` (A0−A3), `reverse` (A1−A3), `current` (A2−A3), jeweils signed Rohwerte, `range_mv`, `lsb_uv`, `voltage_v`, Fehler und `overrange`. `power` und `swr` haben unabhängige Gültigkeit. Erfolgreiche ADC-Erfassung (`measurement_valid:true`) bedeutet **nicht**, dass Watt oder SWR innerhalb der Kalibrierung liegen. Bei ~1: `swr.valid:false`, `swr.value:null`, `quality:"reverse_below_calibrated_floor"`; Rücklaufleistung bleibt `null`. `calibrated:false` kennzeichnet die weiterhin vorläufige Kalibrierung. Historische Felder `dbm`, `mw`, `vpp` in den ADC-Kanälen bleiben `null`.

## Zusätzlicher Stromkoppler und A0-Master

A0 liefert die primäre Vorlaufanzeige und bleibt zusammen mit A1 die Basis für SWR. A2 besitzt eine eigene Kennlinie aus gleichzeitig erfassten A0-Watt/A2-Spannungs-Paaren. Der A2-Wert ersetzt A0 nicht und hat keinen eigenen Hold oder letzten NTP-Messdatensatz. Hauptbalken, Kompaktansicht, Max-Hold und letzter Zeitstempel beziehen sich weiterhin auf A0.

| API-Feld | Bedeutung |
|---|---|
| `current_coupler.valid` | A2-Wattableitung innerhalb der abgeglichenen Kennlinie |
| `current_coupler.power_50ohm_w` | Zusätzliche Leistung, nur für ohmsche 50 Ω am Messort |
| `current_coupler.master` | `A0` |
| `current_coupler.calibration_frequency_hz` | `7100000`, nicht automatisch erkannte Sendefrequenz |
| `current_coupler.frequency_verified` | `false`, Bediener muss passende Frequenz sicherstellen |
| `current_coupler.quality` | `aligned_to_a0_50ohm_only`, `aligned_to_a0_upper_plateau`, `outside_calibrated_range` oder `adc_error` |
| `battery.input` | `GP28/ADC2` |
| `battery.divider_ratio` | `2` |

A2-Messfehler setzen den Zusatzwert ungültig, sperren aber die Richtkoppler-Auswertung nicht. `measurement_valid` beschreibt die Erfassung von A0/A1; den A2-Status separat prüfen. Akkufehler sind ebenfalls separat. Bereich und Endpunktbehandlung siehe [Abgleich-Ergebnis](abgleich-ergebnis-v0.1.32.md).

## Fehler eingrenzen

- Keine Verbindung: USB `network_status`/`net iface` prüfen, Adresse und WLAN-Daten vergleichen.
- Kein OLED/ADC: GP0/GP1, Versorgung, Masse, Pull-ups und Adressen prüfen.
- Rohwerte plausibel, Watt `null`: Tabellenbereich und gewählte Kurve prüfen.
- SWR ~1: Empfindlichkeitsgrenze; keine quantitative Aussage über die Last ableiten.
- A2-Watt ungültig: A2−A3-Rohspannung, Kennliniengrenzen und Verkabelung prüfen. Bei 1 % fehlt eine gültige A0-Referenz; eine hohe ADC-Auflösung ergänzt diese nicht.
- A0/A2 unterscheiden sich: Abgleich gilt nur für unveränderten Aufbau bei 7,1 MHz an 50 Ω; bei Fehlanpassung messen Richtkoppler und Stromkoppler unterschiedliche Größen.
- Batterie ungültig: Teiler/ADC-Spannung mit Multimeter vergleichen; kein angeschlossener Akku wird automatisch erkannt.
- Web wirkt alt: neu laden, gegebenenfalls Browsercache umgehen und `hamlab info` vergleichen.

## Kennlinienprofile ab 0.1.34

`hamlab curves list` zeigt Profile und Auswahl, `hamlab curves select current NAME` schaltet A2 um und speichert die Auswahl. Entsprechend sind `forward`, `reverse_7mhz` und `reverse_50mhz` auswählbar. [Import, Umschaltung und Rückkehr zu Standardkennlinien](kennlinien-profile.md).


## A2-Messkopf und Voltmeter

A2-Rohspannung, signierter ADC-Rohwert, PGA-Bereich und Auflösung stehen in der Vollansicht und JSON-API. Der Rohwert ist nur innerhalb desselben PGA-Bereichs direkt vergleichbar; voltage_v berücksichtigt die jeweilige Auflösung. Kein Spannungsteiler vor A2: Eingangsspannung entspricht der ADC-Spannung. Der 100-kΩ-Schutzwiderstand und Eingangsschutz begrenzen den Eingang; Belastung und Kennlinie bleiben aufbauabhängig. Eine von außen gemessene Impedanz von etwa 7 MΩ ist kein fester ADS1115-Betriebswert.

Vollansicht trennt die Kennlinienplots für Richtkoppler und A2. A2 hat einen eigenen Leistungsbalken, Autoscale und Hold, mW/W sowie dBm. /compact-a2 zeigt die A2-Leistungs- und Spannungsanzeige kompakt. Bei ADC-Übersteuerung oder ab 3,2 V ADC-Spannung erscheint OVERFLOW mit vollem roten Spannungsbalken. Das ist eine vorsorgliche Warnschwelle; eine Spannung vor bereits leitenden Schutzdioden kann daraus nicht bestimmt werden.

Die jeweilige Kennlinie muss zum angeschlossenen Messkopf passen. Profile importieren und nur current auswählen; [Profil-Anleitung](kennlinien-profile.md). Die mW/dBm-Angabe gilt bei einer Leistungskalibrierung, nicht für beliebige Gleichspannungen am Voltmeter.
