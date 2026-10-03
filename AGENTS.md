# Working on Prawo Otwarte

This is an open Polish legal research application. Preserve the Apache-2.0 license.

- Never describe metadata import, a model score or an HTTP 200 as legal validation.
- The target is broad coverage of Polish law; expose actual source coverage and gaps.
- A retrieval timestamp is not a date of legal validity. Historical law requires
  validated versions, amendments and transitional provisions.
- Basal routes cases only. It must not decide entitlements, guilt, outcomes or deadlines.
- Fail explicitly on absent sources, malformed model output, unavailable integrations
  and unverified temporal applicability. Do not manufacture citations or model results.
- Preserve source identifiers, snapshots, hashes, provenance and relationships.
- No raw case descriptions, uploaded documents, user identifiers, secrets, server
  inventories or private operations reports in Git, analytics or request logs.
- The web process does not have an administrative import, shell or deletion endpoint.
- Review existing work before edits. Use a branch for substantive changes; never force-push.
- Run `python -m unittest discover -s tests -v` before a change to application behavior.
- See `docs/ARCHITECTURE.md`, `docs/DEPLOYMENT.md` and `docs/ROADMAP.md`.

Deployment files are templates, not proof of a working deployment. Never change SSH,
Tailscale, an unrelated service or a firewall as an incidental part of installation.
Any removal of previous projects must follow the owner's separately supplied,
private migration instructions. This repository grants no blanket deletion authority.
