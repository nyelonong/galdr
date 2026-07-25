import styles from "./ExecutionRecord.module.css";

const states = [
  {
    state: "REQUEST",
    detail: "Add a customer report export.",
    status: "Received",
  },
  {
    state: "ROUTE",
    detail: "shape-synthesis",
    status: "Selected",
  },
  {
    state: "RED",
    detail: "The focused page contract fails.",
    status: "Expected stop",
  },
  {
    state: "GREEN",
    detail: "The focused page contract passes.",
    status: "Verified",
  },
  {
    state: "GATE",
    detail: "Tests, build, lint, and types pass.",
    status: "Verified",
  },
  {
    state: "RECORDED",
    detail: "Command, verdict, and commit are kept.",
    status: "Complete",
  },
] as const;

export function ExecutionRecord() {
  return (
    <div
      className={styles.record}
      data-execution-record
      data-sequence="complete"
      aria-label="Deterministic execution record"
    >
      <div className={styles.header}>
        <span>EXECUTION / 01</span>
        <span>DETERMINISTIC</span>
      </div>
      <ol className={styles.states}>
        {states.map(({ state, detail, status }, index) => (
          <li
            key={state}
            className={styles.state}
            data-record-state={state}
            style={{ "--state-index": index } as React.CSSProperties}
          >
            <span className={styles.index}>{String(index + 1).padStart(2, "0")}</span>
            <span className={styles.name}>{state}</span>
            <span className={styles.detail}>{detail}</span>
            <span className={styles.status}>{status}</span>
          </li>
        ))}
      </ol>
      <p className={styles.complete}>
        <span aria-hidden="true">■</span>
        Sequence complete
      </p>
    </div>
  );
}
