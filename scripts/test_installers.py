#!/usr/bin/env python3
"""Real-install tests for every skill's bin/install.js, against a throwaway HOME.

Checks a fresh install, a reinstall (backup outside skills/), and that the
installer refuses destinations it does not own: home, the skills root, the
package itself, a folder holding another skill or other files, a bare --dest
and unknown options. Nothing outside a temporary directory is touched.
"""
import glob, os, subprocess, sys, tempfile

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
results = []
def check(name, ok, detail=""):
    results.append(bool(ok)); print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}")

def run(skill_dir, home, *args):
    r = subprocess.run(["node", os.path.join(skill_dir, "bin", "install.js"), *args],
                       env={**os.environ, "HOME": home, "USERPROFILE": home},
                       capture_output=True, text=True, timeout=60)
    return r.returncode, r.stdout + r.stderr

def snapshot(d):
    return sorted(os.path.relpath(os.path.join(p, f), d)
                  for p, _, fs in os.walk(d) for f in fs)

for skill_dir in sorted(glob.glob(os.path.join(ROOT, "skills", "*", "bin", "install.js"))):
    skill_dir = os.path.dirname(os.path.dirname(skill_dir))
    name = os.path.basename(skill_dir)
    with tempfile.TemporaryDirectory() as home:
        target = os.path.join(home, ".claude", "skills", name)
        code, out = run(skill_dir, home)
        files = snapshot(target) if os.path.isdir(target) else []
        check(f"{name}: fresh install lands SKILL.md + scripts, no caches",
              code == 0 and "SKILL.md" in files and any(f.startswith("scripts/") for f in files)
              and not any("__pycache__" in f or f.endswith(".pyc") for f in files), out[-200:] if code else "")
        code, out = run(skill_dir, home)
        backups = glob.glob(os.path.join(home, ".claude", "skill-backups", name + "-*"))
        check(f"{name}: reinstall backs up the old install outside skills/",
              code == 0 and len(backups) == 1 and os.path.isfile(os.path.join(target, "SKILL.md")), out[-200:] if code else "")

        marker = os.path.join(home, "keep.txt"); open(marker, "w").write("x")
        before = snapshot(home)
        for label, args in (("home directory", ["--dest", home]),
                            ("the skills root", ["--dest", os.path.join(home, ".claude", "skills")]),
                            ("the package itself", ["--dest", skill_dir]),
                            ("bare --dest", ["--dest"]),
                            ("unknown option", ["--dset", "x"])):
            code, out = run(skill_dir, home, *args)
            check(f"{name}: refuses {label}, changes nothing",
                  code != 0 and "Nothing was changed" in out and snapshot(home) == before, out.strip().splitlines()[-2:] if code == 0 else "")

        other = os.path.join(home, "other-skill"); os.makedirs(other)
        open(os.path.join(other, "SKILL.md"), "w").write("---\nname: someone-else\n---\n")
        code, out = run(skill_dir, home, "--dest", other)
        check(f"{name}: refuses a folder holding a different skill",
              code != 0 and snapshot(other) == ["SKILL.md"] and os.path.isdir(other))
        stuff = os.path.join(home, "projects"); os.makedirs(stuff)
        open(os.path.join(stuff, "notes.md"), "w").write("mine")
        code, out = run(skill_dir, home, "--dest", stuff)
        check(f"{name}: refuses a non-empty folder that is not a skill install",
              code != 0 and snapshot(stuff) == ["notes.md"])
        empty = os.path.join(home, "empty"); os.makedirs(empty)
        code, out = run(skill_dir, home, "--dest", empty)
        check(f"{name}: installs into an empty --dest folder",
              code == 0 and os.path.isfile(os.path.join(empty, "SKILL.md")), out[-200:] if code else "")

print(f"\n{sum(results)}/{len(results)} passed"); sys.exit(0 if all(results) else 1)
