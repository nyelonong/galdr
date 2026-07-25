import { ExecutionRecord } from "./components/ExecutionRecord";
import { InstallChooser } from "./components/InstallChooser";
import { RouteLab } from "./components/RouteLab";
import { METHOD_STAGES, ROUTE_EXAMPLES, RUNTIME_INSTALLS } from "./content";

const repository = "https://github.com/nyelonong/galdr";

const proofOutputs = [
  {
    title: "Evidence gates",
    body: "A gate records the command, verdict, key numbers, and commit before a completion claim can pass.",
  },
  {
    title: "Durable memory",
    body: "Decisions and evidence remain available to the next request instead of living only in one chat.",
  },
  {
    title: "Crash recovery",
    body: "A continuation reads the brief, current progress, and live repository state before work resumes.",
  },
  {
    title: "Independent review",
    body: "A reviewer inspects the diff and reruns the gate. Another agent's report is never accepted as proof.",
  },
] as const;

export default function Home() {
  return (
    <div className="site-frame">
      <header className="masthead">
        <a className="wordmark" href="#top" aria-label="galdr">
          <span aria-hidden="true">ᚷ</span>
          galdr
        </a>
        <nav aria-label="Primary">
          <a href="#method">METHOD</a>
          <a href="#proof">PROOF</a>
          <a href="#install">INSTALL</a>
          <a href={repository}>GitHub</a>
        </nav>
      </header>

      <main id="top">
        <section className="hero" aria-labelledby="hero-title">
          <div className="hero-copy">
            <p className="eyebrow">
              <span>STATE 00</span>
              <span>REQUEST</span>
            </p>
            <h1 id="hero-title">
              A method for engineering agents that does not trust claims.
            </h1>
            <p className="lede">
              galdr routes each request, requires a failing test before production
              code, and records fresh evidence before work is called done.
            </p>
            <div className="hero-actions">
              <a className="action action-primary" href="#method">
                See the method
              </a>
              <a className="action" href="#install">
                Install galdr
              </a>
            </div>
          </div>
          <ExecutionRecord />
        </section>

        <section
          className="method section-block"
          id="method"
          aria-labelledby="method-title"
        >
          <div className="section-intro">
            <p className="eyebrow">
              <span>STATE 01</span>
              <span>METHOD</span>
            </p>
            <h2 id="method-title">The connected method</h2>
            <p className="section-summary">
              route → shape → plan → waves → verify → memory
            </p>
          </div>

          <ol className="method-flow" aria-label="galdr method stages">
            {METHOD_STAGES.map((stage, index) => (
              <li key={stage.id}>
                <div className="stage-marker">
                  <span>{String(index + 1).padStart(2, "0")}</span>
                  <span>{stage.state}</span>
                </div>
                <h3>{stage.name}</h3>
                <p>{stage.description}</p>
                <div className="stage-output">
                  <span>OUTPUT</span>
                  <strong>{stage.output}</strong>
                </div>
              </li>
            ))}
          </ol>

          <div className="discipline" aria-label="Three discipline rules">
            <article>
              <span>RED / 01</span>
              <h3>Failing test first</h3>
              <p>The contract fails before production code changes.</p>
            </article>
            <article>
              <span>DEBUG / 02</span>
              <h3>Root cause before a fix</h3>
              <p>Reproduce and isolate the cause before changing behavior.</p>
            </article>
            <article>
              <span>GATE / 03</span>
              <h3>Fresh evidence before done</h3>
              <p>Run the proving command again after the last code change.</p>
            </article>
          </div>
        </section>

        <section className="route-section section-block" aria-labelledby="route-title">
          <div className="section-intro split-intro">
            <div>
              <p className="eyebrow">
                <span>STATE 02</span>
                <span>ROUTE</span>
              </p>
              <h2 id="route-title">The request sets the workflow</h2>
            </div>
            <p className="section-summary">
              Four repository-backed examples. One deterministic next move for each.
            </p>
          </div>
          <RouteLab examples={ROUTE_EXAMPLES} />
        </section>

        <section
          className="proof section-block"
          id="proof"
          aria-labelledby="proof-title"
        >
          <div className="section-intro split-intro">
            <div>
              <p className="eyebrow">
                <span>STATE 03</span>
                <span>GATE</span>
              </p>
              <h2 id="proof-title">Proof, not claims</h2>
            </div>
            <p className="section-summary">
              galdr keeps concrete outputs that another engineer can inspect and
              rerun.
            </p>
          </div>

          <div className="proof-grid">
            {proofOutputs.map(({ title, body }, index) => (
              <article key={title}>
                <span className="proof-index">{String(index + 1).padStart(2, "0")}</span>
                <h3>{title}</h3>
                <p>{body}</p>
              </article>
            ))}
          </div>

          <div className="evidence-samples" aria-label="Sample evidence">
            <p data-evidence-line>
              <span>SAMPLE</span> EV [3.1 RED] npx vitest run
              tests/page-contract.test.ts → FAIL (expected page contract)
            </p>
            <p data-evidence-line>
              <span>SAMPLE</span> EV [3.1 GREEN] npx vitest run
              tests/page-contract.test.ts → PASS 10 passed 0 skipped
            </p>
          </div>

          <div className="proof-links" aria-label="Inspect the public proof">
            <a href={`${repository}/tree/main/skills`}>Browse the skills</a>
            <a href={`${repository}/blob/main/skills/tdd/SKILL.md`}>
              Read the testing contract
            </a>
            <a href={`${repository}/blob/main/CHANGELOG.md`}>Read the changelog</a>
          </div>
        </section>

        <section
          className="install section-block"
          id="install"
          aria-labelledby="install-title"
        >
          <div className="section-intro split-intro">
            <div>
              <p className="eyebrow">
                <span>STATE 04</span>
                <span>INSTALL</span>
              </p>
              <h2 id="install-title">Install galdr</h2>
            </div>
            <p className="section-summary">
              Choose the agent runtime, copy the public install command, then
              enable core routing when you want it.
            </p>
          </div>
          <div className="install-shell">
            <InstallChooser installs={RUNTIME_INSTALLS} />
          </div>
          <p className="install-note">
            Need the complete package?
            <a href={repository}> Open the public repository</a>
            {" or "}
            <a href={`${repository}/tree/main/skills`}>read the full documentation</a>.
          </p>
        </section>
      </main>

      <footer>
        <p>galdr is a routed, evidence-gated engineering method for coding agents.</p>
        <a href={repository}>Public repository</a>
        <span>2026</span>
      </footer>
    </div>
  );
}
