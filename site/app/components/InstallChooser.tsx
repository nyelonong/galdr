"use client";

import { useRef, useState } from "react";
import type { RuntimeInstall } from "../content";
import styles from "./InstallChooser.module.css";

export interface InstallChooserProps {
  installs: readonly RuntimeInstall[];
}

type CopyTarget = "install" | "core enable";

export function InstallChooser({ installs }: InstallChooserProps) {
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [copyStatus, setCopyStatus] = useState("");
  const tabRefs = useRef<Array<HTMLButtonElement | null>>([]);

  function selectRuntime(index: number) {
    setSelectedIndex(index);
  }

  function selectRuntimeFromKey(
    event: React.KeyboardEvent<HTMLButtonElement>,
    index: number,
  ) {
    if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") {
      return;
    }

    event.preventDefault();
    const offset = event.key === "ArrowRight" ? 1 : -1;
    const nextIndex = (index + offset + installs.length) % installs.length;
    selectRuntime(nextIndex);
    tabRefs.current[nextIndex]?.focus();
  }

  async function copy(command: string, target: CopyTarget) {
    try {
      await navigator.clipboard.writeText(command);
      setCopyStatus(
        target === "install"
          ? "Install commands copied."
          : "Core enable command copied.",
      );
    } catch {
      setCopyStatus(
        target === "install"
          ? "Could not copy install commands."
          : "Could not copy core enable command.",
      );
    }
  }

  return (
    <section className={styles.chooser} aria-label="Runtime installation">
      <div className={styles.tabs} role="tablist" aria-label="Runtime">
        {installs.map((install, index) => {
          const isSelected = index === selectedIndex;

          return (
            <button
              key={install.id}
              ref={(element) => {
                tabRefs.current[index] = element;
              }}
              id={`${install.id}-tab`}
              className={styles.tab}
              type="button"
              role="tab"
              aria-controls={`${install.id}-panel`}
              aria-selected={isSelected}
              tabIndex={isSelected ? 0 : -1}
              onClick={() => selectRuntime(index)}
              onKeyDown={(event) => selectRuntimeFromKey(event, index)}
            >
              {install.label}
            </button>
          );
        })}
      </div>

      {installs.map((install, index) => {
        const installCommands = install.install.join("\n");

        return (
          <div
            key={install.id}
            id={`${install.id}-panel`}
            className={styles.panel}
            role="tabpanel"
            aria-labelledby={`${install.id}-tab`}
            hidden={index !== selectedIndex}
          >
            <div className={styles.commandGroup}>
              <div className={styles.commandHeader}>
                <h3>Install galdr</h3>
                <button
                  type="button"
                  className={styles.copyButton}
                  onClick={() => copy(installCommands, "install")}
                >
                  Copy install
                </button>
              </div>
              <pre className={styles.command} data-testid="install-commands">
                {installCommands}
              </pre>
            </div>

            <div className={styles.commandGroup}>
              <div className={styles.commandHeader}>
                <h3>Enable core</h3>
                <button
                  type="button"
                  className={styles.copyButton}
                  onClick={() => copy(install.enable, "core enable")}
                >
                  Copy core enable
                </button>
              </div>
              <pre className={styles.command} data-testid="enable-command">
                {install.enable}
              </pre>
            </div>
          </div>
        );
      })}

      <p className={styles.copyStatus} role="status" aria-live="polite">
        {copyStatus}
      </p>
    </section>
  );
}
