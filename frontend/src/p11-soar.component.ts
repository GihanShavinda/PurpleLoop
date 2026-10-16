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
import { Subscription, forkJoin, timeout, finalize } from "rxjs";
type Case = { id: string; asset_id?: string };
type Playbook = {
  key: string;
  name: string;
  description: string;
  mode: string;
};
type Proposal = {
  id: string;
  playbook_key: string;
  incident_id: string | null;
  correlation_id: string | null;
  status: string;
  justification: string;
  proposed_by: string;
  approved_by: string | null;
  decision_note: string;
  output_json: any;
  created_at: string;
};
type Audit = {
  action: string;
  detail: string;
  created_at: string;
  actor_id: string;
};
@Component({
  selector: "app-p11-soar",
  standalone: true,
  imports: [FormsModule],
  styles: [
    `
      .p11-panel {
        border: 1px solid #2a3b58;
        border-radius: 12px;
        padding: 18px;
        background: #101a2d;
        color: #e8edff;
        margin-bottom: 15px;
      }
      .p11-row {
        display: flex;
        gap: 10px;
        flex-wrap: wrap;
        margin: 10px 0;
        align-items: center;
      }
      .p11-input {
        background: #091323;
        border: 1px solid #39496a;
        color: #f1f2ff;
        border-radius: 7px;
        padding: 10px;
        flex: 1;
        min-width: 160px;
      }
      .p11-btn {
        background: #7154d5;
        border: 0;
        color: white;
        border-radius: 7px;
        padding: 10px;
        cursor: pointer;
      }
      .p11-btn:disabled {
        opacity: 0.4;
        cursor: default;
      }
      .p11-error {
        color: #ffb6aa;
      }
      .p11-muted {
        color: #a1b0cf;
        font-size: 12px;
      }
      .p11-good {
        color: #8fe6bf;
      }
      .p11-table {
        width: 100%;
        border-collapse: collapse;
      }
      .p11-table td,
      .p11-table th {
        padding: 9px;
        border-bottom: 1px solid #293951;
        font-size: 12px;
        text-align: left;
      }
      .p11-scroll {
        overflow-x: auto;
      }
    `,
  ],
  template: `
    <section class="p11-panel">
      <h2>P11 · Human-Approved SOAR</h2>
      <p class="p11-muted">
        Simulation-only. No VM, firewall, endpoint or service changes. Separate
        proposal and approval accounts required.
      </p>
      @if (error()) {
        <p class="p11-error">{{ error() }}</p>
      }
      @if (info()) {
        <p class="p11-good">{{ info() }}</p>
      }
      <button class="p11-btn" [disabled]="loading()" (click)="refresh()">
        {{ loading() ? "Loading…" : "Refresh SOAR" }}
      </button>
    </section>
    @if (canWrite) {
      <section class="p11-panel">
        <h3>Propose an advisory playbook</h3>
        <div class="p11-row">
          <select class="p11-input" [(ngModel)]="playbook">
            <option value="">Select dry-run playbook</option>
            @for (p of playbooks(); track p.key) {
              <option [value]="p.key">{{ p.name }}</option>
            }
          </select>
          <select
            class="p11-input"
            [(ngModel)]="targetType"
            (ngModelChange)="targetId = ''"
          >
            <option value="correlation">Correlation case</option>
            <option value="incident">Incident</option>
          </select>
          <select class="p11-input" [(ngModel)]="targetId">
            <option value="">Select target</option>
            @for (c of targets(); track c.id) {
              <option [value]="c.id">{{ c.id.slice(0, 8) }}</option>
            }
          </select>
        </div>
        <textarea
          class="p11-input"
          style="width:100%;box-sizing:border-box;min-height:75px"
          [(ngModel)]="justification"
          placeholder="Reason for proposing this dry-run (10+ characters)"
        ></textarea>
        <button
          class="p11-btn"
          [disabled]="
            busy() || !playbook || !targetId || justification.trim().length < 10
          "
          (click)="propose()"
        >
          Propose for approval
        </button>
      </section>
    }
    <section class="p11-panel">
      <h3>Response proposals</h3>
      <div class="p11-scroll">
        <table class="p11-table">
          <thead>
            <tr>
              <th>PLAYBOOK</th>
              <th>TARGET</th>
              <th>STATUS</th>
              <th>ACTIONS</th>
            </tr>
          </thead>
          <tbody>
            @for (p of proposals(); track p.id) {
              <tr>
                <td>{{ p.playbook_key }}</td>
                <td>
                  {{ (p.incident_id || p.correlation_id || "").slice(0, 8) }}
                </td>
                <td>{{ p.status }}</td>
                <td>
                  <button
                    class="p11-btn"
                    (click)="selected.set(p); loadAudit(p.id)"
                  >
                    Inspect
                  </button>
                  @if (p.status === "pending" && canApprove) {
                    <button
                      class="p11-btn"
                      [disabled]="busy() || !decisionNote.trim()"
                      (click)="decision(p, 'approve')"
                    >
                      Approve
                    </button>
                    <button
                      class="p11-btn"
                      [disabled]="busy() || !decisionNote.trim()"
                      (click)="decision(p, 'reject')"
                    >
                      Reject
                    </button>
                  }
                  @if (p.status === "approved" && canApprove) {
                    <button
                      class="p11-btn"
                      [disabled]="busy()"
                      (click)="simulate(p)"
                    >
                      Run dry simulation
                    </button>
                  }
                </td>
              </tr>
            } @empty {
              <tr>
                <td colspan="4">No proposals yet.</td>
              </tr>
            }
          </tbody>
        </table>
      </div>
    </section>
    @if (canApprove) {
      <section class="p11-panel">
        <label
          >Approval/rejection note (required)
          <input
            class="p11-input"
            style="width:100%;box-sizing:border-box"
            [(ngModel)]="decisionNote"
            placeholder="Evidence-based review reason"
        /></label>
      </section>
    }
    @if (selected(); as p) {
      <section class="p11-panel">
        <h3>Proposal {{ p.id.slice(0, 8) }} · {{ p.status }}</h3>
        <p>{{ p.justification }}</p>
        <p class="p11-muted">Decision: {{ p.decision_note || "Pending" }}</p>
        @if (p.output_json) {
          <h4>Simulation result</h4>
          <p class="p11-good">{{ p.output_json.message }}</p>
          <ul>
            @for (s of p.output_json.steps; track s) {
              <li>{{ s }}</li>
            }
          </ul>
        }
        <h4>Audit history</h4>
        <ul>
          @for (a of audit(); track a.created_at + a.action) {
            <li>{{ a.created_at }} · {{ a.action }} — {{ a.detail }}</li>
          }
        </ul>
      </section>
    }
  `,
})
export class P11SoarComponent implements OnChanges, OnDestroy {
  private http = inject(HttpClient);
  private api = "http://127.0.0.1:8000";
  private lastToken = "";
  private subs: Subscription[] = [];
  @Input() token = "";
  @Input() canWrite = false;
  @Input() canApprove = false;
  loading = signal(false);
  busy = signal(false);
  error = signal("");
  info = signal("");
  playbooks = signal<Playbook[]>([]);
  proposals = signal<Proposal[]>([]);
  incidents = signal<Case[]>([]);
  correlations = signal<Case[]>([]);
  selected = signal<Proposal | null>(null);
  audit = signal<Audit[]>([]);
  playbook = "";
  targetType = "correlation";
  targetId = "";
  justification = "";
  decisionNote = "";
  ngOnChanges(c: SimpleChanges) {
    if (c["token"] && this.token && this.token !== this.lastToken) {
      this.lastToken = this.token;
      this.refresh();
    }
  }
  ngOnDestroy() {
    this.subs.forEach((s) => s.unsubscribe());
  }
  opts() {
    return {
      headers: new HttpHeaders({ Authorization: "Bearer " + this.token }),
    };
  }
  fail(e: any) {
    this.error.set(
      typeof e?.error?.detail === "string"
        ? e.error.detail
        : `Request failed (HTTP ${e?.status ?? 0})`,
    );
  }
  targets() {
    return this.targetType === "incident"
      ? this.incidents()
      : this.correlations();
  }
  refresh() {
    if (this.loading() || !this.token) return;
    this.loading.set(true);
    this.error.set("");
    const s = forkJoin({
      p: this.http.get<Proposal[]>(this.api + "/soar/proposals", this.opts()),
      b: this.http.get<Playbook[]>(this.api + "/soar/playbooks", this.opts()),
      i: this.http.get<Case[]>(this.api + "/incidents", this.opts()),
      c: this.http.get<Case[]>(this.api + "/correlation/cases", this.opts()),
    })
      .pipe(
        timeout(12000),
        finalize(() => this.loading.set(false)),
      )
      .subscribe({
        next: (v) => {
          this.proposals.set(v.p);
          this.playbooks.set(v.b);
          this.incidents.set(v.i);
          this.correlations.set(v.c);
          const old = this.selected();
          if (old) this.selected.set(v.p.find((p) => p.id === old.id) || null);
        },
        error: (e) => this.fail(e),
      });
    this.subs.push(s);
  }
  loadAudit(id: string) {
    const s = this.http
      .get<Audit[]>(this.api + "/soar/proposals/" + id + "/audit", this.opts())
      .pipe(timeout(12000))
      .subscribe({
        next: (v) => this.audit.set(v),
        error: (e) => this.fail(e),
      });
    this.subs.push(s);
  }
  propose() {
    if (this.busy() || !this.canWrite) return;
    this.busy.set(true);
    this.error.set("");
    const body = {
      playbook_key: this.playbook,
      justification: this.justification.trim(),
      incident_id: this.targetType === "incident" ? this.targetId : null,
      correlation_id: this.targetType === "correlation" ? this.targetId : null,
    };
    const s = this.http
      .post<Proposal>(this.api + "/soar/proposals", body, this.opts())
      .pipe(
        timeout(12000),
        finalize(() => this.busy.set(false)),
      )
      .subscribe({
        next: (p) => {
          this.info.set(
            "Proposal created; a separate authorized user must approve it.",
          );
          this.selected.set(p);
          this.justification = "";
          this.refresh();
        },
        error: (e) => this.fail(e),
      });
    this.subs.push(s);
  }
  decision(p: Proposal, action: "approve" | "reject") {
    if (this.busy() || !this.canApprove || !this.decisionNote.trim()) return;
    this.busy.set(true);
    const s = this.http
      .post<Proposal>(
        this.api + "/soar/proposals/" + p.id + "/" + action,
        { note: this.decisionNote.trim() },
        this.opts(),
      )
      .pipe(
        timeout(12000),
        finalize(() => this.busy.set(false)),
      )
      .subscribe({
        next: (v) => {
          this.selected.set(v);
          this.decisionNote = "";
          this.info.set("Decision saved");
          this.refresh();
          this.loadAudit(v.id);
        },
        error: (e) => this.fail(e),
      });
    this.subs.push(s);
  }
  simulate(p: Proposal) {
    if (this.busy() || !this.canApprove) return;
    this.busy.set(true);
    const s = this.http
      .post<Proposal>(
        this.api + "/soar/proposals/" + p.id + "/simulate",
        {},
        this.opts(),
      )
      .pipe(
        timeout(12000),
        finalize(() => this.busy.set(false)),
      )
      .subscribe({
        next: (v) => {
          this.selected.set(v);
          this.info.set("Dry-run complete. No external changes made.");
          this.refresh();
          this.loadAudit(v.id);
        },
        error: (e) => this.fail(e),
      });
    this.subs.push(s);
  }
}
