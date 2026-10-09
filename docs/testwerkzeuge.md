# Test- und Kalibrierwerkzeuge

Die aktiven Werkzeuge laufen auf dem Linux-PC; sie sind keine Pico-Shell-Kommandos. Sie übernehmen keine Kennlinien automatisch in die Firmware. CSV-Auswertung und Übernahme in `src/power_calibration.h` beziehungsweise `src/current_calibration.h` erfolgen getrennt und nachvollziehbar.

## Vorbereitung

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install pyserial
ls -l /dev/serial/by-id/*IC-7300*
```

ICOM-Port im Labor: `/dev/serial/by-id/usb-Silicon_Labs_CP2102_USB_to_UART_Bridge_Controller_IC-7300_03009698-if00-port0`. Auf anderen Rechnern `--port` setzen. Baud bleibt **19200**, CI-V-Adresse **0x94**. Andere CAT-Programme schließen.

`sds` ist ein **separat installiertes Scope-CLI**, nicht Bestandteil dieses Repositorys. Es muss im PATH erreichbar sein und das erwartete Statusformat liefern:

```bash
sds id
sds status
sds tdiv 0.0000001
sds vdiv 1 20
```

`tdiv`: Sekunden/div, hier 100 ns/div. `vdiv`: Kanal und Volt/div, hier CH1 20 V/div. Tastkopffaktor muss am Scope korrekt sein; der Parser skaliert nicht nochmals um ×10. Nie `tdiv 0` als automatische Einstellung verwenden.

## Werkzeugübersicht

| Werkzeug | Zweck |
|---|---|
| `icom7300_read.py` | Frequenz, Modus, Leistungsstellung und ICOM-Anzeigerohwerte lesen |
| `powermeter_probe_test.py` | A0-Spannungssweep und Tastkopfvergleich; historischer Stromkopplerversuch an A0, heute Richtkoppler |
| `powermeter_align_current.py` | A0-Masterwatt und A2-Spannung gepaart aufnehmen; kein Scope; siehe [Abgleich](abgleich-a2-auf-a0.md) |
| `powermeter_calibrate.py` | Einzelne Frequenz mit mehreren Leistungsstufen und optional Scope-Steuerung erfassen |
| `powermeter_series.sh` | Mehrere Frequenzen/Stufen in getrennte CSV-Dateien schreiben |
| `powermeter_frequency_test.py` | Kurzer Frequenzvergleich bei einer Leistungsstellung, inklusive Abweichung zur vorhandenen 7-MHz-Vorlaufkurve |
| `flash_openocd.sh` | Firmware über Debug Probe flashen |
| `embed_web.py` | HTML in `src/hamlab_web.h` einbetten |
| `plot_calibration.py` | Kennliniengrafik direkt aus aktivem Header reproduzieren; benötigt matplotlib |

## A2 automatisch auf A0 abgleichen

Firmware 0.1.31 oder neuer, beide Koppler angeschlossen, A3 Masse. 50-Ω-Dummyload ohne Scope, CW, Tuner aus. Am Pico `hamlab calibration 7100000` wählen. Das wählt die kompatible Rücklaufkurve, keine Senderfrequenz.

```bash
python3 tools/powermeter_align_current.py --plan
python3 tools/powermeter_align_current.py
python3 tools/powermeter_align_current.py --run --key-line rts --baud 19200 \
  --frequency 7100000 \
  --levels 1,2,3,4,5,10,15,20,30,40,50,60,70,80,90,100 \
  --samples 3 --settle 1 --pause 5 \
  --output abgleich_a2_auf_a0_7mhz.csv
```

Die ersten beiden Kommandos senden nicht: Plan ohne Gerätezugriff, danach Verbindungstest. Der dritte startet die Messreihe. Baud 19200, RTS, Pico-Adresse 192.168.178.98 sind fest vorgegeben beziehungsweise Standard. Nach dem Lauf werden RTS deaktiviert, RX angefordert und ursprüngliche ICOM-Frequenz und Leistungsstellung wiederhergestellt.

CSV: `master_mean_w` ist die A0-Wattreferenz, `current_mean_v` die A2-Spannung, `paired_samples` enthält alle Einzelpaare. `alignment_usable` ist nur True, wenn alle Masterwerte gültig sind. Ungültige kleine Stufen werden dokumentiert, ohne eine Wattzahl zu erfinden. Ruhewertzeile 0 % ist keine Wattstützstelle. Keine bestehenden CSVs überschreiben; bei Wiederholung neuen Namen wählen. [Ergebnis der eingebauten Reihe](abgleich-ergebnis-v0.1.32.md).

## ICOM nur auslesen

```bash
python3 tools/icom7300_read.py --baud 19200 --verbose
python3 tools/icom7300_read.py --watch 1
```

Kein PTT-/Frequenz-/Leistungs-Schreibbefehl. Echo der gesendeten CI-V-Frames wird nicht als Antwort gewertet. `po_raw`, `swr_raw`, `alc_raw`, `vd_raw`, `id_raw` sind **Indikatorwerte**, keine direkt kalibrierten W, V oder A. Serienport wird exklusiv geöffnet; RTS/DTR werden zunächst deaktiviert.

## Plan und Verbindungstest

```bash
python3 tools/powermeter_calibrate.py --plan --auto-scope   --frequency 7100000 --levels 1,5,20 --timebase-factors 0.5,1,2
python3 tools/powermeter_calibrate.py
```

`--plan`: kein Gerätezugriff. Ohne `--run`: ICOM/Pico/Scope-Verbindung prüfen, kein Senden oder Einstellungs-Schreibbefehl. Scope muss im Verbindungstest keine HF-Frequenz erkennen.

## Eine Messreihe

Nur an passend belastbarer Dummyload, IC-7300 in CW, Tuner aus, vorhandenes USB-CW-Keying **RTS** mit passender Break-in-Einstellung. Die Tools ändern diese Menüeinstellungen nicht.

```bash
python3 tools/powermeter_calibrate.py --run --key-line rts   --frequency 7100000 --load-ohms 50 --levels 1,2,3,4,5,10,20   --settle 1 --pause 5 --output cal_7mhz_low.csv
```

Ohne `--auto-scope` muss der Bediener V/div und Zeitbasis passend setzen. Niedrige und hohe Stufen bei Bedarf in getrennte Reihen aufteilen.

Automatische Scope-Einstellung:

```bash
python3 tools/powermeter_calibrate.py --run --auto-scope   --frequency 7100000 --load-ohms 50 --levels 1,5,10,20,50,100   --scope-vdiv-map '5:10,20:20,100:50' --timebase-factors 0.5,1,2   --settle 1 --pause 5 --output cal_7mhz_auto.csv
```

V/div-Tabelle bedeutet bis 5 % → 10 V/div, bis 20 % → 20 V/div, darüber bis 100 % → 50 V/div. Das ist eine feste Vorgabe nach Prozentstellung, **kein** signalabhängiges Scope-Autoscaling. Zeitbasis ungefähr `Faktor/Frequenz`, auf 1/2/5-Stufen gerundet. Einstellung im RX vor der Erfassung, CLI-Antwort wird geprüft. Scope bleibt anschließend bei der zuletzt gesetzten Skala; Trigger, Offset, Kopplung und Tastkopffaktor werden nicht automatisch gesetzt.

Erwartet wird ein gültiger Scope-Wert und Frequenz innerhalb 1 % der Sollfrequenz. Die Prüfung auf mehr als 7 vertikale Kästchen erkennt mögliche Überschreitung, kann aber schon abgeschnittene Signale nicht zuverlässig erkennen.

TX-Fenster standardmäßig höchstens 8 s (`--max-tx`, maximal 15 s). Endlichkeits-/Fehlerprüfung, bis zu drei Pico-Leseversuche innerhalb derselben Deadline, CSV nach jedem Punkt flushen. Bei Fehler/Ctrl+C wird RTS deaktiviert, RX angefordert und die ursprüngliche Frequenz/Leistungsstellung nach Möglichkeit wiederhergestellt. Das ist Software-Cleanup, keine unabhängige Hardware-Notabschaltung.

## Mehrere Frequenzen

```bash
bash tools/powermeter_series.sh --plan --auto-scope   --load-ohms 50 --frequencies 7100000,50100000   --levels 1,2,3,4,5,10,15,20,30,40,50,60,70,80,100   --timebase-factors 0.5,1,2 --tag reverse_full
```

Nach Prüfung dasselbe Kommando mit `--run` **anstelle von `--plan`** starten. Neue Ergebnisverzeichnisse, eine CSV je Frequenz. Vorhandenes Verzeichnis wird nicht überschrieben; beim ersten Messfehler stoppt die Reihe. `--load-ohms 25` nur für tatsächlich geschaltete 25-Ω-Last verwenden. Bei umgedrehtem Koppler mit 50 Ω bleibt die Lastoption 50; die spätere Auswertung verwendet dann `reverse_v`/`reference_w`.

Kurzer Frequenztest:

```bash
python3 tools/powermeter_frequency_test.py --run --level 20   --frequencies 1850000,3600000,7100000,14100000,28100000,50100000   --load-ohms 50 --output frequency_test.csv
```

Vergleicht Detektorspannung mit der vorhandenen 7-MHz-Kurve. Erzeugt **keine** neue Frequenzkalibrierung. Dieses ältere kurze Tool reicht Auto-Scope-Optionen nicht weiter; für vollständige Reihen `powermeter_series.sh` verwenden.

## CSV-Felder

- `rf_setting_pct`/`rf_power_raw`: ICOM-Stellgröße, nicht Referenzwatt.
- `scope_vpp_v`, `scope_rms_v`, `scope_frequency_hz`: Scope-Referenzdaten.
- `reference_w`, `load_w`, `reverse_reference_w`: unterschiedliche Größen, siehe [Kalibrierung](messung-und-kalibrierung.md).
- `forward_v`, `reverse_v`: ADC-seitige Detektorspannungen; Rohwerte und Bereiche zusätzlich enthalten.
- `scope_tdiv_s`, `scope_vdiv_v`, `timebase_factor`: Auto-Scope-Plan; ohne Auto-Scope gegebenenfalls leer.
- `scope_vpp_divisions`, `rms_vpp_ratio`: Plausibilitätsdaten.
- `timestamp_utc`: PC-Uhrzeit, nicht NTP-Zeit des Pico.

## Offline-Prüfungen

```bash
python3 tools/icom7300_read.py --self-test
python3 tools/powermeter_calibrate.py --self-test
bash -n tools/powermeter_series.sh
python3 tools/test_powermeter_probe_test.py
python3 tools/test_powermeter_align_current.py
python3 tools/plot_calibration.py
```

Diese Tests prüfen Parser, Einheiten, CI-V-Codierung, Referenzformeln beziehungsweise Grafikdaten; kein Ersatz für Build und Hardwareprüfung. Für Grafik: `python3 -m pip install matplotlib`.

## Historische HamLab-Werkzeuge

`calibrate_ad8307.py`, `characterize_ad8307.py`, `analyze_ad8307.py`, `calibrate_scope_hamlab*.py`, `sweep_fy6900.py`, `sweep_antenna.py`, `measure_filter.py`, `measure_swr.py` stammen aus dem ursprünglichen HamLab. Sie verwenden teilweise DDS/ATT-/AD8307-Annahmen und alte API-Felder. **Keine Anleitung für das aktuelle Powermeter und keine automatische Kalibrierung der 1N4148-Detektoren.**

## JSON-Kennlinien ab 0.1.33

`tools/powermeter_curves.py` validiert offline, überträgt über USB-/Telnet-Shell und exportiert aktive Kennlinien. Import ohne `--save` prüft ausschließlich; mit `--save` wird gespeichert und aktiviert. Keine Sendersteuerung. [Vollständige Anleitung](kennlinien-json.md).

Ab 0.1.34: Import mit `--profile NAME --save` speichert ohne Aktivierung; `list` und `select ROLE NAME` verwalten die Auswahl. [Profile](kennlinien-profile.md).
