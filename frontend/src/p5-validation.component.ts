import { Component, Input, OnInit, inject, signal } from "@angular/core";
import { forkJoin, timeout, finalize } from "rxjs";
import { HttpClient, HttpHeaders } from "@angular/common/http";
import { FormsModule } from "@angular/forms";

type Item = { id: string; name: string };
type Scenario = {
  id: string;
  name: string;
  rule_id: string;
  asset_id: string;
  technique_id: string;
  instructions: string;
};
type Run = {
  id: string;
  scenario_id: string;
  status: string;
  started_at: string;
  evidence_count: number;
  notes: string;
};
@Component({
  selector: "app-p5-validation",
  standalone: true,
  imports: [FormsModule],
  styles: [
    `
      .p5-panel {
        background: #101a2d;
        border: 1px solid #30405c;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 16px;
        color: #e8edff;
      }
      .p5-row {
        display: flex;
        gap: 12px;
        flex-wrap: wrap;
        align-items: center;
        margin: 12px 0;
      }
      .p5-row > * {
        flex: 1;
        min-width: 150px;
      }
      .p5-field {
        background: #0a1324;
        border: 1px solid #3a4b67;
        border-radius: 6px;
        padding: 10px;
        color: #eef;
        width: 100%;
        box-sizing: border-box;
      }
      .p5-btn {
        background: #7656d9;
        color: white;
        border: 0;
        border-radius: 6px;
        padding: 10px;
        cursor: pointer;
      }
      .p5-btn:disabled {
        opacity: 0.5;
        cursor: not-allowed;
      }
      .p5-table {
        width: 100%;
        border-collapse: collapse;
        text-align: left;
      }
      .p5-table td,
      .p5-table th {
        padding: 12px 8px;
        border-bottom: 1px solid #263550;
        font-size: 13px;
      }
      .p5-muted {
        color: #9eabc5;
        font-size: 12px;
      }
      .p5-error {
        color: #ffb3a9;
      }
      .p5-ok {
        color: #8fe4be;
      }
    `,
  ],
  template: ` <section class="p5-panel">
      <h2>P5 · Detection Validation & ATT&CK Mapping</h2>
      <p class="p5-muted">
        Human-driven non-destructive tests. Coverage measures observed scenario
        evidence, not the entire ATT&CK matrix.
      </p>
      <div class="p5-row">
        <button class="p5-btn" [disabled]="busy() || loading" (click)="load()">
          Refresh validation</button
        ><span class="p5-muted">{{ summary() }}</span>
      </div>
      @if (error()) {
        <p class="p5-error">{{ error() }}</p>
      }
      @if (message()) {
        <p class="p5-ok">{{ message() }}</p>
      }
    </section>
    @if (canWrite) {
      <section class="p5-panel">
        <h3>Register validation scenario</h3>
        <div class="p5-row">
          <input
            class="p5-field"
            placeholder="Scenario name"
            [(ngModel)]="name"
            name="name"
          />
          <select class="p5-field" [(ngModel)]="ruleId" name="rule">
            <option value="">Select detection rule</option>
            @for (r of rules(); track r.id) {
              <option [value]="r.id">{{ r.name }}</option>
            }
          </select>
          <select class="p5-field" [(ngModel)]="assetId" name="asset">
            <option value="">Select asset</option>
            @for (a of assets; track a.id) {
              <option [value]="a.id">{{ a.name }}</option>
            }
          </select>
        </div>
        <div class="p5-row">
          <input
            class="p5-field"
            placeholder="Technique ID e.g. T1059.001"
            [(ngModel)]="techniqueId"
            name="technique"
          />
          <input
            class="p5-field"
            placeholder="Description (optional)"
            [(ngModel)]="description"
            name="description"
          />
        </div>
        <div class="p5-row">
          <textarea
            class="p5-field"
            [(ngModel)]="instructions"
            name="instructions"
            rows="3"
            placeholder="Describe authorized harmless validation steps. Nothing executes automatically."
          ></textarea>
        </div>
        <button
          class="p5-btn"
          [disabled]="
            busy() ||
            !name.trim() ||
            !ruleId ||
            !assetId ||
            !techniqueId ||
            !instructions.trim()
          "
          (click)="create()"
        >
          Create scenario
        </button>
      </section>
    }
    <section class="p5-panel">
      <h3>Validation scenarios</h3>
      <div style="overflow-x:auto">
        <table class="p5-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>ATT&CK reference</th>
              <th>Rule</th>
              <th>Asset</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            @for (s of scenarios(); track s.id) {
              <tr>
                <td>
                  {{ s.name }}
                  <p class="p5-muted">{{ s.instructions }}</p>
                </td>
                <td>{{ s.technique_id }}</td>
                <td>{{ label(rules(), s.rule_id) }}</td>
                <td>{{ label(assets, s.asset_id) }}</td>
                <td>
                  @if (canWrite) {
                    <button
                      class="p5-btn"
                      [disabled]="busy()"
                      (click)="start(s)"
                    >
                      Start run
                    </button>
                  }
                </td>
              </tr>
            } @empty {
              <tr>
                <td colspan="5">No scenarios yet.</td>
              </tr>
            }
          </tbody>
        </table>
      </div>
    </section>
    <section class="p5-panel">
      <h3>Validation runs</h3>
      <div style="overflow-x:auto">
        <table class="p5-table">
          <thead>
            <tr>
              <th>Scenario</th>
              <th>Started</th>
              <th>Outcome</th>
              <th>Linked findings</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            @for (r of runs(); track r.id) {
              <tr>
                <td>{{ scenarioLabel(r.scenario_id) }}</td>
                <td>{{ r.started_at }}</td>
                <td>{{ r.status }}</td>
                <td>{{ r.evidence_count }}</td>
                <td>
                  @if (r.status === "running" && canWrite) {
                    <button
                      class="p5-btn"
                      [disabled]="busy()"
                      (click)="finish(r, true)"
                    >
                      Finish test
                    </button>
                    <button class="p5-btn" (click)="finish(r, false)">
                      Inconclusive
                    </button>
                  } @else {
                    <button class="p5-btn" (click)="showEvidence(r.id)">
                      Evidence
                    </button>
                  }
                </td>
              </tr>
            } @empty {
              <tr>
                <td colspan="5">No validation runs yet.</td>
              </tr>
            }
          </tbody>
        </table>
      </div>
      @if (evidence().length) {
        <h4>Linked event evidence</h4>
        @for (e of evidence(); track e.finding_id) {
          <p class="p5-muted">{{ e.event_type }} · {{ e.message }}</p>
        }
      }
    </section>`,
})
export class P5ValidationComponent implements OnInit {
  private http = inject(HttpClient);
  @Input() token = "";
  @Input() assets: Item[] = [];
  @Input() canWrite = false;
  rules = signal<Item[]>([]);
  scenarios = signal<Scenario[]>([]);
  runs = signal<Run[]>([]);
  summary = signal("Loading...");
  error = signal("");
  message = signal("");
  busy = signal(false);
  evidence = signal<any[]>([]);
  name = "";
  description = "";
  ruleId = "";
  assetId = "";
  techniqueId = "T1059.001";
  instructions = "";
  private readonly api = "http://127.0.0.1:8000";
  private opts() {
    return {
      headers: new HttpHeaders({ Authorization: "Bearer " + this.token }),
    };
  }
  // Component is constructed when the logged-in user visits Validation.
  // Asset/role changes must never trigger network requests.
  ngOnInit() {
    if (this.token) this.load();
  }
  loading = false;
  label(items: Item[], id: string) {
    return items.find((x) => x.id === id)?.name || id;
  }
  scenarioLabel(id: string) {
    return this.label(this.scenarios(), id);
  }
  fail(e: any) {
    this.busy.set(false);
    this.error.set(
      typeof e.error?.detail === "string"
        ? e.error.detail
        : `HTTP ${e.status || "error"}`,
    );
  }
  load() {
    if (!this.token || this.loading) return;
    this.loading = true;
    this.error.set("");
    this.summary.set("Loading validation data...");
    // One bounded batch of four requests, not a reactive change-detection loop.
    forkJoin({
      rules: this.http.get<Item[]>(this.api + "/detections/rules", this.opts()),
      scenarios: this.http.get<Scenario[]>(
        this.api + "/validation/scenarios",
        this.opts(),
      ),
      runs: this.http.get<Run[]>(
        this.api + "/validation/runs?limit=50",
        this.opts(),
      ),
      summary: this.http.get<any>(
        this.api + "/validation/summary",
        this.opts(),
      ),
    })
      .pipe(
        timeout(12000),
        finalize(() => {
          this.loading = false;
        }),
      )
      .subscribe({
        next: (x) => {
          this.rules.set(x.rules);
          this.scenarios.set(x.scenarios);
          this.runs.set(x.runs);
          const s = x.summary;
          this.summary.set(
            `${s.passed_scenarios ?? 0}/${s.enabled_scenarios ?? 0} scenarios validated · ${s.coverage_percent ?? 0}% observed coverage`,
          );
        },
        error: (e) => {
          this.summary.set("Unable to load validation data.");
          this.error.set(
            e?.name === "TimeoutError"
              ? "Validation API timed out after 12 seconds. Check FastAPI logs and database performance."
              : typeof e?.error?.detail === "string"
                ? e.error.detail
                : `Validation request failed (HTTP ${e?.status ?? "unknown"}). Check Network tab and FastAPI logs.`,
          );
        },
      });
  }
  create() {
    this.error.set("");
    this.busy.set(true);
    this.http
      .post(
        this.api + "/validation/scenarios",
        {
          name: this.name,
          description: this.description,
          rule_id: this.ruleId,
          asset_id: this.assetId,
          technique_id: this.techniqueId,
          instructions: this.instructions,
        },
        this.opts(),
      )
      .subscribe({
        next: () => {
          this.busy.set(false);
          this.message.set("Scenario created");
          this.name = "";
          this.load();
        },
        error: (e) => this.fail(e),
      });
  }
  start(s: Scenario) {
    this.busy.set(true);
    this.error.set("");
    this.http
      .post(this.api + `/validation/scenarios/${s.id}/start`, {}, this.opts())
      .subscribe({
        next: () => {
          this.busy.set(false);
          this.message.set(
            "Run started. Generate authorized lab telemetry and evaluate P4 detections BEFORE finishing.",
          );
          this.load();
        },
        error: (e) => this.fail(e),
      });
  }
  finish(r: Run, performed: boolean) {
    this.busy.set(true);
    this.http
      .post(
        this.api + `/validation/runs/${r.id}/finish`,
        { test_performed: performed, notes: "Manual evidence review" },
        this.opts(),
      )
      .subscribe({
        next: (v: any) => {
          this.busy.set(false);
          this.message.set(
            `Run ${v.status} with ${v.evidence_count} linked findings`,
          );
          this.load();
        },
        error: (e) => this.fail(e),
      });
  }
  showEvidence(id: string) {
    this.http
      .get<any[]>(this.api + `/validation/runs/${id}/evidence`, this.opts())
      .subscribe({
        next: (x) => {
          this.evidence.set(x);
          if (!x.length) this.message.set("No linked findings for this run");
        },
        error: (e) => this.fail(e),
      });
  }
}
