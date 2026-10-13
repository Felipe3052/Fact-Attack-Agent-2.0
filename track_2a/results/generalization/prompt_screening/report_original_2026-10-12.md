# Task-A-Relation-Prompt: gepaarter Screening-Test

Stand: 12. Oktober 2026. Es wurde genau ein Kandidatenlauf mit den 180 eingefrorenen Task-A-Fällen ausgeführt. Kein Fold-Test und keine weitere Modellvariante wurden gestartet.

## Vergleichbarkeit und Auswahl

Die Stichprobe wurde vor Kandidatenausgaben fixiert: 120 repräsentative Fälle (je 8 pro Goldlabel und datumgruppiertem Fold) sowie 60 separat ausgewertete Diagnosefälle aus vorab dokumentierten B0-Fehlerstrata. Die Diagnosefälle sind bewusst angereichert und keine Populationsstichprobe. `input/selection.csv` enthält Fall-IDs, Fold, Datum, Label und Stratum; `input/manifest.json` dokumentiert Seed und Hashes.

Baseline und Kandidat verarbeiteten dieselben 180 IDs. Für alle Fälle stimmen die protokollierten Claim- und Evidenz-Hashes, Passagenzahlen, Datensatzhashes und Übersetzungscache-Pfade überein. Im effektiven Laufparametervergleich unterscheidet sich nur `A_RELATION_PROMPT` (aus/an). Der Zusatz wurde ausschliesslich an Task A angehängt. Task B, Retrieval, Übersetzung, Labels, Evaluationslogik und Submission-Schnittstelle blieben unverändert.

Die bestehende CSCS-Übersetzungscache-Prüfung fand 115/115 nötige Cross-Language-Einträge und 5 bereits gespeicherte, abgewiesene Übersetzungen, bei denen beide Läufe gleichermassen auf den Claim im Original zurückfielen. Der gespeicherte Cache-Snapshot ist in `input/translation_cache_audit.json` festgehalten.

## Macro-F1, Accuracy und Confusion Matrices

Matrixreihenfolge jeweils **Entailment, Contradiction, Neutral**; Zeilen = Goldlabel, Spalten = Modellvorhersage.

### 120 repräsentative Fälle

| Lauf | Macro-F1 | Accuracy | Fehler | Confusion Matrix |
|---|---:|---:|---:|---|
| Baseline | 0,9411 | 0,9417 | 7 | `[[35, 3, 2], [0, 40, 0], [1, 1, 38]]` |
| Kandidat | **0,9499** | **0,9500** | **6** | `[[36, 0, 4], [0, 40, 0], [0, 2, 38]]` |

Δ Macro-F1: **+0,0088** (rund +0,9 Prozentpunkte). Von den Baselinefehlern wurden 2 korrigiert, 1 zuvor korrekter Fall wurde zum Fehler; 5 Fälle blieben in beiden Läufen falsch, 112 in beiden korrekt.

### 60 gezielte Diagnosefälle

| Lauf | Macro-F1 | Accuracy | Fehler | Confusion Matrix |
|---|---:|---:|---:|---|
| Baseline | 0,0958 | 0,1000 | 54 | `[[3, 15, 18], [0, 1, 3], [8, 10, 2]]` |
| Kandidat | **0,1655** | **0,1833** | **49** | `[[6, 10, 20], [0, 1, 3], [9, 7, 4]]` |

Hier wurden 6 Fehler korrigiert und 1 zuvor korrekter Fall verschlechtert; 48 blieben in beiden Läufen falsch. Dieser deutliche Unterschied gilt nur für das gezielt zusammengestellte Diagnoseset und darf nicht als erwarteter allgemeiner Leistungssprung ausgelegt werden.

### Alle 180 Fälle, nur ergänzend deskriptiv

| Lauf | Macro-F1 | Accuracy | Fehler | Confusion Matrix |
|---|---:|---:|---:|---|
| Baseline | 0,6625 | 0,6611 | 61 | `[[38, 18, 20], [0, 41, 3], [9, 11, 40]]` |
| Kandidat | 0,7003 | 0,6944 | 55 | `[[42, 10, 24], [0, 41, 3], [9, 9, 42]]` |

Panelübergreifend korrigierte der Kandidat 8 Fehler und verursachte 2 neue; 53 blieben in beiden Läufen falsch und 117 in beiden korrekt. Wegen der 60 angereicherten Diagnosefälle ist die gepoolte Differenz **keine** unverzerrte Schätzung auf den Gesamtbestand.

## Fehlergruppen und Verschiebungen

Im Diagnosepanel fielen Entailment→Contradiction-Fehler von 15 auf 10. Drei dieser fünf Fälle wurden korrekt als Entailment bewertet; zwei wechselten jedoch nur zu Entailment→Neutral. Neutral→Contradiction sank von 10 auf 7; alle drei Fälle wurden zu Neutral korrigiert. Gleichzeitig stiegen Entailment→Neutral von 18 auf 20 und Neutral→Entailment von 8 auf 9. Contradiction→Neutral blieb bei 3.

Im repräsentativen Panel verschwanden die drei Entailment→Contradiction-Verwechslungen aus der Matrix, aber nur eine wurde korrigiert; zwei wechselten zu Entailment→Neutral. Diese Neutral-Verwechslung stieg insgesamt von 2 auf 4. Neutral→Entailment sank von 1 auf 0, Neutral→Contradiction stieg von 1 auf 2. Der kleine Nettozuwachs verbirgt somit einen teils echten Gewinn und teils eine Verschiebung zu Neutral.

Nach Claim-Typ im repräsentativen Panel sank die Fehlerzahl bei `committee` von 3 auf 2; `summary` blieb bei 1 (ein alter Fehler korrigiert, ein neuer verursacht). `consequence` blieb bei 2, `legal_text` bei 1; `federal_council` und `other` hatten in dieser Stichprobe keine Fehler in beiden Läufen. Die Fallzahlen sind zu klein, um daraus stabile Untergruppenunterschiede abzuleiten.

Zusätzlich stieg im offiziellen Evidenz-/Zitat-Score `found` von 92/136 (0,6765) auf 97/136 (0,7132). Retrieval-Eingaben waren identisch; diese Differenz betrifft die Modellausgabe und ist ergänzend zu lesen.

## Tokens und Laufzeit

| Messwert, 180 Fälle | Baseline | Kandidat |
|---|---:|---:|
| Input-Tokens gesamt (Ø/Fall) | 704.746 (3.915,3) | 733.906 (4.077,3) |
| Output-Tokens gesamt (Ø/Fall) | 11.654 (64,7) | 12.435 (69,1) |
| aufsummierte Inferenzzeit | 395,8 s (2,199 s/Fall) | 368,1 s (2,045 s/Fall) |
| CLI-Laufzeit | 331,7 s | 95,7 s |

Der Zusatz erhöhte die Eingabe um durchschnittlich 162 Tokens/Fall. Die gemessene Inferenzzeit war im Kandidatenlauf rund 7 % niedriger; bei diesem einen Lauf ist das kein belastbarer Laufzeitvorteil. Die CLI-Laufzeiten sind nicht fair direkt vergleichbar: Beim Baseline-Lauf war der lokale PDF-/Retrieval-Cache kalt, beim Kandidatenlauf bereits warm (Nicht-LLM-Anteil 1.107 ms/Fall gegenüber 9,8 ms/Fall). Beide Läufe lieferten 180/180 Antworten; in den Evaluations-`issues` stehen keine Fehler.

## Einschätzung und nächster Schritt

Der repräsentative Screen zeigt nur **einen Fehler weniger** und +0,9 Macro-F1-Punkte. Das ist ein schwaches, nicht belastbares Signal. Das Diagnoseset stützt die Hypothese gezielter: insbesondere Neutral→Contradiction wurde reduziert; zugleich nahmen Entailment→Neutral-Fehler zu. Der Prompt scheint also einige vorschnelle Contradiction-Ausgaben zu korrigieren, verschiebt aber einen Teil davon lediglich zu Neutral. Ein Modellwechsel oder eine Änderung der produktiven Konfiguration ist dadurch nicht gerechtfertigt.

Ein einzelner kontrollierter Lauf über die bestehenden datumgruppierten Folds wäre als nächster Erkenntnisschritt vertretbar, weil der gezielte Fehlergewinn im Diagnoseset sichtbar ist. Vorher sollte nichts geändert werden; dieser Fold-Test wurde **nicht** gestartet und wartet auf Freigabe. Den eingeschränkt unabhängigen Holdout nicht für wiederholte Variantenwahl verwenden. Wegen der starken Task-B-Baseline muss Task B bei einer späteren Release-Entscheidung separat berücksichtigt werden.

Die relevanten Tests bestanden vor dem Kandidatenlauf: 28/28 (`test_apertus_client`, `test_pipeline`, `test_submission_config`, `test_retriever`). Der Baseline-Log enthält optionale PyMuPDF-`fontTools`-Warnungen; beide Läufe verwendeten dieselben protokollierten Evidenztexte. Alle Implementierungs- und Screeningartefakte liegen im isolierten temporären Worktree unter `<temp>\fact-attack-prompt-screening-20261012`; die produktive Konfiguration und der ursprüngliche Working Tree wurden nicht geändert.
