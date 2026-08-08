import json
import subprocess
from collections.abc import Callable


class GitAdapter:
    def __init__(self, runner: Callable[..., str] | None = None) -> None:
        self._runner = runner or self._run_git

    def current_branch(self) -> str:
        return self._runner(["rev-parse", "--abbrev-ref", "HEAD"]).strip()

    def list_branches(self) -> list[str]:
        output = self._runner(["branch", "--list"])
        return [b.strip().lstrip("* ") for b in output.splitlines() if b.strip()]

    def create_branch(self, name: str) -> None:
        self._runner(["checkout", "-b", name])

    def recent_commits(self, branch: str, count: int) -> list[dict]:
        output = self._runner([
            "log", branch, f"-{count}",
            "--format=__JSON_START__{\"sha\":\"%H\",\"message\":\"%s\",\"date\":\"%aI\"}__JSON_END__",
        ])
        results = []
        for line in output.splitlines():
            start = line.find("__JSON_START__")
            end = line.find("__JSON_END__")
            if start >= 0 and end > start:
                obj = json.loads(line[start + len("__JSON_START__"):end])
                results.append(obj)
        return results

    def get_commit(self, sha: str) -> dict:
        output = self._runner([
            "show", sha,
            "--format=__JSON_START__{\"sha\":\"%H\",\"message\":\"%s\",\"date\":\"%aI\"}__JSON_END__",
            "--no-patch",
        ])
        for line in output.splitlines():
            start = line.find("__JSON_START__")
            end = line.find("__JSON_END__")
            if start >= 0 and end > start:
                return json.loads(line[start + len("__JSON_START__"):end])
        return {}

    @staticmethod
    def _run_git(args: list[str]) -> str:
        result = subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
        )
        return result.stdout
