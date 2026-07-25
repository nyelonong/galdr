"use client";

import { useRef, useState, type KeyboardEvent } from "react";
import type { RouteExample } from "../content";
import styles from "./RouteLab.module.css";

export type RouteLabProps = {
  examples: readonly RouteExample[];
};

export function RouteLab({ examples }: RouteLabProps) {
  const defaultIndex = examples.findIndex(({ id }) => id === "new-export");
  const [selectedIndex, setSelectedIndex] = useState(() =>
    defaultIndex >= 0 ? defaultIndex : 0,
  );
  const tabs = useRef<(HTMLButtonElement | null)[]>([]);
  const selected = examples[selectedIndex];

  function select(index: number) {
    setSelectedIndex(index);
    tabs.current[index]?.focus();
  }

  function handleKeyDown(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    if (examples.length === 0) {
      return;
    }

    if (event.key === "ArrowRight" || event.key === "ArrowDown") {
      event.preventDefault();
      select((index + 1) % examples.length);
      return;
    }

    if (event.key === "ArrowLeft" || event.key === "ArrowUp") {
      event.preventDefault();
      select((index - 1 + examples.length) % examples.length);
      return;
    }

    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      setSelectedIndex(index);
    }
  }

  if (!selected) {
    return null;
  }

  return (
    <section className={styles.routeLab} aria-labelledby="route-lab-heading">
      <p className={styles.eyebrow}>Route lab</p>
      <h3 id="route-lab-heading">Choose the next engineering move</h3>
      <div className={styles.tabs} role="tablist" aria-label="Example requests">
        {examples.map((example, index) => {
          const isSelected = index === selectedIndex;
          const tabId = `route-lab-tab-${example.id}`;
          const panelId = `route-lab-panel-${example.id}`;

          return (
            <button
              key={example.id}
              ref={(element) => {
                tabs.current[index] = element;
              }}
              className={styles.tab}
              type="button"
              role="tab"
              id={tabId}
              aria-label={example.request}
              aria-selected={isSelected}
              aria-controls={panelId}
              tabIndex={isSelected ? 0 : -1}
              onClick={() => select(index)}
              onKeyDown={(event) => handleKeyDown(event, index)}
            >
              <span>{example.request}</span>
              {isSelected ? <span className={styles.selected}>Selected</span> : null}
            </button>
          );
        })}
      </div>

      {examples.map((example, index) => (
        <div
          key={example.id}
          className={styles.result}
          role="tabpanel"
          id={`route-lab-panel-${example.id}`}
          aria-labelledby={`route-lab-tab-${example.id}`}
          hidden={index !== selectedIndex}
        >
          <dl>
            <div>
              <dt>Route</dt>
              <dd>{example.route}</dd>
            </div>
            <div>
              <dt>Reason</dt>
              <dd>{example.reason}</dd>
            </div>
            <div>
              <dt>Next action</dt>
              <dd>{example.next}</dd>
            </div>
          </dl>
        </div>
      ))}
    </section>
  );
}
