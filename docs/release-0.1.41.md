# Firmware 0.1.41

Die Vollansicht zeigt neben A0 und A1 jetzt auch A2−A3: Rohspannung in Volt, ADC-Rohwert, gewählten PGA-Bereich und Übersteuerungsstatus. Die JSON-API enthält diese Werte bereits. Rohspannung und Rohwert bleiben unabhängig von der Leistungskennlinie sichtbar. Bei Verbindungsverlust wird die Anzeige geleert.

Die vorhandenen Kennlinien und Profile werden beibehalten. Lokale Prüfungen: eingebettete Webseiten und JavaScript sowie vorhandene Offline-Tests. Ein Zephyr-Build und ein Hardwaretest müssen auf dem lokalen System erfolgen.
