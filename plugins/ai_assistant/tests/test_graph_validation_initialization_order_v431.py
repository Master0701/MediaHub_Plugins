import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_PATH = ROOT / "plugin.py"


def _text() -> str:
    return PLUGIN_PATH.read_text(encoding="utf-8")


def _tree() -> ast.AST:
    return ast.parse(_text())


def _assignment_lines(name: str) -> list[int]:
    lines: list[int] = []

    for node in ast.walk(_tree()):
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = []

            if isinstance(node, ast.Assign):
                targets.extend(node.targets)
            else:
                targets.append(node.target)

            for target in targets:
                if (
                    isinstance(target, ast.Name)
                    and target.id == name
                ):
                    lines.append(node.lineno)

    return sorted(lines)


def _load_lines(name: str) -> list[int]:
    return sorted(
        node.lineno
        for node in ast.walk(_tree())
        if (
            isinstance(node, ast.Name)
            and node.id == name
            and isinstance(node.ctx, ast.Load)
        )
    )


def test_plugin_syntax_is_valid():
    _tree()


def test_graph_validation_is_assigned_once():
    lines = _assignment_lines("graph_validation")

    assert len(lines) == 1


def test_graph_validation_is_not_read_before_assignment():
    assignment_line = _assignment_lines(
        "graph_validation"
    )[0]
    load_lines = _load_lines("graph_validation")

    assert load_lines
    assert all(
        line > assignment_line
        for line in load_lines
    )


def test_graph_validation_groups_is_assigned_once():
    lines = _assignment_lines(
        "graph_validation_groups"
    )

    assert len(lines) == 1


def test_group_collection_uses_dictionary_filter():
    tree = _tree()

    found = False
    for node in ast.walk(tree):
        if not isinstance(node, ast.ListComp):
            continue

        source = ast.get_source_segment(
            _text(),
            node,
        ) or ""

        if (
            "graph_proposal" in source
            and "franchise_collection" in source
            and "isinstance(group, dict)" in source
        ):
            found = True
            break

    assert found


def test_validator_uses_filtered_group_variable():
    tree = _tree()
    found = False

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        function = node.func
        if not (
            isinstance(function, ast.Attribute)
            and function.attr == "merge"
        ):
            continue

        for keyword in node.keywords:
            if (
                keyword.arg == "graph_groups"
                and isinstance(keyword.value, ast.Name)
                and keyword.value.id
                == "graph_validation_groups"
            ):
                found = True

    assert found


def test_graph_validation_is_exposed_after_assignment():
    assignment_line = _assignment_lines(
        "graph_validation"
    )[0]

    context_lines = []
    for node in ast.walk(_tree()):
        if not isinstance(node, ast.Assign):
            continue

        for target in node.targets:
            if not isinstance(target, ast.Subscript):
                continue

            source = ast.get_source_segment(
                _text(),
                target,
            ) or ""

            if (
                'context.document["graph_validation"]'
                in source
            ):
                context_lines.append(node.lineno)

    assert context_lines
    assert all(
        line > assignment_line
        for line in context_lines
    )


def test_plugin_version_constant_exists():
    text = _text()

    assert 'VERSION = "' in text
