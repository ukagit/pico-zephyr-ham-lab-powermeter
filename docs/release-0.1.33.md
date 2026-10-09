# Firmware 0.1.33 – JSON-Kennlinien, Schritt 1

Vier bestehende Kennlinien können als vollständiger JSON-Satz über die USB-/Telnet-Shell geprüft, gespeichert, aktiviert und exportiert werden. Nach Neustart wird ein gültiger Flash-Satz geladen. Eingebaute Standardkurven entsprechen 0.1.32. WLAN-Settings und Flash-Partitionen bleiben unverändert. USB-Massenspeicher/FAT ist noch nicht implementiert.

Neu: `hamlab curves`, `tools/powermeter_curves.py`, JSON-Vorlage und [Importanleitung](kennlinien-json.md). JSON-Prüfung, NVS-Speicherung mit CRC und kurze Übertragungsblöcke. Kein Heap-Puffer; zusätzliche statische Daten ungefähr 7,3 KiB.

16 Offline-Tests bestanden, einschließlich tatsächlichem C-Parser/Speicherbaustein mit simuliertem Settings-Backend und bestehenden Messwerkzeugtests. C-Bausteine mit GCC `-Wall -Wextra -Werror` geprüft. Zephyr-Build und Hardwaretests für diesen Stand stehen noch aus; Paket enthält Quellen, keine vorgebaute UF2/HEX.
