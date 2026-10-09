# A2-Abgleich auf A0 – Firmware 0.1.32

Referenz: `docs/calibration/abgleich-a2-auf-a0-7mhz.csv`, 6.10.2026, 7.1 MHz, 50-Ω-Dummyload ohne Scope, je drei gepaarte Messungen. Tatsächliche Zuordnung: `current_mean_v` zu `master_mean_w`, nicht die ICOM-Prozentstellung. Vorlauf-/Rücklaufkennlinien und SWR-Berechnung bleiben unverändert.

15 gültige Stufen von 2–100 %. Bei 1 % liegt A0 mit 0.04621 V unter seiner bestehenden Untergrenze 0.0556641 V: keine gültige Masterleistung und daher keine neue A2-Stützstelle. RF-OFF dokumentiert nur den Ruhewert, keine Wattstützstelle.

Neue A2-Kurve: 0.0196875–0.5600625 V, 1.4943–83.3462 W. Stückweise lineare Interpolation; keine Extrapolation.

90/100 % liefern A2 0.5584375/0.5586042 V bei Streuungen 0.0014345/0.0013472 V. Die Spannungen sind nicht sinnvoll unterscheidbar. Beide oberen Punkte werden gleichgewichtet zu 0.5585208 V / 83.3462 W gepoolt. Bis zur höchsten dort tatsächlich beobachteten Einzelspannung bleibt dieser Wattwert konstant, API-Qualität `aligned_to_a0_upper_plateau`. Der untere Rand bis zur niedrigsten bei 2 % beobachteten Spannung bleibt entsprechend auf dem unteren Endwert. Damit führt die gemessene Randstreuung nicht unmittelbar zu wechselnd gültigen/ungültigen Anzeigen. Außerhalb der beobachteten Grenzen bleibt der Wert ungültig.

Der Abgleich passt mittlere Anzeigen im gemessenen Aufbau aneinander an. Er belegt keine höhere absolute Wattgenauigkeit. Einzelanzeigen können aufgrund von Rauschen und zeitlich aufeinanderfolgender ADS1115-Abtastung schwanken. Das obere Plateau trennt 90/100 % nicht zuverlässig.

API: `current_coupler.master="A0"`; `quality="aligned_to_a0_50ohm_only"` bzw. Plateau. `power_50ohm_w` bleibt ein separater Zusatzwert. Kompaktanzeige und SWR verwenden den Richtkoppler. Web-Vollansicht kennzeichnet den A0-Abgleich. Firmware 0.1.32 neu bauen und flashen.
