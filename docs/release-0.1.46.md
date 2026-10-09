# Firmware 0.1.46 – AP-Test mit Rückweg

Die lokale AIROC-Treiberversion wurde von Ulrich geprüft: ap_enable/ap_disable und WHD AP-Start sind vorhanden. Dieses Update ergänzt eine kontrollierte Umschaltung; Pico-Hardwaretest noch ausstehend.

## Erster Test

Über **USB-Shell** testen, da Telnet beim Trennen der WLAN-Verbindung abbricht. Boot bleibt STA mit gespeicherten Zugangsdaten. Danach:

```text
wifi_mode ap
```

Standard: SSID **HamLab-DL2DBG**, WPA2-Passwort **HamLab-DL2DBG**, Kanal 6 / 2,4 GHz. Eigene Werte alternativ:

```text
wifi_mode ap HamLab-DL2DBG MeinTestPasswort
```

Passwort 8–63 Zeichen, SSID 1–32 Bytes. Im einfachen Aufruf keine Leerzeichen. Passwort wird nicht gespeichert oder vom Status ausgegeben. Das Standardpasswort dient diesem Test.

Mit PC/Telefon verbinden, Meldung „Kein Internet“ akzeptieren und die Verbindung behalten. DHCP vergibt 192.168.4.10 oder .11, Netzmaske 255.255.255.0. Pico: **192.168.4.1**. Dann:

- http://192.168.4.1:8080/
- http://192.168.4.1:8080/compact-a2
- http://192.168.4.1:8080/api/v1/state
- Telnet 192.168.4.1 Port 23

Ohne DHCP zur Diagnose manuell PC 192.168.4.10/24, kein Gateway. Nicht gleichzeitig dieselbe Adresse einem anderen Client geben.

## Status und Rückweg

```text
wifi_mode status
network_status
wifi ap status
wifi ap stations
```

Über USB zurück:

```text
wifi_mode sta
```

AP und DHCP-Server werden abgeschaltet, die AP-Adresse entfernt, DHCP-Client und gespeicherte WLAN-Verbindung wieder gestartet. Modus bleibt RAM-only; Neustart/erneutes Einschalten startet STA. Bei Fehlern wird die automatische Wiederverbindung pausiert; `wifi_mode sta` oder Neustart ist der Rückweg. Auch AP-Anforderung und AP-Ereignisfehler werden gemeldet, nicht als funktionierendes AP ausgegeben.

Für diesen Test `wifi_mode` benutzen; direktes `wifi ap enable/disable` umgeht die Koordination mit unserem Wiederverbindungsthread. Falls beim Umschalten ein Fehler erscheint, vollständige USB-Ausgabe einschließlich `network_status` schicken.

## Umsetzung und Grenzen

STA-Wiederverbindung und Moduswechsel sind serialisiert. AP-Statusereignisse werden bis 15 s abgewartet. DHCP-Server hat zwei Adressen. Keine Mess-/Display-Sperre beim Netzwerkwechsel. WPA2, feste IPv4, DHCP-Client/Server getrennt. Gespeicherte WLAN-Zugangsdaten und Kennlinien werden nicht überschrieben. Zephyr-Modushinweis STA_AP kompiliert beide Betriebsarten; verwendet wird immer nur eine.

AP stellt kein Internet-Routing oder NAT bereit; NTP kann ohne Internet nicht neu synchronisieren. OLED/Messung/Web funktionieren weiter. Es gibt keinen zusätzlichen WLAN-Hotspot für gleichzeitigen Fritz!Box-Betrieb.

Offline-Tests prüfen den Netzwerkcode gegen API-Mocks, Fehlerpfade, AP/DHCP-Start und STA-Rückkehr. Kein Zephyr-SDK im Testsystem: tatsächlicher Build, RAM-Verbrauch, Treiber/Funkbetrieb und DHCP müssen beim Nutzer geprüft werden.
