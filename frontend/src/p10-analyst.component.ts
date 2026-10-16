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
import { Subscription, finalize, timeout } from "rxjs";

type Correlation = {
  id: string;
  asset_id: string;
  risk_score: number;
  status: string;
};
type Timeline = {
  event_id: string;
  timestamp: string;
  kind: string;
  event_type: string;
  description: string;
};
type Report = {
  id: string;
  correlation_id: string;
  status: string;
  created_at: string;
  review_note: string;
  report: {
    summary: string;
    risk_score: number;
    kind_counts: Record<string, number>;
    timeline: Timeline[];
    recommended_checks: string[];
    limitations: string[];
    generator: string;
  };
};
@Component({
  selector: "app-p10-analyst",
  standalone: true,
  imports: [FormsModule],
  styles: [
    `
      .p10-panel {
        background: #101a2d;
        border: 1px solid #30405c;
        border-radius: 12px;
        padding: 18px;
        margin-bottom: 16px;
        color: #e8edff;
      }
      .p10-row {
        display: flex;
        gap: 12px;
        align-items: center;
        flex-wrap: wrap;
        margin: 12px 0;
      }
      .p10-control {
        background: #091323;
        color: #e8edff;
        border: 1px solid #364866;
        border-radius: 8px;
        padding: 10px;
        flex: 1;
        min-width: 170px;
      }
      .p10-button {
        background: #7255d5;
        color: white;
        border: 1px solid #8573e6;
        border-radius: 7px;
        padding: 10px;
        cursor: pointer;
      }
      .p10-button:disabled {
        opacity: 0.5;
        cursor: default;
      }
      .p10-muted {
        color: #a9b6d1;
        font-size: 12px;
      }
      .p10-scroll {
        overflow-x: auto;
      }
      .p10-table {
        width: 100%;
        border-collapse: collapse;
        text-align: left;
      }
      .p10-table td,
      .p10-table th {
        border-bottom: 1px solid #2b3953;
        padding: 9px;
        font-size: 12px;
        overflow-wrap: anywhere;
      }
      .p10-warning {
        color: #ffd68a;
      }
      .p10-error {
        color: #ffaba8;
      }
    `,
  ],
  template: `
    <section class="p10-panel">
      <h2>P10 · SOC Analyst Workspace</h2>
      <p class="p10-muted">
        Evidence-grounded deterministic draft, not an LLM verdict. On-demand
        only · maximum 50 evidence entries · human review required.
      </p>
      @if (error()) {
        <p class="p10-error">{{ error() }}</p>
      }
      @if (info()) {
        <p style="color:#8ee6bd">{{ info() }}</p>
      }
      <button class="p10-button" [disabled]="loading()" (click)="refresh()">
        {{ loading() ? "Loading…" : "Refresh analyst workspace" }}
      </button>
    </section>
    @if (canWrite) {
      <section class="p10-panel">
        <h3>Generate investigation draft</h3>
        <div class="p10-row">
          <select class="p10-control" [(ngModel)]="correlationId">
            <option value="">Select P9 correlation case</option>
            @for (c of correlations(); track c.id) {
              <option [value]="c.id">
                {{ assetName(c.asset_id) }} · Risk {{ c.risk_score }} ·
                {{ c.id.slice(0, 8) }}
              </option>
            }</select
          ><button
            class="p10-button"
            [disabled]="saving() || !correlationId"
            (click)="generate()"
          >
            {{ saving() ? "Generating…" : "Generate evidence draft" }}
          </button>
        </div>
      </section>
    }
    <section class="p10-panel">
      <h3>Investigation reports</h3>
      <div class="p10-scroll">
        <table class="p10-table">
          <thead>
            <tr>
              <th>CREATED</th>
              <th>CASE</th>
              <th>STATUS</th>
              <th>RISK</th>
              <th>ACTION</th>
            </tr>
          </thead>
          <tbody>
            @for (r of reports(); track r.id) {
              <tr>
                <td>{{ r.created_at }}</td>
                <td>{{ r.correlation_id.slice(0, 8) }}</td>
                <td>{{ r.status }}</td>
                <td>{{ r.report.risk_score }}/100</td>
                <td>
                  <button class="p10-button" (click)="selected.set(r)">
                    Inspect report
                  </button>
                </td>
              </tr>
            } @empty {
              <tr>
                <td colspan="5">
                  No reports yet. Choose a P9 case and generate one.
                </td>
              </tr>
            }
          </tbody>
        </table>
      </div>
    </section>
    @if (selected(); as r) {
      <section class="p10-panel">
        <h3>Evidence report · {{ r.status }}</h3>
        <p>{{ r.report.summary }}</p>
        <p class="p10-warning">
          Unverified draft — evidence association is not proof of compromise.
        </p>
        <h4>Recommended human checks</h4>
        <ul>
          @for (s of r.report.recommended_checks; track s) {
            <li>{{ s }}</li>
          }
        </ul>
        <h4>Limitations</h4>
        <ul>
          @for (s of r.report.limitations; track s) {
            <li>{{ s }}</li>
          }
        </ul>
        <h4>Observed evidence timeline</h4>
        <div class="p10-scroll">
          <table class="p10-table">
            <thead>
              <tr>
                <th>TIME</th>
                <th>KIND</th>
                <th>EVENT</th>
                <th>MESSAGE</th>
              </tr>
            </thead>
            <tbody>
              @for (e of r.report.timeline; track e.event_id + e.kind) {
                <tr>
                  <td>{{ e.timestamp }}</td>
                  <td>{{ e.kind }}</td>
                  <td>{{ e.event_type }}</td>
                  <td>{{ e.description }}</td>
                </tr>
              } @empty {
                <tr>
                  <td colspan="4">No linked evidence.</td>
                </tr>
              }
            </tbody>
          </table>
        </div>
        @if (r.status === "draft" && canWrite) {
          <h4>Analyst review</h4>
          <textarea
            class="p10-control"
            style="width:100%;box-sizing:border-box;min-height:76px"
            [(ngModel)]="reviewNote"
            placeholder="Required: explain your decision"
          ></textarea>
          <div class="p10-row">
            <button
              class="p10-button"
              [disabled]="saving() || !reviewNote.trim()"
              (click)="review(r, 'accepted')"
            >
              Accept draft</button
            ><button
              class="p10-button"
              [disabled]="saving() || !reviewNote.trim()"
              (click)="review(r, 'rejected')"
            >
              Reject draft
            </button>
          </div>
        } @else {
          <p class="p10-muted">
            Review note: {{ r.review_note || "Not reviewed" }}
          </p>
        }
      </section>
    }
  `,
})
export class P10AnalystComponent implements OnChanges, OnDestroy {
  private http = inject(HttpClient);
  private readonly api = "http://127.0.0.1:8000";
  private lastToken = "";
  private subs: Subscription[] = [];
  @Input() token = "";
  @Input() canWrite = false;
  @Input() assets: { id: string; name: string }[] = [];
  correlations = signal<Correlation[]>([]);
  reports = signal<Report[]>([]);
  selected = signal<Report | null>(null);
  loading = signal(false);
  saving = signal(false);
  error = signal("");
  info = signal("");
  correlationId = "";
  reviewNote = "";
  ngOnChanges(changes: SimpleChanges) {
    if (changes["token"] && this.token && this.token !== this.lastToken) {
      this.lastToken = this.token;
      this.refresh();
    }
  }
  ngOnDestroy() {
    this.subs.forEach((x) => x.unsubscribe());
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
        : `Request failed (HTTP ${e?.status ?? 0})`,
    );
  }
  assetName(id: string) {
    return this.assets.find((x) => x.id === id)?.name ?? id;
  }
  refresh() {
    if (!this.token || this.loading()) return;
    this.loading.set(true);
    this.error.set("");
    const s = this.http
      .get<Report[]>(this.api + "/analyst/reports", this.opts())
      .pipe(
        timeout(12000),
        finalize(() => this.loading.set(false)),
      )
      .subscribe({
        next: (r) => {
          this.reports.set(r);
          if (this.selected()) {
            this.selected.set(
              r.find((x) => x.id === this.selected()!.id) ?? null,
            );
          }
        },
        error: (e) => this.fail(e),
      });
    this.subs.push(s);
    const c = this.http
      .get<Correlation[]>(this.api + "/correlation/cases", this.opts())
      .pipe(timeout(12000))
      .subscribe({
        next: (v) => this.correlations.set(v),
        error: (e) => this.fail(e),
      });
    this.subs.push(c);
  }
  generate() {
    if (!this.canWrite || !this.correlationId || this.saving()) return;
    this.saving.set(true);
    this.error.set("");
    const s = this.http
      .post<Report>(
        this.api + "/analyst/generate",
        { correlation_id: this.correlationId },
        this.opts(),
      )
      .pipe(
        timeout(20000),
        finalize(() => this.saving.set(false)),
      )
      .subscribe({
        next: (r) => {
          this.selected.set(r);
          this.info.set("Draft created; analyst review is required.");
          this.refresh();
        },
        error: (e) => this.fail(e),
      });
    this.subs.push(s);
  }
  review(r: Report, status: "accepted" | "rejected") {
    if (!this.canWrite || this.saving() || !this.reviewNote.trim()) return;
    this.saving.set(true);
    this.error.set("");
    const s = this.http
      .patch<Report>(
        this.api + "/analyst/reports/" + r.id + "/review",
        { status, note: this.reviewNote.trim() },
        this.opts(),
      )
      .pipe(
        timeout(12000),
        finalize(() => this.saving.set(false)),
      )
      .subscribe({
        next: (v) => {
          this.selected.set(v);
          this.reviewNote = "";
          this.info.set("Review saved");
          this.refresh();
        },
        error: (e) => this.fail(e),
      });
    this.subs.push(s);
  }
}
