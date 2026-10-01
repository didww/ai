# Security

## Reporting a vulnerability

Please report security issues privately through GitHub's [private vulnerability reporting](https://github.com/didww/ai/security/advisories/new) for this repository rather than in a public issue. Include the affected skill or script, the steps to reproduce, and the impact. You will get an acknowledgement and a fix or a mitigation before any public disclosure.

## Scope

This repository contains agent skills, scripts and documentation. The skills run on your own machine, call the DIDWW MCP and the voice platforms' APIs under your own credentials, and store nothing. Issues in the DIDWW service itself, the User Panel or the API should go to DIDWW support rather than this tracker.

## What the scripts do with credentials

- Platform API keys are read from environment variables at run time and are never written to disk by any script.
- The installers copy files into `~/.claude/skills/` and do not execute anything from the network.
- The DIDWW side always goes through the DIDWW MCP with OAuth sign-in; no DIDWW API key is required except for the optional read-only health monitor.
