class FakeGitRunner:
    def __init__(
        self,
        current_branch: str = "main",
        branches: list[str] | None = None,
        commits: list[dict] | None = None,
    ) -> None:
        self.current_branch = current_branch
        self.branches = branches or ["main"]
        self.commits = commits or []
        self._created_branches: list[str] = []
        self._commands: list[str] = []

    def run(self, args: list[str]) -> str:
        cmd = " ".join(args)
        self._commands.append(cmd)

        if args[0] == "branch" and len(args) >= 2 and args[1] != "--list" and not args[1].startswith("-"):
            self._created_branches.append(args[1])
            self.branches.append(args[1])
            return ""

        if args[0] == "branch" and "--list" in args:
            return "\n".join(self.branches)

        if args[0] == "log":
            import json
            return json.dumps(self.commits)

        if args[0] == "show":
            import json
            sha = args[1]
            for c in self.commits:
                if c["sha"] == sha:
                    return json.dumps(c)
            return json.dumps({})

        if args[0] == "rev-parse":
            return self.current_branch

        return ""

    @property
    def created_branches(self) -> list[str]:
        return self._created_branches
