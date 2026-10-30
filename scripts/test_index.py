#!/usr/bin/env python3
"""Tests for the agent skills discovery index and its website mirror.

Checks that .well-known/agent-skills/ is current, that every entry follows the
discovery spec v0.2.0 (names, descriptions, sha256 digests of the archives,
SKILL.md at the archive root), that the build is deterministic, and that
mirror_index.py publishes a good set but refuses a tampered one while leaving
the live folder untouched. Offline; nothing outside a temporary directory.
"""
import glob, hashlib, io, json, os, re, shutil, subprocess, sys, tarfile, tempfile

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
OUT = os.path.join(ROOT, ".well-known", "agent-skills")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import build_index, mirror_index

results = []
def check(name, ok, detail=""):
    results.append(bool(ok)); print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}")

r = subprocess.run([sys.executable, "-B", os.path.join(ROOT, "scripts", "build_index.py"), "--check"],
                   capture_output=True, text=True)
check("index and archives are current", r.returncode == 0, (r.stdout + r.stderr).strip()[-300:])

index = json.load(open(os.path.join(OUT, "index.json")))
skills = sorted(os.path.basename(os.path.dirname(p)) for p in
                glob.glob(os.path.join(ROOT, "skills", "*", "SKILL.md")))
check("$schema is discovery v0.2.0", index.get("$schema") == build_index.SCHEMA)
check("one entry per skill folder", [e["name"] for e in index["skills"]] == skills,
      [e["name"] for e in index["skills"]])
for e in index["skills"]:
    blob = open(os.path.join(OUT, e["url"]), "rb").read()
    with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as tar:
        names = tar.getnames()
        skill_md = tar.extractfile("SKILL.md").read() if "SKILL.md" in names else b""
    src_md = open(os.path.join(ROOT, "skills", e["name"], "SKILL.md"), "rb").read()
    check(f"{e['name']}: spec fields and naming",
          e["type"] == "archive" and re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", e["name"])
          and 0 < len(e["description"]) <= 1024 and re.match(r"^sha256:[0-9a-f]{64}$", e["digest"]))
    check(f"{e['name']}: digest is the archive's sha256",
          e["digest"] == "sha256:" + hashlib.sha256(blob).hexdigest())
    check(f"{e['name']}: SKILL.md at the root, same bytes as the source, scripts included, no caches",
          skill_md == src_md and any(n.startswith("scripts/") for n in names)
          and not any(n.startswith("/") or ".." in n.split("/") or "__pycache__" in n for n in names))
    check(f"{e['name']}: description matches SKILL.md frontmatter",
          e["description"] == build_index.frontmatter(os.path.join(ROOT, "skills", e["name"], "SKILL.md"))["description"])
    files = build_index.members(os.path.join(ROOT, "skills", e["name"]))
    check(f"{e['name']}: build is deterministic", build_index.pack(files) == build_index.pack(files))

with tempfile.TemporaryDirectory() as tmp:
    live = os.path.join(tmp, "www", "agent-skills")
    code = mirror_index.mirror(os.path.join(OUT, "index.json"), live)
    check("mirror publishes every skill with verified digests",
          code == len(skills) and sorted(os.listdir(live)) == sorted([e["url"] for e in index["skills"]] + ["index.json"]))
    before = {f: open(os.path.join(live, f), "rb").read() for f in os.listdir(live)}

    bad = os.path.join(tmp, "bad"); shutil.copytree(OUT, bad)
    first = index["skills"][0]["url"]
    with open(os.path.join(bad, first), "ab") as f:
        f.write(b"tampered")
    try:
        mirror_index.mirror(os.path.join(bad, "index.json"), live); refused = False
    except ValueError as err:
        refused = "digest mismatch" in str(err)
    after = {f: open(os.path.join(live, f), "rb").read() for f in os.listdir(live)}
    check("mirror refuses a tampered archive and leaves the live folder as it was", refused and after == before)

    evil = os.path.join(tmp, "evil"); shutil.copytree(OUT, evil)
    idx = json.load(open(os.path.join(evil, "index.json")))
    idx["skills"][0]["url"] = "https://example.com/x.tar.gz"
    json.dump(idx, open(os.path.join(evil, "index.json"), "w"))
    try:
        mirror_index.mirror(os.path.join(evil, "index.json"), live); refused = False
    except ValueError:
        refused = True
    check("mirror refuses URLs pointing at other hosts", refused)

    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w:gz") as tar:
        for n in ("SKILL.md", "../escape"):
            info = tarfile.TarInfo(n); info.size = 1; tar.addfile(info, io.BytesIO(b"x"))
    try:
        mirror_index.check_archive("t", raw.getvalue()); refused = False
    except ValueError:
        refused = True
    check("mirror refuses an archive with path traversal", refused)

print(f"\n{sum(results)}/{len(results)} passed")
sys.exit(0 if all(results) else 1)
