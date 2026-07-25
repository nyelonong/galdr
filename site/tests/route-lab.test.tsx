import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it } from "vitest";
import { ROUTE_EXAMPLES } from "../app/content";
import { RouteLab } from "../app/components/RouteLab";

function renderRouteLab() {
  const user = userEvent.setup();
  render(<RouteLab examples={ROUTE_EXAMPLES} />);
  return { user };
}

function tabFor(id: (typeof ROUTE_EXAMPLES)[number]["id"]) {
  const example = ROUTE_EXAMPLES.find((candidate) => candidate.id === id);
  if (!example) {
    throw new Error(`Missing route example: ${id}`);
  }
  return screen.getByRole("tab", { name: example.request });
}

describe("RouteLab", () => {
  afterEach(cleanup);

  it("route_lab_defaults_to_new_export_shape_synthesis", () => {
    renderRouteLab();

    expect(tabFor("new-export")).toHaveAttribute("aria-selected", "true");
    expect(screen.getByText("shape-synthesis")).toBeVisible();
    expect(
      screen.getByText("The desired outcome needs a useful boundary."),
    ).toBeVisible();
    expect(
      screen.getByText("Shape the workflow before implementation."),
    ).toBeVisible();
  });

  it("route_lab_click_updates_route_reason_and_next", async () => {
    const { user } = renderRouteLab();

    await user.click(tabFor("api-architecture"));

    expect(tabFor("api-architecture")).toHaveAttribute("aria-selected", "true");
    expect(screen.getByText("rearchitect")).toBeVisible();
    expect(
      screen.getByText("The system structure is now the constraint."),
    ).toBeVisible();
    expect(
      screen.getByText("Map the deployment and ownership seams."),
    ).toBeVisible();
  });

  it("route_lab_arrow_keys_move_and_wrap_selection", async () => {
    const { user } = renderRouteLab();
    const newExport = tabFor("new-export");

    newExport.focus();
    await user.keyboard("{ArrowLeft}");

    expect(tabFor("flaky-checkout")).toHaveFocus();
    expect(tabFor("flaky-checkout")).toHaveAttribute("aria-selected", "true");

    await user.keyboard("{ArrowLeft}");

    expect(tabFor("documentation")).toHaveFocus();
    expect(tabFor("documentation")).toHaveAttribute("aria-selected", "true");
  });

  it("route_lab_enter_and_space_activate_focused_request", async () => {
    const { user } = renderRouteLab();

    tabFor("documentation").focus();
    await user.keyboard("{Enter}");
    expect(tabFor("documentation")).toHaveAttribute("aria-selected", "true");

    tabFor("api-architecture").focus();
    await user.keyboard(" ");
    expect(tabFor("api-architecture")).toHaveAttribute("aria-selected", "true");
  });

  it("route_lab_active_state_is_exposed_without_color", () => {
    renderRouteLab();

    const activeTab = tabFor("new-export");
    expect(activeTab).toHaveAttribute("aria-selected", "true");
    expect(activeTab).toHaveTextContent("Selected");
    expect(screen.getByRole("tabpanel")).toHaveAttribute(
      "aria-labelledby",
      activeTab.id,
    );
  });

  it("route_lab_uses_a_nested_section_heading", () => {
    renderRouteLab();

    expect(
      screen.getByRole("heading", {
        level: 3,
        name: "Choose the next engineering move",
      }),
    ).toBeInTheDocument();
  });

  it("every_route_tab_controls_an_existing_panel", () => {
    renderRouteLab();

    const tabs = screen.getAllByRole("tab");
    const panels = screen.getAllByRole("tabpanel", { hidden: true });

    expect(panels).toHaveLength(ROUTE_EXAMPLES.length);
    tabs.forEach((tab) => {
      const panelId = tab.getAttribute("aria-controls");
      expect(panelId).not.toBeNull();
      expect(document.getElementById(panelId as string)).toHaveAttribute(
        "role",
        "tabpanel",
      );
    });
    expect(panels.filter((panel) => panel.hasAttribute("hidden"))).toHaveLength(
      ROUTE_EXAMPLES.length - 1,
    );
  });
});
