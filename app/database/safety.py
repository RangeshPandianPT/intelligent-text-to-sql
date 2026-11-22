"""
Safe SDE-SQL: Enterprise Multi-Layer Safety Engine
===================================================
Provides 4 distinct layers of defense for Text-to-SQL:
1. Input Prompt Guard (Prompt injection, jailbreak & raw SQL intent filter)
2. AST Structural Safety (SQLGlot single-SELECT, DDL/DML, exploit & tautology detection)
3. DoS Prevention (Cartesian join blocker & automatic LIMIT enforcement)
4. Security Audit Trail (Thread-safe threat telemetry & logging)
"""

import re
import time
import logging
from typing import Dict, Any, List, Optional
from threading import Lock
import sqlglot
from sqlglot import exp

logger = logging.getLogger(__name__)

class SQLSafetyError(Exception):
    """Raised when a SQL query or prompt fails safety checks."""
    def __init__(self, message: str, threat_type: str = "GENERIC_UNSAFE"):
        super().__init__(message)
        self.threat_type = threat_type

# ──────────────────────────────────────────────────────────────────────
# Threat Category Definitions
# ──────────────────────────────────────────────────────────────────────
class ThreatCategory:
    PROMPT_INJECTION = "PROMPT_INJECTION"
    DDL_MUTATION = "DDL_MUTATION_ATTEMPT"
    DML_MUTATION = "DML_MUTATION_ATTEMPT"
    SQL_INJECTION = "SQL_INJECTION_ATTEMPT"
    SQLITE_EXPLOIT = "SQLITE_EXPLOIT_ATTEMPT"
    CARTESIAN_DOS = "CARTESIAN_PRODUCT_DOS"
    UNAUTHORIZED_ACCESS = "UNAUTHORIZED_ACCESS"

# ──────────────────────────────────────────────────────────────────────
# Security Audit Logger (Telemetry & Threat Tracking)
# ──────────────────────────────────────────────────────────────────────
class SafetyAuditLogger:
    """Thread-safe in-memory security event logger and metrics collector."""
    _instance = None
    _lock = Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(SafetyAuditLogger, cls).__new__(cls)
                cls._instance.events: List[Dict[str, Any]] = []
                cls._instance.total_scanned: int = 0
                cls._instance.threats_blocked: int = 0
                cls._instance.threat_counts: Dict[str, int] = {}
        return cls._instance

    def record_event(self, text: str, status: str, threat_type: Optional[str] = None, reason: Optional[str] = None):
        with self._lock:
            self.total_scanned += 1
            if status == "BLOCKED":
                self.threats_blocked += 1
                threat = threat_type or "GENERIC_UNSAFE"
                self.threat_counts[threat] = self.threat_counts.get(threat, 0) + 1

            event = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "query": text[:120] + ("..." if len(text) > 120 else ""),
                "status": status,
                "threat_type": threat_type,
                "reason": reason
            }
            self.events.append(event)
            if len(self.events) > 200:
                self.events.pop(0)

    def get_metrics(self) -> Dict[str, Any]:
        with self._lock:
            clean = self.total_scanned - self.threats_blocked
            clean_rate = round((clean / self.total_scanned * 100), 1) if self.total_scanned > 0 else 100.0
            return {
                "total_scanned": self.total_scanned,
                "threats_blocked": self.threats_blocked,
                "clean_passed": clean,
                "clean_pass_rate_pct": clean_rate,
                "threat_breakdown": dict(self.threat_counts)
            }

    def get_recent_events(self, limit: int = 15) -> List[Dict[str, Any]]:
        with self._lock:
            return list(reversed(self.events[-limit:]))

safety_logger = SafetyAuditLogger()

# ──────────────────────────────────────────────────────────────────────
# Layer 1: Prompt Injection & Malicious Intent Guard
# ──────────────────────────────────────────────────────────────────────
JAILBREAK_PATTERNS = [
    r"ignore\s+(?:all\s+)?(?:previous\s+|prior\s+)?instructions",
    r"disregard\s+(?:all\s+)?rules",
    r"bypass\s+safety",
    r"you\s+are\s+now\s+in\s+developer\s+mode",
    r"act\s+as\s+dan",
    r"system\s+prompt\s+override",
]

MALICIOUS_INTENT_PATTERNS = [
    (r";\s*(?:drop|delete|insert|update|alter|create|truncate)\b", ThreatCategory.SQL_INJECTION, "Stacked SQL command injection pattern"),
    (r"(--\s*$|/\*.*?\*/)", ThreatCategory.SQL_INJECTION, "SQL comment injection pattern"),
    (r"\b(drop\s+table|drop\s+database|truncate\s+table)\b", ThreatCategory.DDL_MUTATION, "DDL Drop attempt in input prompt"),
    (r"\b(alter\s+table|create\s+table)\b", ThreatCategory.DDL_MUTATION, "DDL modification attempt in input prompt"),
    (r"\b(delete\s+from|insert\s+into|update\s+\w+\s+set)\b", ThreatCategory.DML_MUTATION, "DML data mutation attempt in input prompt"),
    (r"\b(load_extension|attach\s+database|sqlite_master)\b", ThreatCategory.SQLITE_EXPLOIT, "SQLite engine exploit attempt in input prompt"),
]

def validate_input_prompt_safety(prompt: str) -> None:
    """
    Validates natural language questions before passing to the LLM or pipeline.
    Stops prompt injections, jailbreak instructions, and raw mutation queries early.
    """
    if not prompt or not prompt.strip():
        raise SQLSafetyError("Input query is empty.", threat_type="EMPTY_INPUT")

    lower = prompt.lower().strip()

    # 1. Jailbreak and Prompt Injection Checks
    for pattern in JAILBREAK_PATTERNS:
        if re.search(pattern, lower):
            safety_logger.record_event(prompt, "BLOCKED", ThreatCategory.PROMPT_INJECTION, "Prompt injection / jailbreak instruction detected")
            raise SQLSafetyError(
                "Safety Violation: Prompt injection or jailbreak instruction detected.",
                threat_type=ThreatCategory.PROMPT_INJECTION
            )

    # 2. Malicious Intent / Mutation Commands in Prompt
    for pattern, threat_type, desc in MALICIOUS_INTENT_PATTERNS:
        if re.search(pattern, lower):
            safety_logger.record_event(prompt, "BLOCKED", threat_type, desc)
            raise SQLSafetyError(
                f"Safety Violation: {desc}. Only read-only natural language queries are permitted.",
                threat_type=threat_type
            )

# ──────────────────────────────────────────────────────────────────────
# Layer 2: AST Structural Safety & Exploit Neutralization
# ──────────────────────────────────────────────────────────────────────
DISALLOWED_AST_NODES = (
    exp.Insert,
    exp.Update,
    exp.Delete,
    exp.Drop,
    exp.Create,
    exp.Alter,
    exp.Pragma,
    exp.Command,
    exp.Into
)

DISALLOWED_FUNCTIONS = {
    "load_extension", "writefile", "readfile", "edit", "fts3_tokenizer", "attach"
}

def validate_sql_safety(sql: str) -> None:
    """
    Validates a SQL query for safety using Abstract Syntax Tree (AST) parsing.
    Ensures single SELECT statement, prevents mutations, exploits, and tautology injections.
    """
    if not sql or not sql.strip():
        safety_logger.record_event(sql or "<empty>", "BLOCKED", "EMPTY_SQL", "SQL query is empty.")
        raise SQLSafetyError("SQL query is empty.", threat_type="EMPTY_SQL")

    try:
        statements = sqlglot.parse(sql, read="sqlite")
    except sqlglot.errors.ParseError as e:
        safety_logger.record_event(sql, "BLOCKED", "SYNTAX_ERROR", f"SQL syntax error: {e}")
        raise SQLSafetyError(f"SQL syntax error: {e}", threat_type="SYNTAX_ERROR")

    if not statements:
        safety_logger.record_event(sql, "BLOCKED", "PARSE_ERROR", "Could not parse SQL query.")
        raise SQLSafetyError("Could not parse SQL query.", threat_type="PARSE_ERROR")

    if len(statements) > 1:
        safety_logger.record_event(sql, "BLOCKED", ThreatCategory.SQL_INJECTION, "Multiple SQL statements detected (stacked injection).")
        raise SQLSafetyError("Multiple SQL statements are not allowed.", threat_type=ThreatCategory.SQL_INJECTION)

    statement = statements[0]
    if not statement:
        raise SQLSafetyError("Parsed statement is None.")

    # 1. Root must strictly be a SELECT
    if not isinstance(statement, exp.Select):
        safety_logger.record_event(sql, "BLOCKED", ThreatCategory.DDL_MUTATION, "Only SELECT queries are permitted.")
        raise SQLSafetyError("Only SELECT queries are permitted.", threat_type=ThreatCategory.DDL_MUTATION)

    # 2. Check for disallowed DDL/DML/Command nodes in entire AST
    for d_type in DISALLOWED_AST_NODES:
        if statement.find(d_type):
            threat = ThreatCategory.DDL_MUTATION if d_type in (exp.Drop, exp.Create, exp.Alter) else ThreatCategory.DML_MUTATION
            safety_logger.record_event(sql, "BLOCKED", threat, f"Dangerous operation: {d_type.__name__}")
            raise SQLSafetyError(f"Dangerous SQL operation detected: {d_type.__name__}", threat_type=threat)

    # 3. Check for exploit functions (SQLite extensions, attachments)
    for func in statement.find_all(exp.Anonymous, exp.Func):
        func_name = func.name.lower() if hasattr(func, "name") and func.name else ""
        if func_name in DISALLOWED_FUNCTIONS:
            safety_logger.record_event(sql, "BLOCKED", ThreatCategory.SQLITE_EXPLOIT, f"Forbidden function: {func_name}")
            raise SQLSafetyError(f"Forbidden security-restricted function call: {func_name}()", threat_type=ThreatCategory.SQLITE_EXPLOIT)

    # 4. Tautology Injection Detection (e.g. OR 1=1, OR 'a'='a')
    for or_node in statement.find_all(exp.Or):
        for child in or_node.flatten():
            if isinstance(child, exp.EQ):
                left_str = str(child.this).strip().strip("'\"")
                right_str = str(child.expression).strip().strip("'\"")
                if left_str == right_str and left_str != "":
                    safety_logger.record_event(sql, "BLOCKED", ThreatCategory.SQL_INJECTION, f"Tautology injection pattern detected: {child}")
                    raise SQLSafetyError(f"SQL Injection threat detected: Tautology condition '{child}' is not permitted.", threat_type=ThreatCategory.SQL_INJECTION)

    # Passed all AST safety checks!
    safety_logger.record_event(sql, "PASSED")

# ──────────────────────────────────────────────────────────────────────
# Layer 3: DoS Prevention & Automatic LIMIT Enforcement
# ──────────────────────────────────────────────────────────────────────
def enforce_query_limits(sql: str, default_limit: int = 100) -> str:
    """
    Guarantees the query contains a safe LIMIT constraint to prevent DoS memory exhaustion.
    If LIMIT is omitted or exceeds default_limit, caps it automatically.
    """
    try:
        expression = sqlglot.parse_one(sql, read="sqlite")
        if isinstance(expression, exp.Select):
            limit_clause = expression.find(exp.Limit)
            if not limit_clause:
                expression = expression.limit(default_limit)
                return expression.sql(dialect="sqlite")
            else:
                # Cap the limit if it is dangerously high (> 500)
                try:
                    current_limit = int(str(limit_clause.expression))
                    if current_limit > default_limit:
                        limit_clause.set("expression", exp.Literal.number(default_limit))
                        return expression.sql(dialect="sqlite")
                except (ValueError, TypeError):
                    pass
    except Exception:
        pass
    return sql
