import { readFile } from "node:fs/promises";
import { join } from "node:path";
import { cleanup, render, screen, within } from "@testing-library/react";
import { createElement } from "react";
import { afterEach, describe, expect, it } from "vitest";
import { METHOD_STAGES, ROUTE_EXAMPLES, RUNTIME_INSTALLS } from "../app/content";
import Home from "../app/page";

const repository = "https://github.com/nyelonong/galdr";

async function source(path: string) {
  try {
    return await readFile(join(process.cwd(), path), "utf8");
  } catch {
    return "";
  }
}

function renderPage() {
  const result = render(createElement(Home));
  return result.container;
}

afterEach(cleanup);

describe("public page contract", () => {
  it("page_has_masthead_main_and_footer_landmarks", () => {
    renderPage();

    expect(screen.getByRole("banner")).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "Primary" })).toBeInTheDocument();
    expect(screen.getByRole("main")).toBeInTheDocument();
    expect(screen.getByRole("contentinfo")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "galdr" })).toBeInTheDocument();

    for (const name of ["METHOD", "PROOF", "INSTALL", "GitHub"]) {
      expect(screen.getByRole("link", { name })).toBeInTheDocument();
    }
  });

  it("hero_has_exact_statement_support_and_two_actions", () => {
    renderPage();

    expect(
      screen.getByRole("heading", {
        level: 1,
        name: "A method for engineering agents that does not trust claims.",
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "galdr routes each request, requires a failing test before production code, and records fresh evidence before work is called done.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "See the method" })).toHaveAttribute(
      "href",
      "#method",
    );
    expect(screen.getByRole("link", { name: "Install galdr" })).toHaveAttribute(
      "href",
      "#install",
    );
  });

  it("execution_record_has_six_ordered_states_and_stops", () => {
    const page = renderPage();
    const record = page.querySelector("[data-execution-record]");

    expect(record).not.toBeNull();
    expect(record).toHaveAttribute("data-sequence", "complete");
    expect(
      Array.from(record?.querySelectorAll("[data-record-state]") ?? []).map(
        (element) => element.getAttribute("data-record-state"),
      ),
    ).toEqual(["REQUEST", "ROUTE", "RED", "GREEN", "GATE", "RECORDED"]);
    expect(within(record as HTMLElement).getByText("Sequence complete")).toBeVisible();
  });

  it("method_has_six_connected_stages_and_three_discipline_rules", () => {
    renderPage();
    const method = screen.getByRole("region", { name: "The connected method" });
    const stageItems = within(method).getAllByRole("listitem");

    expect(stageItems).toHaveLength(6);
    METHOD_STAGES.forEach((stage, index) => {
      const stageItem = stageItems[index];
      expect(within(stageItem).getByText(stage.state)).toBeVisible();
      expect(within(stageItem).getByText(stage.description)).toBeVisible();
      expect(within(stageItem).getByText(stage.output)).toBeVisible();
    });

    for (const rule of [
      "Failing test first",
      "Root cause before a fix",
      "Fresh evidence before done",
    ]) {
      expect(within(method).getByText(rule)).toBeVisible();
    }
  });

  it("proof_has_four_concrete_outputs_and_labels_samples", () => {
    const page = renderPage();
    const proof = screen.getByRole("region", { name: "Proof, not claims" });

    for (const output of [
      "Evidence gates",
      "Durable memory",
      "Crash recovery",
      "Independent review",
    ]) {
      expect(within(proof).getByRole("heading", { name: output })).toBeVisible();
    }

    const evidenceLines = page.querySelectorAll("[data-evidence-line]");
    expect(evidenceLines.length).toBeGreaterThan(0);
    evidenceLines.forEach((line) => {
      expect(line).toHaveTextContent(/^SAMPLE\s+EV \[/);
    });
  });

  it("page_integrates_route_lab_and_install_chooser", () => {
    renderPage();

    expect(
      screen.getByRole("heading", { name: "Choose the next engineering move" }),
    ).toBeVisible();
    expect(screen.getAllByRole("tab", { name: ROUTE_EXAMPLES[1].request })[0]).toBeVisible();
    expect(screen.getByRole("region", { name: "Install galdr" })).toBeVisible();
    expect(
      screen.getByRole("tab", { name: RUNTIME_INSTALLS[0].label }),
    ).toBeVisible();
  });

  it("public_links_target_repository_skills_testing_and_changelog", () => {
    renderPage();

    for (const href of [
      repository,
      `${repository}/tree/main/skills`,
      `${repository}/blob/main/skills/tdd/SKILL.md`,
      `${repository}/blob/main/CHANGELOG.md`,
    ]) {
      expect(document.querySelector(`a[href="${href}"]`)).toBeInTheDocument();
    }
  });

  it("page_has_no_fake_metrics_testimonials_or_starter_copy", () => {
    const page = renderPage();
    const copy = page.textContent ?? "";

    expect(copy).not.toMatch(
      /(?:\d[\d,.]*\+?\s+(?:stars|downloads|users)|testimonial|trusted by|your site is taking shape|building your site|codex-preview)/i,
    );
    expect(copy).not.toContain("—");
  });

  it("styles_define_brand_palette_focus_and_320px_layout", async () => {
    const css = await source("app/globals.css");

    expect(css).toMatch(/--background:\s*#[0-9a-f]{6}/i);
    expect(css).toMatch(/--foreground:\s*#[0-9a-f]{6}/i);
    expect(css).toMatch(/--route:\s*#[0-9a-f]{6}/i);
    expect(css).toMatch(/--verified:\s*#[0-9a-f]{6}/i);
    expect(css).toMatch(/--stop:\s*#[0-9a-f]{6}/i);
    expect(css).toMatch(/:focus-visible[\s\S]*outline:/);
    expect(css).toMatch(/@media\s*\(max-width:\s*320px\)/);
    expect(css).toMatch(/overflow-x:\s*(?:clip|hidden)/);
  });

  it("reduced_motion_disables_nonessential_animation", async () => {
    const css = [
      await source("app/globals.css"),
      await source("app/components/ExecutionRecord.module.css"),
    ].join("\n");

    expect(css).toMatch(
      /@media\s*\(prefers-reduced-motion:\s*reduce\)[\s\S]*(?:animation:\s*none|animation-duration:\s*0\.01ms)[\s\S]*(?:transition:\s*none|transition-duration:\s*0\.01ms)/,
    );
    expect(css).toMatch(
      /@media\s*\(prefers-reduced-motion:\s*reduce\)[\s\S]*(?:opacity:\s*1|visibility:\s*visible)/,
    );
  });
});
