# 0.1.37 – Web-Startfehler korrigiert

Die Vollansicht blieb in 0.1.36 bei Verbinden stehen. Ursache reproduziert: JavaScript `??` unmittelbar vor einem einfachen Anführungszeichen erzeugt die C-Trigraph-Sequenz `??'`. Beim Einbetten und Übersetzen mit C99 wird daraus ein anderes Zeichen, das JavaScript syntaktisch ungültig macht. Die Prüfung der HTML-Quelle allein hatte das nicht erkannt.

Der HTML-Generator schützt Fragezeichen jetzt mit dem standardisierten C-Escape. Kompilierte Web-Inhalte stimmen dadurch bytegenau mit den HTML-Quellen überein. Neuer Regressionstest übersetzt die tatsächlich eingebetteten Voll-/Kompaktseiten mit GCC C99 und strengen Warnungen, vergleicht die Bytes und prüft die enthaltenen Scripts mit Node.

20 Offline-Tests bestanden. Kein Zephyr-Build hier durchgeführt. Kennlinien, Profile, gespeicherte Auswahl und Hardwarezuordnung bleiben bestehen. Paket enthält Quellen. Wie üblich bauen und flashen, danach Browser mit Strg+F5 neu laden.
