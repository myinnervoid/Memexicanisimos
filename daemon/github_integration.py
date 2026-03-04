"""
Memex Daemon — Integración con GitHub API
Monitorea issues nuevos y PRs en repositorios configurados.
"""

import os
import json
import time
from typing import List, Dict


# Archivo para rastrear issues ya procesados
PROCESSED_ISSUES_FILE = "/app/workspace/daemon_processed_issues.json"


def _load_processed_ids() -> set:
    """Carga los IDs de issues ya procesados."""
    try:
        if os.path.exists(PROCESSED_ISSUES_FILE):
            with open(PROCESSED_ISSUES_FILE, "r") as f:
                return set(json.load(f))
    except Exception:
        pass
    return set()


def _save_processed_ids(ids: set):
    """Guarda los IDs de issues procesados."""
    try:
        os.makedirs(os.path.dirname(PROCESSED_ISSUES_FILE), exist_ok=True)
        with open(PROCESSED_ISSUES_FILE, "w") as f:
            json.dump(list(ids), f)
    except Exception:
        pass


def check_github_issues(token: str, repos: List[str]) -> List[Dict]:
    """
    Revisa issues nuevos (abiertos en las últimas 24h) en los repos indicados.
    Retorna una lista de dicts con info del issue.

    :param token: Token de acceso personal de GitHub.
    :param repos: Lista de repos en formato "usuario/repo".
    """
    new_issues = []

    try:
        from github import Github
    except ImportError:
        print("[GitHub] PyGithub no disponible. Omitiendo monitoreo de GitHub.")
        return new_issues

    processed_ids = _load_processed_ids()

    try:
        g = Github(token)

        for repo_name in repos:
            try:
                repo = g.get_repo(repo_name)
                # Obtener issues abiertos recientes
                issues = repo.get_issues(state="open", sort="created", direction="desc")

                for issue in issues[:10]:  # máximo 10 por repo
                    issue_key = f"{repo_name}#{issue.number}"
                    if issue_key in processed_ids:
                        continue

                    # Solo issues de las últimas 24 horas
                    created_timestamp = issue.created_at.timestamp()
                    if time.time() - created_timestamp > 86400:
                        continue

                    # Ignorar PRs (GitHub los lista como issues)
                    if issue.pull_request is not None:
                        continue

                    new_issues.append({
                        "repo": repo_name,
                        "number": issue.number,
                        "title": issue.title,
                        "body": (issue.body or "")[:2000],
                        "url": issue.html_url,
                        "labels": [l.name for l in issue.labels],
                        "created_at": issue.created_at.isoformat()
                    })

                    processed_ids.add(issue_key)

            except Exception as e:
                print(f"[GitHub] Error en {repo_name}: {e}")

        _save_processed_ids(processed_ids)

    except Exception as e:
        print(f"[GitHub] Error de autenticación: {e}")

    return new_issues
