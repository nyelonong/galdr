# galdr site

The public product page for
[galdr](https://github.com/nyelonong/galdr), a routed, evidence-gated
engineering method for coding agents.

## Local development

Requires Node.js `>=22.13.0`.

```bash
npm install
npm run dev
```

The page is a single vinext route. It uses local font packages, deterministic
browser interactions, and no database, runtime secret, external connector, or
client persistence.

## Verification

```bash
npm test
npm run lint
npx tsc --noEmit
npx wrangler deploy --dry-run
```

`npm test` builds the Cloudflare Worker, runs the component and content
contracts, then verifies the rendered Worker HTML. The Wrangler command is a
dry run only.

## Deployment

The source of truth is this `site/` directory. The recommended production host
is `galdr.afrani.id`. In Cloudflare Workers Builds, set **Root directory** to
`site`, **Build command** to `npm run build`, and **Deploy command** to
`npx wrangler deploy`.

No command in this README publishes the repository, deploys the Worker, binds a
domain, or changes DNS.
