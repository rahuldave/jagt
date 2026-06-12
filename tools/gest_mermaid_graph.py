#!/usr/bin/env python3
"""Export Gest iteration/task relationships as a Mermaid HTML graph."""

from __future__ import annotations

import argparse
import html
import sqlite3
from dataclasses import dataclass
from pathlib import Path

LEGACY_DB = Path.home() / "Library/Application Support/gest/gest.db"
DEFAULT_SERVE_URL = "http://127.0.0.1:2300"


@dataclass(frozen=True)
class Iteration:
    id: str
    title: str
    status: str


@dataclass(frozen=True)
class Task:
    id: str
    title: str
    status: str
    priority: int | None


@dataclass(frozen=True)
class IterationTask:
    iteration_id: str
    task_id: str
    phase: int


@dataclass(frozen=True)
class Relationship:
    rel_type: str
    source_id: str
    source_type: str
    target_id: str
    target_type: str


def default_db_for(project_root: Path) -> Path:
    local_db = project_root.resolve() / ".gest" / "gest.db"
    if local_db.exists():
        return local_db
    return LEGACY_DB


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export the current Gest project's iteration/task graph as Mermaid HTML."
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=None,
        help=(
            "Gest SQLite database path. Default: <project-root>/.gest/gest.db "
            f"when present, otherwise {LEGACY_DB}"
        ),
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path.cwd(),
        help="Project root to resolve in Gest. Default: current directory.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("exports/gest/relationships.html"),
        help="HTML output path. Default: exports/gest/relationships.html",
    )
    parser.add_argument(
        "--serve-url",
        default=DEFAULT_SERVE_URL,
        help=f"Base URL for clickable gest serve links. Default: {DEFAULT_SERVE_URL}",
    )
    parser.add_argument(
        "--iteration",
        action="append",
        default=[],
        help="Only include an iteration ID or unique prefix. Can be repeated.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help=(
            "Include terminal iterations/tasks in project-wide graphs. "
            "Focused --iteration graphs include terminal tasks by default."
        ),
    )
    parser.add_argument(
        "--direction",
        choices=("TB", "TD", "BT", "LR", "RL"),
        default="TB",
        help="Mermaid flowchart direction. Default: TB, a vertical top-to-bottom graph.",
    )
    parser.add_argument(
        "--single-diagram",
        action="store_true",
        help=(
            "Render all selected iterations as one Mermaid diagram instead of "
            "stacked per-iteration sections."
        ),
    )
    return parser.parse_args()


def connect_read_only(db_path: Path) -> sqlite3.Connection:
    uri = f"file:{db_path}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def resolve_project_id(conn: sqlite3.Connection, root: Path) -> str:
    resolved = root.resolve()
    candidates = [str(resolved)]
    candidates.extend(str(parent) for parent in resolved.parents)

    for candidate in candidates:
        row = conn.execute("SELECT id FROM projects WHERE root = ?", (candidate,)).fetchone()
        if row:
            return row["id"]

        row = conn.execute(
            "SELECT project_id FROM project_workspaces WHERE path = ?",
            (candidate,),
        ).fetchone()
        if row:
            return row["project_id"]

    raise SystemExit(f"No Gest project found for {resolved}")


def resolve_iteration_ids(
    conn: sqlite3.Connection,
    project_id: str,
    prefixes: list[str],
) -> set[str] | None:
    if not prefixes:
        return None

    resolved: set[str] = set()
    for prefix in prefixes:
        rows = conn.execute(
            "SELECT id FROM iterations WHERE project_id = ? AND id LIKE ?",
            (project_id, f"{prefix}%"),
        ).fetchall()
        if not rows:
            raise SystemExit(f"No iteration matches prefix {prefix!r}")
        if len(rows) > 1:
            matches = ", ".join(row["id"][:8] for row in rows[:8])
            raise SystemExit(f"Iteration prefix {prefix!r} is ambiguous: {matches}")
        resolved.add(rows[0]["id"])
    return resolved


def fetch_graph(
    conn: sqlite3.Connection,
    project_id: str,
    include_all: bool,
    iteration_ids: set[str] | None,
) -> tuple[list[Iteration], dict[str, Task], list[IterationTask], list[Relationship]]:
    iter_filter = ""
    params: list[object] = [project_id]
    if not include_all:
        iter_filter = " AND status NOT IN ('completed', 'cancelled')"
    if iteration_ids is not None:
        marks = ",".join("?" for _ in iteration_ids)
        iter_filter += f" AND id IN ({marks})"
        params.extend(sorted(iteration_ids))

    iterations = [
        Iteration(row["id"], row["title"], row["status"])
        for row in conn.execute(
            f"""
            SELECT id, title, status
            FROM iterations
            WHERE project_id = ?{iter_filter}
            ORDER BY created_at, title
            """,
            params,
        )
    ]
    iter_ids = {iteration.id for iteration in iterations}

    if not iter_ids:
        return [], {}, [], []

    marks = ",".join("?" for _ in iter_ids)
    iteration_tasks = [
        IterationTask(row["iteration_id"], row["task_id"], row["phase"])
        for row in conn.execute(
            f"""
            SELECT iteration_id, task_id, phase
            FROM iteration_tasks
            WHERE iteration_id IN ({marks})
            ORDER BY iteration_id, phase, created_at
            """,
            sorted(iter_ids),
        )
    ]
    task_ids = {row.task_id for row in iteration_tasks}

    relationships: list[Relationship] = []
    if task_ids:
        marks = ",".join("?" for _ in task_ids)
        relationships = [
            Relationship(
                row["rel_type"],
                row["source_id"],
                row["source_type"],
                row["target_id"],
                row["target_type"],
            )
            for row in conn.execute(
                f"""
                SELECT rel_type, source_id, source_type, target_id, target_type
                FROM relationships
                WHERE (source_type = 'task' AND source_id IN ({marks}))
                   OR (target_type = 'task' AND target_id IN ({marks}))
                ORDER BY rel_type, created_at
                """,
                sorted(task_ids) + sorted(task_ids),
            )
        ]
        for rel in relationships:
            if rel.source_type == "task":
                task_ids.add(rel.source_id)
            if rel.target_type == "task":
                task_ids.add(rel.target_id)

    tasks: dict[str, Task] = {}
    if task_ids:
        marks = ",".join("?" for _ in task_ids)
        task_filter = "" if include_all else " AND status NOT IN ('done', 'cancelled')"
        rows = conn.execute(
            f"""
            SELECT id, title, status, priority
            FROM tasks
            WHERE project_id = ? AND id IN ({marks}){task_filter}
            ORDER BY created_at, title
            """,
            [project_id, *sorted(task_ids)],
        ).fetchall()
        tasks = {
            row["id"]: Task(row["id"], row["title"], row["status"], row["priority"])
            for row in rows
        }

    iteration_tasks = [row for row in iteration_tasks if row.task_id in tasks]
    relationships = [
        rel
        for rel in relationships
        if (rel.source_type != "task" or rel.source_id in tasks)
        and (rel.target_type != "task" or rel.target_id in tasks)
    ]
    return iterations, tasks, iteration_tasks, relationships


def node_id(kind: str, entity_id: str) -> str:
    return f"{kind}_{entity_id[:12]}"


def label(*parts: object) -> str:
    text = " | ".join(str(part) for part in parts if part is not None and str(part))
    return text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


def wrapped_title(title: str, max_words_per_line: int = 4) -> str:
    words = title.split()
    if len(words) <= max_words_per_line:
        return title

    lines = []
    for index in range(0, len(words), max_words_per_line):
        lines.append(" ".join(words[index : index + max_words_per_line]))
    return "<br/>".join(lines)


def mermaid_class_for_status(status: str) -> str:
    return {
        "active": "active",
        "open": "open",
        "in-progress": "progress",
        "done": "done",
        "completed": "done",
        "cancelled": "cancelled",
    }.get(status, "default")


def build_mermaid(
    iterations: list[Iteration],
    tasks: dict[str, Task],
    iteration_tasks: list[IterationTask],
    relationships: list[Relationship],
    serve_url: str,
    direction: str,
    stack_iterations: bool,
) -> str:
    lines = [
        f"flowchart {direction}",
        "  classDef iteration fill:#17324d,stroke:#67b7dc,color:#f6fbff;",
        "  classDef active fill:#15391f,stroke:#6fcf97,color:#f7fff9;",
        "  classDef open fill:#2f2f2f,stroke:#d6d6d6,color:#ffffff;",
        "  classDef progress fill:#463814,stroke:#f2c94c,color:#fff8db;",
        "  classDef done fill:#20382f,stroke:#7bd88f,color:#f1fff3;",
        "  classDef cancelled fill:#3d2525,stroke:#eb5757,color:#fff4f4;",
        "  classDef legend fill:#11161c,stroke:#6b7280,color:#e5e7eb;",
    ]

    previous_iteration_id: str | None = None
    for iteration in iterations:
        ident = node_id("I", iteration.id)
        iteration_label = label(
            iteration.id[:8],
            wrapped_title(iteration.title),
            iteration.status,
        )
        lines.append(
            f'  {ident}["{iteration_label}"]'
        )
        lines.append(f"  class {ident} iteration;")
        lines.append(f'  click {ident} "{serve_url.rstrip("/")}/iterations/{iteration.id}" _blank')
        if stack_iterations and previous_iteration_id is not None:
            lines.append(
                f'  {node_id("I", previous_iteration_id)} -. "next iteration" .-> {ident}'
            )
        previous_iteration_id = iteration.id

    for task in tasks.values():
        ident = node_id("T", task.id)
        priority = f"P{task.priority}" if task.priority is not None else None
        task_label = label(task.id[:8], wrapped_title(task.title), task.status, priority)
        lines.append(f'  {ident}["{task_label}"]')
        lines.append(f"  class {ident} {mermaid_class_for_status(task.status)};")
        lines.append(f'  click {ident} "{serve_url.rstrip("/")}/tasks/{task.id}" _blank')

    for row in iteration_tasks:
        if row.task_id not in tasks:
            continue
        iteration_node = node_id("I", row.iteration_id)
        task_node = node_id("T", row.task_id)
        lines.append(
            f'  {iteration_node} -- "phase {row.phase}" --> {task_node}'
        )

    for rel in relationships:
        if rel.source_type != "task" or rel.target_type != "task":
            continue
        if rel.source_id not in tasks or rel.target_id not in tasks:
            continue
        if rel.rel_type == "child-of":
            parent_node = node_id("T", rel.target_id)
            child_node = node_id("T", rel.source_id)
            lines.append(
                f'  {parent_node} -- "parent of" --> {child_node}'
            )
        else:
            source_node = node_id("T", rel.source_id)
            target_node = node_id("T", rel.target_id)
            lines.append(
                f'  {source_node} -- "{label(rel.rel_type)}" --> {target_node}'
            )

    return "\n".join(lines)


def related_phase_graph(
    iteration_id: str,
    phase: int,
    tasks: dict[str, Task],
    iteration_tasks: list[IterationTask],
    relationships: list[Relationship],
    serve_url: str,
    direction: str,
) -> str:
    selected_iteration_tasks = [
        row
        for row in iteration_tasks
        if row.iteration_id == iteration_id and row.phase == phase
    ]
    selected_task_ids = {row.task_id for row in selected_iteration_tasks}

    selected_relationships = [
        rel
        for rel in relationships
        if (rel.source_type != "task" or rel.source_id in selected_task_ids)
        or (rel.target_type != "task" or rel.target_id in selected_task_ids)
    ]
    for rel in selected_relationships:
        if rel.source_type == "task":
            selected_task_ids.add(rel.source_id)
        if rel.target_type == "task":
            selected_task_ids.add(rel.target_id)

    selected_tasks = {
        task_id: task
        for task_id, task in tasks.items()
        if task_id in selected_task_ids
    }
    selected_iteration_tasks = [
        row for row in selected_iteration_tasks if row.task_id in selected_tasks
    ]
    selected_relationships = [
        rel
        for rel in selected_relationships
        if (rel.source_type != "task" or rel.source_id in selected_tasks)
        and (rel.target_type != "task" or rel.target_id in selected_tasks)
    ]

    return build_mermaid(
        [],
        selected_tasks,
        [],
        selected_relationships,
        serve_url,
        direction,
        stack_iterations=False,
    )


def render_legend() -> str:
    return """<div class="legend" aria-label="Legend">
      <span><b class="swatch iteration"></b>iteration</span>
      <span><b class="swatch open"></b>open task</span>
      <span><b class="swatch progress"></b>in progress</span>
      <span><b class="swatch done"></b>done/completed</span>
      <span><b class="swatch cancelled"></b>cancelled</span>
      <span><b class="line solid"></b>relationship</span>
      <span><b class="line dashed"></b>iteration order</span>
    </div>"""


def render_html(
    title: str,
    graph: str | None,
    serve_url: str,
    sections: list[tuple[Iteration, list[tuple[int, str]]]] | None = None,
) -> str:
    escaped_graph = html.escape(graph) if graph is not None else ""
    section_html = ""
    if sections is not None:
        parts = []
        for iteration, phase_graphs in sections:
            phase_parts = []
            iteration_url = (
                f"{html.escape(serve_url.rstrip('/'))}/iterations/"
                f"{html.escape(iteration.id)}"
            )
            iteration_link = (
                f'<a href="{iteration_url}" target="_blank" rel="noreferrer">'
                f"{html.escape(iteration.id[:8])}</a>"
            )
            iteration_heading = (
                f"{iteration_link} {html.escape(iteration.title)} "
                f"<span>{html.escape(iteration.status)}</span>"
            )
            for phase, section_graph in phase_graphs:
                phase_parts.append(
                    f"""<div class="phase-section">
          <h3>Phase {phase}</h3>
          <div class="graph graph-compact">
            <pre class="mermaid">
{html.escape(section_graph)}
            </pre>
          </div>
        </div>"""
                )
            parts.append(
                f"""<section class="iteration-section">
        <div class="section-marker" aria-hidden="true"></div>
        <h2>{iteration_heading}</h2>
        {''.join(phase_parts)}
      </section>"""
            )
        section_html = "\n".join(parts)
    body_graph = (
        f'<div class="iteration-stack">{section_html}</div>'
        if sections is not None
        else f"""<div class="graph">
      <pre class="mermaid">
{escaped_graph}
      </pre>
    </div>"""
    )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg: #101214;
      --panel: #171a1f;
      --text: #f4f4f5;
      --muted: #9aa3ad;
      --line: #2c333a;
      --accent: #67b7dc;
    }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font: 14px/1.5 ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont,
        "Segoe UI", sans-serif;
    }}
    header {{
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      gap: 16px;
      padding: 18px 22px;
      border-bottom: 1px solid var(--line);
      background: var(--panel);
    }}
    h1 {{
      margin: 0;
      font-size: 18px;
      font-weight: 650;
      letter-spacing: 0;
    }}
    a {{ color: var(--accent); }}
    main {{ padding: 18px 22px 30px; }}
    .hint {{ color: var(--muted); }}
    .legend {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px 16px;
      align-items: center;
      margin: 0 0 16px;
      color: var(--muted);
    }}
    .legend span {{ display: inline-flex; align-items: center; gap: 6px; }}
    .swatch {{
      width: 12px;
      height: 12px;
      border-radius: 2px;
      display: inline-block;
      border: 1px solid #6b7280;
    }}
    .swatch.iteration {{ background: #17324d; border-color: #67b7dc; }}
    .swatch.open {{ background: #2f2f2f; border-color: #d6d6d6; }}
    .swatch.progress {{ background: #463814; border-color: #f2c94c; }}
    .swatch.done {{ background: #20382f; border-color: #7bd88f; }}
    .swatch.cancelled {{ background: #3d2525; border-color: #eb5757; }}
    .line {{
      width: 20px;
      height: 0;
      display: inline-block;
      border-top: 2px solid #9aa3ad;
    }}
    .line.dashed {{ border-top-style: dashed; }}
    .iteration-stack {{
      position: relative;
      margin-left: 14px;
      padding-left: 26px;
      border-left: 2px dashed #49515a;
    }}
    .iteration-section {{
      position: relative;
      margin: 0 0 22px;
    }}
    .section-marker {{
      position: absolute;
      left: -34px;
      top: 11px;
      width: 12px;
      height: 12px;
      border-radius: 50%;
      background: var(--accent);
      box-shadow: 0 0 0 4px var(--bg);
    }}
    .iteration-section h2 {{
      margin: 0 0 8px;
      font-size: 15px;
      font-weight: 650;
      letter-spacing: 0;
    }}
    .iteration-section h2 span {{
      color: var(--muted);
      font-weight: 500;
      margin-left: 6px;
    }}
    .phase-section {{
      margin: 10px 0 14px;
    }}
    .phase-section h3 {{
      margin: 0 0 6px;
      color: var(--muted);
      font-size: 13px;
      font-weight: 650;
      letter-spacing: 0;
    }}
    .graph {{
      overflow: auto;
      min-height: 70vh;
      padding: 16px;
      border: 1px solid var(--line);
      background: #0c0e10;
    }}
    .graph-compact {{
      min-height: 0;
    }}
  </style>
</head>
<body>
  <header>
    <h1>{html.escape(title)}</h1>
    <a href="{html.escape(serve_url.rstrip('/'))}" target="_blank" rel="noreferrer">gest serve</a>
  </header>
  <main>
    <p class="hint">
      Click any iteration or task node to open it in gest serve. Start it with
      <code>gest serve</code> if links do not load.
    </p>
    {render_legend()}
    {body_graph}
  </main>
  <script type="module">
    import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";
    mermaid.initialize({{ startOnLoad: true, theme: "dark", securityLevel: "loose" }});
  </script>
</body>
</html>
"""


def main() -> None:
    args = parse_args()
    args.project_root = args.project_root.resolve()
    if args.db is None:
        args.db = default_db_for(args.project_root)
    with connect_read_only(args.db) as conn:
        project_id = resolve_project_id(conn, args.project_root)
        iteration_ids = resolve_iteration_ids(conn, project_id, args.iteration)
        include_all = args.all or iteration_ids is not None
        iterations, tasks, iteration_tasks, relationships = fetch_graph(
            conn,
            project_id,
            include_all,
            iteration_ids,
        )

    graph = build_mermaid(
        iterations,
        tasks,
        iteration_tasks,
        relationships,
        args.serve_url,
        args.direction,
        stack_iterations=not args.single_diagram and args.direction in {"TB", "TD"},
    )
    sections = None
    if iteration_ids is None and len(iterations) > 1 and not args.single_diagram:
        phase_by_iteration: dict[str, list[int]] = {}
        for row in iteration_tasks:
            phase_by_iteration.setdefault(row.iteration_id, [])
            if row.phase not in phase_by_iteration[row.iteration_id]:
                phase_by_iteration[row.iteration_id].append(row.phase)

        sections = [
            (
                iteration,
                [
                    (
                        phase,
                        related_phase_graph(
                            iteration.id,
                            phase,
                            tasks,
                            iteration_tasks,
                            relationships,
                            args.serve_url,
                            args.direction,
                        ),
                    )
                    for phase in sorted(phase_by_iteration.get(iteration.id, []))
                ],
            )
            for iteration in iterations
        ]
        graph = None
    title = "Gest Relationship Graph"
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_html(title, graph, args.serve_url, sections), encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
