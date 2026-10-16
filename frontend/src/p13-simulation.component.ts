import {
  Component,
  Input,
  OnChanges,
  OnDestroy,
  SimpleChanges,
  inject,
  signal,
} from "@angular/core";
import { HttpClient, HttpHeaders } from "@angular/common/http";
import { FormsModule } from "@angular/forms";
import { Subscription, timeout, finalize } from "rxjs";
type Asset = { id: string; name: string };
type Run = {
  id: string;
  asset_id: string;
  scenario_key: string;
  marker: string;
  command: string;
  status: string;
  started_at: string;
  ended_at: string | null;
  evidence_event_id: string | null;
  note: string;
};
@Component({
  selector: "app-p13-simulation",
  standalone: true,
  imports: [FormsModule],
  styles: [
    `
      .panel {
        border: 1px solid #293c5a;
        border-radius: 12px;
        background: #101a2d;
        color: #ecf1ff;
        padding: 18px;
        margin: 12px 0;
      }
      .row {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        align-items: center;
      }
      .field {
        background: #091425;
        color: white;
        border: 1px solid #394b6d;
        border-radius: 7px;
        padding: 10px;
        min-width: 200px;
        flex: 1;
      }
      .btn {
        background: #7154d5;
        border: 0;
        color: white;
        border-radius: 7px;
        padding: 10px;
        cursor: pointer;
      }
      .btn:disabled {
        opacity: 0.45;
      }
      .muted {
        font-size: 12px;
        color: #a5b5d1;
      }
      .err {
        color: #ff9f99;
      }
      .good {
        color: #8ce6b9;
      }
      table {
        width: 100%;
        border-collapse: collapse;
        font-size: 12px;
      }
      td,
      th {
        text-align: left;
        border-bottom: 1px solid #293951;
        padding: 10px;
      }
      .scroll {
        overflow-x: auto;
      }
      code {
        overflow-wrap: anywhere;
      }
    `,
  ],
  template: `
    <section class="panel">
      <h2>P13 · Authorized Lab Validation</h2>
      <p class="muted">
        Manual Ubuntu journal marker exercise only. The application NEVER runs
        guest commands or exploits. One-time API actions; no automatic polling.
      </p>
      @if (error()) {
        <p class="err">{{ error() }}</p>
      }
      @if (info()) {
        <p class="good">{{ info() }}</p>
      }
      <button class="btn" [disabled]="loading()" (click)="refresh()">
        {{ loading() ? "Loading…" : "Refresh runs" }}
      </button>
    </section>
    @if (canWrite) {
      <section class="panel">
        <h3>Start controlled scenario</h3>
        <div class="row">
          <select class="field" [(ngModel)]="assetId">
            <option value="">Select authorized Ubuntu asset</option>
            @for (a of assets; track a.id) {
              <option [value]="a.id">{{ a.name }}</option>
            }</select
          ><button
            class="btn"
            [disabled]="busy() || !assetId"
            (click)="start()"
          >
            Start manual run
          </button>
        </div>
        <p class="muted">Only registered lab Ubuntu assets are accepted.</p>
      </section>
    }
    <section class="panel scroll">
      <h3>Manual run history</h3>
      <table>
        <thead>
          <tr>
            <th>ASSET</th>
            <th>STATUS</th>
            <th>START</th>
            <th>EVIDENCE</th>
            <th>ACTIONS</th>
          </tr>
        </thead>
        <tbody>
          @for (r of rows(); track r.id) {
            <tr>
              <td>{{ assetName(r.asset_id) }}</td>
              <td>{{ r.status }}</td>
              <td>{{ r.started_at }}</td>
              <td>{{ r.evidence_event_id || "Not yet verified" }}</td>
              <td>
                <button class="btn" (click)="selected.set(r)">Inspect</button>
                @if (r.status === "awaiting_evidence" && canWrite) {
                  <button class="btn" [disabled]="busy()" (click)="verify(r)">
                    Verify evidence
                  </button>
                }
              </td>
            </tr>
          } @empty {
            <tr>
              <td colspan="5">No runs yet.</td>
            </tr>
          }
        </tbody>
      </table>
    </section>
    @if (selected(); as r) {
      <section class="panel">
        <h3>Run {{ r.id.slice(0, 8) }} — {{ r.status }}</h3>
        <p class="muted">
          Run the following harmless command YOURSELF on the named Ubuntu VM,
          after starting the run:
        </p>
        <p>
          <code>{{ r.command }}</code>
        </p>
        <button class="btn" (click)="copy(r.command)">Copy command</button>
        <p class="muted">
          Wait for Journald shipping, then click Verify evidence. The backend
          checks asset, unique marker and ingestion time.
        </p>
        @if (r.evidence_event_id) {
          <p class="good">Verified event: {{ r.evidence_event_id }}</p>
        }
        @if (r.status === "awaiting_evidence" && canWrite) {
          <div class="row">
            <input
              class="field"
              [(ngModel)]="note"
              placeholder="Reason for closing without evidence (10+ chars)"
            /><button
              class="btn"
              [disabled]="busy() || note.trim().length < 10"
              (click)="close(r)"
            >
              Close inconclusive
            </button>
          </div>
        }
      </section>
    }
  `,
})
export class P13SimulationComponent implements OnChanges, OnDestroy {
  @Input() token = "";
  @Input() assets: Asset[] = [];
  @Input() canWrite = false;
  private http = inject(HttpClient);
  private base = "http://127.0.0.1:8000";
  private lastToken = "";
  private subscriptions: Subscription[] = [];
  loading = signal(false);
  busy = signal(false);
  rows = signal<Run[]>([]);
  selected = signal<Run | null>(null);
  error = signal("");
  info = signal("");
  assetId = "";
  note = "";
  ngOnChanges(c: SimpleChanges) {
    if (c["token"] && this.token && this.token !== this.lastToken) {
      this.lastToken = this.token;
      this.refresh();
    }
  }
  ngOnDestroy() {
    this.subscriptions.forEach((s) => s.unsubscribe());
  }
  headers() {
    return {
      headers: new HttpHeaders({ Authorization: "Bearer " + this.token }),
    };
  }
  failure(e: any) {
    this.error.set(
      typeof e?.error?.detail === "string"
        ? e.error.detail
        : `Request failed (HTTP ${e?.status ?? 0})`,
    );
  }
  assetName(id: string) {
    return this.assets.find((a) => a.id === id)?.name || id;
  }
  copy(v: string) {
    if (navigator.clipboard)
      navigator.clipboard
        .writeText(v)
        .catch(() =>
          this.error.set("Copy unavailable; select command manually."),
        );
  }
  refresh() {
    if (this.loading() || !this.token) return;
    this.loading.set(true);
    this.error.set("");
    const s = this.http
      .get<Run[]>(this.base + "/simulation/runs", this.headers())
      .pipe(
        timeout(12000),
        finalize(() => this.loading.set(false)),
      )
      .subscribe({
        next: (v) => {
          this.rows.set(v);
          const selected = this.selected();
          if (selected)
            this.selected.set(v.find((x) => x.id === selected.id) || null);
        },
        error: (e) => this.failure(e),
      });
    this.subscriptions.push(s);
  }
  start() {
    if (!this.assetId || this.busy() || !this.canWrite) return;
    this.busy.set(true);
    this.error.set("");
    const s = this.http
      .post<Run>(
        this.base + "/simulation/runs",
        { asset_id: this.assetId, scenario_key: "ubuntu_journal_marker" },
        this.headers(),
      )
      .pipe(
        timeout(12000),
        finalize(() => this.busy.set(false)),
      )
      .subscribe({
        next: (r) => {
          this.selected.set(r);
          this.info.set(
            "Manual run started. No command was executed by PurpleForge.",
          );
          this.refresh();
        },
        error: (e) => this.failure(e),
      });
    this.subscriptions.push(s);
  }
  verify(r: Run) {
    if (this.busy() || !this.canWrite) return;
    this.busy.set(true);
    this.error.set("");
    const s = this.http
      .post<Run>(
        this.base + "/simulation/runs/" + r.id + "/verify",
        {},
        this.headers(),
      )
      .pipe(
        timeout(12000),
        finalize(() => this.busy.set(false)),
      )
      .subscribe({
        next: (v) => {
          this.selected.set(v);
          this.info.set("Unique event verified in stored telemetry.");
          this.refresh();
        },
        error: (e) => this.failure(e),
      });
    this.subscriptions.push(s);
  }
  close(r: Run) {
    if (this.busy() || this.note.trim().length < 10 || !this.canWrite) return;
    this.busy.set(true);
    const s = this.http
      .post<Run>(
        this.base + "/simulation/runs/" + r.id + "/close",
        { note: this.note.trim() },
        this.headers(),
      )
      .pipe(
        timeout(12000),
        finalize(() => this.busy.set(false)),
      )
      .subscribe({
        next: (v) => {
          this.selected.set(v);
          this.note = "";
          this.refresh();
        },
        error: (e) => this.failure(e),
      });
    this.subscriptions.push(s);
  }
}
