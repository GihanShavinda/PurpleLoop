import {
  Component,
  Input,
  OnChanges,
  OnDestroy,
  SimpleChanges,
  inject,
  signal,
} from "@angular/core";
import { FormsModule } from "@angular/forms";
import { HttpClient, HttpHeaders } from "@angular/common/http";
import { Subscription, finalize, timeout } from "rxjs";
type Indicator = {
  id: string;
  kind: string;
  value: string;
  confidence: number;
  source_label: string;
  description: string;
  enabled: boolean;
};
type IntelMatch = {
  id: string;
  indicator: string;
  kind: string;
  asset_id: string;
  event_time: string;
  event_type: string;
  message: string;
};
@Component({
  selector: "app-p8-intelligence",
  standalone: true,
  imports: [FormsModule],
  styles: [
    `
      .p8-panel {
        background: #101a2d;
        border: 1px solid #30405c;
        border-radius: 12px;
        padding: 18px;
        margin-bottom: 15px;
        color: #e8edff;
      }
      .p8-row {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        align-items: center;
        margin: 10px 0;
      }
      .p8-row > * {
        flex: 1;
        min-width: 130px;
      }
      .p8-field {
        background: #091323;
        color: #e8edff;
        border: 1px solid #364866;
        border-radius: 8px;
        padding: 10px;
        max-width: 100%;
        box-sizing: border-box;
      }
      .p8-btn {
        background: #7255d5;
        color: #fff;
        border: 1px solid #8573e6;
        border-radius: 7px;
        padding: 10px;
        cursor: pointer;
      }
      .p8-btn:disabled {
        opacity: 0.45;
        cursor: default;
      }
      .p8-muted {
        font-size: 12px;
        color: #a9b6d1;
      }
      .p8-table {
        width: 100%;
        border-collapse: collapse;
        text-align: left;
      }
      .p8-table td,
      .p8-table th {
        border-bottom: 1px solid #2b3953;
        padding: 9px;
        font-size: 12px;
        overflow-wrap: anywhere;
      }
      .p8-scroll {
        overflow-x: auto;
      }
    `,
  ],
  template: `
    <section class="p8-panel">
      <h2>P8 · Threat Intelligence & IOC Enrichment</h2>
      <p class="p8-muted">
        Reviewed manual indicators only · recorded telemetry only · no external
        lookups, scans, or automatic blocking
      </p>
      @if (error()) {
        <p style="color:#ffaba8">{{ error() }}</p>
      }
      @if (info()) {
        <p style="color:#78dcb2">{{ info() }}</p>
      }
      <div class="p8-row">
        <div>
          Indicators: <b>{{ summary().indicators }}</b>
        </div>
        <div>
          Enabled: <b>{{ summary().enabled }}</b>
        </div>
        <div>
          Evidence matches: <b>{{ summary().matches }}</b>
        </div>
        <button class="p8-btn" [disabled]="loading()" (click)="refresh()">
          Refresh intelligence
        </button>
      </div>
    </section>
    @if (canWrite) {
      <section class="p8-panel">
        <h3>Register reviewed indicator</h3>
        <div class="p8-row">
          <select class="p8-field" [(ngModel)]="kind">
            <option value="ip">IP</option>
            <option value="domain">Domain</option>
            <option value="hash">Hash</option>
            <option value="process">Process</option>
          </select>
          <input
            class="p8-field"
            placeholder="Exact indicator value"
            [(ngModel)]="value"
          />
          <input
            class="p8-field"
            placeholder="Source label"
            [(ngModel)]="sourceLabel"
          />
          <input
            class="p8-field"
            type="number"
            min="0"
            max="100"
            [(ngModel)]="confidence"
          />
        </div>
        <div class="p8-row">
          <input
            class="p8-field"
            placeholder="Analyst description"
            [(ngModel)]="description"
          />
          <button
            class="p8-btn"
            [disabled]="saving() || !value.trim()"
            (click)="add()"
          >
            Register indicator
          </button>
        </div>
      </section>
    }
    <section class="p8-panel">
      <h3>Indicators</h3>
      <div class="p8-scroll">
        <table class="p8-table">
          <thead>
            <tr>
              <th>TYPE</th>
              <th>VALUE</th>
              <th>SOURCE</th>
              <th>CONFIDENCE</th>
              <th>STATE</th>
              <th>ACTION</th>
            </tr>
          </thead>
          <tbody>
            @for (i of indicators(); track i.id) {
              <tr>
                <td>{{ i.kind }}</td>
                <td>{{ i.value }}</td>
                <td>{{ i.source_label }}</td>
                <td>{{ i.confidence }}%</td>
                <td>{{ i.enabled ? "Enabled" : "Disabled" }}</td>
                <td>
                  @if (canWrite) {
                    <button
                      class="p8-btn"
                      [disabled]="saving()"
                      (click)="toggle(i)"
                    >
                      {{ i.enabled ? "Disable" : "Enable" }}
                    </button>
                  }
                </td>
              </tr>
            } @empty {
              <tr>
                <td colspan="6">No reviewed indicators yet.</td>
              </tr>
            }
          </tbody>
        </table>
      </div>
    </section>
    @if (canWrite) {
      <section class="p8-panel">
        <h3>Run bounded historical enrichment</h3>
        <p class="p8-muted">
          Checks up to 100 enabled indicators against at most 1,000 recent
          events. Explicit click only.
        </p>
        <div class="p8-row">
          <label
            >Lookback hours
            <input
              class="p8-field"
              type="number"
              min="1"
              max="168"
              [(ngModel)]="hours"
          /></label>
          <label
            >Maximum events
            <input
              class="p8-field"
              type="number"
              min="1"
              max="1000"
              [(ngModel)]="maxEvents"
          /></label>
          <button class="p8-btn" [disabled]="saving()" (click)="enrich()">
            {{ saving() ? "Checking…" : "Enrich stored telemetry" }}
          </button>
        </div>
      </section>
    }
    <section class="p8-panel">
      <h3>Evidence matches (latest 100)</h3>
      <div class="p8-scroll">
        <table class="p8-table">
          <thead>
            <tr>
              <th>TIME</th>
              <th>INDICATOR</th>
              <th>ASSET</th>
              <th>EVENT TYPE</th>
              <th>MESSAGE</th>
            </tr>
          </thead>
          <tbody>
            @for (m of matches(); track m.id) {
              <tr>
                <td>{{ m.event_time }}</td>
                <td>{{ m.kind }}: {{ m.indicator }}</td>
                <td>{{ assetName(m.asset_id) }}</td>
                <td>{{ m.event_type }}</td>
                <td>{{ m.message }}</td>
              </tr>
            } @empty {
              <tr>
                <td colspan="5">
                  No matches yet. Register a reviewed IOC and enrich.
                </td>
              </tr>
            }
          </tbody>
        </table>
      </div>
    </section>
  `,
})
export class P8IntelligenceComponent implements OnChanges, OnDestroy {
  private http = inject(HttpClient);
  private readonly api = "http://127.0.0.1:8000";
  private lastToken = "";
  private pending: Subscription[] = [];
  @Input() token = "";
  @Input() canWrite = false;
  @Input() assets: { id: string; name: string }[] = [];
  indicators = signal<Indicator[]>([]);
  matches = signal<IntelMatch[]>([]);
  summary = signal({ indicators: 0, enabled: 0, matches: 0 });
  loading = signal(false);
  saving = signal(false);
  error = signal("");
  info = signal("");
  kind = "ip";
  value = "";
  sourceLabel = "manual";
  confidence = 50;
  description = "";
  hours = 1;
  maxEvents = 500;
  ngOnChanges(c: SimpleChanges) {
    if (c["token"] && this.token && this.token !== this.lastToken) {
      this.lastToken = this.token;
      this.refresh();
    }
  }
  ngOnDestroy() {
    this.pending.forEach((x) => x.unsubscribe());
  }
  assetName(id: string) {
    return this.assets.find((x) => x.id === id)?.name || id;
  }
  private headers() {
    return {
      headers: new HttpHeaders({ Authorization: "Bearer " + this.token }),
    };
  }
  private fail(e: any) {
    this.error.set(
      typeof e?.error?.detail === "string"
        ? e.error.detail
        : "HTTP " + (e?.status ?? 0) + " · Request failed",
    );
  }
  refresh() {
    if (!this.token || this.loading()) return;
    this.loading.set(true);
    this.error.set("");
    let remaining = 3;
    const done = () => {
      remaining--;
      if (!remaining) this.loading.set(false);
    };
    const r1 = this.http
      .get<Indicator[]>(this.api + "/intelligence/indicators", this.headers())
      .pipe(timeout(12000), finalize(done))
      .subscribe({
        next: (x) => this.indicators.set(x),
        error: (e) => this.fail(e),
      });
    const r2 = this.http
      .get<IntelMatch[]>(this.api + "/intelligence/matches", this.headers())
      .pipe(timeout(12000), finalize(done))
      .subscribe({
        next: (x) => this.matches.set(x),
        error: (e) => this.fail(e),
      });
    const r3 = this.http
      .get<{ indicators: number; enabled: number; matches: number }>(
        this.api + "/intelligence/summary",
        this.headers(),
      )
      .pipe(timeout(12000), finalize(done))
      .subscribe({
        next: (x) => this.summary.set(x),
        error: (e) => this.fail(e),
      });
    this.pending.push(r1, r2, r3);
  }
  add() {
    if (!this.canWrite || this.saving()) return;
    this.saving.set(true);
    const sub = this.http
      .post(
        this.api + "/intelligence/indicators",
        {
          kind: this.kind,
          value: this.value.trim(),
          source_label: this.sourceLabel.trim() || "manual",
          confidence: this.confidence,
          description: this.description,
        },
        this.headers(),
      )
      .pipe(
        timeout(12000),
        finalize(() => this.saving.set(false)),
      )
      .subscribe({
        next: () => {
          this.value = "";
          this.info.set("Indicator registered");
          this.refresh();
        },
        error: (e) => this.fail(e),
      });
    this.pending.push(sub);
  }
  toggle(i: Indicator) {
    if (!this.canWrite || this.saving()) return;
    this.saving.set(true);
    const sub = this.http
      .patch(
        this.api +
          "/intelligence/indicators/" +
          i.id +
          "?enabled=" +
          !i.enabled,
        {},
        this.headers(),
      )
      .pipe(
        timeout(12000),
        finalize(() => this.saving.set(false)),
      )
      .subscribe({ next: () => this.refresh(), error: (e) => this.fail(e) });
    this.pending.push(sub);
  }
  enrich() {
    if (!this.canWrite || this.saving()) return;
    this.saving.set(true);
    const sub = this.http
      .post<{
        indicators_checked: number;
        events_checked: number;
        new_matches: number;
      }>(
        this.api + "/intelligence/enrich",
        { lookback_hours: this.hours, max_events: this.maxEvents },
        this.headers(),
      )
      .pipe(
        timeout(20000),
        finalize(() => this.saving.set(false)),
      )
      .subscribe({
        next: (x) => {
          this.info.set(
            `Checked ${x.events_checked} events and ${x.indicators_checked} indicators; added ${x.new_matches} matches.`,
          );
          this.refresh();
        },
        error: (e) => this.fail(e),
      });
    this.pending.push(sub);
  }
}
