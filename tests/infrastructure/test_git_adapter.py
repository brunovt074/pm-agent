from pmagent.infrastructure.git_adapter import GitAdapter


class TestGitAdapter:
    def test_current_branch(self):
        git = GitAdapter()
        git._runner = lambda args: "feature/login"
        assert git.current_branch() == "feature/login"

    def test_list_branches(self):
        git = GitAdapter()
        git._runner = lambda args: "main\n  feature/login\n  fix/bug-42"
        branches = git.list_branches()
        assert branches == ["main", "feature/login", "fix/bug-42"]

    def test_create_branch(self):
        created: list[str] = []

        def _fake_runner(args):
            if args[0] == "checkout" and args[1] == "-b":
                created.append(args[2])
                return ""
            return ""

        git = GitAdapter()
        git._runner = _fake_runner
        git.create_branch("feature/new-feature")
        assert created == ["feature/new-feature"]

    def test_recent_commits_parses_log(self):
        import json
        commits = [
            {"sha": "abc123", "message": "feat: add login", "date": "2026-01-01T00:00:00Z"},
            {"sha": "def456", "message": "fix: crash on null", "date": "2026-01-02T00:00:00Z"},
        ]

        def _fake_output(args):
            lines = []
            for c in commits:
                lines.append(f"__JSON_START__{json.dumps(c)}__JSON_END__")
            return "\n".join(lines)

        git = GitAdapter()
        git._runner = _fake_output
        result = git.recent_commits("feature/login", 5)

        assert len(result) == 2
        assert result[0]["sha"] == "abc123"
        assert result[1]["message"] == "fix: crash on null"

    def test_get_commit(self):
        import json
        commit = {"sha": "abc123", "message": "feat: add login", "date": "2026-01-01T00:00:00Z"}

        git = GitAdapter()
        git._runner = lambda args: f"__JSON_START__{json.dumps(commit)}__JSON_END__\n"
        result = git.get_commit("abc123")

        assert result["sha"] == "abc123"
        assert result["message"] == "feat: add login"
