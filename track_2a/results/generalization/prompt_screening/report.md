# Task-A-Relation-Prompt: gepaarter Screening-Test

Stand: 12. Oktober 2026. Es wurde genau ein Kandidatenlauf mit den 180 eingefrorenen Task-A-Fällen ausgeführt. Kein Fold-Test und keine weitere Modellvariante wurden gestartet.

> **Korrektur vom 12. Oktober 2026 (nach Nachrechnung aus den gespeicherten Vorhersagen).** Die Confusion Matrices
> der ursprünglichen Fassung standen in Label-Reihenfolge **Entailment, Neutral, Contradiction** (IDs 0, 1, 2), waren
> aber mit „Entailment, Contradiction, Neutral“ beschriftet. Dadurch waren Neutral- und Contradiction-Fehler in der
> Deutung vertauscht. Korrigiert sind die drei Matrix-Tabellen, der Abschnitt „Fehlergruppen und Verschiebungen“ und
> die Einschätzung. Unverändert und bestätigt sind Macro-F1, Accuracy, Fehlerzahlen, korrigierte/neue Fehler,
> Claim-Typ-Zahlen, Evidenz-Score, Tokens und Laufzeiten. Modellresultate wurden nicht verändert. Die ursprüngliche
> Fassung liegt unverändert in `report_original_2026-10-12.md`.

## Vergleichbarkeit und Auswahl

Die Stichprobe wurde vor Kandidatenausgaben fixiert: 120 repräsentative Fälle (je 8 pro Goldlabel und datumgruppiertem Fold) sowie 60 separat ausgewertete Diagnosefälle aus vorab dokumentierten B0-Fehlerstrata. Die Diagnosefälle sind bewusst angereichert und keine Populationsstichprobe. `input/selection.csv` enthält Fall-IDs, Fold, Datum, Label und Stratum; `input/manifest.json` dokumentiert Seed und Hashes.

Baseline und Kandidat verarbeiteten dieselben 180 IDs. Für alle Fälle stimmen die protokollierten Claim- und Evidenz-Hashes, Passagenzahlen, Datensatzhashes und Übersetzungscache-Pfade überein. Im effektiven Laufparametervergleich unterscheidet sich nur `A_RELATION_PROMPT` (aus/an). Der Zusatz wurde ausschliesslich an Task A angehängt. Task B, Retrieval, Übersetzung, Labels, Evaluationslogik und Submission-Schnittstelle blieben unverändert.

Die bestehende CSCS-Übersetzungscache-Prüfung fand 115/115 nötige Cross-Language-Einträge und 5 bereits gespeicherte, abgewiesene Übersetzungen, bei denen beide Läufe gleichermassen auf den Claim im Original zurückfielen. Der gespeicherte Cache-Snapshot ist in `input/translation_cache_audit.json` festgehalten.

## Macro-F1, Accuracy und Confusion Matrices

Matrixreihenfolge jeweils **Entailment, Contradiction, Neutral**; Zeilen = Goldlabel, Spalten = Modellvorhersage.

### 120 repräsentative Fälle

| Lauf | Macro-F1 | Accuracy | Fehler | Confusion Matrix |
|---|---:|---:|---:|---|
| Baseline | 0,9411 | 0,9417 | 7 | `[[35, 2, 3], [1, 38, 1], [0, 0, 40]]` |
| Kandidat | **0,9499** | **0,9500** | **6** | `[[36, 4, 0], [0, 38, 2], [0, 0, 40]]` |

Δ Macro-F1: **+0,0088** (rund +0,9 Prozentpunkte). Von den Baselinefehlern wurden 2 korrigiert, 1 zuvor korrekter Fall wurde zum Fehler; 5 Fälle blieben in beiden Läufen falsch, 112 in beiden korrekt.

### 60 gezielte Diagnosefälle

| Lauf | Macro-F1 | Accuracy | Fehler | Confusion Matrix |
|---|---:|---:|---:|---|
| Baseline | 0,0958 | 0,1000 | 54 | `[[3, 18, 15], [8, 2, 10], [0, 3, 1]]` |
| Kandidat | **0,1655** | **0,1833** | **49** | `[[6, 20, 10], [9, 4, 7], [0, 3, 1]]` |

Hier wurden 6 Fehler korrigiert und 1 zuvor korrekter Fall verschlechtert; 48 blieben in beiden Läufen falsch. Dieser deutliche Unterschied gilt nur für das gezielt zusammengestellte Diagnoseset und darf nicht als erwarteter allgemeiner Leistungssprung ausgelegt werden.

### Alle 180 Fälle, nur ergänzend deskriptiv

| Lauf | Macro-F1 | Accuracy | Fehler | Confusion Matrix |
|---|---:|---:|---:|---|
| Baseline | 0,6625 | 0,6611 | 61 | `[[38, 20, 18], [9, 40, 11], [0, 3, 41]]` |
| Kandidat | 0,7003 | 0,6944 | 55 | `[[42, 24, 10], [9, 42, 9], [0, 3, 41]]` |

Panelübergreifend korrigierte der Kandidat 8 Fehler und verursachte 2 neue; 53 blieben in beiden Läufen falsch und 117 in beiden korrekt. Wegen der 60 angereicherten Diagnosefälle ist die gepoolte Differenz **keine** unverzerrte Schätzung auf den Gesamtbestand.

## Fehlergruppen und Verschiebungen

*(Korrigierte Fassung; Schreibweise Gold→Vorhersage.)*

Im Diagnosepanel fielen Entailment→Neutral-Fehler von 15 auf 10 und Contradiction→Neutral von 10 auf 7. Gleichzeitig stiegen Entailment→Contradiction von 18 auf 20 und Contradiction→Entailment von 8 auf 9; Neutral→Contradiction blieb bei 3. Fünf Fälle wechselten von Entailment→Neutral zu Entailment→Contradiction, blieben also falsch.

Im repräsentativen Panel verschwanden alle drei Entailment→Neutral-Fehler: einer wurde korrigiert, zwei wechselten zu **Entailment→Contradiction**, das dadurch von 2 auf 4 stieg. Contradiction→Entailment sank von 1 auf 0, Contradiction→Neutral stieg von 1 auf 2. Der kleine Nettozuwachs verbirgt somit einen teils echten Gewinn und teils eine **Verschiebung zu Contradiction**. Entailment→Contradiction ist in der Gesamtpopulation die grösste Fehlerklasse (34 von 85 Fehlern in B0).

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

Der repräsentative Screen zeigt nur **einen Fehler weniger** und +0,9 Macro-F1-Punkte. Das ist ein schwaches, nicht belastbares Signal. *(Korrigiert:)* Das Diagnoseset zeigt, dass der Prompt vor allem zu zurückhaltende Neutral-Antworten korrigiert (Entailment→Neutral, Contradiction→Neutral). Zugleich nahmen Entailment→Contradiction-Fehler zu; ein Teil der Neutral-Fehler wird lediglich zu Contradiction verschoben. Der Prompt macht das Modell also kontradiktionsfreudiger, nicht neutraler. Ein Modellwechsel oder eine Änderung der produktiven Konfiguration ist dadurch nicht gerechtfertigt.

*(Ursprüngliche Empfehlung, nach der Korrektur nicht mehr gestützt:)* Ein einzelner kontrollierter Lauf über die bestehenden datumgruppierten Folds wäre als nächster Erkenntnisschritt vertretbar, weil der gezielte Fehlergewinn im Diagnoseset sichtbar ist. Wegen der Zunahme von Entailment→Contradiction wird ein Fold-Test mit diesem Prompt nicht empfohlen. Vorher sollte nichts geändert werden; dieser Fold-Test wurde **nicht** gestartet und wartet auf Freigabe. Den eingeschränkt unabhängigen Holdout nicht für wiederholte Variantenwahl verwenden. Wegen der starken Task-B-Baseline muss Task B bei einer späteren Release-Entscheidung separat berücksichtigt werden.

Die relevanten Tests bestanden vor dem Kandidatenlauf: 28/28 (`test_apertus_client`, `test_pipeline`, `test_submission_config`, `test_retriever`). Der Baseline-Log enthält optionale PyMuPDF-`fontTools`-Warnungen; beide Läufe verwendeten dieselben protokollierten Evidenztexte. Alle Implementierungs- und Screeningartefakte liegen im isolierten temporären Worktree unter `<temp>\fact-attack-prompt-screening-20261012`; die produktive Konfiguration und der ursprüngliche Working Tree wurden nicht geändert.

## Nachtrag: abgebrochener Fold-Baseline-Lauf (12. Oktober 2026)

*(Korrigierte Fassung; nur Angaben aus den Protokollen im temporären Worktree `fact-attack-prompt-screening-20261012`,
Ordner `runs/relation_prompt_folds_baseline`.)*

Nach Abschluss dieses Berichts wurde im temporären Worktree ein Fold-Baseline-Lauf gestartet
(`run_decision.py --data …/fold_input --task A --name relation_prompt_folds_baseline`, 1.488 Task-A-Fälle,
`A_RELATION_PROMPT=false`).

| Angabe | Beleg | Status |
|---|---|---|
| Start | Dateizeitstempel von `relation_prompt_folds_baseline_driver.log` 14:54:15 und `run.json` 14:54:16 | belegt (Zeitstempel) |
| Fortschritt | `prompt_inputs.jsonl`: 1.287 Einträge mit eindeutigen Fall-IDs, letzter Schreibzeitpunkt 15:03:21 | belegt |
| Ende | `cli.log` und Treiber-Log leer, keine `predictions.jsonl`, kein Exit-Status in `run.json` | **ungeklärt**; die Prozesse wurden in der Skill-Screening-Sitzung auf Anweisung beendet, der genaue Zeitpunkt ist nicht protokolliert (frühestens nach dem letzten Journal-Eintrag um 15:03:21) |
| Begonnene / beantwortete Anfragen | Das Journal schreibt einen Eintrag unmittelbar vor jedem Inferenzaufruf | höchstens 1.287 Aufrufe begonnen; wie viele beantwortet wurden, ist **ungeklärt** |
| Freigabe | In der Skill-Screening-Sitzung war ein Fold-Test nicht freigegeben. Die spätere Fassung von `fold_preflight.md` im temporären Worktree (Zeitstempel 15:05) gibt eine ausdrückliche Freigabe in der dortigen Sitzung an. | aus den Protokollen **ungeklärt** |

Die Dateien des abgebrochenen Laufs liegen unverändert im temporären Worktree und werden nicht ausgewertet. Die hier
gesicherte `fold_preflight.md` entspricht dem Stand vor 15:05; die spätere Fassung wurde nicht übernommen.

*Korrekturvermerk (Pre-Push-Bereinigung, 12. Oktober 2026):* Die erste Fassung dieses Nachtrags nannte den Lauf
„nicht freigegeben“, den Stopp „um ca. 14:57 Uhr“ und „1.287 Anfragen an CSCS gesendet“. Der Stoppzeitpunkt widerspricht
dem letzten Journal-Eintrag (15:03:21); Freigabestatus und Zahl der beantworteten Anfragen sind nicht belegbar.

## Skill-Screening: `A_SKILL_PROMPT` gegen frische Baseline (12. Oktober 2026)

Freigegeben waren genau zwei Läufe auf denselben 180 eingefrorenen Fällen: eine frische Baseline-Wiederholung
(`runs/baseline_repeat`) und Variante B, Baseline plus kompakter Skill (`runs/skill`). Kein Fold-Test, keine Variante C.
Code: Branch `exp/task-a-prompt-screening`, Commit `c174a1e` (Schalter standardmässig aus; ausgeschaltet sind die Anfragen
byte-identisch zu `7c17c9c`; 147 Tests bestanden). Start: `launch_skill_screen.py`, Auswertung: `analyze_skill_screen.py`
→ `skill_screen_analysis.json`.

**Vergleichbarkeit.** Gleiche Eingabe-Hashes (Claim + Passagen) in allen vier Läufen: 180/180 (vorhandene Baseline,
frische Baseline, Skill, Relation-Prompt). Gleicher Übersetzungs-Cache (`diag_contexts`, 749 Einträge, vor/nach den
Läufen hash-identisch), gleiches Modell und gleiche Parameter; einziger Unterschied `A_SKILL_PROMPT`. 0 API-Fehler,
0 fehlgeschlagene Fälle. Matrizen: Zeilen = Gold, Spalten = Vorhersage, Reihenfolge **E, C, N**.

### 120 repräsentative Fälle

| Lauf | Macro-F1 | Accuracy | Fehler | Confusion Matrix (E, C, N) | Fehlerübergänge |
|---|---:|---:|---:|---|---|
| Baseline (vorhanden) | 0,9411 | 0,9417 | 7 | `[[35, 2, 3], [1, 38, 1], [0, 0, 40]]` | E→C 2, E→N 3, C→E 1, C→N 1 |
| Baseline (frisch) | 0,9415 | 0,9417 | 7 | `[[35, 2, 3], [0, 38, 2], [0, 0, 40]]` | E→C 2, E→N 3, C→N 2 |
| **Skill** | **0,9580** | **0,9583** | **5** | `[[36, 1, 3], [1, 39, 0], [0, 0, 40]]` | E→C 1, E→N 3, C→E 1 |
| Relation-Prompt (Referenz) | 0,9499 | 0,9500 | 6 | `[[36, 4, 0], [0, 38, 2], [0, 0, 40]]` | E→C 4, C→N 2 |

- Schwankung der Baseline: 1 von 120 Labels anders (C: E→N), Fehlerzahl gleich.
- Skill gegenüber frischer Baseline: 2 korrigiert (C: N→C, E: N→E), 0 neu falsch, 2 falsch → anders falsch
  (C: N→E, E: C→N). E→C sinkt von 2 auf 1, E→N bleibt bei 3. Nach Claim-Typ: committee 3 → 2, legal_text 1 → 0.

### 60 Diagnosefälle (Fehleranalyse, keine Leistungsschätzung)

| Lauf | Macro-F1 | Accuracy | Fehler | Confusion Matrix (E, C, N) | Fehlerübergänge |
|---|---:|---:|---:|---|---|
| Baseline (vorhanden) | 0,0958 | 0,1000 | 54 | `[[3, 18, 15], [8, 2, 10], [0, 3, 1]]` | E→C 18, E→N 15, C→E 8, C→N 10, N→C 3 |
| Baseline (frisch) | 0,0148 | 0,0167 | 59 | `[[0, 20, 16], [9, 1, 10], [0, 4, 0]]` | E→C 20, E→N 16, C→E 9, C→N 10, N→C 4 |
| Skill | 0,1285 | 0,1667 | 50 | `[[4, 25, 7], [8, 6, 6], [1, 3, 0]]` | **E→C 25**, E→N 7, C→E 8, C→N 6, N→C 3, N→E 1 |
| Relation-Prompt (Referenz) | 0,1655 | 0,1833 | 49 | `[[6, 20, 10], [9, 4, 7], [0, 3, 1]]` | E→C 20, E→N 10, C→E 9, C→N 7, N→C 3 |

- Schwankung der Baseline: 5 von 60 Labels anders, alle zum Schlechteren; diese schwierigen Fälle sind instabil.
- Skill gegenüber frischer Baseline: 10 korrigiert (davon 6 C: N→C, 3 E: C→E, 1 E: N→E), 1 neu falsch (C: C→N),
  10 falsch → anders falsch, davon **8 Entailment-Fälle von Neutral zu Contradiction**. E→N sinkt von 16 auf 7, E→C
  steigt von 20 auf 25.

### Evidenz, Tokens, Laufzeit (180 Fälle)

| Messwert | Baseline (vorhanden) | Baseline (frisch) | Skill |
|---|---:|---:|---:|
| Evidenz `found` (offiziell) | 92/136 (0,676) | 89/136 (0,654) | 96/136 (0,706) |
| Ø Input-Tokens / Fall | 3.915,3 | 3.915,3 | 4.102,3 (+187, +4,8 %) |
| Ø Output-Tokens / Fall | 64,7 | 65,9 | 63,1 |
| Ø Inferenzzeit / Fall | 2,20 s | 2,02 s | 2,00 s |
| CLI-Laufzeit (Parse-Cache warm) | 331,7 s (kalt) | 94,0 s | 93,4 s |

### Einordnung

- **Repräsentativ:** 2 Fehler weniger als die frische Baseline (7 → 5), ohne neue Fehler und ohne zusätzliches
  E→C. Das liegt über der hier beobachteten Schwankung (1 Labelwechsel), beruht aber auf 2 von 120 Fällen und einem
  einzigen Wiederholungslauf.
- **Diagnose:** Der Skill korrigiert vor allem übersehene Widersprüche (C→N) und zu zurückhaltende Antworten, verschiebt
  aber 8 Entailment-Fälle von Neutral zu Contradiction. Dasselbe Muster zeigt der Relation-Prompt (5 Fälle), beim Skill
  stärker. E→C ist in der Gesamtpopulation die grösste Fehlerklasse (34 von 85 in B0).
- **Tokens:** +4,8 % Input pro Fall; unter der Bewertungsformel braucht es grob +0,005 Macro-F1 in der
  Gesamtpopulation, um das auszugleichen.
- **Entscheidung nach dem vereinbarten Kriterium:** Auf den repräsentativen Fällen gibt es einen kleinen, plausiblen
  Vorteil ohne zusätzliche E→C-Fehler. Die Diagnosefälle zeigen aber, dass der Mechanismus unsichere Entailment-Fälle
  zu Contradiction verschiebt; ob das in der Population netto gewinnt, lässt sich mit diesem Screening nicht klären.
  Das Ergebnis ist damit **unklar**; die produktive Baseline bleibt unverändert. Kein weiterer Lauf gestartet.

## Bereinigung vor Veröffentlichung (12. Oktober 2026)

Keine Modellresultate, Evaluationslogik oder produktive Konfiguration wurden geändert.

- **Nicht mehr im Repository:** `input/expected-labels.jsonl` (Gold-Labels mit Gold-Referenztexten), `input/cases.jsonl`
  (Claims, Abstimmungstitel, absolute lokale Booklet-Pfade) und `input/subsets/A/` (von `run_decision.py` erzeugte
  Kopie). `input/.gitignore` verhindert, dass wiederhergestellte Dateien erneut committet werden.
- **Wiederherstellung** (aus `track_2a`; nur der gepinnte öffentliche Datensatz wird benötigt):
  1. `python scripts/prepare_competition_cases.py --version v1.1 --scope all --download-booklets --output .cache/gen/data`
  2. `python results/generalization/prompt_screening/restore_inputs.py --data .cache/gen/data`

  Das Skript ordnet die Fälle nach `input/selection.csv` und prüft das Ergebnis gegen `input/restore_check.json`
  (Hashes mit LF-Zeilenenden; Booklet-Pfade als `booklets/<datei>` verglichen). Geprüft am 12. Oktober: beide Dateien
  byte-identisch zur vorher committeten Fassung; die erneute Auswertung mit `analyze_skill_screen.py` ergibt eine
  identische `skill_screen_analysis.json`. Alternativ erzeugt `prepare_screen.py` den ganzen Ordner `input/` neu
  (ebenfalls byte-identisch; die Hashes in `manifest.json` wurden unter Windows mit CRLF-Zeilenenden berechnet).
- **Entfernt:** `runs/relation_prompt_driver.log` (UTF-16-Kopie der Kennzahlen aus `groups.json`). In
  `runs/baseline/cli.log` wurden 49 identische PyMuPDF-`fontTools`-Warnungen entfernt; die `[timing]`-Zeile bleibt (auch
  in `run.json` → `cli_timing`).
- **Platzhalter statt lokaler Pfade:** `<temp>` in `report.md` und `report_original_2026-10-12.md` (im Originalbericht ist
  dies die einzige Änderung), `<skill-screening-worktree>` in `runs/baseline_repeat/cli.log` und `runs/skill/cli.log`.
  `launch_skill_screen.py` nimmt Datensatz, Übersetzungs-Cache und optional eine `.env`-Datei als Argumente.
- **Unverändert** (Laufprotokolle): `run.json` enthält weiterhin den Pfad des verwendeten Übersetzungs-Caches
  (`C:\GitHub\Apertus-Team-Fact-Attack-2026\…`, ohne Benutzernamen).
- **Weitere geprüfte Skripte** (nach der Wiederherstellung, aus `track_2a`): `PYTHONPATH=. QUERY_TRANSLATION_CACHE_DIR=<cache>
  python results/generalization/prompt_screening/audit_translations.py` reproduziert `input/translation_cache_audit.json`
  identisch (115/115 Cache-Treffer, 5 gespeicherte Ablehnungen).

## Kompakt-Screening: `A_COMPACT_PROMPT` gegen frische Baseline (12. Oktober 2026)

Freigegeben war genau ein Kandidatenlauf auf denselben 180 Fällen (`runs/compact`). Keine dritte Baseline, kein Fold-Test.
Code: Commit `5907dd3` (Schalter standardmässig aus; ausgeschaltet byte-identisch zu `7c17c9c`; 148 Tests bestanden).
Auswertung: `analyze_compact_screen.py` → `compact_screen_analysis.json` (nach `restore_inputs.py`).

Zusatz (454 Zeichen, nur Task A, nicht mit Relation-Prompt oder langem Skill kombiniert):

```
LABEL RULES: Compare actor, action, object and the decisive conditions or modality of the claim with the passages.
0 only if the passages support the claim, also when worded differently, summarised or in another language, but never
on information they do not state. 2 only if they state something incompatible with the same claim; missing support is
not a contradiction. 1 if they neither support nor refute it. Use only the passages, no outside facts.
```

**Vergleichbarkeit.** Vor der Inferenz ein Mock-Trockenlauf ohne Endpunkt/Schlüssel: Eingabe-Hashes 180/180 gleich wie
`baseline_repeat`. Im echten Lauf ebenfalls 180/180 gleich; Übersetzungs-Cache vor/nach unverändert; 0 API-Fehler,
0 fehlgeschlagene Fälle. Hit@5: offizieller Matcher, Nenner = Fälle mit Gold E/C im Panel (repräsentativ 80, Diagnose 56).

### 120 repräsentative Fälle

| Lauf | Macro-F1 | Accuracy | Fehler | Confusion Matrix (E, C, N) | Übergänge | Hit@5 (/80) |
|---|---:|---:|---:|---|---|---:|
| Baseline (vorhanden) | 0,9411 | 0,9417 | 7 | `[[35, 2, 3], [1, 38, 1], [0, 0, 40]]` | E→C 2, E→N 3, C→E 1, C→N 1 | 68 |
| Baseline (frisch) | 0,9415 | 0,9417 | 7 | `[[35, 2, 3], [0, 38, 2], [0, 0, 40]]` | E→C 2, E→N 3, C→N 2 | 66 |
| **Kompakt** | **0,9580** | **0,9583** | **5** | `[[36, 3, 1], [1, 39, 0], [0, 0, 40]]` | E→C 3, E→N 1, C→E 1 | **70** |
| Langer Skill (Referenz) | 0,9580 | 0,9583 | 5 | `[[36, 1, 3], [1, 39, 0], [0, 0, 40]]` | E→C 1, E→N 3, C→E 1 | 66 |

- Gegenüber frischer Baseline: 2 korrigiert (`row-1348` C: N→C, `row-296` E: N→E), 0 neu falsch, 2 falsch → anders falsch
  (`row-1318` C: N→E; `row-140` E: N→C). **E→C steigt um 1** (2 → 3) durch `row-140`, das in beiden Baseline-Läufen bereits
  als E→N falsch war. Hit@5 +4 / −0.
- Baseline-Schwankung: 1 Label, Hit@5 −2.

### 60 Diagnosefälle (Fehleranalyse, keine Leistungsschätzung)

| Lauf | Macro-F1 | Accuracy | Fehler | Confusion Matrix (E, C, N) | Übergänge | Hit@5 (/56) |
|---|---:|---:|---:|---|---|---:|
| Baseline (frisch) | 0,0148 | 0,0167 | 59 | `[[0, 20, 16], [9, 1, 10], [0, 4, 0]]` | E→C 20, E→N 16, C→E 9, C→N 10, N→C 4 | 23 |
| **Kompakt** | 0,2475 | 0,2667 | 44 | `[[9, 18, 9], [8, 5, 7], [1, 1, 2]]` | E→C 18, E→N 9, C→E 8, C→N 7, N→C 1, N→E 1 | 30 |
| Langer Skill (Referenz) | 0,1285 | 0,1667 | 50 | `[[4, 25, 7], [8, 6, 6], [1, 3, 0]]` | E→C 25, E→N 7, C→E 8, C→N 6, N→C 3, N→E 1 | 30 |

- Gegenüber frischer Baseline: 15 korrigiert (7 E: C→E, 4 C: N→C, 2 E: N→E, 2 N: C→N), 0 neu falsch, 7 falsch → anders
  falsch (davon 5 E: N→C). E→C sinkt von 20 auf 18; beim langen Skill stieg es auf 25. Baseline-Schwankung: 5 Labels.

### Tokens und Laufzeit (180 Fälle)

| Messwert | Baseline (frisch) | Kompakt | Langer Skill |
|---|---:|---:|---:|
| Ø Input-Tokens / Fall | 3.915,3 | 4.012,3 (+97, +2,5 %) | 4.102,3 (+187, +4,8 %) |
| Ø Output-Tokens / Fall | 65,9 | 66,8 | 63,1 |
| Ø Inferenzzeit / Fall | 2,02 s | 2,00 s | 2,00 s |
| Nicht-LLM-Zeit / Fall (CLI) | 8,8 ms | 9,0 ms | 8,5 ms |
| CLI-Wall-Clock | 94,0 s | 93,3 s | 93,4 s |

### Einordnung (keine Entscheidung über eine Vollevaluation)

Repräsentativ 2 Fehler weniger, 0 neu falsch und +4 Hit@5 ohne Verlust, bei +2,5 % Input-Tokens. Das liegt über der
beobachteten Baseline-Schwankung (1 Label), beruht aber auf wenigen Fällen und einer Wiederholung. Ein zusätzlicher
E→C-Fehler entsteht nur durch Verschiebung eines bereits falschen Falls. Im Diagnosepanel korrigiert der Kompakt-Prompt
mehr und verschiebt weniger zu Contradiction als der lange Skill. Ob das auf die Population übertragbar ist, klärt
dieses Screening nicht.

## Publikationsbereinigung E9 (12. Oktober 2026)

- `input/selection.csv` enthält die Spalten `gold` und `baseline_transition` (Gold→B0-Vorhersage) nicht mehr. Sie werden
  von keinem Skript gelesen: `restore_inputs.py` nutzt nur die Fall-IDs und ihre Reihenfolge, die Auswertungen nur
  `panel` und `claim_type`. Nach dem Entfernen ergeben `restore_inputs.py` sowie `analyze_skill_screen.py` und
  `analyze_compact_screen.py` inhaltlich identische Ergebnisdateien. `prepare_screen.py` erzeugt weiterhin die
  vollständige Fassung mit diesen Spalten aus dem gepinnten Datensatz.
- Weiterhin enthalten (Grundsatzentscheidung offen, gleiche Praxis wie die bereits veröffentlichten E1–E3-Berichte
  auf `main`): Fall-ID-Listen korrigierter/neu falscher Fälle in den Auswertungen und vier im Bericht genannte Fälle.
  Zusammen mit den Vorhersagen lässt sich daraus für diese Fälle das Gold-Label ableiten; Gold-Referenztexte sind nicht
  enthalten.
