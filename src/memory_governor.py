"""
title: Memex Memory Governor
author: Memexicanisimos Team
version: 1.0.0
description: |
  Motor de gobernanza de memoria con scoring normalizado,
  decay exponencial, entropy accionable, y control transaccional WAL.
  Diseñado para operar como ciclo nocturno o bajo demanda.
"""

import sqlite3
import os
import json
import gzip
import shutil
import time
from math import log, log2, exp
from datetime import datetime, timedelta
from typing import Optional, Dict, Any


class MemoryGovernor:
    """
    Gobernanza inteligente de memoria con:
    - Scoring normalizado (no explota con access_count alto)
    - Decay exponencial controlable vía λ
    - Entropy accionable (trigger compact si > threshold)
    - Transacciones atómicas WAL con rollback
    - Rotación de logs JSONL
    """

    # --- Mutation Governance: Solo modificable manualmente ---
    LAMBDA_DECAY = 0.1            # Factor de decaimiento temporal
    MAX_EXPECTED_ACCESS = 100     # Techo de normalización
    ENTROPY_THRESHOLD = 2.0       # Trigger de compactación (log2; max teórico ~2.8 con 7 tipos)
    MIN_MEMORIES_FOR_ENTROPY = 50 # No calcular entropy si < 50 memorias
    ARCHIVE_SCORE_THRESHOLD = 0.1 # Score bajo el cual se archiva
    LOG_MAX_BYTES = 100 * 1024 * 1024  # 100MB max per log file
    MAX_ROTATED_FILES = 5         # Máximo de archivos rotados a mantener

    MEMORY_TYPE_WEIGHT = {
        "decision": 1.5,
        "rule":     1.3,
        "plan":     1.2,
        "lesson":   1.1,
        "general":  1.0,
        "entidad":  1.0,
        "marca":    0.9,
        "estilo":   0.9,
        "note":     0.8,
        "log":      0.5,
    }

    def __init__(self, db_path: str = "/app/backend/data/memex_memory.db"):
        self.db_path = db_path
        self.governance_log = os.path.join(
            os.path.dirname(db_path), "workspace", "governance_log.jsonl"
        )
        self.purge_count = 0

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.row_factory = sqlite3.Row
        return conn

    def _log_event(self, event: dict):
        """Escribe evento a JSONL con rotación automática."""
        event["timestamp"] = datetime.now().isoformat()
        self._rotate_log(self.governance_log)
        os.makedirs(os.path.dirname(self.governance_log), exist_ok=True)
        with open(self.governance_log, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")

    def _rotate_log(self, path: str):
        """Rota log si > LOG_MAX_BYTES. Comprime el viejo."""
        if not os.path.exists(path):
            return
        if os.path.getsize(path) < self.LOG_MAX_BYTES:
            return
        rotated = f"{path}.{int(time.time())}.gz"
        with open(path, 'rb') as f_in:
            with gzip.open(rotated, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        # Truncar el archivo original
        with open(path, 'w') as f:
            f.write("")
        # Limpiar archivos antiguos (mantener solo MAX_ROTATED_FILES)
        self._cleanup_old_rotations(path)

    def _cleanup_old_rotations(self, base_path: str):
        """Elimina archivos rotados más antiguos si exceden MAX_ROTATED_FILES."""
        import glob
        pattern = f"{base_path}.*.gz"
        rotated = sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)
        for old_file in rotated[self.MAX_ROTATED_FILES:]:
            try:
                os.remove(old_file)
            except OSError:
                pass

    # ==================== SCHEMA MIGRATION ====================

    def migrate_schema(self):
        """Añade columnas de governance si no existen. Idempotente."""
        conn = self._get_conn()
        migrations = [
            "ALTER TABLE memories ADD COLUMN importance_score REAL DEFAULT 0.5",
            "ALTER TABLE memories ADD COLUMN access_count INTEGER DEFAULT 0",
            "ALTER TABLE memories ADD COLUMN last_accessed TEXT",
        ]
        for sql in migrations:
            try:
                conn.execute(sql)
            except sqlite3.OperationalError:
                pass  # Columna ya existe

        # Índices para evitar full table scans
        indices = [
            "CREATE INDEX IF NOT EXISTS idx_importance ON memories(importance_score)",
            "CREATE INDEX IF NOT EXISTS idx_last_accessed ON memories(last_accessed)",
            "CREATE INDEX IF NOT EXISTS idx_type ON memories(type)",
        ]
        for sql in indices:
            conn.execute(sql)

        # Tabla de archivo
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memory_archive (
                id INTEGER PRIMARY KEY,
                user_id TEXT,
                title TEXT,
                type TEXT,
                tags TEXT,
                importance_score REAL,
                access_count INTEGER,
                created_at TEXT,
                last_accessed TEXT,
                archived_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

    # ==================== SCORING ====================

    def calculate_score(self, memory: dict) -> float:
        """
        importance_score = base_weight × recency_factor × normalized_access
        
        Propiedades:
        - Score ∈ [0, base_weight]
        - Decaimiento suave controlado por λ
        - No explosión por access_count (normalizado)
        """
        base = self.MEMORY_TYPE_WEIGHT.get(memory.get("type", "general"), 1.0)

        # Normalized access: log(n+1) / log(MAX+1) ∈ [0, 1]
        access = memory.get("access_count", 0)
        normalized_access = log(access + 1) / log(self.MAX_EXPECTED_ACCESS + 1)

        # Recency: exp(-λ × days) ∈ (0, 1]
        last_accessed = memory.get("last_accessed")
        if last_accessed:
            try:
                last_dt = datetime.fromisoformat(last_accessed)
                days_since = (datetime.now() - last_dt).days
            except (ValueError, TypeError):
                days_since = 30
        else:
            days_since = 30

        recency_factor = exp(-self.LAMBDA_DECAY * days_since)

        return base * recency_factor * normalized_access

    def calculate_initial_score(self, memory_type: str, content_length: int) -> float:
        """Score inicial al crear una memoria (antes de tener accesos)."""
        base = self.MEMORY_TYPE_WEIGHT.get(memory_type, 1.0)
        # Bonus por contenido sustancial (normalizado)
        length_bonus = min(content_length / 1000, 0.3)
        return min(base * 0.5 + length_bonus, base)

    # ==================== ENTROPY ====================

    def memory_entropy(self, conn: sqlite3.Connection) -> Optional[float]:
        """
        entropy = -Σ(p_i × log(p_i)) donde p_i = proporción de cada type.
        
        Retorna None si < MIN_MEMORIES_FOR_ENTROPY (evita ruido estadístico).
        Trigger compact() si entropy > ENTROPY_THRESHOLD.
        """
        rows = conn.execute(
            "SELECT type, COUNT(*) as cnt FROM memories GROUP BY type"
        ).fetchall()

        total = sum(r["cnt"] for r in rows)

        if total < self.MIN_MEMORIES_FOR_ENTROPY:
            return None  # Insuficiente para estadísticas significativas

        entropy = 0.0
        for row in rows:
            p = row["cnt"] / total
            if p > 0:
                entropy -= p * log2(p)  # log2 para que threshold 2.0 sea alcanzable

        return entropy

    # ==================== GOVERNANCE CYCLE ====================

    def run_cycle(self) -> dict:
        """
        Ciclo atómico completo: score → decay → archive → entropy check.
        Transacción WAL con rollback en caso de error.
        
        Retorna métricas del ciclo para observabilidad.
        """
        start_time = time.time()
        self.purge_count = 0
        conn = self._get_conn()

        conn.execute("BEGIN")
        try:
            # 1. Recalcular scores para todas las memorias
            scored = self._recalculate_scores(conn)

            # 2. Archivar memorias con score < threshold
            archived = self._archive_low_scored(conn)

            # 3. Calcular entropy (solo si suficientes memorias)
            entropy = self.memory_entropy(conn)
            compacted = False
            if entropy is not None and entropy > self.ENTROPY_THRESHOLD:
                compacted = True
                # En compact: eliminar duplicados semánticos, merge similares
                self._compact(conn)

            conn.commit()

            duration = time.time() - start_time
            result = {
                "action": "governance_cycle",
                "memories_scored": scored,
                "memories_archived": archived,
                "entropy": entropy,
                "compacted": compacted,
                "duration_seconds": round(duration, 3),
                "purge_count": self.purge_count,
            }
            self._log_event(result)
            return result

        except Exception as e:
            conn.rollback()
            error_result = {"action": "governance_cycle", "error": str(e)}
            self._log_event(error_result)
            raise
        finally:
            conn.close()

    def _recalculate_scores(self, conn: sqlite3.Connection) -> int:
        """Recalcula importance_score para todas las memorias activas."""
        rows = conn.execute(
            "SELECT id, type, access_count, last_accessed FROM memories"
        ).fetchall()

        count = 0
        for row in rows:
            score = self.calculate_score(dict(row))
            conn.execute(
                "UPDATE memories SET importance_score = ? WHERE id = ?",
                (score, row["id"])
            )
            count += 1

        return count

    def _archive_low_scored(self, conn: sqlite3.Connection) -> int:
        """Mueve memorias con score < threshold a memory_archive."""
        rows = conn.execute(
            "SELECT id, user_id, title, type, tags, importance_score, "
            "access_count, created_at, last_accessed FROM memories "
            "WHERE importance_score < ?",
            (self.ARCHIVE_SCORE_THRESHOLD,)
        ).fetchall()

        archived = 0
        for row in rows:
            conn.execute(
                "INSERT INTO memory_archive "
                "(id, user_id, title, type, tags, importance_score, "
                "access_count, created_at, last_accessed) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                tuple(row)
            )
            # Eliminar de FTS y tabla principal
            conn.execute("DELETE FROM memories_fts WHERE content_id = ?", (row["id"],))
            conn.execute("DELETE FROM memories WHERE id = ?", (row["id"],))
            archived += 1

        self.purge_count = archived
        return archived

    def _compact(self, conn: sqlite3.Connection):
        """
        Compactación: elimina memorias de tipo 'log' con score muy bajo.
        Futuro: merge de memorias semánticamente similares.
        """
        conn.execute(
            "DELETE FROM memories WHERE type = 'log' AND importance_score < ?",
            (self.ARCHIVE_SCORE_THRESHOLD * 2,)
        )

    # ==================== REPORTING ====================

    def health_report(self) -> dict:
        """Genera reporte de salud de la memoria."""
        conn = self._get_conn()
        try:
            total = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
            archived = conn.execute("SELECT COUNT(*) FROM memory_archive").fetchone()[0]

            type_dist = conn.execute(
                "SELECT type, COUNT(*) as cnt, "
                "AVG(importance_score) as avg_score, "
                "AVG(access_count) as avg_access "
                "FROM memories GROUP BY type ORDER BY cnt DESC"
            ).fetchall()

            low_scored = conn.execute(
                "SELECT COUNT(*) FROM memories WHERE importance_score < ?",
                (self.ARCHIVE_SCORE_THRESHOLD * 3,)
            ).fetchone()[0]

            entropy = self.memory_entropy(conn)

            return {
                "total_active": total,
                "total_archived": archived,
                "low_scored_at_risk": low_scored,
                "entropy": entropy,
                "entropy_status": (
                    "healthy" if entropy is None or entropy <= self.ENTROPY_THRESHOLD
                    else "needs_compaction"
                ),
                "types": [
                    {
                        "type": r["type"],
                        "count": r["cnt"],
                        "avg_score": round(r["avg_score"] or 0, 3),
                        "avg_access": round(r["avg_access"] or 0, 1),
                    }
                    for r in type_dist
                ],
            }
        finally:
            conn.close()
