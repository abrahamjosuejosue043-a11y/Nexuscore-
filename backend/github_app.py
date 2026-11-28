"""Read-only GitHub App integration for the Nexuscore Engineering department."""
from __future__ import annotations
import base64, os, re, time
from dataclasses import dataclass
from typing import Optional
from urllib.parse import quote
import httpx, jwt

GITHUB_API = "https://api.github.com"
GITHUB_API_VERSION = "2022-11-28"
MAX_FILE_BYTES = 128 * 1024
ALLOWED_ROOTS = ("backend/", "tests/", "frontend/", ".github/workflows/")
ALLOWED_FILES = frozenset({"main.py", "README.md", "requirements.txt"})

class GitHubIntegrationError(RuntimeError):
    """Safe, user-displayable GitHub integration failure."""

@dataclass(frozen=True)
class GitHubAppConfig:
    app_id: str
    private_key: str
    installation_id: str
    repository: str

    @classmethod
    def from_env(cls) -> Optional["GitHubAppConfig"]:
        values = {
            "app_id": os.getenv("GITHUB_APP_ID", "").strip(),
            "private_key": os.getenv("GITHUB_APP_PRIVATE_KEY", "").strip(),
            "installation_id": os.getenv("GITHUB_INSTALLATION_ID", "").strip(),
            "repository": os.getenv("GITHUB_REPOSITORY", "").strip(),
        }
        if not all(values.values()):
            return None
        if not values["app_id"].isdigit() or not values["installation_id"].isdigit():
            return None
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", values["repository"]):
            return None
        return cls(**values)

def validate_repository_path(path: str) -> str:
    """Allow source/documentation paths only; reject traversal and secret locations."""
    normalized = str(path or "").strip().replace("\\", "/")
    if not normalized or normalized.startswith("/") or "\x00" in normalized:
        raise GitHubIntegrationError("Caminho de arquivo inválido.")
    if any(part in {"", ".", ".."} for part in normalized.split("/")):
        raise GitHubIntegrationError("Caminho de arquivo inválido.")
    lowered = normalized.lower()
    if any(part.startswith(".env") or "secret" in part or "credential" in part for part in lowered.split("/")):
        raise GitHubIntegrationError("O acesso a arquivos de segredo ou credenciais é bloqueado.")
    if normalized not in ALLOWED_FILES and not normalized.startswith(ALLOWED_ROOTS):
        raise GitHubIntegrationError("Esse caminho está fora das pastas autorizadas para leitura.")
    if lowered.endswith((".pem", ".key", ".p12", ".pfx", ".sqlite", ".db")):
        raise GitHubIntegrationError("Esse tipo de arquivo não pode ser lido pela integração.")
    return normalized

class GitHubAppReadOnlyClient:
    def __init__(self, config: Optional[GitHubAppConfig] = None, http_client_factory=None):
        self.config = config or GitHubAppConfig.from_env()
        self._http_client_factory = http_client_factory or httpx.AsyncClient

    @property
    def configured(self) -> bool:
        return self.config is not None

    def _app_jwt(self) -> str:
        if not self.config:
            raise GitHubIntegrationError("Integração GitHub ainda não configurada.")
        now = int(time.time())
        private_key = self.config.private_key.replace("\\n", "\n")
        try:
            return jwt.encode(
                {"iat": now - 60, "exp": now + 540, "iss": self.config.app_id},
                private_key, algorithm="RS256",
            )
        except Exception as exc:
            raise GitHubIntegrationError("A chave privada da GitHub App não pôde ser validada.") from exc

    async def _installation_token(self) -> str:
        if not self.config:
            raise GitHubIntegrationError("Integração GitHub ainda não configurada.")
        headers = {
            "Authorization": f"Bearer {self._app_jwt()}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": GITHUB_API_VERSION,
        }
        url = f"{GITHUB_API}/app/installations/{self.config.installation_id}/access_tokens"
        try:
            async with self._http_client_factory(timeout=15.0, follow_redirects=False) as client:
                response = await client.post(url, headers=headers, json={"permissions": {"contents": "read"}})
            if response.status_code != 201:
                raise GitHubIntegrationError(
                    f"GitHub não autorizou o acesso da instalação (HTTP {response.status_code})."
                )
            token = response.json().get("token")
            if not token:
                raise GitHubIntegrationError("GitHub não retornou um token temporário de instalação.")
            return token
        except GitHubIntegrationError:
            raise
        except (httpx.HTTPError, ValueError, KeyError) as exc:
            raise GitHubIntegrationError("Não foi possível autenticar com o GitHub.") from exc

    async def _get(self, endpoint: str) -> dict:
        if not self.config:
            raise GitHubIntegrationError("Integração GitHub ainda não configurada.")
        token = await self._installation_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": GITHUB_API_VERSION,
        }
        try:
            async with self._http_client_factory(timeout=15.0, follow_redirects=False) as client:
                response = await client.get(f"{GITHUB_API}{endpoint}", headers=headers)
            if response.status_code == 404:
                raise GitHubIntegrationError("Repositório ou arquivo não encontrado, ou sem permissão de leitura.")
            if response.status_code != 200:
                raise GitHubIntegrationError(f"GitHub recusou a leitura (HTTP {response.status_code}).")
            return response.json()
        except GitHubIntegrationError:
            raise
        except (httpx.HTTPError, ValueError) as exc:
            raise GitHubIntegrationError("Não foi possível consultar o GitHub.") from exc

    async def repository_status(self) -> dict:
        if not self.config:
            return {"configured": False, "connected": False, "mode": "read_only"}
        repo = quote(self.config.repository, safe="/")
        data = await self._get(f"/repos/{repo}")
        return {
            "configured": True, "connected": True, "mode": "read_only",
            "repository": self.config.repository,
            "default_branch": data.get("default_branch"),
            "private": bool(data.get("private", False)),
            "permissions": {"contents": "read", "pull_requests": "none", "actions": "none"},
        }

    async def read_file(self, path: str) -> dict:
        safe_path = validate_repository_path(path)
        if not self.config:
            raise GitHubIntegrationError("Integração GitHub ainda não configurada.")
        repo = quote(self.config.repository, safe="/")
        data = await self._get(f"/repos/{repo}/contents/{quote(safe_path, safe='/')}")
        if data.get("type") != "file":
            raise GitHubIntegrationError("O caminho solicitado não corresponde a um arquivo.")
        if int(data.get("size") or 0) > MAX_FILE_BYTES:
            raise GitHubIntegrationError("Arquivo excede o limite de leitura de 128 KB.")
        if data.get("encoding") != "base64" or not data.get("content"):
            raise GitHubIntegrationError("GitHub não retornou conteúdo textual em formato suportado.")
        try:
            raw = base64.b64decode(data["content"], validate=False)
            content = raw.decode("utf-8")
        except (ValueError, UnicodeDecodeError) as exc:
            raise GitHubIntegrationError("O arquivo não é texto UTF-8 legível.") from exc
        if len(raw) > MAX_FILE_BYTES:
            raise GitHubIntegrationError("Arquivo excede o limite de leitura de 128 KB.")
        return {
            "path": safe_path, "name": data.get("name", safe_path.rsplit("/", 1)[-1]),
            "size": len(raw), "sha": data.get("sha"), "html_url": data.get("html_url"),
            "content": content,
        }
