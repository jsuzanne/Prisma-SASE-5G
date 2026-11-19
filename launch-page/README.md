# Stigix × Prisma SASE 5G — Lab Launchpad (Cloudflare Pages)

Static launch portal for the **Stigix × Palo Alto Networks Prisma SASE 5G** demonstration environment.

## Primary Lab Endpoints
- **5G Core & RAN Endpoint Orchestrator**: `https://5gorchestrator.stigix.io/`
- **Stigix 5G Traffic & Security Validation Lab**: `https://stigix5glab.stigix.io/`
- **Stigix Official Site**: `https://stigix.io/`

## Local Preview
```bash
python3 -m http.server 8088 --directory launch-page
```
Then open `http://localhost:8088` in your browser.

## Cloudflare Pages Deployment
- **Live URL**: `https://5glab.pages.dev` (Custom Domain: `https://5glab.stigix.io`)
- **Deploy via Wrangler CLI**:
  ```bash
  npx -y wrangler pages deploy launch-page --project-name=5glab --branch=main
  ```
