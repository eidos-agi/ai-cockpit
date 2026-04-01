"""cockpit — Launch pad for all your AI cockpits.

Usage:
    cockpit              Interactive TUI cockpit selector
    cockpit <name>       Open Claude Code (auto mode unlocked via Shift+Tab)
    cockpit <name> -a    Open IN auto mode (--permission-mode auto)
    cockpit <name> -y    Open with --dangerously-skip-permissions
    cockpit scan         Auto-discover cockpits in known directories
    cockpit status       Show version + capabilities for all cockpits
    cockpit upgrade <n>  Plan upgrade to latest schema (add --apply to execute)
    cockpit list         Non-interactive list
    cockpit add <path>   Register a cockpit manually
    cockpit remove <name> Remove from registry
    cockpit new <path>   Create a new cockpit from the template
    cockpit can-i-close  Check if all cockpits are safe to close (alias: cic)
    cockpit touch-and-go Commit & push all dirty cockpits (alias: tag)
    cockpit config       Show/edit configuration
    cockpit marketplace  Discover Claude Code plugins

Schema versions:
    v0  Pre-cockpit-cockpit (state.json only)
    v1  Has cockpit-settings.yaml + state.json
    v2  Has lifecycle skills + .visionlog/
    v3  Has trilogy (.visionlog/ + .research/ + .ike/)

All cockpits launch with --enable-auto-mode by default.
"""

import json
import os
import shutil
import subprocess
import sys
import traceback
from datetime import datetime
from pathlib import Path

CRASH_LOG = Path.home() / ".cockpit" / "cockpit-cockpit.log"
CONFIG_PATH = Path.home() / ".cockpit" / "config.json"


def log_crash(exc):
    """Append crash details to ~/.cockpit/crash.log"""
    CRASH_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(CRASH_LOG, "a") as f:
        f.write(f"\n{'=' * 60}\n")
        f.write(f"CRASH: {datetime.now().isoformat()}\n")
        f.write(f"Args:  {sys.argv}\n")
        f.write(f"{'=' * 60}\n")
        traceback.print_exception(type(exc), exc, exc.__traceback__, file=f)
        f.write("\n")


def load_config():
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text())
        except Exception:
            return {}
    return {}


def save_config(cfg):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2) + "\n")


def get_scan_dirs():
    cfg = load_config()
    dirs = cfg.get("scan_dirs", [])
    return [Path(d).expanduser() for d in dirs]


REGISTRY_PATH = Path.home() / ".cockpit" / "registry.json"


def load_registry():
    if REGISTRY_PATH.exists():
        return json.loads(REGISTRY_PATH.read_text())
    return {"cockpits": []}


def save_registry(reg):
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY_PATH.write_text(json.dumps(reg, indent=2) + "\n")


def read_state(path):
    state_file = Path(path) / "state.json"
    if not state_file.exists():
        return None
    try:
        data = json.loads(state_file.read_text())
        return data.get("cockpit", {})
    except Exception:
        return None


def read_settings(path):
    """Read cockpit-cockpit/cockpit-settings.yaml from a repo."""
    settings_file = Path(path) / "cockpit-cockpit" / "cockpit-settings.yaml"
    if not settings_file.exists():
        return None
    try:
        import yaml
        return yaml.safe_load(settings_file.read_text())
    except ImportError:
        data = {}
        for line in settings_file.read_text().splitlines():
            line = line.strip()
            if ":" in line and not line.startswith("#") and not line.startswith("-"):
                key, _, val = line.partition(":")
                val = val.strip()
                if val and not val.startswith("{") and not val.startswith("["):
                    data[key.strip()] = val
        return data
    except Exception:
        return None


def find_cockpit(reg, name):
    name_lower = name.lower()
    for c in reg["cockpits"]:
        if c["slug"] == name_lower or c["name"].lower() == name_lower:
            return c
    for c in reg["cockpits"]:
        if name_lower in c["slug"] or name_lower in c["name"].lower():
            return c
    return None


def slugify(name):
    return name.lower().replace(" ", "-").replace("_", "-")


# ─── Version Detection ────────────────────────────────────

CORE_SKILLS = ["takeoff", "land", "cockpit-status", "pre-flight", "cockpit-repair"]


def detect_capabilities(path):
    """Auto-detect what a cockpit has. Returns a dict of capability flags."""
    p = Path(path)
    caps = {
        "exists": p.exists(),
        "state_json": (p / "state.json").exists(),
        "settings_yaml": (p / "cockpit-cockpit" / "cockpit-settings.yaml").exists(),
        "skills_dir": (p / ".claude" / "skills").is_dir(),
        "skills": [],
        "visionlog": (p / ".visionlog").is_dir(),
        "research": (p / ".research").is_dir(),
        "ike": (p / ".ike").is_dir(),
        "claude_md": (p / "CLAUDE.md").exists(),
        "mcp_json": (p / ".mcp.json").exists(),
    }

    # Check which core skills exist
    skills_dir = p / ".claude" / "skills"
    if skills_dir.is_dir():
        for skill in CORE_SKILLS:
            skill_file = skills_dir / skill / "skill.md"
            if skill_file.exists():
                caps["skills"].append(skill)

    # Trilogy check
    caps["has_trilogy"] = all([caps["visionlog"], caps["research"], caps["ike"]])
    caps["core_skills_count"] = len(caps["skills"])
    caps["core_skills_complete"] = caps["core_skills_count"] == len(CORE_SKILLS)

    return caps


def detect_schema_version(path):
    """Compute observed schema version from capabilities."""
    caps = detect_capabilities(path)

    if not caps["exists"]:
        return -1, caps  # Missing

    # v3: has trilogy + settings
    if caps["has_trilogy"] and caps["settings_yaml"] and caps["core_skills_complete"]:
        return 3, caps

    # v2: has lifecycle skills + visionlog
    if caps["core_skills_count"] >= 3 and caps["visionlog"] and caps["settings_yaml"]:
        return 2, caps

    # v1: has settings yaml + state.json
    if caps["settings_yaml"] and caps["state_json"]:
        return 1, caps

    # v0: has state.json only (pre-cockpit-cockpit)
    if caps["state_json"]:
        return 0, caps

    return -1, caps  # Not a cockpit


def version_badge(observed, declared=None):
    """Return a colored version string."""
    if observed == -1:
        return "\033[31m✗ missing\033[0m"
    if observed == 0:
        return "\033[90mv0 (unmanaged)\033[0m"

    badge = f"\033[36mv{observed}\033[0m"
    if declared is not None and declared != observed:
        badge += f" \033[33m(declared v{declared})\033[0m"
    return badge


UPGRADE_STEPS = {
    # (from_version, to_version): list of (description, check_fn, apply_fn)
}


def plan_upgrade(path, current_version, target_version):
    """Plan upgrade steps from current to target version."""
    p = Path(path)
    steps = []

    if current_version < 1 and target_version >= 1:
        # v0 → v1: add cockpit-settings.yaml
        settings_dir = p / "cockpit-cockpit"
        if not (settings_dir / "cockpit-settings.yaml").exists():
            state = read_state(path) or {}
            name = state.get("name", p.name)
            steps.append({
                "version": 1,
                "action": "create",
                "path": str(settings_dir / "cockpit-settings.yaml"),
                "description": f"Create cockpit-settings.yaml (name: {name})",
            })

    if current_version < 2 and target_version >= 2:
        # v1 → v2: add lifecycle skills + visionlog
        skills_dir = p / ".claude" / "skills"
        for skill in CORE_SKILLS:
            skill_file = skills_dir / skill / "skill.md"
            if not skill_file.exists():
                steps.append({
                    "version": 2,
                    "action": "copy_skill",
                    "skill": skill,
                    "path": str(skill_file),
                    "description": f"Install skill: {skill}",
                })

        if not (p / ".visionlog").is_dir():
            steps.append({
                "version": 2,
                "action": "init_visionlog",
                "path": str(p / ".visionlog"),
                "description": "Initialize .visionlog/",
            })

    if current_version < 3 and target_version >= 3:
        # v2 → v3: add research + ike
        if not (p / ".research").is_dir():
            steps.append({
                "version": 3,
                "action": "init_research",
                "path": str(p / ".research"),
                "description": "Initialize .research/",
            })
        if not (p / ".ike").is_dir():
            steps.append({
                "version": 3,
                "action": "init_ike",
                "path": str(p / ".ike"),
                "description": "Initialize .ike/",
            })

    return steps


def _get_package_skills_dir():
    """Find the bundled skills directory from the ai-cockpit-template package."""
    # The package is installed from ai-cockpit-template repo.
    # Skills live at <repo>/.claude/skills/ relative to the package source.
    pkg_dir = Path(__file__).resolve().parent  # src/ai_cockpit/
    # Walk up: src/ai_cockpit -> src -> repo root
    repo_root = pkg_dir.parent.parent
    skills_dir = repo_root / ".claude" / "skills"
    if skills_dir.is_dir():
        return skills_dir
    return None


def apply_upgrade_step(step, cockpit_path):
    """Apply a single upgrade step. Returns True on success."""
    p = Path(cockpit_path)
    action = step["action"]
    reg_cockpits = load_registry().get("cockpits", [])

    if action == "create":
        # Create cockpit-settings.yaml
        target = Path(step["path"])
        target.parent.mkdir(parents=True, exist_ok=True)
        state = read_state(cockpit_path) or {}
        name = state.get("name", p.name)
        slug = slugify(name)
        org = state.get("org", p.parts[-2] if len(p.parts) > 2 else "unknown")
        content = f"""name: {name}
slug: {slug}
org: {org}
version: 1

claude:
  permission_mode: default

startup:
  command: /takeoff
"""
        target.write_text(content)
        return True

    elif action == "copy_skill":
        # Copy skill from the ai-cockpit package's bundled skills
        skill = step["skill"]
        target = Path(step["path"])

        template_sources = []
        # First: check the package's own bundled skills
        pkg_skills = _get_package_skills_dir()
        if pkg_skills:
            template_skills = pkg_skills / skill / "skill.md"
            template_sources.append(template_skills)
        # Also check registered cockpits for skill sources
        for existing in reg_cockpits:
            src = Path(existing["path"]) / ".claude" / "skills" / skill / "skill.md"
            if src.exists():
                template_sources.append(src)
                break

        for src in template_sources:
            if src.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(src.read_text())
                return True
        # Create placeholder if no template found
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f"# {skill}\n\nTODO: Configure this skill.\n")
        return True

    elif action in ("init_visionlog", "init_research", "init_ike"):
        # Just create the directory — MCP tools will initialize properly on first use
        target = Path(step["path"])
        target.mkdir(parents=True, exist_ok=True)
        return True

    return False


def build_claude_cmd(cockpit, mode=None):
    """Build the claude command from cockpit settings."""
    path = cockpit["path"]
    settings = read_settings(path) or {}
    claude_cfg = settings.get("claude", {}) if isinstance(settings.get("claude"), dict) else {}
    startup = settings.get("startup", {}) if isinstance(settings.get("startup"), dict) else {}

    cmd = ["claude"]

    if mode == "auto":
        cmd.extend(["--permission-mode", "auto"])
    elif mode == "yolo":
        cmd.append("--dangerously-skip-permissions")
    elif mode is None:
        pm = claude_cfg.get("permission_mode", "default")
        if pm == "auto":
            cmd.extend(["--permission-mode", "auto"])
        elif pm == "bypassPermissions":
            cmd.append("--dangerously-skip-permissions")
        elif pm != "default":
            cmd.extend(["--permission-mode", pm])
        if "--permission-mode" not in cmd and "--dangerously-skip-permissions" not in cmd:
            cmd.append("--enable-auto-mode")

    if claude_cfg.get("model"):
        cmd.extend(["--model", claude_cfg["model"]])
    if claude_cfg.get("effort"):
        cmd.extend(["--effort", claude_cfg["effort"]])
    if claude_cfg.get("chrome"):
        cmd.append("--chrome")
    for d in claude_cfg.get("add_dirs", []):
        cmd.extend(["--add-dir", d])
    for t in claude_cfg.get("allowed_tools", []):
        cmd.extend(["--allowed-tools", t])

    if startup.get("command"):
        cmd.append(startup["command"])
    elif startup.get("prompt"):
        cmd.append(startup["prompt"])

    return cmd, startup.get("command")


def launch_cockpit(cockpit, mode=None):
    """Launch Claude Code in a cockpit directory."""
    path = cockpit["path"]
    if not Path(path).exists():
        print(f"  \033[31mPath missing:\033[0m {path}")
        sys.exit(1)

    cmd, startup_cmd = build_claude_cmd(cockpit, mode)

    print(f"\n  \033[36m→\033[0m Opening \033[1m{cockpit['name']}\033[0m")
    print(f"  \033[90m{path}\033[0m")
    if mode:
        print(f"  \033[33mMode: {mode}\033[0m")
    else:
        print(f"  \033[90mAuto mode: unlocked (Shift+Tab)\033[0m")
    if startup_cmd:
        print(f"  \033[90mStartup: {startup_cmd}\033[0m")
    print()

    os.chdir(path)
    os.execvp("claude", cmd)


# ─── TUI ──────────────────────────────────────────────────


def run_tui(reg):
    """Interactive Textual TUI — two-pane cockpit selector with number-key navigation."""
    from textual.app import App, ComposeResult
    from textual.containers import Horizontal, Vertical, VerticalScroll
    from textual.widgets import Footer, Header, ListItem, ListView, Static
    from textual.binding import Binding

    cockpits = reg["cockpits"]
    if not cockpits:
        print("  No cockpits registered. Run: cockpit scan")
        return

    # Flat ordered list, grouped by org
    ordered = []
    orgs = {}
    for c in cockpits:
        orgs.setdefault(c.get("org", "unknown"), []).append(c)
    for org in sorted(orgs.keys()):
        for c in sorted(orgs[org], key=lambda x: x["name"]):
            ordered.append(c)

    scan_dirs = get_scan_dirs()

    # Check dirty repos per org directory (scan all git repos in each scan dir)
    def scan_dirty_repos(scan_dir):
        """Return list of (repo_name, dirty_file_count) for dirty repos in a directory."""
        dirty = []
        if not scan_dir.exists():
            return dirty
        for child in sorted(scan_dir.iterdir()):
            if not child.is_dir() or not (child / ".git").exists():
                continue
            try:
                result = subprocess.run(
                    ["git", "status", "--porcelain"],
                    cwd=child, capture_output=True, text=True, timeout=3,
                )
                lines = result.stdout.strip().splitlines() if result.stdout.strip() else []
                if lines:
                    dirty.append((child.name, len(lines)))
            except Exception:
                pass
        return dirty

    # Map org names to scan dirs
    org_to_scan_dir = {}
    for c in cockpits:
        org = c.get("org", "unknown")
        p = Path(c["path"])
        parent = p.parent
        if parent in scan_dirs:
            org_to_scan_dir[org] = parent

    # Scan each org's directory for dirty repos
    org_dirty_repos = {}  # org -> [(repo_name, file_count), ...]
    seen_dirs = set()
    for org, scan_dir in org_to_scan_dir.items():
        if scan_dir in seen_dirs:
            # Multiple orgs from same dir — merge
            for existing_org, existing_dir in org_to_scan_dir.items():
                if existing_dir == scan_dir and existing_org in org_dirty_repos:
                    org_dirty_repos[org] = org_dirty_repos[existing_org]
                    break
            else:
                org_dirty_repos[org] = scan_dirty_repos(scan_dir)
        else:
            org_dirty_repos[org] = scan_dirty_repos(scan_dir)
            seen_dirs.add(scan_dir)

    selected_cockpit = [None]
    selected_mode = [None]

    def esc(text):
        return str(text).replace("[", "\\[")

    def build_preview(c):
        if c is None:
            return ""

        settings = read_settings(c["path"]) or {}
        claude_cfg = settings.get("claude", {}) if isinstance(settings.get("claude"), dict) else {}
        startup = settings.get("startup", {}) if isinstance(settings.get("startup"), dict) else {}
        state = read_state(c["path"]) or {}

        lines = []
        lines.append(f"[bold cyan]{esc(c['name'])}[/bold cyan]")
        if c.get("description"):
            lines.append(f"[dim]{esc(c['description'])}[/dim]")
        lines.append("")
        lines.append(f"[bold]Path[/bold]   {esc(c['path'])}")
        lines.append(f"[bold]Org[/bold]    {esc(c.get('org', 'unknown'))}")
        lines.append(f"[bold]Slug[/bold]   {esc(c['slug'])}")
        exists = Path(c["path"]).exists()
        lines.append(f"[bold]Status[/bold] {'[green]● available[/green]' if exists else '[red]✗ missing[/red]'}")
        lines.append("")

        if claude_cfg:
            lines.append("[bold yellow]━━ Claude Settings ━━[/bold yellow]")
            pm = claude_cfg.get("permission_mode", "default")
            lines.append(f"  Permission  {pm}")
            if claude_cfg.get("effort"):
                lines.append(f"  Effort      {claude_cfg['effort']}")
            if claude_cfg.get("model"):
                lines.append(f"  Model       {claude_cfg['model']}")
            if claude_cfg.get("chrome"):
                lines.append(f"  Chrome      [green]enabled[/green]")
            lines.append("")

        if startup.get("command") or startup.get("prompt"):
            lines.append("[bold green]━━ Startup ━━[/bold green]")
            if startup.get("command"):
                lines.append(f"  Command     {esc(startup['command'])}")
            if startup.get("prompt"):
                lines.append(f"  Prompt      {esc(startup['prompt'])}")
            lines.append("")

        if state:
            lines.append("[bold blue]━━ Cockpit State ━━[/bold blue]")
            if state.get("version"):
                lines.append(f"  Version     {state['version']}")
            if state.get("template"):
                lines.append(f"  Template    {esc(state['template'])}")
            lines.append("")

        # Read watermarks from state.json
        state_file = Path(c["path"]) / "state.json"
        if state_file.exists():
            try:
                full_state = json.loads(state_file.read_text())
                wm = full_state.get("watermarks", {})
                counters = full_state.get("counters", {})
                if wm.get("last_takeoff"):
                    lines.append(f"[bold magenta]━━ Activity ━━[/bold magenta]")
                    lines.append(f"  Last takeoff  {wm['last_takeoff'][:16]}")
                if wm.get("last_land"):
                    lines.append(f"  Last landing  {wm['last_land'][:16]}")
                if counters.get("sessions"):
                    lines.append(f"  Sessions      {counters['sessions']}")
                if any(wm.values()) or any(counters.values()):
                    lines.append("")
            except Exception:
                pass

        tags = settings.get("tags", [])
        if tags and isinstance(tags, list):
            lines.append(f"[bold]Tags[/bold]   {', '.join(str(t) for t in tags)}")

        # Show the claude command that would be built
        cmd, _ = build_claude_cmd(c)
        lines.append("")
        lines.append("[bold]━━ Launch Command ━━[/bold]")
        lines.append(f"  [dim]{' '.join(cmd)}[/dim]")

        return "\n".join(lines)

    class OrgHeader(ListItem):
        """Non-selectable org group header."""
        def __init__(self, org_name, cockpit_count, dirty_repos, **kwargs):
            super().__init__(**kwargs)
            self.org_name = org_name
            self.cockpit_count = cockpit_count
            self.dirty_repos = dirty_repos  # list of (repo_name, file_count)
            self.cockpit_data = None

        def compose(self):
            n_dirty = len(self.dirty_repos)
            dirty_tag = f"  [bold red]{n_dirty} dirty repos[/bold red]" if n_dirty else "  [green]clean[/green]"
            yield Static(
                f"\n [bold]{esc(self.org_name)}[/bold]  [dim]{self.cockpit_count} cockpits[/dim]{dirty_tag}",
                markup=True,
            )

    class NavItem(ListItem):
        def __init__(self, number, cockpit_data, **kwargs):
            super().__init__(**kwargs)
            self.number = number
            self.cockpit_data = cockpit_data

        def compose(self):
            c = self.cockpit_data
            exists = Path(c["path"]).exists()
            dot = "[green]●[/green]" if exists else "[red]✗[/red]"
            gear = "[cyan]⚙[/cyan]" if c.get("has_settings") else " "
            num = f"[bold yellow]{self.number}[/bold yellow]"
            name = f"[bold]{esc(c['slug'])}[/bold]"
            subtitle = f"[dim]{esc(c['name'])}[/dim]" if c['name'] != c['slug'] else ""
            yield Static(f"   {num}  {dot} {gear} {name}  {subtitle}", markup=True)

    from textual.theme import Theme as TextualTheme

    THEME_DEFS = [
        TextualTheme(name="eidos", primary="#c4935a", secondary="#7a8c72", accent="#b8c4a0",
                     background="#1e1a17", surface="#161210", panel="#2a2420",
                     error="#c4694f", warning="#c4935a", success="#7a8c72"),
        TextualTheme(name="eidos-light", primary="#9a6d35", secondary="#5a6c52", accent="#4a6a3a",
                     background="#f0ebe4", surface="#e4ded6", panel="#d8d2c8", dark=False,
                     error="#c4694f", warning="#9a6d35", success="#5a6c52"),
        TextualTheme(name="cockpit-dark", primary="#58a6ff", secondary="#3fb950", accent="#d29922",
                     background="#0d1117", surface="#161b22", panel="#1c2128"),
        TextualTheme(name="midnight", primary="#7c3aed", secondary="#06b6d4", accent="#f59e0b",
                     background="#0f0a1a", surface="#1a1028", panel="#231838"),
        TextualTheme(name="ocean", primary="#0ea5e9", secondary="#10b981", accent="#f97316",
                     background="#042f2e", surface="#083344", panel="#0c4a6e"),
        TextualTheme(name="ember", primary="#ef4444", secondary="#f97316", accent="#eab308",
                     background="#1c1008", surface="#27180a", panel="#362010"),
        TextualTheme(name="forest", primary="#22c55e", secondary="#84cc16", accent="#06b6d4",
                     background="#052e16", surface="#0a3d1f", panel="#14532d"),
        TextualTheme(name="mono", primary="#a1a1aa", secondary="#71717a", accent="#e4e4e7",
                     background="#09090b", surface="#18181b", panel="#27272a"),
        TextualTheme(name="daylight", primary="#2563eb", secondary="#16a34a", accent="#d97706",
                     background="#ffffff", surface="#f8fafc", panel="#f1f5f9", dark=False),
        TextualTheme(name="paper", primary="#1e293b", secondary="#475569", accent="#0891b2",
                     background="#fafaf9", surface="#f5f5f4", panel="#e7e5e4", dark=False),
        TextualTheme(name="sand", primary="#92400e", secondary="#166534", accent="#1e40af",
                     background="#fefce8", surface="#fef9c3", panel="#fef08a", dark=False),
    ]

    current_theme_idx = [0]

    class CockpitApp(App):
        CSS = """
        Screen { layout: horizontal; }
        #nav-pane {
            width: 40%;
            border-right: heavy $primary;
            padding: 1;
            background: $surface;
        }
        #preview-pane {
            width: 60%;
            padding: 1 2;
            overflow-y: auto;
        }
        ListView { height: 100%; }
        ListItem { padding: 0; height: 2; }
        ListItem:hover { background: $boost; }
        ListView > ListItem.--highlight { background: $primary 25%; }
        """

        TITLE = "cockpit-cockpit"

        def on_mount(self):
            # Register custom themes
            for t in THEME_DEFS:
                self.register_theme(t)
            self.theme = THEME_DEFS[0].name

            lv = self.query_one("#nav-list", ListView)
            if ordered:
                lv.index = 0
                self.query_one("#preview", Static).update(build_preview(ordered[0]))

        def _handle_exception(self, error: Exception) -> None:
            log_crash(error)
            self.notify(f"Crash logged: {type(error).__name__}", severity="error")
            super()._handle_exception(error)

        BINDINGS = [
            Binding("enter", "launch", "Open"),
            Binding("a", "launch_auto", "Auto"),
            Binding("y", "launch_yolo", "Bypass"),
            Binding("t", "cycle_theme", "Theme"),
            Binding("s", "scan", "Scan"),
            Binding("q", "quit", "Quit"),
            Binding("escape", "quit", "Quit"),
        ]

        def compose(self) -> ComposeResult:
            yield Header()
            # Build list items grouped by org with headers
            items = []
            num = 1
            for org in sorted(orgs.keys()):
                items.append(OrgHeader(org, len(orgs[org]), org_dirty_repos.get(org, [])))
                for c in sorted(orgs[org], key=lambda x: x["name"]):
                    items.append(NavItem(num, c))
                    num += 1
            with Horizontal():
                with Vertical(id="nav-pane"):
                    yield ListView(*items, id="nav-list")
                with VerticalScroll(id="preview-pane"):
                    yield Static(id="preview")
            yield Footer()

        def on_key(self, event):
            # Number keys for instant selection (1-9)
            if event.character and event.character.isdigit() and event.character != "0":
                num = int(event.character) - 1
                if 0 <= num < len(ordered):
                    lv = self.query_one("#nav-list", ListView)
                    lv.index = num
                    self.query_one("#preview", Static).update(build_preview(ordered[num]))

        def on_list_view_highlighted(self, event):
            if not event.item:
                return
            if hasattr(event.item, "cockpit_data") and event.item.cockpit_data:
                self.query_one("#preview", Static).update(
                    build_preview(event.item.cockpit_data)
                )
            elif hasattr(event.item, "dirty_repos"):
                # Org header selected — show dirty repos for this org
                lines = [f"[bold]{esc(event.item.org_name)}[/bold]", ""]
                dr = event.item.dirty_repos
                if dr:
                    lines.append(f"[bold red]{len(dr)} dirty repos:[/bold red]")
                    for repo_name, file_count in sorted(dr):
                        lines.append(f"  [yellow]●[/yellow] {esc(repo_name)}  [dim]{file_count} files[/dim]")
                else:
                    lines.append("[green]All repos clean[/green]")
                self.query_one("#preview", Static).update("\n".join(lines))

        def _get_selected(self):
            lv = self.query_one("#nav-list", ListView)
            if lv.highlighted_child and hasattr(lv.highlighted_child, "cockpit_data"):
                return lv.highlighted_child.cockpit_data
            return None

        def action_launch(self):
            c = self._get_selected()
            if c:
                selected_cockpit[0] = c
                selected_mode[0] = None
                self.exit()

        def action_launch_auto(self):
            c = self._get_selected()
            if c:
                selected_cockpit[0] = c
                selected_mode[0] = "auto"
                self.exit()

        def action_launch_yolo(self):
            c = self._get_selected()
            if c:
                selected_cockpit[0] = c
                selected_mode[0] = "yolo"
                self.exit()

        def action_cycle_theme(self):
            current_theme_idx[0] = (current_theme_idx[0] + 1) % len(THEME_DEFS)
            t = THEME_DEFS[current_theme_idx[0]]
            self.theme = t.name
            self.notify(f"Theme: {t.name}")

        def action_scan(self):
            cmd_scan(reg)
            self.notify(f"Rescanned. {len(reg['cockpits'])} cockpits.")

    app = CockpitApp()
    try:
        app.run()
    except Exception as exc:
        log_crash(exc)
        print(f"\n  \033[31mTUI crash logged to {CRASH_LOG}\033[0m")
        print(f"  \033[90m{type(exc).__name__}: {exc}\033[0m\n")

    # Also check if Textual captured an exception internally
    if hasattr(app, "_exception") and app._exception is not None:
        log_crash(app._exception)
        print(f"\n  \033[31mTextual error logged to {CRASH_LOG}\033[0m")
        print(f"  \033[90m{type(app._exception).__name__}: {app._exception}\033[0m\n")

    if selected_cockpit[0]:
        launch_cockpit(selected_cockpit[0], selected_mode[0])


# ─── Commands ─────────────────────────────────────────────


def cmd_list(reg):
    cockpits = reg["cockpits"]
    if not cockpits:
        print("  No cockpits registered. Run: cockpit scan")
        return

    print()
    print("  \033[1m\033[36mCOCKPITS\033[0m")
    print()

    orgs = {}
    for c in cockpits:
        org = c.get("org", "unknown")
        orgs.setdefault(org, []).append(c)

    for org, items in sorted(orgs.items()):
        print(f"  \033[90m{org}\033[0m")
        for c in sorted(items, key=lambda x: x["name"]):
            exists = Path(c["path"]).exists()
            status = "\033[32m●\033[0m" if exists else "\033[31m✗\033[0m"
            slug = f"\033[1m{c['slug']}\033[0m"
            name = c["name"]
            print(f"    {status} {slug:<30s} {name}")
        print()

    print(f"  \033[90m{len(cockpits)} cockpits registered\033[0m")
    print(f"  \033[90mOpen: cockpit <name>  |  Auto mode: -a  |  Bypass: -y  |  All have Shift+Tab auto\033[0m")
    print()


def cmd_add(reg, path_str):
    path = Path(path_str).resolve()
    state = read_state(path)
    settings = read_settings(path)
    if not state and not settings:
        print(f"  \033[31mNo state.json or cockpit-settings.yaml at:\033[0m {path}")
        sys.exit(1)

    if settings:
        name = settings.get("name", path.name)
        slug = settings.get("slug", slugify(name))
        org = settings.get("org", path.parts[-2] if len(path.parts) > 2 else "unknown")
        desc = settings.get("description", "")
    else:
        name = state.get("name", path.name)
        slug = slugify(name)
        org = state.get("org", path.parts[-2] if len(path.parts) > 2 else "unknown")
        desc = ""

    for c in reg["cockpits"]:
        if c["path"] == str(path):
            print(f"  \033[33mAlready registered:\033[0m {name} ({slug})")
            return

    reg["cockpits"].append({
        "name": name,
        "slug": slug,
        "path": str(path),
        "org": org,
        "description": desc,
        "has_settings": settings is not None,
    })
    save_registry(reg)
    print(f"  \033[32m+\033[0m {name} ({slug}) → {path}")


def cmd_scan(reg):
    scan_dirs = get_scan_dirs()
    if not scan_dirs:
        print("  No scan directories configured.")
        print("  Add one with: cockpit config --add-scan-dir ~/my-repos")
        return

    found = 0
    for scan_dir in scan_dirs:
        if not scan_dir.exists():
            continue
        for child in sorted(scan_dir.iterdir()):
            if not child.is_dir():
                continue

            settings = read_settings(child)
            state = read_state(child)

            if not settings and not (state and state.get("name")):
                continue

            already = any(c["path"] == str(child) for c in reg["cockpits"])
            if already:
                continue

            if settings:
                name = settings.get("name", child.name)
                slug = settings.get("slug", slugify(name))
                org = settings.get("org", scan_dir.name)
                desc = settings.get("description", "")
            else:
                name = state["name"]
                slug = slugify(name)
                org = state.get("org", scan_dir.name)
                desc = ""

            reg["cockpits"].append({
                "name": name,
                "slug": slug,
                "path": str(child),
                "org": org,
                "description": desc,
                "has_settings": settings is not None,
            })
            marker = "\033[36m⚙\033[0m" if settings else "\033[90m○\033[0m"
            print(f"  \033[32m+\033[0m {marker} {name} ({slug}) → {child}")
            found += 1

    save_registry(reg)
    total = len(reg["cockpits"])
    print(f"\n  \033[90mFound {found} new, {total} total\033[0m")

    # Marketplace hint if no marketplace configured
    cfg = load_config()
    if not cfg.get("marketplace_seen"):
        print(f"\n  \033[90mTip: Run `cockpit marketplace` to discover Claude Code plugins\033[0m")


def cmd_status(reg):
    """Show version and capabilities for all cockpits."""
    cockpits = reg["cockpits"]
    if not cockpits:
        print("  No cockpits registered. Run: cockpit scan")
        return

    print()
    print("  \033[1m\033[36mCOCKPIT STATUS\033[0m")
    print()
    print(f"  {'NAME':<28s} {'VERSION':<22s} {'SKILLS':<10s} {'TRILOGY':<10s} {'SETTINGS'}")
    print(f"  {'─' * 28} {'─' * 22} {'─' * 10} {'─' * 10} {'─' * 10}")

    for c in sorted(cockpits, key=lambda x: (x.get("org", ""), x["name"])):
        observed, caps = detect_schema_version(c["path"])
        settings = read_settings(c["path"]) or {}
        declared = settings.get("version")

        name = c["slug"][:26]
        ver = version_badge(observed, declared)

        skills_n = caps.get("core_skills_count", 0)
        skills_total = len(CORE_SKILLS)
        if skills_n == skills_total:
            skills_str = f"\033[32m{skills_n}/{skills_total}\033[0m"
        elif skills_n > 0:
            skills_str = f"\033[33m{skills_n}/{skills_total}\033[0m"
        else:
            skills_str = f"\033[90m0/{skills_total}\033[0m"

        trilogy_parts = sum([caps.get("visionlog", False), caps.get("research", False), caps.get("ike", False)])
        if trilogy_parts == 3:
            trilogy_str = "\033[32m3/3\033[0m"
        elif trilogy_parts > 0:
            trilogy_str = f"\033[33m{trilogy_parts}/3\033[0m"
        else:
            trilogy_str = "\033[90m0/3\033[0m"

        has_settings = "\033[32m⚙\033[0m" if caps.get("settings_yaml") else "\033[90m-\033[0m"

        print(f"  {name:<28s} {ver:<32s} {skills_str:<20s} {trilogy_str:<20s} {has_settings}")

    print()
    print(f"  \033[90mUpgrade: cockpit upgrade <name> [--plan|--apply]\033[0m")
    print()


def cmd_upgrade(reg, name, dry_run=True):
    """Upgrade a cockpit to the latest schema version."""
    c = find_cockpit(reg, name)
    if not c:
        print(f"  \033[31mNot found:\033[0m {name}")
        sys.exit(1)

    path = c["path"]
    observed, caps = detect_schema_version(path)
    target = 3  # Latest version

    if observed >= target:
        print(f"  \033[32m{c['name']} is already at v{observed} (latest)\033[0m")
        return

    steps = plan_upgrade(path, observed, target)
    if not steps:
        print(f"  \033[32mNo upgrade steps needed\033[0m")
        return

    print()
    print(f"  \033[1m\033[36mUPGRADE PLAN: {c['name']}\033[0m")
    print(f"  \033[90mv{observed} → v{target}\033[0m")
    print()

    for i, step in enumerate(steps):
        marker = f"\033[33mv{step['version']}\033[0m"
        print(f"  {i + 1}. [{marker}] {step['description']}")
        print(f"     \033[90m→ {step['path']}\033[0m")

    print()

    if dry_run:
        print(f"  \033[90mThis is a plan. Run with --apply to execute.\033[0m")
        print(f"  \033[90m  cockpit upgrade {c['slug']} --apply\033[0m")
        return

    # Check git status
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"], cwd=path,
            capture_output=True, text=True, timeout=3,
        )
        if result.stdout.strip():
            print(f"  \033[33mWarning: working tree is dirty ({len(result.stdout.strip().splitlines())} files)\033[0m")
    except Exception:
        pass

    # Apply steps
    for i, step in enumerate(steps):
        success = apply_upgrade_step(step, path)
        status = "\033[32m✓\033[0m" if success else "\033[31m✗\033[0m"
        print(f"  {status} {step['description']}")

    # Update declared version in settings
    settings_file = Path(path) / "cockpit-cockpit" / "cockpit-settings.yaml"
    if settings_file.exists():
        content = settings_file.read_text()
        if "version:" in content:
            import re
            content = re.sub(r'version:\s*\S+', f'version: {target}', content, count=1)
        else:
            content += f"\nversion: {target}\n"
        settings_file.write_text(content)

    print()
    new_observed, _ = detect_schema_version(path)
    print(f"  \033[32mUpgraded to v{new_observed}\033[0m")
    print()


def cmd_remove(reg, name):
    c = find_cockpit(reg, name)
    if not c:
        print(f"  \033[31mNot found:\033[0m {name}")
        sys.exit(1)

    reg["cockpits"] = [x for x in reg["cockpits"] if x["slug"] != c["slug"]]
    save_registry(reg)
    print(f"  \033[31m-\033[0m Removed {c['name']} ({c['slug']})")


def cmd_config(args):
    """Show or edit cockpit configuration."""
    cfg = load_config()

    if "--add-scan-dir" in args:
        idx = args.index("--add-scan-dir")
        if idx + 1 >= len(args):
            print("  \033[31mUsage: cockpit config --add-scan-dir <path>\033[0m")
            sys.exit(1)
        new_dir = args[idx + 1]
        dirs = cfg.get("scan_dirs", [])
        # Normalize: expand ~ but store as given
        resolved = str(Path(new_dir).expanduser().resolve())
        # Store the user-provided form
        if new_dir not in dirs and resolved not in dirs:
            dirs.append(new_dir)
            cfg["scan_dirs"] = dirs
            save_config(cfg)
            print(f"  \033[32m+\033[0m Added scan directory: {new_dir}")
        else:
            print(f"  \033[33mAlready configured:\033[0m {new_dir}")
        return

    if "--remove-scan-dir" in args:
        idx = args.index("--remove-scan-dir")
        if idx + 1 >= len(args):
            print("  \033[31mUsage: cockpit config --remove-scan-dir <path>\033[0m")
            sys.exit(1)
        rm_dir = args[idx + 1]
        dirs = cfg.get("scan_dirs", [])
        resolved = str(Path(rm_dir).expanduser().resolve())
        new_dirs = [d for d in dirs if d != rm_dir and str(Path(d).expanduser().resolve()) != resolved]
        if len(new_dirs) < len(dirs):
            cfg["scan_dirs"] = new_dirs
            save_config(cfg)
            print(f"  \033[31m-\033[0m Removed scan directory: {rm_dir}")
        else:
            print(f"  \033[33mNot found:\033[0m {rm_dir}")
        return

    # Show current config
    print()
    print("  \033[1m\033[36mCOCKPIT CONFIG\033[0m")
    print(f"  \033[90m{CONFIG_PATH}\033[0m")
    print()

    dirs = cfg.get("scan_dirs", [])
    if dirs:
        print("  \033[1mScan directories:\033[0m")
        for d in dirs:
            p = Path(d).expanduser()
            exists = p.exists()
            status = "\033[32m●\033[0m" if exists else "\033[31m✗\033[0m"
            print(f"    {status} {d}")
    else:
        print("  \033[90mNo scan directories configured.\033[0m")
        print("  \033[90mAdd one with: cockpit config --add-scan-dir ~/my-repos\033[0m")

    print()


def cmd_new(args):
    """Create a new cockpit from the template."""
    TEMPLATE_DIR = Path(__file__).parent / "template"

    if not TEMPLATE_DIR.exists():
        print("  \033[31mTemplate files not found in package.\033[0m")
        print("  Reinstall: pip install ai-cockpit")
        sys.exit(1)

    # Parse args
    github = "--github" in args
    path_args = [a for a in args if not a.startswith("--")]

    if not path_args:
        print()
        print("  \033[1m\033[36mCreate a new cockpit\033[0m")
        print()
        print("  Usage: cockpit new <path> [--github]")
        print()
        print("  Examples:")
        print("    cockpit new ~/repos/my-planning-cockpit")
        print("    cockpit new ./ops-cockpit --github")
        print()
        print("  This creates a ready-to-fly cockpit with:")
        print("    - /takeoff, /land, /cockpit-status skills")
        print("    - state.json for session tracking")
        print("    - CLAUDE.md template with placeholder sections to fill in")
        print("    - Git repo initialized")
        print()
        print("  After creating, customize CLAUDE.md with your role context,")
        print("  then run: cockpit <name>")
        print()
        return

    target = Path(path_args[0]).expanduser().resolve()

    if target.exists() and any(target.iterdir()):
        print(f"  \033[31mDirectory not empty:\033[0m {target}")
        sys.exit(1)

    # Interactive setup
    print()
    print("  \033[1m\033[36mNew Cockpit\033[0m")
    print()

    name = target.name
    try:
        name_input = input(f"  Name [{name}]: ").strip()
        if name_input:
            name = name_input

        org = target.parent.name
        org_input = input(f"  Org [{org}]: ").strip()
        if org_input:
            org = org_input

        description = input("  Description (optional): ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n  Cancelled.")
        return

    slug = name.lower().replace(" ", "-").replace("_", "-")

    # Copy template
    print()
    print(f"  \033[90mScaffolding {target}...\033[0m")
    target.mkdir(parents=True, exist_ok=True)

    # Copy skills
    src_skills = TEMPLATE_DIR / ".claude" / "skills"
    dst_skills = target / ".claude" / "skills"
    if src_skills.exists():
        shutil.copytree(src_skills, dst_skills, dirs_exist_ok=True)
        skill_count = len(list(dst_skills.iterdir()))
        print(f"  \033[32m+\033[0m {skill_count} skills installed")

    # Copy tools
    src_tools = TEMPLATE_DIR / "tools"
    if src_tools.exists():
        shutil.copytree(src_tools, target / "tools", dirs_exist_ok=True)

    # Write state.json
    today = datetime.now().strftime("%Y-%m-%d")
    state = {
        "cockpit": {
            "name": name,
            "version": "1.3.0",
            "template": "eidos-agi/ai-cockpit-template",
            "template_version": "v0.1.0",
            "created": today,
        },
        "theme": {
            "primary": "#3fb950",
            "danger": "#f85149",
            "warning": "#d29922",
            "bg": "#0d1117",
            "surface": "#161b22",
            "text": "#e6edf3",
            "muted": "#8b949e",
        },
        "watermarks": {
            "last_takeoff": None,
            "last_land": None,
            "last_status_check": None,
        },
        "counters": {"sessions": 0, "takeoffs": 0, "landings": 0},
        "custom": {},
    }
    (target / "state.json").write_text(json.dumps(state, indent=2) + "\n")
    print("  \033[32m+\033[0m state.json")

    # Write CLAUDE.md from template
    claude_md = (TEMPLATE_DIR / "CLAUDE.md").read_text()
    claude_md = claude_md.replace("[YOUR ROLE]", name)
    claude_md = claude_md.replace("[YOUR ORG]", org)
    claude_md = claude_md.replace("AI Cockpit Template", name)
    (target / "CLAUDE.md").write_text(claude_md)
    print("  \033[32m+\033[0m CLAUDE.md")

    # Write .gitignore
    (target / ".gitignore").write_text(
        "# OS\n.DS_Store\n\n# Claude Code\n.claude/settings.local.json\n"
    )

    # Git init
    try:
        subprocess.run(["git", "init"], cwd=target, capture_output=True, check=True)
        subprocess.run(["git", "add", "."], cwd=target, capture_output=True, check=True)
        subprocess.run(
            ["git", "commit", "-m", f"init: {name} cockpit from ai-cockpit template"],
            cwd=target, capture_output=True, check=True,
        )
        print("  \033[32m+\033[0m git repo initialized")
    except Exception:
        print("  \033[33m!\033[0m git init skipped (git not available)")

    # GitHub repo
    if github:
        try:
            subprocess.run(
                ["gh", "repo", "create", f"{org}/{slug}", "--private", "--source", str(target), "--push"],
                cwd=target, check=True,
            )
            print(f"  \033[32m+\033[0m GitHub repo: {org}/{slug}")
        except Exception as e:
            print(f"  \033[33m!\033[0m GitHub repo creation failed: {e}")
            print(f"    Create manually: gh repo create {org}/{slug} --source {target}")

    # Register in cockpit
    reg = load_registry()
    entry = {
        "name": name,
        "slug": slug,
        "path": str(target),
        "org": org,
        "description": description,
        "has_settings": False,
    }
    reg["cockpits"].append(entry)
    save_registry(reg)

    # Done!
    print()
    print(f"  \033[1m\033[32mCockpit ready.\033[0m")
    print()
    print(f"  Next steps:")
    print(f"    1. Edit {target}/CLAUDE.md — fill in your role context and rules")
    print(f"    2. Run: \033[1mcockpit {slug}\033[0m")
    print(f"    3. Type /takeoff in Claude Code")
    print()
    print(f"  Optional — install Claude Code plugins:")
    print(f"    cockpit marketplace")
    print()


def _git(path, *args, timeout=5):
    """Run a git command in a directory, return stdout or None on failure."""
    try:
        r = subprocess.run(
            ["git", *args], cwd=path,
            capture_output=True, text=True, timeout=timeout,
        )
        return r.stdout.strip() if r.returncode == 0 else None
    except Exception:
        return None


def _check_cockpit_workspace(path):
    """Run workspace contract checks on a single cockpit path. Returns (clears, warns, blocks)."""
    p = Path(path)
    clears, warns, blocks = [], [], []

    if not p.exists():
        blocks.append("Path missing")
        return clears, warns, blocks

    # 1. Uncommitted changes
    status = _git(p, "status", "--porcelain")
    if status is not None:
        lines = status.splitlines() if status else []
        untracked = [l for l in lines if l.startswith("??")]
        modified = [l for l in lines if not l.startswith("??")]
        if modified:
            blocks.append(f"{len(modified)} uncommitted changes")
        elif untracked:
            warns.append(f"{len(untracked)} untracked files")
        else:
            clears.append("Working tree clean")
    else:
        warns.append("Not a git repo")

    # 2. Unpushed commits
    unpushed = _git(p, "log", "@{push}..HEAD", "--oneline")
    if unpushed is not None:
        if unpushed:
            count = len(unpushed.splitlines())
            blocks.append(f"{count} unpushed commits")
        else:
            clears.append("All commits pushed")

    # 3. Merge conflicts
    if status:
        conflicts = [l for l in status.splitlines() if l.startswith("UU") or l.startswith("AA")]
        if conflicts:
            blocks.append(f"{len(conflicts)} merge conflicts")

    # 4. Secrets staged
    staged = _git(p, "diff", "--cached", "--name-only")
    if staged:
        sensitive = [f for f in staged.splitlines()
                     if any(s in f.lower() for s in [".env", "secret", "credential", "token", "password", ".key"])]
        if sensitive:
            blocks.append(f"Sensitive files staged: {', '.join(sensitive)}")

    return clears, warns, blocks


def cmd_can_i_close(reg, args):
    """Run workspace contract checks across all registered cockpits."""
    if "--help" in args or "-h" in args:
        print()
        print("  \033[1m\033[36mcan-i-close\033[0m — Check if cockpits are safe to close")
        print()
        print("  Usage:")
        print("    cockpit can-i-close            Check all registered cockpits")
        print("    cockpit can-i-close <name>     Check a specific cockpit")
        print("    cockpit cic                    Shorthand alias")
        print()
        print("  Checks the workspace contract:")
        print("    - Uncommitted changes")
        print("    - Unpushed commits")
        print("    - Merge conflicts")
        print("    - Staged secrets (.env, credentials, tokens)")
        print()
        print("  For the full 20-check audit (session + conversation contracts),")
        print("  run /can-i-close inside Claude Code.")
        print()
        return

    cockpits = reg["cockpits"]

    # If a specific cockpit is named, check just that one
    if args:
        name = " ".join(a for a in args if not a.startswith("-"))
        if name:
            c = find_cockpit(reg, name)
            if c:
                cockpits = [c]
            else:
                print(f"  \033[31mNot found:\033[0m {name}")
                sys.exit(1)

    print()
    print("  \033[1m\033[36mCAN I CLOSE?\033[0m")
    print()

    total_blocks = 0
    total_warns = 0

    for c in sorted(cockpits, key=lambda x: (x.get("org", ""), x["name"])):
        p = Path(c["path"])
        if not p.exists():
            continue

        clears, warns, blocks = _check_cockpit_workspace(c["path"])

        if blocks:
            verdict = "\033[31mBLOCK\033[0m"
            total_blocks += len(blocks)
        elif warns:
            verdict = "\033[33mWARN\033[0m"
            total_warns += len(warns)
        else:
            verdict = "\033[32mCLEAR\033[0m"

        print(f"  {verdict}  \033[1m{c['slug']}\033[0m")
        for b in blocks:
            print(f"         \033[31m✗\033[0m {b}")
        for w in warns:
            print(f"         \033[33m!\033[0m {w}")

    print()

    if total_blocks:
        print(f"  \033[31mBLOCKED\033[0m — {total_blocks} issues must be fixed before closing")
        print(f"  Fix them, or run inside Claude Code for the full 20-check audit")
    elif total_warns:
        print(f"  \033[33mWARN\033[0m — safe to close, but {total_warns} loose ends")
    else:
        print(f"  \033[32mCLEAR\033[0m — all cockpits clean. Safe to close.")

    print()
    print(f"  \033[90mThis checks the workspace contract (git state).")
    print(f"  For session + conversation contracts, run /can-i-close inside Claude Code.\033[0m")
    print()


def cmd_touch_and_go(reg, args):
    """Commit and push all dirty registered cockpits."""
    if "--help" in args or "-h" in args:
        print()
        print("  \033[1m\033[36mtouch-and-go\033[0m — Checkpoint all dirty cockpits")
        print()
        print("  Usage:")
        print("    cockpit touch-and-go           Commit & push all dirty cockpits")
        print("    cockpit touch-and-go <name>    Checkpoint a specific cockpit")
        print("    cockpit tag                    Shorthand alias")
        print()
        print("  For each dirty cockpit:")
        print("    1. Stages all changes")
        print("    2. Commits with timestamped message")
        print("    3. Pushes to remote")
        print()
        print("  This is a save point, not a session end.")
        print("  Inside Claude Code, /touch-and-go also writes bookmarks")
        print("  and triggers context compaction.")
        print()
        return

    cockpits = reg["cockpits"]

    # If a specific cockpit is named, just that one
    if args:
        name = " ".join(a for a in args if not a.startswith("-"))
        if name:
            c = find_cockpit(reg, name)
            if c:
                cockpits = [c]
            else:
                print(f"  \033[31mNot found:\033[0m {name}")
                sys.exit(1)

    print()
    print("  \033[1m\033[36mTOUCH AND GO\033[0m")
    print()

    committed = 0
    pushed = 0
    skipped = 0

    for c in sorted(cockpits, key=lambda x: (x.get("org", ""), x["name"])):
        p = Path(c["path"])
        if not p.exists():
            continue

        status = _git(p, "status", "--porcelain")
        if not status:
            skipped += 1
            continue

        lines = status.splitlines()
        print(f"  \033[1m{c['slug']}\033[0m — {len(lines)} dirty files")

        # Stage all
        _git(p, "add", "-A")

        # Commit
        msg = f"touch-and-go: checkpoint {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        result = _git(p, "commit", "-m", msg)
        if result is not None:
            committed += 1
            print(f"    \033[32m✓\033[0m committed")

            # Push
            push_result = _git(p, "push", timeout=15)
            if push_result is not None:
                pushed += 1
                print(f"    \033[32m✓\033[0m pushed")
            else:
                print(f"    \033[33m!\033[0m push failed (no remote or auth issue)")
        else:
            print(f"    \033[33m!\033[0m commit failed")

    print()
    if committed:
        print(f"  \033[32m{committed} committed, {pushed} pushed, {skipped} clean\033[0m")
    else:
        print(f"  \033[90mAll cockpits clean. Nothing to checkpoint.\033[0m")
    print()


def cmd_marketplace():
    """Show marketplace info."""
    print()
    print("  \033[1m\033[36mEidos Marketplace\033[0m — plugins for Claude Code")
    print()
    print("  Install the marketplace:")
    print("    \033[1mclaude plugins marketplace add eidos-agi/eidos-marketplace\033[0m")
    print()
    print("  Then install plugins:")
    print("    \033[1mclaude plugins install resume-resume\033[0m    Session recovery & search")
    print("    \033[1mclaude plugins install ike\033[0m              Task & project management")
    print("    \033[1mclaude plugins install visionlog\033[0m        Vision, goals, guardrails, ADRs")
    print("    \033[1mclaude plugins install railguey\033[0m         Railway deployment management")
    print()
    print("  Browse: \033[4mhttps://github.com/eidos-agi/eidos-marketplace\033[0m")
    print()

    # Mark marketplace as seen so we don't nag
    cfg = load_config()
    cfg["marketplace_seen"] = True
    save_config(cfg)


# ─── Main ─────────────────────────────────────────────────


def _main():
    reg = load_registry()
    args = sys.argv[1:]

    if not args:
        # Default: interactive TUI
        if reg["cockpits"]:
            run_tui(reg)
        else:
            print("  No cockpits registered. Run: cockpit scan")
        return

    command = args[0]

    if command == "new":
        cmd_new(args[1:])
    elif command in ("can-i-close", "cic"):
        cmd_can_i_close(reg, args[1:])
    elif command in ("touch-and-go", "tag"):
        cmd_touch_and_go(reg, args[1:])
    elif command == "scan":
        cmd_scan(reg)
    elif command == "status":
        cmd_status(reg)
    elif command == "list":
        cmd_list(reg)
    elif command == "config":
        cmd_config(args[1:])
    elif command == "marketplace":
        cmd_marketplace()
    elif command == "add" and len(args) > 1:
        cmd_add(reg, args[1])
    elif command == "remove" and len(args) > 1:
        cmd_remove(reg, " ".join(args[1:]))
    elif command == "upgrade" and len(args) > 1:
        name = args[1]
        dry_run = "--apply" not in args
        cmd_upgrade(reg, name, dry_run=dry_run)
    elif command in ("-h", "--help", "help"):
        print(__doc__)
    else:
        # Direct open: cockpit <name> [-a|-y]
        mode = None
        name_parts = []
        for a in args:
            if a in ("-a", "--auto"):
                mode = "auto"
            elif a in ("-y", "--yolo"):
                mode = "yolo"
            else:
                name_parts.append(a)
        name = " ".join(name_parts)
        if name:
            c = find_cockpit(reg, name)
            if c:
                launch_cockpit(c, mode)
            else:
                print(f"  \033[31mNot found:\033[0m {name}")
                print(f"  Run: cockpit list")
                sys.exit(1)
        else:
            run_tui(reg)


def main():
    try:
        _main()
    except KeyboardInterrupt:
        pass
    except Exception as exc:
        log_crash(exc)
        print(f"\n  \033[31mCrash logged to {CRASH_LOG}\033[0m")
        print(f"  \033[90m{type(exc).__name__}: {exc}\033[0m\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
