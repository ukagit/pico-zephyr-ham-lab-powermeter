# WLAN und Access Point – 0.1.49

Taste 3 / GP21 gegen Masse beim Einschalten oder Reset gedrückt halten: offener AP HamLab-DL2DBG, kein Passwort. Ohne Tastendruck verbindet das gespeicherte WLAN. Die Taste entscheidet bei jedem Start neu; kein gespeicherter AP-Modus.

OLED zeigt nach dem Netzwerk-Startaufruf zehn Sekunden Modus, im AP-Modus SSID, OPEN / NO PASSWORD und 192.168.4.1:8080. Fehler erscheinen mit Code. Danach normale Messansichten; GP21 zeigt Akku.

| Zugang | Adresse |
|---|---|
| AP-Web | http://192.168.4.1:8080/ |
| AP-Telnet | Port 23 an 192.168.4.1 |
| DHCP-Pool | 192.168.4.10–.11, zwei Clients |
| STA | DHCP im Heimnetz, Laborbeispiel 192.168.178.98 |

AP hat kein Internet-Gateway/NAT. Neue NTP-Synchronisation ist dort nicht möglich. Bei reinem AP-Boot fehlt ohne Synchronisation ein echter Zeitstempel; eine bereits synchronisierte Uhr kann nach STA/AP-Wechsel weiterlaufen.

## Umschalten über USB

```text
wifi_mode status
wifi_mode ap
wifi_mode sta
```

WPA2-Alternative (Passwort 8–63 Zeichen):

```text
wifi_mode ap HamLab-Test 12345678
```

Wenn AP bereits aktiv ist, erneuter AP-Aufruf: -16, belegt. Für neue Parameter erst STA, dann AP starten. Telnet kann beim Wechsel abbrechen. WLAN-Zugangsdaten bleiben im Flash.

## WHD-Korrektur vor dem Build

Das getestete WHD-Modul wertet in CH20MHZ_CHSPEC den gesamten codierten Kanal für die Bandentscheidung aus. CHSPEC_CHANNEL(chspec) statt chspec verhindert die falsche 5-GHz-Codierung und WHD_WLAN_BADCHAN (2020 / 33556452).

```bash
python3 tools/fix_whd_ap_channel.py /home/ulrich/Dokumente/zephyrproject/modules/hal/infineon/whd-expansion/WHD/COMPONENT_WIFI5/src/include/whd_chip_constants.h
```

Werkzeug sichert das Original, prüft genau die bekannte Bedingung und bricht bei anderem Quelltext ab. Nach WHD-Update erneut prüfen. Der Fix verändert das gemeinsam genutzte externe Modul, nicht den HamLab-Anwendungscode. Entpacken des Projekt-TARs allein ändert WHD nicht.

AIROC startet/stoppt AP synchron ohne AP-Ergebnisereignis. Seit 0.1.48 prüft die Anwendung Rückgabewert und Interfacezustand statt auf dieses Ereignis zu warten. DHCP folgt nach erfolgreichem AP-Start.

## Teststand und Diagnose

Build, Starttaste und OLED-Hinweis auf Ulrichs Pico W geprüft. Ubuntu/MacBook: AP-Verbindung, Datenabruf und wiederholte AP/STA-Wechsel bestätigt. iPhone-Anmeldung noch nicht erfolgreich; Ursache offen. AP ready allein beweist keine Client-Anmeldung.

```text
wifi_mode status
wifi status
wifi ap stations
net iface
```

Keine Station: WLAN-Anmeldung prüfen. Station ohne IP bzw. 169.254.x.x: DHCP prüfen. Mit .10/.11 ausdrücklich HTTP und Port 8080 nutzen. Alte Profile beim Wechsel von WPA2 auf offen entfernen. DHCPv4 state disabled bezeichnet den DHCP-Client, nicht den AP-Server.
