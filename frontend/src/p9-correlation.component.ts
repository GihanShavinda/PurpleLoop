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
import { Subscription, timeout, finalize } from "rxjs";
type Case = {
  id: string;
  asset_id: string;
  window_start: string;
  window_end: string;
  risk_score: number;
  risk_reasons: {
    finding_points: number;
    intelligence_points: number;
    asset_points: number;
    note: string;
  };
  finding_count: number;
  indicator_count: number;
  status: string;
};
type Evidence = {
  id: string;
  event_time: string;
  event_type: string;
  message: string;
  kind: string;
};
@Component({
  selector: "app-p9-correlation",
  standalone: true,
  imports: [FormsModule],
  styles: [
    `
      .p9-panel {
        background: #101a2d;
        border: 1px solid #30405c;
        border-radius: 12px;
        padding: 18px;
        margin-bottom: 16px;
        color: #e8edff;
      }
      .p9-row {
        display: flex;
        gap: 12px;
        align-items: center;
        flex-wrap: wrap;
        margin: 10px 0;
      }
      .p9-row > * {
        flex: 1;
        min-width: 150px;
      }
      .p9-control {
        background: #091323;
        color: #e8edff;
        border: 1px solid #364866;
        border-radius: 8px;
        padding: 10px;
        max-width: 100%;
        box-sizing: border-box;
      }
      .p9-button {
        background: #7255d5;
        color: white;
        border: 1px solid #8573e6;
        border-radius: 7px;
        padding: 10px;
        cursor: pointer;
      }
      .p9-button:disabled {
        opacity: 0.45;
      }
      .p9-muted {
        color: #a9b6d1;
        font-size: 12px;
      }
      .p9-scroll {
        overflow-x: auto;
      }
      .p9-table {
        width: 100%;
        border-collapse: collapse;
        text-align: left;
      }
      .p9-table td,
      .p9-table th {
        border-bottom: 1px solid #2b3953;
        padding: 10px;
        font-size: 12px;
        overflow-wrap: anywhere;
      }
    `,
  ],
  template: `
    <section class="p9-panel">
      <h2>P9 · Correlation & Evidence Timeline</h2>
      <p class="p9-muted">
        Explicit bounded, same-asset correlation. Evidence association is not
        proof of an attack chain. No auto-response or polling.
      </p>
      @if (error()) {
        <p style="color:#ffaba8">{{ error() }}</p>
      }
      @if (info()) {
        <p style="color:#8ee6bd">{{ info() }}</p>
      }
      <div class="p9-row">
        <button class="p9-button" [disabled]="loading()" (click)="refresh()">
          Refresh correlations</button
        ><span class="p9-muted">{{ cases().length }} recent cases</span>
      </div>
    </section>
    @if (canWrite) {
      <section class="p9-panel">
        <h3>Evaluate one asset</h3>
        <div class="p9-row">
          <select class="p9-control" [(ngModel)]="assetId">
            <option value="">Select asset</option>
            @for (a of assets; track a.id) {
              <option [value]="a.id">{{ a.name }}</option>
            }
          </select>
          <label
            >Window (minutes)<input
              class="p9-control"
              type="number"
              min="5"
              max="240"
              [(ngModel)]="minutes"
          /></label>
          <label
            >Max evidence<input
              class="p9-control"
              type="number"
              min="2"
              max="200"
              [(ngModel)]="maxEvidence"
          /></label>
          <button
            class="p9-button"
            [disabled]="saving() || !assetId"
            (click)="evaluate()"
          >
            {{ saving() ? "Evaluating…" : "Evaluate evidence" }}
          </button>
        </div>
      </section>
    }
    <section class="p9-panel">
      <h3>Correlation cases</h3>
      <div class="p9-scroll">
        <table class="p9-table">
          <thead>
            <tr>
              <th>ASSET</th>
              <th>WINDOW</th>
              <th>RISK</th>
              <th>EVIDENCE</th>
              <th>STATUS</th>
              <th>ACTIONS</th>
            </tr>
          </thead>
          <tbody>
            @for (c of cases(); track c.id) {
              <tr>
                <td>{{ assetName(c.asset_id) }}</td>
                <td>{{ c.window_start }} → {{ c.window_end }}</td>
                <td>
                  <b>{{ c.risk_score }}/100</b>
                  <div class="p9-muted">
                    Findings {{ c.risk_reasons.finding_points }} · IOC
                    {{ c.risk_reasons.intelligence_points }} · Asset
                    {{ c.risk_reasons.asset_points }}
                  </div>
                </td>
                <td>
                  {{ c.finding_count }} findings / {{ c.indicator_count }} IOC
                  matches
                </td>
                <td>{{ c.status }}</td>
                <td>
                  <button class="p9-button" (click)="openEvidence(c.id)">
                    Timeline
                  </button>
                  @if (canWrite) {
                    <button
                      class="p9-button"
                      [disabled]="saving()"
                      (click)="review(c, 'reviewed')"
                    >
                      Review
                    </button>
                    <button
                      class="p9-button"
                      [disabled]="saving()"
                      (click)="review(c, 'dismissed')"
                    >
                      Dismiss
                    </button>
                  }
                </td>
              </tr>
            } @empty {
              <tr>
                <td colspan="6">
                  No correlated evidence yet. Generate P4 findings or P8
                  matches, then evaluate an asset.
                </td>
              </tr>
            }
          </tbody>
        </table>
      </div>
    </section>
    @if (selectedId()) {
      <section class="p9-panel">
        <h3>Evidence timeline</h3>
        <p class="p9-muted">
          Chronological observed events only; no inferred lateral movement or
          confirmed exploitation.
        </p>
        <div class="p9-scroll">
          <table class="p9-table">
            <thead>
              <tr>
                <th>TIME</th>
                <th>KIND</th>
                <th>TYPE</th>
                <th>MESSAGE</th>
              </tr>
            </thead>
            <tbody>
              @for (e of evidence(); track e.id) {
                <tr>
                  <td>{{ e.event_time }}</td>
                  <td>{{ e.kind }}</td>
                  <td>{{ e.event_type }}</td>
                  <td>{{ e.message }}</td>
                </tr>
              } @empty {
                <tr>
                  <td colspan="4">No evidence available.</td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      </section>
    }
  `,
})
export class P9CorrelationComponent implements OnChanges, OnDestroy {
  private http = inject(HttpClient);
  private api = "http://127.0.0.1:8000";
  private lastToken = "";
  private subscriptions: Subscription[] = [];
  @Input() token = "";
  @Input() canWrite = false;
  @Input() assets: { id: string; name: string }[] = [];
  cases = signal<Case[]>([]);
  evidence = signal<Evidence[]>([]);
  selectedId = signal("");
  loading = signal(false);
  saving = signal(false);
  error = signal("");
  info = signal("");
  assetId = "";
  minutes = 60;
  maxEvidence = 100;
  ngOnChanges(c: SimpleChanges) {
    if (c["token"] && this.token && this.token !== this.lastToken) {
      this.lastToken = this.token;
      this.refresh();
    }
  }
  ngOnDestroy() {
    this.subscriptions.forEach((s) => s.unsubscribe());
  }
  private opts() {
    return {
      headers: new HttpHeaders({ Authorization: "Bearer " + this.token }),
    };
  }
  private fail(e: any) {
    this.error.set(
      typeof e?.error?.detail === "string"
        ? e.error.detail
        : "Request failed (HTTP " + (e?.status ?? 0) + ")",
    );
  }
  assetName(id: string) {
    return this.assets.find((a) => a.id === id)?.name ?? id;
  }
  refresh() {
    if (!this.token || this.loading()) return;
    this.loading.set(true);
    this.error.set("");
    const s = this.http
      .get<Case[]>(this.api + "/correlation/cases", this.opts())
      .pipe(
        timeout(12000),
        finalize(() => this.loading.set(false)),
      )
      .subscribe({
        next: (x) => this.cases.set(x),
        error: (e) => this.fail(e),
      });
    this.subscriptions.push(s);
  }
  evaluate() {
    if (!this.canWrite || !this.assetId || this.saving()) return;
    this.saving.set(true);
    this.error.set("");
    const s = this.http
      .post<{ created: boolean; reason?: string; case?: Case }>(
        this.api + "/correlation/evaluate",
        {
          asset_id: this.assetId,
          window_minutes: this.minutes,
          max_evidence: this.maxEvidence,
        },
        this.opts(),
      )
      .pipe(
        timeout(20000),
        finalize(() => this.saving.set(false)),
      )
      .subscribe({
        next: (x) => {
          this.info.set(
            x.created
              ? "Correlation recorded"
              : (x.reason ?? "Already evaluated in this minute"),
          );
          this.refresh();
        },
        error: (e) => this.fail(e),
      });
    this.subscriptions.push(s);
  }
  openEvidence(id: string) {
    if (this.loading()) return;
    this.selectedId.set(id);
    const s = this.http
      .get<Evidence[]>(
        this.api + "/correlation/cases/" + id + "/evidence",
        this.opts(),
      )
      .pipe(timeout(12000))
      .subscribe({
        next: (x) => this.evidence.set(x),
        error: (e) => this.fail(e),
      });
    this.subscriptions.push(s);
  }
  review(c: Case, status: string) {
    if (!this.canWrite || this.saving()) return;
    this.saving.set(true);
    const s = this.http
      .patch(this.api + "/correlation/cases/" + c.id, { status }, this.opts())
      .pipe(
        timeout(12000),
        finalize(() => this.saving.set(false)),
      )
      .subscribe({ next: () => this.refresh(), error: (e) => this.fail(e) });
    this.subscriptions.push(s);
  }
}
