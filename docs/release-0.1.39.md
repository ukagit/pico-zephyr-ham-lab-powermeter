# 0.1.39 – eigener A2-Leistungsbalken

Die Web-Vollansicht ergänzt einen eigenständigen A2-Leistungsbereich mit Zahl, blauem Balken, Autoscale, gelber 3-s-Max-Hold-Marke und Hold-Text. mW bei einer maximalen Kennlinienleistung unter 1 W, sonst W. Beispiel: 211,6 mW werden auf einer 250-mW-Skala dargestellt. Profil, Referenz und Frequenz stehen darunter.

A2-Hold wird in der Firmware unabhängig von Vorlauf/SWR geführt. Höhere Werte übernehmen die Marke sofort; nach drei Sekunden wird sie auf den aktuellen gültigen Wert gesetzt, auch nach unten. Bei ungültiger A2-Messung läuft Hold nach drei Sekunden aus. Profilwechsel/Import und der bestehende Reset setzen alle Holds zurück. Der zusätzliche A2-Resetknopf benutzt diesen gemeinsamen Reset.

JSON current_coupler ergänzt peak_w (W oder null). A2-Bereich wird aus dem eigenen Kanalstatus aktualisiert, auch bei einem Fehler des Richtkopplers. Hauptanzeige, OLED und Kompaktansicht bleiben unverändert. Die zwei Kennlinienplots bleiben erhalten. Kein erneuter Profilimport nötig.

21 Offline-Tests bestehen, einschließlich C99-kompilierter Web-Inhalte und JavaScript-Prüfung. Der Diagrammtest prüft jetzt zusätzlich A2-Balken in mW/W, Autoscale, Hold-Marke sowie ungültige/offline Zustände. Zephyr-Build und Hardwaretest stehen noch aus.
