"""
Memex Daemon — Monitor de Repositorios Git Locales
Detecta cambios no commiteados y nuevos commits en repos dentro del workspace.
"""

import os
from typing import Dict, Optional


def check_git_repos(workspace_path: str) -> Dict[str, str]:
    """
    Recorre el workspace buscando repositorios Git.
    Retorna un diccionario {nombre_repo: resumen_de_cambios} para repos con cambios.
    """
    changes = {}

    try:
        import git
    except ImportError:
        print("[GitMonitor] gitpython no disponible. Omitiendo monitoreo Git.")
        return changes

    # Buscar directorios que sean repos Git
    for item in os.listdir(workspace_path):
        item_path = os.path.join(workspace_path, item)
        if not os.path.isdir(item_path):
            continue

        git_dir = os.path.join(item_path, ".git")
        if not os.path.exists(git_dir):
            continue

        try:
            repo = git.Repo(item_path)
            change_info = _analyze_repo(repo, item)
            if change_info:
                changes[item] = change_info
        except Exception as e:
            print(f"[GitMonitor] Error analizando {item}: {e}")

    return changes


def _analyze_repo(repo, repo_name: str) -> Optional[str]:
    """
    Analiza un repositorio Git y retorna un resumen de cambios pendientes.
    Retorna None si no hay cambios.
    """
    parts = []

    # Archivos modificados no commiteados
    if repo.is_dirty(untracked_files=True):
        # Cambios en staging
        staged = [item.a_path for item in repo.index.diff("HEAD")]
        if staged:
            parts.append(f"**Archivos en staging ({len(staged)}):** {', '.join(staged[:10])}")

        # Cambios no staged
        unstaged = [item.a_path for item in repo.index.diff(None)]
        if unstaged:
            parts.append(f"**Archivos modificados ({len(unstaged)}):** {', '.join(unstaged[:10])}")

        # Archivos sin rastrear
        untracked = repo.untracked_files
        if untracked:
            parts.append(f"**Archivos nuevos ({len(untracked)}):** {', '.join(untracked[:10])}")

        # Obtener diff resumido (máx 2000 chars)
        try:
            diff_text = repo.git.diff("--stat")
            if diff_text:
                parts.append(f"**Diff resumen:**\n```\n{diff_text[:2000]}\n```")
        except Exception:
            pass

    # Commits recientes (últimas 24h)
    try:
        import time
        one_day_ago = time.time() - 86400
        recent_commits = []
        for commit in repo.iter_commits(max_count=10):
            if commit.committed_date > one_day_ago:
                recent_commits.append(f"- `{commit.hexsha[:7]}` {commit.message.strip()[:80]}")
        if recent_commits:
            parts.append(f"**Commits recientes (24h):**\n" + "\n".join(recent_commits))
    except Exception:
        pass

    if not parts:
        return None

    return f"## Repositorio: {repo_name}\n\n" + "\n\n".join(parts)
