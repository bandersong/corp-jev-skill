"""The /corp agent types (CEO decision E11): ~/.claude/agents/corp-*.md pin `model:` and `effort:` because the Agent tool
has no effort field. The committed copies in corp/agents/ are the source (F7); every installed type must be its source,
byte for byte, and say that its brief carries COMMON and its output schema (F8). Pure code: no Jev, no network. Run with:
python3 -m unittest test_agents -v (from this directory). CORP_AGENTS_DIR overrides the installed folder (tests of a copy).
"""
import json
import os
import re
import unittest

AGENTS = os.environ.get("CORP_AGENTS_DIR") or os.path.expanduser("~/.claude/agents")
SOURCE = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "agents")   # corp/agents/, committed
WANT = {   # E11, verbatim: type -> (model, effort)
    "corp-final-fable": ("fable", "max"), "corp-final-opus": ("opus", "max"), "corp-judge": ("opus", "xhigh"),
    "corp-doc-builder": ("opus", "xhigh"), "corp-sw-builder": ("sonnet", "high"), "corp-auditor": ("sonnet", "high"),
    "corp-mech": ("haiku", "medium"),
}
THINK_FIRST = "Think the problem through before you answer."   # the kit's THINK_FIRST, the auditor's last role line


def frontmatter(text):
    """The YAML subset these files use: `key: value`, a value bare or a JSON (= YAML double-quoted) string."""
    m = re.match(r"\A---\n(.*?)\n---\n", text, re.S)
    if not m:
        raise AssertionError("no --- frontmatter block at the top")
    out = {}
    for line in m.group(1).split("\n"):
        key, sep, value = line.partition(": ")
        if not sep or not re.fullmatch(r"[a-z_]+", key):
            raise AssertionError(f"not a 'key: value' line: {line!r}")
        if value.startswith('"'):
            out[key] = json.loads(value)
        else:
            if ": " in value or value.startswith(("'", "[", "{", "&", "*", "!", "|", ">")):
                raise AssertionError(f"{key}: a bare YAML value may not hold ': ' or start with {value[:1]!r}")
            out[key] = value
    return out, text[m.end():]


class AgentTypesTest(unittest.TestCase):
    def read(self, name):
        with open(os.path.join(AGENTS, name + ".md"), encoding="utf-8") as fh:
            return fh.read()

    def test_every_type_pins_its_model_and_effort(self):
        for name, (model, effort) in WANT.items():
            with self.subTest(name=name):
                fm, _ = frontmatter(self.read(name))
                self.assertEqual((fm.get("name"), fm.get("model"), fm.get("effort")), (name, model, effort))
                self.assertIn("E11", fm.get("description", ""))                # says why it exists: effort

    def test_each_body_is_the_perimeter_and_the_unattended_clause_not_the_whole_common(self):
        for name in WANT:
            with self.subTest(name=name):
                _, body = frontmatter(self.read(name))
                for must in ("PERIMETER", "UNATTENDED", "never a session scratchpad", "under /Volumes",
                             "cp -p X X.bak-<YYYYMMDD>", "a send is HUMAN-ONLY", "status 'partial'", "could_not_check"):
                    self.assertIn(must, body)
                self.assertNotIn("JEV (corp references/jev.md", body)            # the COMMON preamble rides the brief
                self.assertLess(len(body.encode()), 4000)
        _, body = frontmatter(self.read("corp-auditor"))
        self.assertIn(THINK_FIRST, body)                                        # D11: sonnet at high thinks first

    def test_each_installed_type_is_its_committed_source(self):
        # F7 (re-gate FABLE-B RG-05, OPUS RG-07): two copies, nothing compared them -- a seat could run at another
        # effort than the versioned definition says
        self.assertEqual(sorted(f for f in os.listdir(SOURCE) if f.endswith(".md")), sorted(n + ".md" for n in WANT))
        for name in WANT:
            with self.subTest(name=name):
                with open(os.path.join(SOURCE, name + ".md"), "rb") as fh:
                    src = fh.read()
                with open(os.path.join(AGENTS, name + ".md"), "rb") as fh:
                    self.assertEqual(fh.read(), src, f"{AGENTS}/{name}.md is not corp/agents/{name}.md: reinstall it "
                                                     "(preflight prints the command)")

    def test_each_body_says_its_brief_carries_common_and_its_schema(self):
        # F8 (re-gate OPUS OM-03): the Agent-tool path had no way to put COMMON or a schema into a brief
        for name in WANT:
            with self.subTest(name=name):
                _, body = frontmatter(self.read(name))
                for must in ("scripts/kit-run common <slots.json>", "scripts/kit-run schema <NAME>",
                             "Return ONLY one JSON object matching that schema", "CEO decision\nF8"):
                    self.assertIn(must, body)

    def test_the_kit_think_first_line_is_the_same_text(self):
        kit = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "templates", "corp-kit.js")
        with open(kit, encoding="utf-8") as fh:
            self.assertIn(f"const THINK_FIRST = '{THINK_FIRST}'", fh.read())


if __name__ == "__main__":
    unittest.main()
