# 0.1.40 – Footer, Copyright und A2-Kompaktseite

Zeit-/NTP-Meldung und Navigation stehen am Ende der Vollansicht nach beiden Diagrammen. Neben der Firmwareversion erscheint © DL2DBG, auch in beiden Kompaktansichten.

Neue URL http://192.168.178.98:8080/compact-a2 (auch /compact-a2.html). Kleine Überschrift, A2-Leistung in mW/W, Autoscale-Balken, gelbe Hold-Marke und Hold-Text, Profil/Referenz/Frequenz, Links zur Vollansicht und A0-Kompaktseite. Messabfrage wie bisher alle etwa 200 ms. Doppelklick auf A2-Balken setzt über den bestehenden gemeinsamen Reset alle Holds zurück. Keine NTP-Meldung von A0 in A2-Kompaktansicht.

A0-Kompaktansicht bleibt /compact. Footer beider Seiten erlaubt den Wechsel. Profile, Kennlinien, Auswahl, OLED und Messlogik unverändert.

21 Offline-Tests bestanden. Der C99-Webtest prüft jetzt alle drei kompilierten Seiten bytegenau und auf gültiges JavaScript. Kein Zephyr-Build oder Hardware-/Browsertest hier durchgeführt. Nach Flash alle Seiten mit Strg+F5 neu laden.
