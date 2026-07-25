import { access, readFile } from "node:fs/promises";
import { join } from "node:path";
import { render, screen } from "@testing-library/react";
import { createElement } from "react";
import { describe, expect, it } from "vitest";
import { METHOD_STAGES, ROUTE_EXAMPLES, RUNTIME_INSTALLS } from "../app/content";
import { siteMetadata } from "../app/layout";
import Home from "../app/page";

async function source(path: string) {
  return readFile(join(process.cwd(), path), "utf8");
}

describe("site foundation content contract", () => {
  it("content_has_exact_six_stage_flow", () => {
    expect(METHOD_STAGES.map(({ id }) => id)).toEqual([
      "route",
      "shape",
      "plan",
      "waves",
      "verify",
      "memory",
    ]);
    expect(METHOD_STAGES).toHaveLength(6);
    expect(METHOD_STAGES.every(({ output }) => output.length > 0)).toBe(true);
  });

  it("routes_have_four_ids_and_shape_default", () => {
    expect(ROUTE_EXAMPLES.map(({ id }) => id)).toEqual([
      "flaky-checkout",
      "new-export",
      "api-architecture",
      "documentation",
    ]);
    expect(ROUTE_EXAMPLES.find(({ id }) => id === "new-export")?.route).toBe(
      "shape-synthesis",
    );
  });

  it("installs_cover_three_runtimes", () => {
    expect(RUNTIME_INSTALLS).toEqual([
      {
        id: "claude",
        label: "Claude Code",
        install: [
          "/plugin marketplace add nyelonong/galdr",
          "/plugin install galdr@nyelonong",
        ],
        enable: "/galdr:core install claude",
      },
      {
        id: "codex",
        label: "Codex",
        install: ["npx skills add nyelonong/galdr"],
        enable: "/galdr:core install codex",
      },
      {
        id: "antigravity",
        label: "Antigravity",
        install: ["npx skills add nyelonong/galdr"],
        enable: "/galdr:core install antigravity",
      },
    ]);
  });

  it("foundation_has_galdr_metadata_and_main_landmark", async () => {
    const [manifest, layout, css] = await Promise.all([
      source("package.json"),
      source("app/layout.tsx"),
      source("app/globals.css"),
    ]);

    expect.soft(manifest).toContain('"name": "galdr-site"');
    expect.soft(manifest).toContain('"@fontsource-variable/newsreader"');
    expect.soft(manifest).toContain('"@fontsource/ibm-plex-mono"');
    expect.soft(layout).toContain('@fontsource-variable/newsreader/wght.css');
    expect.soft(layout).toContain('@fontsource/ibm-plex-mono/400.css');
    expect.soft(css).toContain('"Newsreader Variable"');
    expect.soft(css).toContain('"IBM Plex Mono"');

    render(createElement(Home));

    expect(siteMetadata.title).toBe(
      "galdr | Evidence-gated engineering for coding agents",
    );
    expect.soft(siteMetadata.description).toBe(
      "galdr routes each request, requires a failing test before production code, and records fresh evidence before work is called done.",
    );
    expect.soft(
      screen.queryByRole("heading", {
        level: 1,
        name: "A method for engineering agents that does not trust claims.",
      }),
    ).toBeInTheDocument();
    expect.soft(
      screen.queryByText(
        "galdr routes each request, requires a failing test before production code, and records fresh evidence before work is called done.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByRole("main")).toBeInTheDocument();
  });

  it("foundation_has_no_starter_preview_marker", async () => {
    const files = await Promise.all([
      source("app/page.tsx"),
      source("app/layout.tsx"),
      source("package.json"),
    ]);
    const starterMarkers = new RegExp(
      [
        ["codex", "preview"].join("-"),
        ["Your site is taking", "shape"].join(" "),
        ["Building your", "site"].join(" "),
        ["react-loading", "skeleton"].join("-"),
      ].join("|"),
    );

    expect(files.join("\n")).not.toMatch(starterMarkers);
  });

  it("foundation_has_no_unused_auth_or_starter_assets", async () => {
    const absentPaths = [
      "app/chatgpt-auth.ts",
      "public/file.svg",
      "public/globe.svg",
      "public/window.svg",
    ];
    const readme = await source("README.md");

    await Promise.all(
      absentPaths.map(async (path) => {
        await expect(access(join(process.cwd(), path))).rejects.toThrow();
      }),
    );
    expect(readme).not.toMatch(
      /vinext-starter|Workspace Auth Headers|ChatGPT Sign-In|rendered loading skeleton/,
    );
  });

  it("foundation_has_no_database_or_image_connector_scaffold", async () => {
    const absentPaths = [
      "cloudflare-env.d.ts",
      "db/index.ts",
      "db/schema.ts",
      "drizzle.config.ts",
      "drizzle/meta/_journal.json",
      "examples/d1/app/api/notes/route.ts",
      "examples/d1/db/schema.ts",
    ];
    const [manifest, worker, viteConfig, sitesPlugin] = await Promise.all([
      source("package.json"),
      source("worker/index.ts"),
      source("vite.config.ts"),
      source("build/sites-vite-plugin.ts"),
    ]);

    await Promise.all(
      absentPaths.map(async (path) => {
        await expect(access(join(process.cwd(), path))).rejects.toThrow();
      }),
    );
    expect(manifest).not.toMatch(/drizzle|db:generate/);
    expect(worker).not.toMatch(
      /D1Database|IMAGES|image-optimization|_vinext\/image/,
    );
    expect(viteConfig).not.toMatch(
      /d1_databases|r2_buckets|PLACEHOLDER_DATABASE|hostingConfig/,
    );
    expect(sitesPlugin).not.toMatch(/drizzle/i);
  });

  it("public_readme_does_not_link_private_development_docs", async () => {
    const readme = await source("README.md");

    expect(readme).not.toMatch(/\]\(\.\.\/docs\//);
    expect(readme).toContain("galdr.afrani.id");
    expect(readme).toContain("Root directory");
    expect(readme).toContain("npm run build");
    expect(readme).toContain("npx wrangler deploy");
  });

  it("foundation_has_reduced_motion_rule", async () => {
    await expect(source("app/globals.css")).resolves.toMatch(
      /@media \(prefers-reduced-motion: reduce\)\s*\{[\s\S]*animation-duration: 0\.01ms[\s\S]*transition-duration: 0\.01ms/,
    );
  });

  it("wrangler_config_names_galdr_worker", async () => {
    const config = await source("wrangler.jsonc");

    expect.soft(config).toMatch(/"name": "galdr"/);
    expect.soft(config).toMatch(/"main": "\.\/worker\/index\.ts"/);
    expect.soft(config).toMatch(/"compatibility_date": "2026-05-22"/);
    expect.soft(config).toMatch(/"nodejs_compat"/);
  });
});
