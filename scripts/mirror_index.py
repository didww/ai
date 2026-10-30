#!/usr/bin/env python3
"""Mirrors the DIDWW agent skills index onto a web server, for cron.

  python3 scripts/mirror_index.py --dest /var/www/didww.com/.well-known/agent-skills

Downloads index.json and every archive it lists from GitHub (or --source),
checks each sha256 digest and that every archive is safe to unpack (SKILL.md
at the root, no absolute paths, no "..", no links), then swaps the new folder
in at once. On any failure the live folder is left untouched and the exit
code is 1, so a half-updated or tampered set is never served. Stdlib only.
"""
import argparse, hashlib, io, json, os, shutil, sys, tarfile, tempfile, urllib.parse, urllib.request

DEFAULT_SOURCE = "https://raw.githubusercontent.com/didww/ai/main/.well-known/agent-skills/index.json"
SCHEMA = "https://schemas.agentskills.io/discovery/0.2.0/schema.json"
MAX_BYTES = 20 * 1024 * 1024

def fetch(url):
    if "://" not in url:  # a local path, for tests and manual runs
        return open(url, "rb").read()
    if urllib.parse.urlparse(url).scheme != "https":
        raise ValueError(f"{url}: only https sources are allowed")
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "didww-skills-mirror"}), timeout=60) as r:
        data = r.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError(f"{url}: larger than {MAX_BYTES} bytes")
    return data

def check_archive(name, blob):
    with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as tar:
        names = []
        for m in tar.getmembers():
            if m.name.startswith("/") or ".." in m.name.split("/") or not (m.isfile() or m.isdir()):
                raise ValueError(f"{name}: unsafe archive member {m.name!r}")
            names.append(m.name)
    if "SKILL.md" not in names:
        raise ValueError(f"{name}: no SKILL.md at the archive root")

def mirror(source, dest):
    index_bytes = fetch(source)
    index = json.loads(index_bytes)
    if index.get("$schema") != SCHEMA:
        raise ValueError(f"unexpected $schema {index.get('$schema')!r}")
    files = {"index.json": index_bytes}
    remote = "://" in source
    base = source.rsplit("/", 1)[0] if remote else os.path.dirname(os.path.abspath(source))
    for skill in index["skills"]:
        url = skill["url"]
        # Only plain file names next to the index: the mirror never fetches other hosts.
        if "/" in url or "\\" in url or url.startswith(".") or not url.endswith(".tar.gz"):
            raise ValueError(f"{skill['name']}: url {url!r} is not a file next to the index")
        blob = fetch(f"{base}/{urllib.parse.quote(url)}" if remote else os.path.join(base, url))
        digest = "sha256:" + hashlib.sha256(blob).hexdigest()
        if digest != skill["digest"]:
            raise ValueError(f"{skill['name']}: digest mismatch ({digest} != {skill['digest']})")
        check_archive(skill["name"], blob)
        files[url] = blob
    dest = os.path.abspath(dest)
    parent = os.path.dirname(dest)
    os.makedirs(parent, exist_ok=True)
    staging = tempfile.mkdtemp(prefix=".agent-skills-new-", dir=parent)
    try:
        for fname, data in files.items():
            # Names come from the downloaded index: keep every write inside staging.
            target = os.path.realpath(os.path.join(staging, os.path.basename(fname)))
            if os.path.commonpath([target, os.path.realpath(staging)]) != os.path.realpath(staging):
                raise ValueError(f"{fname}: would be written outside {dest}")
            with open(target, "wb") as f:
                f.write(data)
            os.chmod(target, 0o644)
        os.chmod(staging, 0o755)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    old = None
    if os.path.exists(dest):
        old = tempfile.mkdtemp(prefix=".agent-skills-old-", dir=parent)
        os.rmdir(old)
        os.rename(dest, old)
    os.rename(staging, dest)
    if old:
        shutil.rmtree(old)
    return len(index["skills"])

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dest", required=True, help="folder served as /.well-known/agent-skills/")
    ap.add_argument("--source", default=DEFAULT_SOURCE, help="index.json URL or local path")
    args = ap.parse_args()
    try:
        n = mirror(args.source, args.dest)
    except Exception as e:
        print(f"Mirror failed, live folder unchanged: {e}", file=sys.stderr)
        sys.exit(1)
    print(f"Mirrored {n} skills to {args.dest}")
