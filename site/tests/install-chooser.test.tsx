import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { RUNTIME_INSTALLS } from "../app/content";
import { InstallChooser } from "../app/components/InstallChooser";

const claudeInstall = [
  "/plugin marketplace add nyelonong/galdr",
  "/plugin install galdr@nyelonong",
].join("\n");

const originalClipboard = Object.getOwnPropertyDescriptor(navigator, "clipboard");

function setClipboard(writeText: (text: string) => Promise<void>) {
  Object.defineProperty(navigator, "clipboard", {
    configurable: true,
    value: { writeText },
  });
}

function visiblePanel() {
  return screen.getByRole("tabpanel");
}

afterEach(() => {
  cleanup();

  if (originalClipboard) {
    Object.defineProperty(navigator, "clipboard", originalClipboard);
    return;
  }

  Reflect.deleteProperty(navigator, "clipboard");
});

describe("InstallChooser", () => {
  it("install_chooser_defaults_to_claude", () => {
    render(<InstallChooser installs={RUNTIME_INSTALLS} />);

    expect(screen.getByRole("tab", { name: "Claude Code" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    expect(within(visiblePanel()).getByTestId("install-commands").textContent).toBe(
      claudeInstall,
    );
    expect(within(visiblePanel()).getByTestId("enable-command").textContent).toBe(
      "/galdr:core install claude",
    );

    fireEvent.click(screen.getByRole("tab", { name: "Codex" }));

    expect(within(visiblePanel()).getByTestId("install-commands").textContent).toBe(
      "npx skills add nyelonong/galdr",
    );
    expect(within(visiblePanel()).getByTestId("enable-command").textContent).toBe(
      "/galdr:core install codex",
    );
  });

  it("install_chooser_arrow_keys_switch_runtime", () => {
    render(<InstallChooser installs={RUNTIME_INSTALLS} />);

    const claudeTab = screen.getByRole("tab", { name: "Claude Code" });
    claudeTab.focus();
    fireEvent.keyDown(claudeTab, { key: "ArrowRight" });

    expect(screen.getByRole("tab", { name: "Codex" })).toHaveFocus();
    expect(screen.getByRole("tab", { name: "Codex" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    expect(within(visiblePanel()).getByTestId("enable-command").textContent).toBe(
      "/galdr:core install codex",
    );

    fireEvent.keyDown(screen.getByRole("tab", { name: "Codex" }), {
      key: "ArrowLeft",
    });

    expect(claudeTab).toHaveFocus();
    expect(claudeTab).toHaveAttribute("aria-selected", "true");
  });

  it("copy_install_writes_exact_visible_commands", async () => {
    const writeText = vi.fn<(text: string) => Promise<void>>().mockResolvedValue();
    setClipboard(writeText);
    render(<InstallChooser installs={RUNTIME_INSTALLS} />);

    const visibleCommands = within(visiblePanel()).getByTestId(
      "install-commands",
    ).textContent;
    await fireEvent.click(screen.getByRole("button", { name: "Copy install" }));

    expect(visibleCommands).toBe(claudeInstall);
    expect(writeText).toHaveBeenCalledWith(visibleCommands);
  });

  it("copy_enable_writes_exact_core_command", async () => {
    const writeText = vi.fn<(text: string) => Promise<void>>().mockResolvedValue();
    setClipboard(writeText);
    render(<InstallChooser installs={RUNTIME_INSTALLS} />);

    const visibleCommand = within(visiblePanel()).getByTestId(
      "enable-command",
    ).textContent;
    await fireEvent.click(screen.getByRole("button", { name: "Copy core enable" }));

    expect(visibleCommand).toBe("/galdr:core install claude");
    expect(writeText).toHaveBeenCalledWith(visibleCommand);
  });

  it("copy_success_is_announced", async () => {
    setClipboard(vi.fn<(text: string) => Promise<void>>().mockResolvedValue());
    render(<InstallChooser installs={RUNTIME_INSTALLS} />);

    await fireEvent.click(screen.getByRole("button", { name: "Copy install" }));

    await waitFor(() => {
      expect(screen.getByRole("status")).toHaveTextContent(
        "Install commands copied.",
      );
    });
  });

  it("copy_failure_is_announced", async () => {
    setClipboard(
      vi.fn<(text: string) => Promise<void>>().mockRejectedValue(new Error("blocked")),
    );
    render(<InstallChooser installs={RUNTIME_INSTALLS} />);

    await fireEvent.click(screen.getByRole("button", { name: "Copy core enable" }));

    await waitFor(() => {
      expect(screen.getByRole("status")).toHaveTextContent(
        "Could not copy core enable command.",
      );
    });
  });

  it("every_runtime_tab_controls_an_existing_panel", () => {
    render(<InstallChooser installs={RUNTIME_INSTALLS} />);

    const tabs = screen.getAllByRole("tab");
    const panels = screen.getAllByRole("tabpanel", { hidden: true });

    expect(panels).toHaveLength(RUNTIME_INSTALLS.length);
    tabs.forEach((tab) => {
      const panelId = tab.getAttribute("aria-controls");
      expect(panelId).not.toBeNull();
      expect(document.getElementById(panelId as string)).toHaveAttribute(
        "role",
        "tabpanel",
      );
    });
    expect(panels.filter((panel) => panel.hasAttribute("hidden"))).toHaveLength(
      RUNTIME_INSTALLS.length - 1,
    );
  });
});
