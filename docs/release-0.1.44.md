# Firmware 0.1.44 – A2 Overflow

A2-Voltmeter in Vollansicht und A2-Kompaktseite: Bei ADC-Übersteuerung oder ab 3,2 V am ADC erscheint ein voll ausgefüllter roter Balken, OVERFLOW statt Zahlenwert und ein deutlicher Text. Nach Rückkehr in den Messbereich wird die normale Anzeige wiederhergestellt. Bei Verbindungsverlust werden Werte und Warnung geleert. JSON/Shell-Kanal A2 enthält `voltage_overflow`.

Hardwareangabe: ca. 7 MΩ Eingangswiderstand und 100 kΩ Serien-Schutzwiderstand mit Eingangsschutzdioden. Kein Spannungsteiler, weiterhin 1:1. Keine pauschale Korrektur des Eingangs-/Serienwiderstands: Eingangswiderstand des ADS1115 hängt unter anderem vom PGA-Bereich ab.

3,2 V ist eine vorsorgliche Warnschwelle nahe 3,3 V Versorgung, keine Messung der Schutzdioden-Leitgrenze. Nach Begrenzung ist die tatsächliche Spannung vor dem Schutzwiderstand nicht bestimmbar. Ein niedrigerer externer Clamp-Pegel wäre auf diesem Weg nicht erkennbar. Der PGA-Endwert allein erkennt Überspannung nicht zuverlässig, da Autorange größere PGA-Bereiche wählen kann. Hardware-Schutzwirkung und zulässige Ströme werden durch diese Anzeige nicht bestätigt.

Offline-Prüfungen; Zephyr-Build und Hardwaretest beim Nutzer.
