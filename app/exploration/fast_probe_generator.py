"""
Fast Rule-Based Probe Generator (No LLM)
=========================================
Generates SQL exploration probes deterministically from the linked schema
instead of asking the LLM to generate them.

Each probe is a simple, fast SQLite query:
  - Stage A: SELECT DISTINCT for every selected text/int column → discovers
             candidate values used in WHERE clauses.
  - Stage B: Combines question-token values with LIKE / = filters to verify
             which combinations actually return rows.
"""

import logging
import re
from typing import List, Dict, Any

from app.exploration.schemas import Probe, ProbeResult
from app.exploration.probe_executor import ProbeExecutor
from app.config import settings

logger = logging.getLogger(__name__)


def _tokenize(text: str) -> List[str]:
    """Return lowercase alphanumeric tokens longer than 2 chars."""
    stop = {
        "the", "a", "an", "is", "are", "and", "or", "of", "in", "on",
        "at", "to", "for", "from", "with", "all", "any", "not", "what",
        "which", "who", "how", "me", "my", "show", "list", "find", "give",
        "get", "fetch", "display", "name", "names", "where", "when", "their",
        "there", "will", "that", "this", "by", "each", "per",
    }
    return [
        t for t in re.findall(r"[a-zA-Z0-9]+", text.lower())
        if len(t) > 2 and t not in stop
    ]


class FastProbeGenerator:
    """
    Generates probes using pure SQL rules — zero LLM calls.

    Stage A — candidate exploration:
        SELECT DISTINCT <col> FROM <table> LIMIT 20
        for every selected column in the linked schema.

    Stage B — combination exploration:
        For each text column + each question token:
          SELECT COUNT(*) FROM <table> WHERE <col> LIKE '%<token>%' LIMIT 1
        to verify which token/column combos exist in the DB.
    """

    def generate_stage_a_probes(
        self,
        question: str,
        linked_schema: Dict[str, Any],
        max_probes: int = None,
    ) -> List[Probe]:
        if max_probes is None:
            max_probes = settings.max_probes

        probes: List[Probe] = []

        for table in linked_schema.get("tables", []):
            tname = table.get("name", "")
            # selected columns from fast_linker or LLM linker output
            sel_cols = table.get("selected_columns", [])
            if not sel_cols:
                sel_cols = table.get("columns", [])

            for col in sel_cols:
                cname = col.get("name", "") if isinstance(col, dict) else col.name
                ctype = (col.get("type", "") if isinstance(col, dict) else col.type).upper()

                if "TEXT" in ctype or "VARCHAR" in ctype or "INT" in ctype or "REAL" in ctype:
                    sql = f"SELECT DISTINCT {cname} FROM {tname} LIMIT 20;"
                    probes.append(
                        Probe(
                            purpose=f"Discover values of {tname}.{cname}",
                            sql=sql,
                        )
                    )

                if len(probes) >= max_probes:
                    return probes

        return probes[:max_probes]

    def generate_stage_b_probes(
        self,
        question: str,
        linked_schema: Dict[str, Any],
        stage_a_results: List[ProbeResult],
        max_probes: int = None,
    ) -> List[Probe]:
        if max_probes is None:
            max_probes = settings.max_probes

        tokens = _tokenize(question)
        probes: List[Probe] = []

        for table in linked_schema.get("tables", []):
            tname = table.get("name", "")
            sel_cols = table.get("selected_columns", [])
            if not sel_cols:
                sel_cols = table.get("columns", [])

            for col in sel_cols:
                cname = col.get("name", "") if isinstance(col, dict) else col.name
                ctype = (col.get("type", "") if isinstance(col, dict) else col.type).upper()

                if "TEXT" not in ctype and "VARCHAR" not in ctype:
                    continue

                for token in tokens:
                    sql = (
                        f"SELECT COUNT(*) AS cnt FROM {tname} "
                        f"WHERE {cname} LIKE '%{token}%' LIMIT 1;"
                    )
                    probes.append(
                        Probe(
                            purpose=f"Check if {tname}.{cname} contains '{token}'",
                            sql=sql,
                        )
                    )
                    if len(probes) >= max_probes:
                        return probes

        return probes[:max_probes]

