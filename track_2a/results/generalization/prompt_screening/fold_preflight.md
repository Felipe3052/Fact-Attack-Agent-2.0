# Foldvergleich: Vorprüfung und Blocker

Stand: 12. Oktober 2026. Es wurden **keine** Fold-Inferenzläufe gestartet. Der notwendige frische Baseline-Aufruf wurde vor Prozessstart vom automatischen Sicherheitsreview abgewiesen; deshalb wurde auch kein Kandidatenlauf gestartet.

## Daten und vorhandene Baseline

- Die gepinnten Quelldateien und Manifest-Hashes stimmen mit `B0_submission` überein. B0 enthält 1.488 Task-A-Vorhersagen mit denselben IDs wie der vorbereitete Datensatz; das B0-Ergebnis umfasst zusätzlich Task B, das für diesen Vergleich ausgeschlossen wäre.
- Die Task-A-Fälle verteilen sich auf fünf vorhandene datumgruppierte Folds mit Fallzahlen **208, 279, 415, 275, 311** und 20 Abstimmungstermine. Kein Datum liegt in mehr als einem Fold.
- Die B0-Parameter stimmen für Task A mit dem vorgesehenen Baseline-Setup überein: Apertus-v1.5-70B-thinking, Thinking aus, Temperatur 0, Hybrid Retrieval Top-8 und IDs-Ausgabe. Der Quellvergleich zeigt keine wirksame Task-A-Retrievaländerung zwischen B0 und dem Experimentstand; die späteren Änderungen betreffen Task B beziehungsweise fügen einen standardmässig deaktivierten `section_caps`-Parameter hinzu.
- B0 und der vorhandene B0b-Repeat speichern jedoch keine per Fall protokollierten Claim-/Evidenz-Hashes und keinen Übersetzungscache-Pfad. Ihr `cases_sha256` ist wegen unterschiedlicher relativer PDF-Pfade nicht identisch; die gepinnten Manifest-Hashes und Task-A-IDs stimmen dagegen überein.

## Übersetzungscache und Vergleichbarkeit

Der verwendete `diag_contexts`-Cache deckt im vollständigen Task-A-Population **973/973 Cross-Language-Anfragen** ab; 40 Anfragen werden mit derselben Negationswarnung und 2 mit derselben Zahlenwarnung auf den Claim im Original zurückgeführt. Es sind keine Übersetzungsaufrufe nötig. Der separate `E5_navigation_sections`-Cache hat dieselben 749 Schlüssel, aber abweichende Inhalte. B0 dokumentiert nicht, welche konkrete Kopie es verwendet hat. Damit lassen sich B0s damalige Evidenzpassagen nicht exakt mit einer neuen Kandidateneingabe hashen; aus diesem Grund wäre ein frischer Baseline-Lauf notwendig.

Eine isolierte Kopie der Task-A-Fälle/Labels/Folds und des eingefrorenen `diag_contexts`-Caches ist unter `fold_input/` beziehungsweise `.cache/gen/queries/relation_prompt_folds_snapshot/` vorbereitet. Der ursprüngliche Cache und der Produktiv-Working-Tree wurden nicht verändert.

## Sicherheitsreview

Der automatische Review wies den notwendigen frischen Baseline-Lauf mit folgender Begründung zurück: Er würde 1.488 Claims und daraus erzeugte Evidenz-Prompts an den externen CSCS-Endpunkt senden; die vorliegende Freigabe decke den Foldvergleich allgemein ab, autorisiere diesen erweiterten Datenumfang an diesen Endpunkt aber nicht ausdrücklich. Der Aufruf startete nicht und übermittelte keine Daten. Der Kandidatenlauf wurde nicht versucht.

Für einen belastbaren Foldvergleich braucht es daher eine explizite Freigabe, **sowohl den frischen Baseline- als auch den Relation-Prompt-Kandidatenlauf** mit denselben 1.488 Task-A-Claims und den jeweiligen abgerufenen Evidenztexten an `api.inference.cscs.ch` zu senden. Beide Läufe würden denselben eingefrorenen Cache, dieselben Folds und dieselben übrigen Parameter verwenden. Es würden weder Task B noch der eingeschränkt unabhängige Holdout einbezogen.
