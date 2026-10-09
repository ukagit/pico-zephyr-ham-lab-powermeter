# Firmware 0.1.47 – Buildkorrektur AP

Der lokale Zephyr-Build von 0.1.46 scheiterte in ap_request: net_mgmt ist ein Makro mit Token-Pasting und akzeptiert hier keinen bedingten Ausdruck als Request. AP_ENABLE und AP_DISABLE werden jetzt in zwei getrennten Aufrufen mit festen Request-Namen ausgeführt.

Der Offline-Netzwerktest bildet jetzt die Makro-Eigenschaft ab, statt net_mgmt als normale Funktion zu ersetzen. Die AP/STA-Bedienung aus release-0.1.46.md bleibt bestehen: über USB wifi_mode ap, SSID/Passwort HamLab-DL2DBG, http://192.168.4.1:8080/, Rückweg wifi_mode sta oder Neustart.

23 Offline-Prüfungen bestanden; tatsächlicher Zephyr-Build und Hardwaretest beim Nutzer.
