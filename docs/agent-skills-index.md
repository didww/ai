# Serving the agent skills index on didww.com

For the DIDWW web team. The goal is one URL that lets AI agents and skill directories find every DIDWW agent skill:

```
https://www.didww.com/.well-known/agent-skills/index.json
```

It uses the [Agent Skills discovery](https://github.com/cloudflare/agent-skills-discovery-rfc) format (v0.2.0), the same one Telnyx serves at `https://telnyx.com/.well-known/agent-skills/index.json`. Nothing on the site is written by hand: the files are generated in the [didww/ai](https://github.com/didww/ai) repository and the site keeps a copy.

## What gets served

The folder [`.well-known/agent-skills/`](../.well-known/agent-skills/) in the repository, as is:

| File | Content-Type |
|---|---|
| `index.json` | `application/json` |
| `<skill-name>.tar.gz` (one per skill) | `application/gzip` |

The index refers to each archive by a relative URL (`didww-connect.tar.gz`), so the files must sit side by side under `/.well-known/agent-skills/`.

## Keeping it current

Run the mirror script on a schedule, for example hourly from cron. It needs Python 3 and nothing else:

```bash
python3 mirror_index.py --dest /path/to/webroot/.well-known/agent-skills
```

Download [`scripts/mirror_index.py`](../scripts/mirror_index.py) once, or run it from a clone of the repository. It reads the index from GitHub (`main` branch), downloads every archive, checks each sha256 digest and that every archive is safe to unpack, then replaces the folder in a single step. If anything fails (network, a digest mismatch, a malformed archive) it exits with code 1 and leaves the live folder exactly as it was. It only fetches files that sit next to the index on GitHub.

Example crontab line:

```
17 * * * * python3 /opt/didww-skills/mirror_index.py --dest /var/www/didww.com/.well-known/agent-skills >> /var/log/didww-skills-mirror.log 2>&1
```

## Web server settings

- The Content-Types above. With nginx, `location ~ ^/\.well-known/agent-skills/.+\.tar\.gz$ { types { } default_type application/gzip; }` covers the archives; `.json` is mapped to `application/json` by the default `mime.types`.
- `GET` and `HEAD`, and `404` for files that do not exist.
- `Cache-Control: public, max-age=3600` matches an hourly mirror.
- `Access-Control-Allow-Origin: *`, so browser-based agents can read the index.
- No redirect from `didww.com` to `www.didww.com` is required, but agents follow redirects if there is one.

## Checking it

```bash
curl -sI https://www.didww.com/.well-known/agent-skills/index.json   # 200, application/json
curl -s  https://www.didww.com/.well-known/agent-skills/index.json | python3 -m json.tool | head
```

Every `digest` in the index must equal `sha256:` plus the SHA-256 of the archive the site serves. The mirror guarantees this as long as nothing else writes to the folder.
