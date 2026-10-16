import {
  Component,
  Input,
  OnChanges,
  SimpleChanges,
  OnDestroy,
  inject,
  signal,
} from "@angular/core";
import { FormsModule } from "@angular/forms";
import { HttpClient, HttpHeaders } from "@angular/common/http";
import { forkJoin, timeout, finalize, Subscription } from "rxjs";

type AssetItem = { id: string; name: string };
type Finding = {
  id: string;
  asset_id: string;
  severity: string;
  rule_name: string;
  message: string;
};
type Case = {
  id: string;
  title: string;
  description: string;
  asset_id: string;
  severity: string;
  status: string;
  finding_count: number;
  assignee_id: string | null;
};
type Detail = {
  case: Case;
  findings: {
    id: string;
    rule_name: string;
    event_time: string;
    message: string;
  }[];
  notes: { id: string; note: string; created_at: string }[];
};
@Component({
  selector: "app-p6-incidents",
  standalone: true,
  imports: [FormsModule],
  styles: [
    `
      .p6-panel {
        background: #101a2d;
        border: 1px solid #30405c;
        border-radius: 12px;
        padding: 19px;
        margin-bottom: 16px;
        color: #e8edff;
      }
      .p6-row {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        align-items: center;
        margin: 12px 0;
      }
      .p6-row > * {
        min-width: 130px;
        flex: 1;
      }
      .p6-field {
        background: #091323;
        border: 1px solid #364866;
        border-radius: 7px;
        color: #eef;
        padding: 10px;
        max-width: 100%;
        box-sizing: border-box;
      }
      .p6-btn {
        border: 1px solid #7060c8;
        border-radius: 7px;
        background: #7557d7;
        color: white;
        padding: 9px 12px;
        cursor: pointer;
      }
      .p6-btn:disabled {
        opacity: 0.45;
        cursor: not-allowed;
      }
      .p6-table {
        width: 100%;
        border-collapse: collapse;
        text-align: left;
      }
      .p6-table td,
      .p6-table th {
        padding: 10px 7px;
        border-bottom: 1px solid #283954;
        font-size: 12px;
        vertical-align: top;
      }
      .p6-muted {
        color: #9eabc5;
        font-size: 12px;
      }
      .p6-warn {
        color: #ffaaa5;
      }
      .p6-ok {
        color: #81e4b5;
      }
    `,
  ],
  template: `
    <section class="p6-panel">
      <h2>P6 · Incident Triage & Finding Correlation</h2>
      <p class="p6-muted">
        Evidence-linked case management. Correlation is manual, bounded and
        same-asset only; no active containment or attack execution.
      </p>
      <div class="p6-row">
        <button class="p6-btn" [disabled]="loading()" (click)="load()">
          {{ loading() ? "Loading…" : "Refresh cases" }}
        </button>
        <span class="p6-muted">{{ summary() }}</span>
      </div>
      @if (error()) {
        <p class="p6-warn">{{ error() }}</p>
      }
      @if (info()) {
        <p class="p6-ok">{{ info() }}</p>
      }
    </section>
    @if (canWrite) {
      <section class="p6-panel">
        <h3>Create incident from existing detection finding</h3>
        <div class="p6-row">
          <select class="p6-field" [(ngModel)]="findingId">
            <option value="">Select unlinked finding</option>
            @for (f of findings(); track f.id) {
              <option [value]="f.id">
                {{ f.rule_name }} · {{ label(f.asset_id) }} · {{ f.severity }}
              </option>
            }
          </select>
          <input
            class="p6-field"
            placeholder="Incident title"
            [(ngModel)]="title"
          />
        </div>
        <textarea
          class="p6-field"
          style="width:100%"
          rows="2"
          placeholder="Analyst notes (optional)"
          [(ngModel)]="description"
        ></textarea>
        <button
          class="p6-btn"
          style="margin-top:12px"
          [disabled]="saving() || !findingId || title.trim().length < 5"
          (click)="create()"
        >
          Create incident
        </button>
      </section>
    }
    <section class="p6-panel">
      <h3>Incident cases</h3>
      <div style="overflow-x:auto">
        <table class="p6-table">
          <thead>
            <tr>
              <th>TITLE</th>
              <th>ASSET</th>
              <th>SEVERITY</th>
              <th>STATUS</th>
              <th>FINDINGS</th>
              <th>ACTION</th>
            </tr>
          </thead>
          <tbody>
            @for (c of cases(); track c.id) {
              <tr>
                <td>{{ c.title }}</td>
                <td>{{ label(c.asset_id) }}</td>
                <td>{{ c.severity }}</td>
                <td>{{ c.status }}</td>
                <td>{{ c.finding_count }}</td>
                <td>
                  <button class="p6-btn" (click)="details(c.id)">
                    View case
                  </button>
                </td>
              </tr>
            } @empty {
              <tr>
                <td colspan="6">
                  No incident cases. Promote a P4 finding to create your first
                  case.
                </td>
              </tr>
            }
          </tbody>
        </table>
      </div>
    </section>
    @if (selected()) {
      <section class="p6-panel">
        <h3>{{ selected()!.case.title }}</h3>
        <p class="p6-muted">
          {{ selected()!.case.description }} ·
          {{ label(selected()!.case.asset_id) }}
        </p>
        @if (canWrite) {
          <div class="p6-row">
            <select class="p6-field" [(ngModel)]="nextStatus">
              @for (s of statuses; track s) {
                <option [value]="s">{{ s }}</option>
              }
            </select>
            <button
              class="p6-btn"
              [disabled]="saving()"
              (click)="changeStatus()"
            >
              Update status
            </button>
            <button class="p6-btn" [disabled]="saving()" (click)="correlate()">
              Find related evidence (60 min)
            </button>
          </div>
          <div class="p6-row">
            <input
              class="p6-field"
              placeholder="Investigation note"
              [(ngModel)]="noteText"
            />
            <button
              class="p6-btn"
              [disabled]="saving() || noteText.trim().length < 3"
              (click)="addNote()"
            >
              Add note
            </button>
          </div>
        }
        <h4>Linked findings</h4>
        @for (f of selected()!.findings; track f.id) {
          <p class="p6-muted">
            <strong>{{ f.rule_name }}</strong> · {{ f.event_time }} ·
            {{ f.message }}
          </p>
        } @empty {
          <p class="p6-muted">No linked findings</p>
        }
        <h4>Investigation notes</h4>
        @for (n of selected()!.notes; track n.id) {
          <p class="p6-muted">{{ n.created_at }} · {{ n.note }}</p>
        }
      </section>
    }
  `,
})
export class P6IncidentsComponent implements OnChanges, OnDestroy {
  private http = inject(HttpClient);
  @Input() token = "";
  @Input() assets: AssetItem[] = [];
  @Input() canWrite = false;
  private readonly api = "http://127.0.0.1:8000";
  private req?: Subscription;
  private lastToken = "";
  cases = signal<Case[]>([]);
  findings = signal<Finding[]>([]);
  selected = signal<Detail | null>(null);
  loading = signal(false);
  saving = signal(false);
  error = signal("");
  info = signal("");
  summary = signal("Not loaded");
  findingId = "";
  title = "";
  description = "";
  nextStatus = "open";
  noteText = "";
  statuses = [
    "open",
    "investigating",
    "contained",
    "resolved",
    "false_positive",
  ];
  private auth() {
    return {
      headers: new HttpHeaders({ Authorization: "Bearer " + this.token }),
    };
  }
  ngOnChanges(changes: SimpleChanges) {
    if (changes["token"] && this.token && this.token !== this.lastToken) {
      this.lastToken = this.token;
      this.load();
    }
  }
  ngOnDestroy() {
    this.req?.unsubscribe();
  }
  label(id: string) {
    return this.assets.find((a) => a.id === id)?.name || id;
  }
  private fail(e: any) {
    this.error.set(
      typeof e.error?.detail === "string"
        ? e.error.detail
        : `Request failed (HTTP ${e.status || 0})`,
    );
  }
  load() {
    if (!this.token || this.loading()) return;
    this.error.set("");
    this.loading.set(true);
    this.req = forkJoin({
      cases: this.http.get<Case[]>(this.api + "/incidents", this.auth()),
      findings: this.http.get<Finding[]>(
        this.api + "/incidents/unlinked-findings",
        this.auth(),
      ),
      summary: this.http.get<{
        total: number;
        by_status: Record<string, number>;
      }>(this.api + "/incidents/summary", this.auth()),
    })
      .pipe(
        timeout(12000),
        finalize(() => this.loading.set(false)),
      )
      .subscribe({
        next: (v) => {
          this.cases.set(v.cases);
          this.findings.set(v.findings);
          this.summary.set(
            `${v.summary.total} cases · ${v.summary.by_status["open"] || 0} open · ${v.summary.by_status["investigating"] || 0} investigating`,
          );
        },
        error: (e) => this.fail(e),
      });
  }
  create() {
    if (!this.findingId || this.title.trim().length < 5) return;
    this.saving.set(true);
    this.http
      .post(
        this.api + "/incidents",
        {
          finding_id: this.findingId,
          title: this.title.trim(),
          description: this.description.trim(),
        },
        this.auth(),
      )
      .pipe(
        timeout(12000),
        finalize(() => this.saving.set(false)),
      )
      .subscribe({
        next: () => {
          this.info.set("Incident created");
          this.title = "";
          this.description = "";
          this.findingId = "";
          this.load();
        },
        error: (e) => this.fail(e),
      });
  }
  details(id: string) {
    this.http
      .get<Detail>(this.api + "/incidents/" + id, this.auth())
      .pipe(timeout(12000))
      .subscribe({
        next: (d) => {
          this.selected.set(d);
          this.nextStatus = d.case.status;
        },
        error: (e) => this.fail(e),
      });
  }
  changeStatus() {
    const c = this.selected()?.case;
    if (!c) return;
    this.saving.set(true);
    this.http
      .patch(
        this.api + "/incidents/" + c.id,
        { status: this.nextStatus },
        this.auth(),
      )
      .pipe(
        timeout(12000),
        finalize(() => this.saving.set(false)),
      )
      .subscribe({
        next: () => {
          this.info.set("Status updated");
          this.details(c.id);
          this.load();
        },
        error: (e) => this.fail(e),
      });
  }
  correlate() {
    const c = this.selected()?.case;
    if (!c) return;
    this.saving.set(true);
    this.http
      .post<{ linked_count: number }>(
        this.api + "/incidents/" + c.id + "/correlate?minutes=60",
        {},
        this.auth(),
      )
      .pipe(
        timeout(12000),
        finalize(() => this.saving.set(false)),
      )
      .subscribe({
        next: (v) => {
          this.info.set(`Linked ${v.linked_count} related findings`);
          this.details(c.id);
          this.load();
        },
        error: (e) => this.fail(e),
      });
  }
  addNote() {
    const c = this.selected()?.case;
    if (!c || this.noteText.trim().length < 3) return;
    this.saving.set(true);
    this.http
      .post(
        this.api + "/incidents/" + c.id + "/notes",
        { note: this.noteText.trim() },
        this.auth(),
      )
      .pipe(
        timeout(12000),
        finalize(() => this.saving.set(false)),
      )
      .subscribe({
        next: () => {
          this.noteText = "";
          this.info.set("Note added");
          this.details(c.id);
        },
        error: (e) => this.fail(e),
      });
  }
}
