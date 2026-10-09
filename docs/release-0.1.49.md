# Firmware 0.1.49: Taste 3 wählt Netzwerk beim Start

Taste 3 (Batterietaste, GP21 gegen Masse) beim Einschalten oder Reset gedrückt halten. Die Firmware konfiguriert den internen Pull-up und prüft zweimal im Abstand von 30 ms, bevor eine WLAN-Verbindung angefordert wird.

- Beide Abfragen gedrückt: offener Access Point HamLab-DL2DBG, kein Passwort. Web http://192.168.4.1:8080/, Telnet Port 23, DHCP .10–.11. Kein Internet-Gateway.
- Nicht gedrückt oder GPIO-Lesefehler: gespeichertes WLAN als Station.

Nach dem Netzwerk-Startaufruf zeigt das OLED zehn Sekunden lang den gewählten Modus. Im AP-Modus stehen SSID, OPEN / NO PASSWORD und die Webadresse auf dem Display. Fehler werden mit START ERROR und Fehlercode angezeigt; bei AP-Fehler wird nicht still ins gespeicherte WLAN gewechselt. Danach erscheinen die üblichen Messansichten. Taste 3 behält im laufenden Betrieb ihre Batteriefunktion.

Der Modus wird nicht im Flash gespeichert: bei jedem Start entscheidet die Taste neu. `wifi_mode ap` startet nun ebenfalls den offenen Standard-AP. `wifi_mode ap SSID PASSWORD` erlaubt weiterhin WPA2 mit 8–63 Zeichen. `wifi_mode sta` kehrt zum gespeicherten WLAN zurück.

Der externe WHD-Kanalfix aus release-0.1.48.md bleibt erforderlich; das Projekt-TAR verändert das externe Modul nicht. Eine Aktualisierung des Moduls kann den Fix überschreiben.

23 Offline-Tests bestanden, einschließlich offenen AP-Parametern, Boot-Auswahl AP/STA, Fehlerfällen und Rückkehr zu STA. Build, GP21-Start und OLED-Hinweis wurden von Ulrich auf dem Pico W geprüft. Verbindungen und Datenabruf mit Ubuntu/MacBook sowie wiederholte AP/STA-Wechsel bestätigt. iPhone-Anmeldung bleibt offen.
