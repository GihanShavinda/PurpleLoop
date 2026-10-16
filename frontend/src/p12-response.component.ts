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
import { Subscription, timeout, finalize, forkJoin } from "rxjs";
type Proposal = {
  id: string;
  status: string;
  playbook_key: string;
  justification: string;
};
type Rehearsal = {
  id: string;
  proposal_id: string;
  status: string;
  plan_json: {
    mode: string;
    steps: string[];
    external_actions: number;
    vm_changes: number;
    disclaimer: string;
  };
  created_at: string;
  rollback_note: string;
};
@Component({
  selector: "app-p12-response",
  standalone: true,
  imports: [FormsModule],
  styles: [
    `
      .panel {
        border: 1px solid #2a3b58;
        border-radius: 12px;
        padding: 18px;
        background: #101a2d;
        color: #e8edff;
        margin: 15px 0;
      }
      .muted {
        color: #a1b0cf;
        font-size: 12px;
      }
      .err {
        color: #ffb6aa;
      }
      .good {
        color: #8fe6bf;
      }
      .row {
        display: flex;
        gap: 10px;
        flex-wrap: wrap;
        align-items: center;
        margin: 10px 0;
      }
      .field {
        background: #091323;
        border: 1px solid #39496a;
        color: #f1f2ff;
        border-radius: 7px;
        padding: 10px;
        flex: 1;
        min-width: 160px;
      }
      .btn {
        background: #7154d5;
        color: white;
        border: 0;
        border-radius: 7px;
        padding: 10px;
        cursor: pointer;
      }
      .btn:disabled {
        opacity: 0.4;
        cursor: default;
      }
      table {
        width: 100%;
        border-collapse: collapse;
      }
      th,
      td {
        padding: 9px;
        border-bottom: 1px solid #293951;
        font-size: 12px;
        text-align: left;
      }
      section {
        overflow-x: auto;
      }
    `,
  ],
  template: `
    <section class="panel">
      <h2>P12 · Response Rehearsal & Simulated Rollback</h2>
      <p class="muted">
        No shell commands, network changes, VM actions, or firewall updates. A
        recorded rollback closes a simulation only.
      </p>
      @if (error()) {
        <p class="err">{{ error() }}</p>
      }
      @if (info()) {
        <p class="good">{{ info() }}</p>
      }
      <button class="btn" [disabled]="loading()" (click)="refresh()">
        {{ loading() ? "Loading…" : "Refresh rehearsals" }}
      </button>
    </section>
    @if (canApprove) {
      <section class="panel">
        <h3>Run approved P11 proposal rehearsal</h3>
        <div class="row">
          <select class="field" [(ngModel)]="proposalId">
            <option value="">Select completed P11 simulation</option>
            @for (p of eligible(); track p.id) {
              <option [value]="p.id">
                {{ p.playbook_key }} · {{ p.id.slice(0, 8) }}
              </option>
            }</select
          ><button
            class="btn"
            [disabled]="busy() || !proposalId"
            (click)="rehearse()"
          >
            Create rehearsal
          </button>
        </div>
      </section>
    }
    <section class="panel">
      <h3>Rehearsal history</h3>
      <table>
        <thead>
          <tr>
            <th>PROPOSAL</th>
            <th>STATUS</th>
            <th>MODE</th>
            <th>EXTERNAL ACTIONS</th>
            <th>ACTIONS</th>
          </tr>
        </thead>
        <tbody>
          @for (r of rows(); track r.id) {
            <tr>
              <td>{{ r.proposal_id.slice(0, 8) }}</td>
              <td>{{ r.status }}</td>
              <td>{{ r.plan_json.mode }}</td>
              <td>{{ r.plan_json.external_actions }}</td>
              <td>
                <button class="btn" (click)="selected.set(r)">Inspect</button>
                @if (canApprove && r.status === "rehearsed") {
                  <button
                    class="btn"
                    [disabled]="busy() || note.trim().length < 10"
                    (click)="rollback(r)"
                  >
                    Close simulation
                  </button>
                }
              </td>
            </tr>
          } @empty {
            <tr>
              <td colspan="5">No rehearsals yet.</td>
            </tr>
          }
        </tbody>
      </table>
      @if (canApprove) {
        <p class="muted">
          Review note for closing an open rehearsal (10+ characters)
        </p>
        <textarea
          class="field"
          style="width:100%;box-sizing:border-box"
          [(ngModel)]="note"
          placeholder="State why the simulation is being closed"
        ></textarea>
      }
    </section>
    @if (selected(); as r) {
      <section class="panel">
        <h3>Rehearsal {{ r.id.slice(0, 8) }}</h3>
        <p class="good">
          {{ r.plan_json.mode }} · {{ r.plan_json.external_actions }} external
          actions · {{ r.plan_json.vm_changes }} VM changes
        </p>
        <ol>
          @for (step of r.plan_json.steps; track step) {
            <li>{{ step }}</li>
          }
        </ol>
        <p class="muted">{{ r.plan_json.disclaimer }}</p>
        @if (r.rollback_note) {
          <p>Closure: {{ r.rollback_note }}</p>
        }
      </section>
    }
  `,
})
export class P12ResponseComponent implements OnChanges, OnDestroy {
  @Input() token = "";
  @Input() canApprove = false;
  private http = inject(HttpClient);
  private api = "http://127.0.0.1:8000";
  private lastToken = "";
  private subs: Subscription[] = [];
  loading = signal(false);
  busy = signal(false);
  error = signal("");
  info = signal("");
  proposals = signal<Proposal[]>([]);
  rows = signal<Rehearsal[]>([]);
  selected = signal<Rehearsal | null>(null);
  proposalId = "";
  note = "";
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
  eligible() {
    return this.proposals().filter((p) => p.status === "simulated");
  }
  refresh() {
    if (this.loading() || !this.token) return;
    this.loading.set(true);
    this.error.set("");
    const s = forkJoin({
      p: this.http.get<Proposal[]>(this.api + "/soar/proposals", this.opts()),
      r: this.http.get<Rehearsal[]>(
        this.api + "/response/rehearsals",
        this.opts(),
      ),
    })
      .pipe(
        timeout(12000),
        finalize(() => this.loading.set(false)),
      )
      .subscribe({
        next: (v) => {
          this.proposals.set(v.p);
          this.rows.set(v.r);
          const old = this.selected();
          if (old) this.selected.set(v.r.find((x) => x.id === old.id) || null);
        },
        error: (e) => this.fail(e),
      });
    this.subs.push(s);
  }
  rehearse() {
    if (this.busy() || !this.canApprove || !this.proposalId) return;
    this.busy.set(true);
    const s = this.http
      .post<Rehearsal>(
        this.api + "/response/proposals/" + this.proposalId + "/rehearse",
        {},
        this.opts(),
      )
      .pipe(
        timeout(12000),
        finalize(() => this.busy.set(false)),
      )
      .subscribe({
        next: (r) => {
          this.info.set(
            "Simulation rehearsal recorded; no infrastructure changes.",
          );
          this.selected.set(r);
          this.refresh();
        },
        error: (e) => this.fail(e),
      });
    this.subs.push(s);
  }
  rollback(r: Rehearsal) {
    if (this.busy() || !this.canApprove || this.note.trim().length < 10) return;
    this.busy.set(true);
    const s = this.http
      .post<Rehearsal>(
        this.api + "/response/rehearsals/" + r.id + "/rollback",
        { note: this.note.trim() },
        this.opts(),
      )
      .pipe(
        timeout(12000),
        finalize(() => this.busy.set(false)),
      )
      .subscribe({
        next: (v) => {
          this.selected.set(v);
          this.note = "";
          this.info.set(
            "Simulation marked rolled back; no external state changed.",
          );
          this.refresh();
        },
        error: (e) => this.fail(e),
      });
    this.subs.push(s);
  }
}
