# Firmware 0.1.48: AIROC-Access-Point

Der installierte Zephyr-AIROC-Treiber startet und stoppt den AP synchron: Erfolg wird durch Rückgabewert 0 und geänderte Interface-Dormanz angezeigt. Er sendet keine AP-Ergebnisereignisse. Die bisherige Firmware wartete trotzdem darauf und schaltete nach einem Timeout den AP wieder ab.

0.1.48 wertet den synchronen Rückgabewert aus und prüft anschließend maximal fünf Sekunden den Interface-Zustand. DHCP und AP-IP werden erst nach erfolgreichem Start eingerichtet. Fehler beim Start, DHCP oder Stoppen werden weiterhin gemeldet. Die Bandbreite wird ausdrücklich auf 20 MHz gesetzt.

## Externer WHD-Kanalfix erforderlich

Zusätzlich muss die bereits besprochene Änderung in COMPONENT_WIFI5/src/include/whd_chip_constants.h erhalten bleiben. Im Makro CH20MHZ_CHSPEC muss die Bandentscheidung die Kanalnummer verwenden:

```c
((CHSPEC_CHANNEL(chspec)<=CH_MAX_2G_CHANNEL) ? ...)
```

Die ursprüngliche Bedingung `(chspec)<=CH_MAX_2G_CHANNEL` wertet den gesamten codierten Kanal aus und kann Kanal 6 als 5-GHz-Kanal behandeln. Das ergibt WHD_WLAN_BADCHAN (2020). Diese externe Moduländerung wird nicht durch Entpacken dieses Projekt-TARs vorgenommen und kann beim Aktualisieren des WHD-Moduls verloren gehen. Das beigefügte tools/fix_whd_ap_channel.py prüft und korrigiert genau diese Stelle, mit Sicherung.

## Test über USB

```text
wifi_mode ap
wifi_mode status
```

SSID und Passwort jeweils HamLab-DL2DBG. Webseite http://192.168.4.1:8080/; Telnet-Port 23. Kein Internet im AP-Modus. Zurück mit `wifi_mode sta`. Nach Neustart gilt weiterhin STA mit gespeicherten Zugangsdaten.

23 Offline-Tests bestanden, darunter echter network.c mit einem synchronen Treibermodell ohne AP-Ereignisse, Interface-Timeout, Treiber-/DHCP-Fehler und Rückkehr zu STA. Kein Zephyr-Build oder Hardwaretest in dieser Umgebung; diese Prüfung erfolgt auf Ulrichs Pico W.
