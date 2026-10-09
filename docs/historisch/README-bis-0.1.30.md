# Historische README – nicht die aktuelle Bedienungsanleitung

Enthält überholte Zwischenstände. Maßgeblich sind die aktuelle README und die dort verlinkten Anleitungen.

# pico-zephyr-ham-lab-powermeter

Version **0.1.13**, eigenständige Kopie von pico-zephyr-hamlab 0.3.7 für **Pico W / RP2040**.
Erster Schritt: USB-Shell, gespeichertes WLAN, Telnet und vorhandene Oberflächen.
Quellpaket; Build und Hardwaretest auf dem Pico W stehen noch aus.

## Build

In der vorhandenen Zephyr-4.4.99-Umgebung:

```bash
cd /home/ulrich/Dokumente/zephyrproject/apps/pico-zephyr-ham-lab-powermeter
west blobs fetch hal_infineon
west build -b rpi_pico/rp2040/w -S cdc-acm-console . -d build -p always
./tools/flash_openocd.sh
```

Das Flash-Skript verwendet CMSIS-DAP und target/rp2040.cfg. OPENOCD_ROOT und
ZEPHYR_ROOT können wie bisher angepasst werden. Alternativ zephyr.uf2 per BOOTSEL.
Build-Ausgabe mit RAM/Flash-Verbrauch prüfen; Settings liegen bei 0x1f0000,
64 KiB am Ende des 2-MiB-Flashs. Der neue Pico benötigt eigene WLAN-Zugangsdaten.

## USB und WLAN

USB ist eine Shell ohne Benutzer-/Passwort-Anmeldung. Nach dem Flash den Port ermitteln:

```bash
ls /dev/ttyACM*
python3 -m serial.tools.miniterm /dev/ttyACM0 115200
```

In der Pico-Shell:

```text
hamlab info
network_status
wifi cred add -h
```

Zugangsdaten mit der von `wifi cred add -h` ausgegebenen Syntax speichern,
danach `wifi_stored` ausführen. Der übernommene Autostart verbindet auch nach Neustart.
`net iface` zeigt die DHCP-Adresse; `network_status` den Verbindungszustand.

```bash
telnet <pico-ip> 23
curl http://<pico-ip>:8080/api/v1/info
```

In der Telnet-Shell `hamlab info` und `hamlab status` prüfen. Telnet ebenfalls ohne
Benutzer-/Passwort-Anmeldung im vertrauenswürdigen lokalen Netz.
Web: http://<pico-ip>:8080/ und /compact.
Die Shell-Befehle bleiben für Kompatibilität unter `hamlab`.

## Hardware und Messstatus

GPIO-I²C: GP0 SDA / GP1 SCL; ADS1115 0x48, SSD1306 0x3c.
Encoder: GP15 CLK / GP14 DT / GP13 Taster. DDS und ATT bleiben übernommen.
A0-A3 Vorlauf, A1-A3 Rücklauf, A3 Masse, A2 frei. AutoRange je Kanal.
Vorläufige Vorlauf-Wattanzeige bei 7.031670 MHz, gemessen 4..92.16 W.
Rücklaufleistung und SWR bleiben unkalibriert. Details: [Kalibrierung](../vorlauf-0.1.4.md).
Web: http://192.168.178.98:8080/ und /compact.

## Abnahme von Schritt 1

1. Build erfolgreich; RAM/Flash-Verbrauch dokumentieren.
2. USB: `hamlab info` zeigt 0.1.2 und rpi_pico/rp2040/w.
3. WLAN-Zugangsdaten speichern, DHCP-Adresse prüfen.
4. Telnet: `hamlab info` ausführen; beide Webansichten öffnen.
5. Neustart: automatische WLAN-Verbindung und Telnet erneut prüfen.

Danach A2/A3-Rohspannungen ergänzen und eigenen Koppler/Detektorkennlinien auslegen.
Historische Bedienung und Dokumentation: docs/hamlab-0.3.7-basis.md.

## Buildfix 0.1.2

Der erste RP2040-Build meldete undefinierte z_impl_sys_rand_get-Referenzen.
Für die Inbetriebnahme ist Zephyrs Timer-Zufallszahlengenerator aktiviert.
Er ist nicht kryptografisch sicher und nur als Übergang für den lokalen
Verbindungstest vorgesehen. Vor dauerhaftem Betrieb die Entropiequelle prüfen.
Build auf dem Zielsystem erneut mit -p always ausführen.

## OLED / I²C 0.1.2

Gemeinsamer GPIO-I²C-Bus für SSD1306 und ADS1115: GP0 SDA, GP1 SCL.
UART0 deaktiviert, damit GP0/GP1 frei bleiben; USB-Shell bleibt erhalten.
SSD1306: 128×64, Adresse 0x3c. OLED startet automatisch beim Boot.
Pull-ups nach 3,3 V und gemeinsame Masse verwenden.
OLED-ready/not-found-Meldung beim Boot beobachten. Nach Anschluss neu starten.

## 0.1.3: ADS1115-Differenzmessung

Vorlauf A0-A3, Rücklauf A1-A3; A2 frei. GPIO-I²C GP0 SDA / GP1 SCL.
A3 ist Referenzeingang, keine intern erzeugte Masse. Beide Eingänge jeder
Differenzmessung müssen innerhalb GND..VDD des ADS1115 bleiben.
AutoRange je Kanal: ±6144/4096/2048/1024/512/256 mV.
Start im breitesten Bereich, Umwahl bei >80% oder <30%; Ziel <=80%.
Nach jeder Umwahl neue Single-Shot-Wandlung mit 128 SPS; Timeout 60 ms.
Negative Werte bleiben für Offsetdiagnose erhalten. Fehlerwerte erscheinen
als null, nicht als Nullspannung. Sättigung wird markiert und neu gemessen.

Shell: `hamlab meter` für neue Messung, `hamlab status` für letzten Stand.
API: GET /api/v1/measure und /api/v1/state. Rohwert, range_mv, lsb_uv, voltage_v.
OLED zeigt beide Differenzspannungen, Webansichten zeigen Rohwerte und Bereiche.
DDS/ATT und Encoder bleiben vorhanden. AD8307-Sweep, Watt und SWR deaktiviert.
Die alten Kalibrierdateien sind nur historische Bestandteile, nicht aktiv.

Erster Test ohne HF: A0, A1 und A3 mit ADC-GND verbinden und Offset lesen.
Danach A3 an ADC-GND lassen und bekannte kleine DC-Spannung gegen ADC-GND
auf A0 bzw. A1 geben (z.B. 0.1 V und 1.0 V); mit Multimeter vergleichen.
Build und realer ADC/OLED-Test stehen aus.

## 0.1.5 Peak-Hold

Web und OLED zeigen gehaltene Vorlaufleistung; Web-Button setzt Peak zurück.
SWR-Peak vorbereitet, noch unkalibriert. DDS-Infos aus Anzeigen entfernt.
Unterbereich-Rohspannungen dokumentiert, Wattreferenzen fehlen noch:
[Messnotizen](../unterbereich-messnotizen.md).

## 0.1.6 Balkenanzeige

Grün: aktuelle Vorlaufleistung. Gelbe Marke im Balken: gehaltener Maximalwert.
Autoscale 10,20,50,100,150 W, kleinster Bereich der aktuellen Leistung und Peak umfasst.
Ein hoher Peak hält den Bereich bis zum Reset; danach passt er sich erneut an.
150 W ist nur eine Anzeigeskala, die Kalibrierung bleibt bei 4..92.16 W.

## 0.1.7 Kompaktansicht

/compact zeigt nur Watt und Leistungsbalken samt Skala und Max-Hold-Marke.
Doppelklick auf den Balken setzt Max-Hold zurück. Vollansicht unverändert.

## 0.1.8 Zeitbegrenztes Max-Hold

Höhere Werte sofort; nach 3 Sekunden fällt die Marke auf den aktuellen gültigen Wert.
Ohne kalibrierten Wert verschwindet sie nach Ablauf der Haltezeit. Autoscale folgt.
Kompakt: kleine Überschrift, Watt/Balken, letzte gültige ADC-Abfrage mit Browserdatum/-zeit, Link Vollansicht.
Der Zeitstempel ist die Empfangszeit im Browser, keine NTP-Uhr im Pico.

## 0.1.9 NTP-Zeitstempel

NTP-UTC wird im Pico synchronisiert (pool.ntp.org, Ausweichserver time.cloudflare.com).
Erster Versuch nach 10 s, Fehler-Wiederholung 30 s, Synchronisierung stündlich.
DNS über DHCP; Internetzugang und UDP 123 erforderlich.
Nach 24 h ohne Sync gilt die Uhr als nicht synchronisiert.
JSON time.last_measurement_unix_ms und last_forward_w gehören zur letzten gültigen kalibrierten Vorlaufmessung mit verfügbarer NTP-Zeit. Ohne Signal bleibt dieser Datensatz stehen.
Web zeigt Europe/Berlin inklusive Sommerzeit; UTC im Tooltip. Browserzeit ist keine Quelle mehr.
Zeitstempel im RAM, nach Neustart bis NTP und neuer Leistungsmessung null.
Kompakt zeigt Max-Hold zusätzlich als kleinen Text.

## 0.1.10 Schnellere Liveanzeige

Web liest /api/v1/state etwa alle 200 ms, ohne weitere ADC-Konvertierung auszulösen.
Keine überlappenden Abfragen. Messschleife 100 ms Pause plus ADC-Laufzeit; OLED separat ca. 400 ms Pause.
/api/v1/measure bleibt für Kalibrierskripte eine frische Messung.
Reale Aktualisierung hängt zusätzlich von WLAN, AutoRange und GPIO-I²C-Laufzeit ab.

## 0.1.11 Vorläufiger Rücklauf / SWR

Siehe [Rücklauf und abschließender Messplan](../ruecklauf-0.1.11.md).
Rücklauf 1.0816..2.6244 W; darunter SWR --, nicht automatisch 1.0.
Shell hamlab swr, Web-Vollansicht und OLED zeigen numerisches SWR im gültigen Bereich.

## 0.1.12 Shell-Abfragen

hamlab swr und hamlab power lesen laufende Messwerte ohne neue ADC-Konvertierung.
Messsperre maximal 250 ms, danach busy statt unbegrenzt zu warten.
Kein Hardware-Nachweis der ursprünglichen Hängerursache; bitte auf Pico testen.

## 0.1.13 SWR-Balken

Voll-/Kompaktansicht: SWR-Balken von 1 bis 3+, grün 1..1.5, gelb 1.5..2, rot 2..3+.
Weißer Strich aktuelles SWR, schmaler gelber Strich 3-s-Max-Hold.
Oberhalb 3 bleibt Zahl unverändert, Marke am rechten Rand. Fehlende Werte werden nicht als 1 ausgegeben.
Farben sind Orientierung, keine Geräteschutzgrenzen. Kennlinien unverändert.


## Version 0.1.14: OLED und Akku

Startseite OLED: Kompakt. GP19 wählt Kompakt (Watt groß, Balken mit Hold, SWR), GP20 Vollansicht, GP21 Batterie. Alle drei Taster gegen GND; interne Pull-ups, Entprellung 30 ms. Alte DDS-Ansteuerung ist deaktiviert; keine Ausgänge auf GP19/20/21.

Eine 3,7-V-Lithiumzelle / 1800 mAh: Akku+ → 10 kΩ (1 %) → A2 → 10 kΩ (1 %) → GND. Akku−, A3 und ADS-GND verbinden. Optional 100 nF von A2 nach Masse. ADC wird als A2-A3 mit ±4,096 V gemessen; Akkuspannung = ADC-Spannung × 2. Der Teiler ist Voraussetzung! Nicht direkt an A2 anschließen. ADS-Eingänge müssen zwischen GND und VDD bleiben, auch bei ausgeschaltetem Gerät; daher Akku-Messzweig zusammen mit der Versorgung abschalten. Diese Messung ist keine Ladeschaltung und kein Tiefentladeschutz. Zunächst Spannung am Multimeter mit OLED vergleichen; keine Ladeprozent-/Restlaufzeitschätzung. Ein unbeschalteter Eingang kann schweben und ist keine Batterieerkennung.

JSON `battery`: valid, error, input, voltage_v, adc_voltage_v, divider_ratio, nominal_capacity_mah. Batteriesampling 2 s; Fehler beeinflussen nicht die RF-Gültigkeit. `time.last_swr` gehört zur selben Erfassung wie last_forward_w/last_measurement_unix_ms und ist null bei ungültigem SWR.

Hostprüfung: Web-JavaScript-Syntax; C-Framebuffer mit Bounds-Sanitizern, Batteriekanal/Skalierung und gemeinsame NTP/SWR-Erfassung. Zephyr-Build, Flash, Taster und echte ADC/OLED-Hardware hier nicht geprüft.


## Version 0.1.15: Stackreserve

Nach gemeldetem Hänger in 0.1.14 reduziert 0.1.15 den Stackbedarf von HTTP und JSON-Aufbau. JSON-Zwischenpuffer sind statisch und durch die bestehende Messsperre geschützt; HTTP-Antwortpuffer gehört ausschließlich dem einzelnen HTTP-Thread. Antwortpuffer 3072 Byte; OLED-Stack 3072 Byte. Bei zu kleinem Antwortpuffer wird eine gültige JSON-Fehlermeldung erzeugt. Die vermutete Stacküberschreitung ist ohne Hardware-Faultlog nicht abschließend bestätigt. Kennlinien, Tasterbelegung und Akku-Teiler bleiben wie 0.1.14.


## Version 0.1.16: OLED-Layout

Große Wattzahl ab Zeile 18 unterhalb des gelben 16-Pixel-Bereichs. Balken mit Hold darunter, MAX-Watt und SWR in einer gemeinsamen Fußzeile. Skalenende in der kleinen Kopfzeile. Akkuseite ohne Teiler-Hinweis; die elektrische Beschaltung mit 10k/10k bleibt Voraussetzung.


## Version 0.1.17: Watt / SWR groß

OLED-Kompakt zeigt ein kleines W und gemeinsame Zahlenzeile, z. B. W88 / 1.5. Leistung gerundet auf ganze Watt, SWR mit einer Nachkommastelle, fehlende Werte --. Wattziffern 3-fach, SWR 2-fach vergrößert; unterhalb des gelben Bereichs. Balken mit Hold und genaue MAX-Leistung mit einer Nachkommastelle bleiben erhalten. Messwerte und Web-Ausgabe werden nicht gerundet verändert.


## Version 0.1.18: Bereinigung und Frequenztest

Aktive Shell-Kommandos: hamlab info, status, meter, power, swr. Keine ATT-/DDS-/Sweep-Kommandos oder zugehörigen HTTP-Routen. State liefert keine erfundene Messfrequenz/ATT. Encoder und GP13 schalten OLED-Seiten, GP19/20/21 wählen sie direkt. Historische Abschnitte zu DDS/ATT/Sweep gelten für diese Version nicht. Sweep-RAM und Thread entfernt.

### Kurzer 50-Ohm-Frequenztest

IC-7300 CW, USB-Keying RTS, 19200 Baud, Tuner aus. Bereits erprobte 50-Ohm-Dummyload und Scope-Abgriff verwenden. Scope manuell so einstellen, dass auch der größte Pegel nicht abgeschnitten wird. Die Skop-/Tastkopf-/Teiler-Genauigkeit muss auch bei 50 MHz passen; DC-ohmische 50 Ohm allein garantieren dort keine HF-Anpassung.

Zunächst `python3 tools/powermeter_frequency_test.py` für reine Verbindungskontrolle. Danach:

```bash
python3 tools/powermeter_frequency_test.py --run --level 20 --settle 1 --pause 5 --frequencies 1850000,3600000,7031670,14100000,28100000,50100000 --output freq_50ohm_20pct.csv
```

Das Script nutzt den vorhandenen Kalibrierer pro Frequenz und stellt dessen ursprüngliche Icom-Frequenz/Leistung nach jedem Punkt wieder her. Jede Sendephase hat die bestehende 8-s-Softwaregrenze. Bei Fehler stoppt die Reihe; schon gespeicherte Punkte bleiben. RF-Prozent sind keine Watt. Referenz weiterhin Vpp²/400 an 50 Ohm für Sinus. `forward_7mhz_w` und `forward_error_pct` vergleichen die aktuelle 7-MHz-Kurve mit der Referenz je Frequenz; leere Werte außerhalb der Kennlinie. Aussage zuerst nur zum Vorlauf-Frequenzgang bei einer Leistung. Ein zweiter Durchlauf mit anderer Leistungsstufe und separate Rücklaufmessungen sind für Linearität und SWR über das Band erforderlich. Keine Kennlinie wird automatisch geändert.

Hostprüfung: vollständige main.c-Syntax mit Zephyr-Stubs, Scope-Parser-Selbsttest und gemockter Mehrfrequenzablauf einschließlich CSV-/Kurvenvergleich. Kein echter Zephyr-Build oder RF-Test hier.


## Version 0.1.19: Meter-Shell und richtige Lastreferenz

`hamlab meter` und `status` liefern den neuesten laufend erfassten Messwert, ohne zusätzliche I2C-Messung. Sperrwartezeit 250 ms, bei Belegung -EBUSY. Gemeinsamer Shell-Antwortpuffer statisch und separat gesperrt, damit er weder USB- noch Telnet-Stack belastet.

Beide Messwerkzeuge unterstützen `--load-ohms 25` oder `--load-ohms 50` (Standard). Die tatsächliche Last ausdrücklich wählen. CSV `reference_w` ist Vorlaufleistung; `load_w` ist in der Last umgesetzte Leistung, `reverse_reference_w` die ideale Rücklaufleistung aus ohmischer Last und 50-Ohm-System. Bei 25 Ohm gilt Vorlauf=Vpp²·9/1600, Rücklauf=Vpp²/1600. Aussagen setzen HF-ohmische Last und Messung am Lastanschluss voraus. Die frühere Frequenz-CSV war tatsächlich mit 25 Ohm erfasst, obwohl der Name 50 Ohm nennt; siehe docs/frequenztest-0.1.19.md. Original-CSV unverändert dokumentiert.


## Version 0.1.20: Diagnose bei Kalibrierabbruch

Pico-Messungen erhalten bis zu drei Leseversuche bei temporären Fehlern. Fehlermeldungen enthalten HTTP-Status, measurement_error und Kanalstatus. Zwischen Versuchen 200 ms, vorhandene TX-Deadline bleibt maßgeblich. Keine Fehlerpunkte in CSV. Das Firmware-Messverhalten ist unverändert; die Ursache des Abbruchs ist ohne Fehlercode noch offen. Ein alter Teillauf bleibt erhalten; Wiederholung mit neuem Dateinamen starten.


## Version 0.1.21: kleiner Vorlaufbereich

Vorläufige 7.03167-MHz-Vorlaufkurve ab 0.0556641 V / 1.2544 W. 1–4 % aus 10-V/div-Reihe vom 5.10.2026, 5–20 % aus vollständiger 20-V/div-Reihe desselben Tages. Höhere Punkte aus bisheriger Kalibrierung. Originaldateien unter docs/calibration. Wiederholte 5 %: 38.8 Vpp / 3.7636 W gegenüber 40 Vpp / 4 W, ADC 0.2413125 gegenüber 0.2404375 V. Scope-Referenzunterschied rund 6 %, daher vorläufig. Keine Extrapolation unter den kleinsten Punkt, Rücklauf und SWR-Untergrenze bleiben unverändert. OLED unter 9.95 W mit einer Nachkommastelle; ab dort gerundete ganze Watt, um die gemeinsame SWR-Zeile einzuhalten.


## Version 0.1.22: automatische Frequenz-/Leistungsreihe

`bash tools/powermeter_series.sh` prüft nur Verbindungen. `--run` startet je Frequenz alle Leistungsstufen. Defaults: 50 Ohm, 5/10/15/20 %, 1.85/3.6/7.1/14.1/28.1/50.1 MHz, RTS, 19200 Baud, settle 1 s, pause 5 s. Encoder/OLED/Kennlinien unverändert. Für dieses Werkzeug kein erneutes Flashen nötig.

Tuner aus, tatsächliche Last und Scope-Skalierung vor jedem Durchgang manuell wählen. --tag ist nur ein Dateinamen-Hinweis, stellt das Scope nicht um! Python-Messprogramm sichert die bestehende TX-Zeitgrenze und RX/Wiederherstellung. Skript beendet die Reihe beim ersten Fehler; vorherige CSVs bleiben, ein neuer Lauf bekommt ein neues Verzeichnis. Pro Frequenz eine CSV. Vorhandenes --output-dir wird abgelehnt.

Beispiele:

```bash
# Kleine Stufen, 50 Ohm, Scope zuvor 20 V/div einstellen:
bash tools/powermeter_series.sh --run --load-ohms 50 --levels 5,10,15,20 --tag low_20Vdiv
# Hohe Stufen, 50 Ohm, Scope zuvor 50 V/div einstellen:
bash tools/powermeter_series.sh --run --load-ohms 50 --levels 20,30,40,50,60,70,80,90,100 --tag high_50Vdiv
# Rücklauf: Last tatsächlich auf 25 Ohm umschalten, zunächst kleine Stufen:
bash tools/powermeter_series.sh --run --load-ohms 25 --levels 5,10,15,20 --tag low_20Vdiv
# Unterbereich, Scope zuvor passend auf 10 V/div einstellen:
bash tools/powermeter_series.sh --run --load-ohms 50 --levels 1,2,3,4,5 --tag small_10Vdiv
```

Die hohen 25-Ohm-Stufen folgen mit demselben Werkzeug nach Prüfung der Lastbelastbarkeit und passenden Scope-Skalierung. Auswahl einzelner Bänder über --frequencies, z. B. 3600000,7100000. --port/--pico/--scope-command werden an das Pythonprogramm übergeben. Keine automatische Kalibrieränderung und kein DDS-Sweep im Pico.


## Version 0.1.23: automatische Scope-Einstellungen

Nur die PC-Messwerkzeuge wurden erweitert; erneutes Flashen ist nicht erforderlich.
`--auto-scope` aktiviert `sds tdiv Sekunden` und `sds vdiv Kanal Volt`.
Beide Befehle laufen vor jedem Punkt im Empfangsbetrieb. CLI-Rückmeldung wird
auf den angeforderten Wert geprüft; keine unabhängige SCPI-Rücklesung vorhanden.
Baudrate 19200, RTS, TX-Zeitbegrenzung und RX/Wiederherstellung bleiben erhalten.
Ohne --run keine Geräteänderungen; --plan greift überhaupt nicht auf Geräte zu.

Standard-Zeitbasis ungefähr eine Periode pro Division, gerundet auf 1/2/5-Stufen.
Standard-V/div: bis 5 % 10 V/div, bis 20 % 20 V/div, darüber 50 V/div.
Dies ist eine konfigurierbare Stufentabelle, keine Rückkopplungs-Autoskalierung.
Tastkopf-Faktor, Eingangskopplung, Trigger und vertikalen Offset vorher prüfen;
das Signal muss mittig und vollständig sichtbar sein. Diese Einstellungen
werden nicht verändert. Scope-Zeitbasis/V/div verbleiben am letzten Messpunkt.
Ein gemeldetes Vpp über 7 Divisionen bricht ab; bereits gekappte Signale kann
man damit nicht sicher erkennen. Kleinere V/div gezielt über die Tabelle wählen.

CSV ergänzt scope_tdiv_s, scope_vdiv_v, timebase_factor, scope_vpp_divisions
und rms_vpp_ratio = RMS * 2 * sqrt(2) / Vpp. Letzteres liegt beim idealen Sinus
bei 1 und ist ein Vergleichswert, keine automatische Korrektur der Referenz.
Referenz bleibt aus Vpp berechnet; auffällige Daten vor Kennlinienübernahme prüfen.
Bei manueller Skalierung bleiben Scope-Einstellfelder leer.

Zuerst Plan ohne Gerätezugriff ansehen:

```bash
bash tools/powermeter_series.sh --auto-scope --plan \
  --load-ohms 50 --frequencies 7100000,50100000 --levels 5,20 \
  --timebase-factors 0.5,1,2 --tag scope_check
```

Danach derselbe kleine Diagnoselauf mit tatsächlich angeschlossener 50-Ohm-Last:

```bash
bash tools/powermeter_series.sh --auto-scope --run \
  --load-ohms 50 --frequencies 7100000,50100000 --levels 5,20 \
  --timebase-factors 0.5,1,2 --tag scope_check
```

Jeder Punkt wird mit drei Zeitbasen in getrennten Sendepulsen erfasst, jeweils
mit Pause. Bei 7.1 MHz: 50/100/200 ns/div; bei 50.1 MHz: 10/20/50 ns/div.
Damit zuerst den Zeitbasiseinfluss vergleichen, noch keine neue Kalibrierkurve.
Für eine normale Reihe --timebase-factors weglassen (Standard 1):

```bash
bash tools/powermeter_series.sh --auto-scope --run --load-ohms 50 \
  --levels 1,2,3,4,5,10,15,20,30,40,50,60,70,80,90,100 --tag auto_scope
# Nach manueller Lastumschaltung zunächst kleine 25-Ohm-Stufen:
bash tools/powermeter_series.sh --auto-scope --run --load-ohms 25 \
  --levels 5,10,15,20 --tag auto_scope
```

Alternative Skalierung: --scope-vdiv-map '5:5,20:20,100:50'.
Andere Scope-Adresse: --scope-control 'sds --ip HOST' und
--scope-command 'sds --ip HOST status' gemeinsam angeben.
Tests: Python/Bash-Syntax, Referenz-Selbsttest und simulierte sechs Messungen mit
Scope-Befehlen ausschließlich in RX, CSV-Einstellwerten und Rig-Wiederherstellung.
Keine Hardware- oder Zephyr-Buildprüfung in der Auslieferungsumgebung.


## Version 0.1.24: neue Rücklaufkennlinien

Neue umgedrehte-Koppler-Reihen bei 7.1 und 50.1 MHz integriert.
`reverse_v` gegen `reference_w`, keine Verwendung des nullwertigen
`reverse_reference_w`. Drei Zeitbasen gemittelt, obere Plateaus gepoolt.
Vorlaufkennlinie unverändert. Details und Grenzen: docs/ruecklauf-0.1.24.md.

```text
hamlab calibration
hamlab calibration 7100000
hamlab calibration 50100000
```

Standard 7.1 MHz, Auswahl RAM-only. Bei 50.1 MHz ist nur der Rücklauf
neu kalibriert; SWR wird wegen fehlender passender Vorlaufkurve gesperrt.
Unterhalb der Rücklaufstützstellen numerisches SWR weiterhin nicht möglich.
Eine neue Firmware muss hierfür gebaut und geflasht werden.


## Version 0.1.25: deutliche SWR-Warnanzeige

Voll-/Kompaktweb: ungültiges SWR als Text direkt im Balken plus lesbare Erklärung.
Rot schraffiert bei Rücklauf >= Vorlauf, Rücklauf über Messgrenze oder ADC-Fehler.
Gelbbraun bei zu kleinem Rücklauf, fehlendem Vorlauf, fehlender Frequenzkalibrierung
oder Verbindungsabbruch. Kein alter SWR-Holdmarker bei ungültiger aktueller Messung.
Gültige SWR-Werte ab 3 erhalten ebenfalls einen deutlichen Warntext.
OLED: Kompakt-Fußzeile ersetzt MAX durch SWR-Grund, Vollansicht zeigt denselben Grund.
Offene Last wird nicht sicher erkannt; keine erfundene Zahl und kein falscher SWR-1-Wert.
Kennlinien unverändert.

## Version 0.1.26: SWR-Status hervorheben

Ungültige Messungen heißen im Web „SWR NICHT BESTIMMBAR“. Gültiges SWR über 3 wird direkt im Balken als „SWR > 3“ hervorgehoben. OLED-Kompaktansicht zeigt „SWR UNBESTIMMT“ bzw. „SWR > 3 !“ im Statusfeld. Ungültige Messungen werden nicht als gesichertes SWR > 3 ausgegeben. Kennlinien unverändert.

## Version 0.1.27: ruhige normale SWR-Anzeige

Unterhalb der Rücklauf-Kalibriergrenze und ohne ausreichenden Vorlauf bleibt SWR -- ohne große Balkenwarnung. Der neutrale Balken zeigt keinen gültigen Wert. Rücklauf unter Messgrenze bleibt als dezenter Text sichtbar. OLED-Kompaktansicht behält MAX-Fußzeile bei, Vollansicht zeigt SWR --. Hohe gültige Werte und kritische Messfehler bleiben deutlich markiert. Keine neue Extrapolation oder SWR-1-Annahme.

## Version 0.1.28: geschätztes SWR bei kleinem Rücklauf

Nur zur SWR-Anzeige wird unterhalb der ersten Rücklaufstützstelle eine lineare Leistungsschätzung ab dem angenommenen Nullpunkt genutzt: Pr = Pmin * Vrev / Vmin. Keine gemessene Kennlinie und keine Offsetkorrektur. Web kennzeichnet den Wert mit ≈, OLED mit ~ und JSON mit quality estimated_below_calibrated_floor. Das streng kalibrierte reverse_w bleibt in diesem Bereich null. Vorlauf muss weiterhin im Messbereich liegen, Frequenzprüfung unverändert. Ohne ausreichenden Vorlauf SWR --. Gemessene Kennlinien unverändert. Geschätzte SWR-Werte können auch in Hold und letzter Messung enthalten sein.

## Version 0.1.29: angenommene Anzeige ~1 statt berechneter Schätzung

Lineare Nullpunkt-Fortführung entfernt: am Detektor war bei rund 0,42 W kein Unterschied zum Ruhewert erkennbar. Bei gültigem Vorlauf und Rücklauf unter erster Stützstelle zeigt Web/OLED ~1 als Annahme, keine numerische SWR-Messung. API bleibt valid false, value null und quality reverse_below_calibrated_floor. Keine neuen SWR-Hold-Werte oder gespeicherten numerischen SWR-Werte aus dieser Annahme. Ohne HF weiter --. Gemessene Kennlinien unverändert. ~1 belegt weder SWR 1 noch eine bestimmte obere SWR-Grenze.

## Version 0.1.30: blaue SWR-Marke für ~1

Web zeigt den farbigen SWR-Balken auch bei angenommener Anzeige ~1. Blaue Marke am Anfang und blauer Text kennzeichnen die Annahme. Gemessene Werte bleiben weiß, Max-Hold gelb. Ohne HF bleibt der Balken neutral ohne Marke. API, Berechnung und OLED unverändert.
