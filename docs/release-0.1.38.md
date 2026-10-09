# 0.1.38 – getrennte Kennliniendiagramme

Die Web-Vollansicht zeigt zwei Diagramme mit unabhängig skalierten Achsen:

- Richtkoppler: forward, reverse_7mhz und reverse_50mhz in Watt.
- A2-Messkopf: nur current, bei einer maximalen Kennlinienleistung unter 1 W in mW, sonst in W.

Die 1-MHz-1N4148-Kurve wird damit auf einer 250-mW-Achse dargestellt. Beim Wechsel auf den 7,1-MHz-Stromkoppler verwendet A2 automatisch Watt. Beide Diagramme zeigen Detektorspannung in V auf der X-Achse, Profilnamen, Frequenzen, Stützstellen und lineare Interpolation. Kurven lassen sich unabhängig ausblenden; Tooltip zeigt die Werte in der passenden Einheit. Keine Extrapolation über die Kurvenenden. Aktualisierung alle fünf Sekunden.

Kennlinienwerte, Profile, Auswahl, OLED, JSON-Einheiten (weiterhin W), Messung und Kompaktseite bleiben unverändert. Nur Web-Vollansicht und Versionsnummer geändert.

21 Offline-Tests bestanden, darunter C99-kompilierte Web-Inhalte mit bytegenauem Vergleich und JavaScript-Syntaxprüfung. Regressionstest prüft getrennte Achsen, 17 A2-Punkte, 250-mW-Skalierung, Wechsel mW/W und Ausblenden. Zephyr-Build und Hardware-/Browsertest stehen noch aus.

Nach Build/Flash Vollansicht unter http://192.168.178.98:8080/ öffnen, Strg+F5. Import der Kennlinien ist nicht erneut notwendig.
