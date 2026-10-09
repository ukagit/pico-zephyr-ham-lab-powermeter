# Firmware 0.1.35 – aktive Kennlinien im Web

Die Web-Vollansicht ergänzt ein SVG-Diagramm der vier aktuell gewählten Kennlinien mit Profilnamen und Frequenzen. X-Achse: ADC-Detektorspannung in V, Y-Achse: Leistung in W. Die Stützstellen werden als Punkte, die tatsächlich verwendete lineare Interpolation als Verbindungslinien angezeigt. Kein Fortsetzen außerhalb der Kurvenenden.

Kurven sind einzeln ein-/ausblendbar. Maus über einen Punkt zeigt seine V/W-Werte. Die Achsen passen sich den sichtbaren Kurven an. Diagrammaktualisierung alle fünf Sekunden, schnelle Live-Messwertabfrage unverändert. Bei Abruffehlern wird der zuletzt geladene Satz mit einem sichtbaren Hinweis beibehalten. Während eines Imports ist der Kurvenabruf gesperrt.

GET `/api/v1/curves` liefert die vier aktiven Kurven zusammen mit den vier ausgewählten Profilnamen in einem konsistenten Snapshot. Keine Profiländerung über Web in diesem Stand. Kompaktseite unverändert. Vorhandene Profile und Auswahl bleiben erhalten.

18 bisherige Offline-Tests bestanden, JavaScript-Syntax geprüft; Diagrammlogik mit 60 Punkten, vier Kurven, Ausblendung und endlichen Koordinaten geprüft. Zephyr-Build und Browser-/Hardwaretest stehen noch aus. HTTP-JSON-Puffer um 512 Bytes erweitert, um die Profilnamen mit dem maximalen Kurvensatz auszugeben.

Nach Update Vollansicht unter http://192.168.178.98:8080/ öffnen und gegebenenfalls mit Strg+F5 neu laden.
