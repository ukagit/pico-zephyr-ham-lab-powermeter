# Rücklaufkalibrierung 0.1.24

Quelle: Koppler umgedreht, 50-Ohm-Last. ADC-Zuordnung unverändert. reverse_v wird gegen reference_w kalibriert; reverse_reference_w=0 wird nicht verwendet.

Je Leistungsstufe arithmetisches Mittel der drei Zeitbasismessungen. Gleiche Leistungswerte und fallende Leistungsmittel werden durch benachbarte gewichtete Mittel zusammengefasst (monotone Poolung); keine erzwungene Steigung auf einem Plateau. Keine Nullstützstelle oder Extrapolation.

## 7100000 Hz

| ADC A1−A3 V | Referenz W |
|---:|---:|
| 0.0530182 | 1.3456 |
| 0.0829349 | 1.7424 |
| 0.1362760 | 2.4336 |
| 0.2390937 | 3.9469 |
| 0.5619896 | 11.6512 |
| 0.6655833 | 14.5419 |
| 0.7942084 | 18.4331 |
| 1.0455833 | 29.5233 |
| 1.2900625 | 39.6900 |
| 1.5458750 | 53.7800 |
| 1.7054167 | 61.8867 |
| 1.8639167 | 72.8200 |
| 1.9976250 | 82.8100 |
| 2.0872083 | 88.9900 |

## 50100000 Hz

| ADC A1−A3 V | Referenz W |
|---:|---:|
| 0.0249870 | 1.1096 |
| 0.0444479 | 1.3768 |
| 0.0852552 | 1.9791 |
| 0.1664193 | 3.1451 |
| 0.4418229 | 9.2427 |
| 0.5395625 | 11.9259 |
| 0.6560625 | 15.4736 |
| 0.9020000 | 25.6733 |
| 1.1729375 | 38.4400 |
| 1.4391458 | 52.8067 |
| 1.5773958 | 62.4100 |
| 1.6880000 | 68.8967 |
| 1.6989167 | 70.0100 |
| 1.7051250 | 70.5600 |

## Verwendung und Grenzen

Default: Rücklaufkurve 7.1 MHz, Vorlauf weiterhin unveränderte vorläufige 7.03167-MHz-Kurve. Die Kombination wird als vorläufig behandelt. 50.1 MHz ist nur für Rücklauf kalibriert; Auswahl sperrt numerisches SWR in JSON, OLED, Hold und letztem Messwert. Vorlaufanzeige bleibt aus der alten Tabelle und wird in power.quality als forward_frequency_not_calibrated gekennzeichnet. Keine Behauptung einer absoluten Genauigkeit.

`hamlab calibration` zeigt Auswahl; `hamlab calibration 50100000` wählt 50.1 MHz, `hamlab calibration 7100000` zurück. Auswahl nur RAM, Neustart stellt 7.1 MHz ein; kein CAT-/DDS-Frequenzbefehl. Kein automatisches Erkennen der Sendefrequenz.

Unterhalb 1.3456 W (7.1 MHz) bzw. 1.1096 W (50.1 MHz) keine numerische Rücklaufleistung/SWR. Es wird weder null Watt noch SWR 1 erfunden. Bei 10 W Vorlauf kann damit SWR nahe 1 noch nicht quantitativ erfasst werden.

Plateaus: 7.1 MHz 90/100 % gemittelt; 50.1 MHz 80/90 % gepoolt, weil die gemittelte Referenz minimal fällt. Tabellen begrenzen auf die gemittelten Endpunkte. Einzelmessungen an den Endpunkten können deshalb außerhalb liegen. Weitere Frequenzen sind nicht ausgemessen.


## Prüfung

Host-C-Test aller Stützstellen und Zwischenwerte, unterer/oberer Grenzen, NaN/Inf, unveränderter Vorlauf-Endpunkte, Kurvenauswahl und ungültiger Auswahl. JSON und SWR-Sperre bei fehlender Vorlauf-Frequenzkalibrierung geprüft. C-Warnungen einschließlich Formatprüfung als Fehler behandelt für die geänderten JSON-/Shell-Funktionen. Kein Zephyr-Build oder Hardwaretest in dieser Umgebung.
