# Firmware 0.1.34 – Kennlinienprofile

Bis zu acht benannte Kennliniensätze im Flash; Auswahl einzeln für Vorlauf, Rücklauf 7/50 MHz und Stromkoppler. Gewählte Kurven und Namen werden gemeinsam gespeichert und nach Neustart geladen. Beim Umschalten werden Hold und letzte Messung zurückgesetzt. Import eines benannten Profils speichert ohne Aktivierung.

Gespeicherter Satz aus 0.1.33 bleibt unverändert als `legacy` verfügbar. `builtin` ermöglicht die Rückkehr zu den Standardstützstellen. Aktive Profile sind gegen Überschreiben gesperrt. WLAN und Flash-Partitionen bleiben bestehen; USB-Massenspeicher folgt separat.

[Bedienung und Import](kennlinien-profile.md). 18 Offline-Tests bestanden, tatsächliche C-Bausteine mit simuliertem Settings-Backend und strengen GCC-Warnungen getestet. Shell-Handler zusätzlich auf Syntax und printf-Argumente geprüft. Kein Zephyr-Build oder Hardwaretest in dieser Umgebung. Paket enthält Quellen, keine vorgebaute Firmware.
