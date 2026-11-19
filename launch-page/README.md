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
- **Option 1 (Git Integration)**: Connect the repository to Cloudflare Pages and set the **Build output directory** to `launch-page` (no build command needed).
- **Option 2 (Wrangler CLI)**:
  ```bash
  npx wrangler pages deploy launch-page --project-name stigix-5g-launchpad
  ```
