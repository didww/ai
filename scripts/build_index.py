#!/usr/bin/env python3
"""Builds .well-known/agent-skills/: the Agent Skills discovery index (v0.2.0)
plus one .tar.gz per skill, so any site can serve the family from one folder.

  python3 scripts/build_index.py           write index.json and archives
  python3 scripts/build_index.py --check   fail if they are out of date (CI)

Each archive holds what bin/install.js installs (SKILL.md, scripts/,
references/) plus LICENSE, at the archive root as the spec requires.
Archives are rewritten only when their contents change, so digests stay
put between builds. Spec: github.com/cloudflare/agent-skills-discovery-rfc
"""
import glob, gzip, hashlib, io, json, os, re, sys, tarfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
OUT = os.path.join(ROOT, ".well-known", "agent-skills")
SCHEMA = "https://schemas.agentskills.io/discovery/0.2.0/schema.json"
REPO = "https://github.com/didww/ai"
PARTS = ["SKILL.md", "LICENSE", "scripts", "references"]
SKIP = re.compile(r"(^|/)(__pycache__|\.DS_Store|.*\.pyc)(/|$)")
NAME = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

def frontmatter(path):
    """name and description from SKILL.md; handles plain and folded (>) scalars."""
    text = open(path, encoding="utf-8").read()
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        sys.exit(f"{path}: no YAML frontmatter")
    fields, key, lines = {}, None, []
    for line in m.group(1).split("\n") + ["end:"]:
        top = re.match(r"^([A-Za-z_-]+):\s*(.*)$", line)
        if top:
            if key:
                fields[key] = re.sub(r"\s+", " ", " ".join(lines)).strip()
            key, value = top.groups()
            lines = [] if value in (">", ">-", "|", "|-") else [value.strip().strip('"\'')]
        elif key:
            lines.append(line.strip())
    return fields

def members(skill_dir):
    """(archive path, mode, bytes) for every file the archive should hold, sorted."""
    files = []
    for part in PARTS:
        src = os.path.join(skill_dir, part)
        paths = [src] if os.path.isfile(src) else sorted(
            os.path.join(p, f) for p, _, fs in os.walk(src) for f in fs)
        for p in paths:
            rel = os.path.relpath(p, skill_dir).replace(os.sep, "/")
            if SKIP.search(rel) or os.path.islink(p):
                continue
            mode = 0o755 if os.stat(p).st_mode & 0o111 else 0o644
            files.append((rel, mode, open(p, "rb").read()))
    return sorted(files)

def pack(files):
    """Deterministic tar.gz: fixed owner and times, no wrapper directory."""
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w", format=tarfile.PAX_FORMAT) as tar:
        for rel, mode, data in files:
            info = tarfile.TarInfo(rel)
            info.size, info.mode, info.mtime = len(data), mode, 0
            info.uid = info.gid = 0; info.uname = info.gname = ""
            tar.addfile(info, io.BytesIO(data))
    out = io.BytesIO()
    with gzip.GzipFile(fileobj=out, mode="wb", mtime=0, filename="") as gz:
        gz.write(raw.getvalue())
    return out.getvalue()

def unpack(blob):
    """(path, mode, bytes) of a built archive, to compare with the sources."""
    with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as tar:
        return sorted((m.name, m.mode, tar.extractfile(m).read()) for m in tar.getmembers() if m.isfile())

def build(check):
    stale, entries = [], []
    for skill_md in sorted(glob.glob(os.path.join(ROOT, "skills", "*", "SKILL.md"))):
        skill_dir = os.path.dirname(skill_md)
        folder = os.path.basename(skill_dir)
        fm = frontmatter(skill_md)
        name, desc = fm.get("name", ""), fm.get("description", "")
        if name != folder or not NAME.match(name) or len(name) > 64:
            sys.exit(f"{skill_md}: name '{name}' must match the folder and the Agent Skills naming rules")
        if not desc or len(desc) > 1024:
            sys.exit(f"{skill_md}: description must be 1 to 1024 characters (has {len(desc)})")
        version = json.load(open(os.path.join(skill_dir, "package.json")))["version"]
        files = members(skill_dir)
        archive = os.path.join(OUT, f"{name}.tar.gz")
        blob = open(archive, "rb").read() if os.path.isfile(archive) else None
        if blob is None or unpack(blob) != files:
            stale.append(os.path.relpath(archive, ROOT))
            blob = pack(files)
            if not check:
                os.makedirs(OUT, exist_ok=True)
                open(archive, "wb").write(blob)
        entries.append({
            "name": name,
            "type": "archive",
            "description": desc,
            "url": f"{name}.tar.gz",
            "digest": "sha256:" + hashlib.sha256(blob).hexdigest(),
            "version": version,
            "documentation": f"{REPO}/blob/main/docs/{name}.md"
                             if os.path.isfile(os.path.join(ROOT, "docs", f"{name}.md"))
                             else f"{REPO}/tree/main/skills/{name}",
            "install": f"npx {name}",
        })
    index = {
        "$schema": SCHEMA,
        "name": "DIDWW Agent Skills",
        "description": "Official DIDWW agent skills: put an AI voice agent on a real DIDWW phone "
                       "number with any major voice AI platform, through the DIDWW MCP "
                       "(https://api.didww.com/mcp).",
        "repository": REPO,
        "homepage": "https://www.didww.com/",
        "skills": entries,
    }
    text = json.dumps(index, indent=2, ensure_ascii=False) + "\n"
    index_path = os.path.join(OUT, "index.json")
    current = open(index_path, encoding="utf-8").read() if os.path.isfile(index_path) else None
    if current != text:
        stale.append(os.path.relpath(index_path, ROOT))
        if not check:
            os.makedirs(OUT, exist_ok=True)
            open(index_path, "w", encoding="utf-8").write(text)
    # Archives of skills that no longer exist.
    known = {f"{e['name']}.tar.gz" for e in entries} | {"index.json"}
    for extra in sorted(set(os.listdir(OUT)) - known if os.path.isdir(OUT) else []):
        if extra.endswith(".tar.gz"):
            stale.append(os.path.relpath(os.path.join(OUT, extra), ROOT))
            if not check:
                os.remove(os.path.join(OUT, extra))
    return entries, stale

if __name__ == "__main__":
    check = "--check" in sys.argv[1:]
    entries, stale = build(check)
    if check:
        if stale:
            print("Out of date: " + ", ".join(stale))
            print("Run: python3 scripts/build_index.py, then commit .well-known/")
            sys.exit(1)
        print(f"PASS  .well-known/agent-skills is current ({len(entries)} skills)")
    else:
        print(f"{len(entries)} skills; " + (f"updated {', '.join(stale)}" if stale else "nothing changed"))
