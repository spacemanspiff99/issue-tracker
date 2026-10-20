---
paths:
  - "deployment/**"
  - ".github/workflows/**"
  - ".env.example"
---

# Deployment and config invariants (IT-6)

- Env vars only for secrets/hosts; `.env.example` holds placeholders, never real values.
- Compose files stay in `deployment/`; no `sudo`; migrations are an explicit command, never
  app startup.
- `local-pipeline.yml` and `remote-compose-deploy.sh` touch real hosts — editing is fine,
  dispatching needs explicit user approval.
- `mirror-rules.yml` publishes guidance to vibecoding on `main`; keep its `paths:` in step with
  where guidance lives.
- Procedure: `deploy-safety` skill.
