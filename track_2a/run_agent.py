"""
Interactive CLI Runner for Fact Attack Agent 2.0.
Executes the LangGraph workflow with full node visibility and Tracing.
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(env_path)

_track_dir = Path(__file__).resolve().parent
if str(_track_dir) not in sys.path:
    sys.path.insert(0, str(_track_dir))

from src.agent.workflow import build_fact_check_graph

def main():
    print("=" * 70, flush=True)
    print("[CH] FACT ATTACK AGENT 2.0 -- LIVE WORKFLOW RUNNER", flush=True)
    print("=" * 70, flush=True)
    
    model = os.getenv("MODEL", "swiss-ai/Apertus-v1.5-70B-thinking")
    base_url = os.getenv("BASE_URL", "https://api.inference.cscs.ch/v1")
    tracing = os.getenv("LANGCHAIN_TRACING_V2", "false")
    print(f"Modell:        {model}", flush=True)
    print(f"Endpoint:      {base_url}", flush=True)
    print(f"LangSmith:     {'Aktiviert (Traces werden gesendet)' if tracing == 'true' else 'Deaktiviert'}", flush=True)
    print("-" * 70, flush=True)

    sample_pdf = _track_dir / "data" / "booklets" / "2026-06-14_de.pdf"
    if not sample_pdf.exists():
        print(f"Hinweis: '{sample_pdf}' nicht gefunden.", flush=True)
        return

    claim = "Laut der Zusammenfassung empfiehlt der Bundesrat die Vorlage zur Ablehnung."
    vote_title = "Prämien-Entlastungs-Initiative"

    print(f"Büchlein:     {sample_pdf.name}", flush=True)
    print(f"Vorlage:      {vote_title}", flush=True)
    print(f"Behauptung:   {claim}", flush=True)
    print("-" * 70, flush=True)
    print("Starte LangGraph Workflow...", flush=True)

    graph = build_fact_check_graph()

    initial_state = {
        "messages": [],
        "claim": claim,
        "booklet_path": str(sample_pdf),
        "vote_title": vote_title,
        "detected_language": "de",
        "candidate_pages": [],
        "context_text": "",
        "verdict": None,
        "audit": None,
        "audit_passed": True,
        "audit_retries": 0,
        "needs_human_clarification": False,
        "final_response": "",
    }

    final_state = dict(initial_state)
    for step in graph.stream(initial_state):
        for node_name, state_update in step.items():
            final_state.update(state_update)
            print(f"  -> Node abgeschlossen: [{node_name}]", flush=True)
            if "verdict" in state_update and state_update["verdict"]:
                v = state_update["verdict"]
                print(f"     [NLI-Urteil] {v.get('label_name')} | Seitenzahlen: {v.get('cited_pages')}", flush=True)
            if "audit" in state_update and state_update["audit"]:
                a = state_update["audit"]
                print(f"     [Audit-Score] Treue: {a.get('score')} | Bestanden: {state_update.get('audit_passed')}", flush=True)

    print("=" * 70, flush=True)
    print(final_state.get("final_response", "Keine finale Antwort."), flush=True)
    print("=" * 70, flush=True)
    if tracing == "true":
        print("LangSmith Trace erfolgreich aufgezeichnet auf: https://smith.langchain.com", flush=True)

if __name__ == "__main__":
    main()
