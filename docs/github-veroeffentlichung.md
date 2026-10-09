# Projekt auf GitHub veröffentlichen

Ziel: eigenständiges Repository `ukagit/pico-zephyr-ham-lab-powermeter`. Das ursprüngliche HamLab-Repository bleibt unverändert. Dieses Dokument ist eine Veröffentlichungsvorbereitung, kein Nachweis eines bereits erfolgten Uploads.

## Vor dem ersten Push

- README, Hardwarebelegung und Messgrenzen gegen den Aufbau prüfen.
- Aktuelle Firmware 0.1.49: Akku GP28, zusätzlicher Stromkoppler A2 und A0-Master-Abgleich. Diese Dokumentationslieferung verändert die Firmware nicht.
- Quellcode, HTML, ausgewählte Mess-CSVs und Grafiken einschließen.
- Keine Builds, virtuelle Umgebung, WLAN-Passwörter oder privaten Messprotokolle hinzufügen.
- `.gitignore` erlaubt dokumentierte CSV-Dateien ausschließlich unter `docs/calibration/`.
- Die ursprünglichen Projekte bleiben als Herkunft verlinkt. Im gelieferten Ausgangsstand war keine eindeutige Projektlizenzdatei enthalten; vor Festlegung einer Lizenz die Rechte der ursprünglichen Quellen klären. Keine neue Lizenz stillschweigend hinzufügen.

## Lokaler Build und Prüfung

```bash
west build -b rpi_pico/rp2040/w -S cdc-acm-console . -d build -p always
./tools/flash_openocd.sh
python3 tools/icom7300_read.py --self-test
python3 tools/powermeter_calibrate.py --self-test
python3 tools/test_powermeter_align_current.py
```

Auf Hardware USB/Telnet, Web, fünf OLED-Ansichten, A0/A1/A2, Akku GP28, Hold und ~1/hohes SWR prüfen. Firmware 0.1.49 wurde von Ulrich im Betrieb bestätigt; in dieser Dokumentationslieferung wurde kein zusätzlicher Zephyr-Build durchgeführt. Einen erfolgreichen Build nur für den tatsächlich geprüften Stand angeben.

## Neues Repository – GitHub CLI auf Ulrichs PC

Im **Powermeter-Verzeichnis**, nicht im ursprünglichen HamLab:

```bash
pwd
git init -b main
git add .
git status --short
git diff --cached --stat
git commit -m "Document powermeter 0.1.49, calibration profiles and AP operation"
gh auth status
gh repo create ukagit/pico-zephyr-ham-lab-powermeter   --public --source=. --remote=origin --push   --description "HF-Leistungs- und SWR-Anzeige mit Pico W, Zephyr, ADS1115, OLED und Weboberfläche"
```

`--public` ist eine bewusste Veröffentlichung; für ein privates Repository `--private` verwenden. Der Create-Befehl gilt **nur, wenn das Zielrepository noch nicht existiert und kein origin gesetzt ist**. Bei bestehendem Repository zuerst prüfen:

```bash
git remote -v
gh repo view ukagit/pico-zephyr-ham-lab-powermeter
```

Ein bestehendes Remote nicht ungeprüft ersetzen und niemals Force-Push benutzen. Bei bestehendem origin zum richtigen Powermeter-Repository genügt nach Commit `git push -u origin main`; vorher eventuelle Remote-Historie berücksichtigen. Danach README-Grafiken und CSV-Dateien auf GitHub kontrollieren.

Das flache TAR enthält keine `.git`-Historie. Bestehendes lokales `.git` wird beim Entpacken nicht ersetzt. Bei bereits vorhandener Repository-Historie `git init`/Initial-Commit nicht erneut als Neuanlage interpretieren, sondern normal Änderungen committen.


## Netzwerkstand 9.10.2026

AP und Datenabruf mit Ubuntu/MacBook sowie wiederholte AP/STA-Wechsel wurden bestätigt. iPhone-Anmeldung bleibt offen. Externer WHD-Fix und Start über GP21: [Netzwerk-Anleitung](netzwerk-ap.md). 23 Offline-Tests mit `python3 -m unittest discover -s tools -p "test_*.py"`. Firmware bleibt 0.1.49.
