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
import { finalize, Subscription, timeout } from "rxjs";
type Asset = { id: string; name: string };
type HuntEvent = {
  id: string;
  asset_id: string;
  event_time: string;
  event_type: string;
  severity: string;
  message: string;
  payload: Record<string, unknown>;
};
type Saved = { id: string; name: string; filters: any };
type Case = { id: string; title: string; asset_id: string; status: string };
@Component({
  selector: "app-p7-hunting",
  standalone: true,
  imports: [FormsModule],
  styles: [
    `
      .p7-panel {
        background: #101a2d;
        border: 1px solid #30405c;
        border-radius: 12px;
        padding: 18px;
        margin-bottom: 15px;
        color: #e8edff;
      }
      .p7-row {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        align-items: center;
        margin: 10px 0;
      }
      .p7-row > * {
        flex: 1;
        min-width: 135px;
      }
      .p7-field {
        background: #091323;
        color: #e8edff;
        border: 1px solid #364866;
        border-radius: 8px;
        padding: 10px;
        box-sizing: border-box;
        max-width: 100%;
      }
      .p7-btn {
        background: #7255d5;
        border: 1px solid #8573e6;
        color: white;
        border-radius: 7px;
        padding: 10px;
        cursor: pointer;
      }
      .p7-btn:disabled {
        opacity: 0.4;
        cursor: default;
      }
      .p7-muted {
        font-size: 12px;
        color: #a9b6d1;
      }
      .p7-error {
        color: #ffaaa5;
      }
      .p7-table {
        width: 100%;
        border-collapse: collapse;
        text-align: left;
      }
      .p7-table td,
      .p7-table th {
        border-bottom: 1px solid #2b3953;
        padding: 9px;
        font-size: 12px;
        vertical-align: top;
      }
      .p7-table td:last-child {
        max-width: 460px;
        overflow-wrap: anywhere;
      }
      .p7-scroll {
        overflow-x: auto;
      }
    `,
  ],
  template: ` <section class="p7-panel">
      <h2>P7 · Threat Hunting Workspace</h2>
      <p class="p7-muted">
        Historical telemetry searches only · max 7 days, 200 rows · no active
        scans or automated containment
      </p>
      @if (error()) {
        <p class="p7-error">{{ error() }}</p>
      }
      @if (info()) {
        <p style="color:#80ddb2">{{ info() }}</p>
      }
      <div class="p7-row">
        <label
          >From
          <input
            class="p7-field"
            type="datetime-local"
            [(ngModel)]="start" /></label
        ><label
          >To <input class="p7-field" type="datetime-local" [(ngModel)]="end"
        /></label>
        <select class="p7-field" [(ngModel)]="assetId">
          <option value="">All assets</option>
          @for (a of assets; track a.id) {
            <option [value]="a.id">{{ a.name }}</option>
          }
        </select>
        <input
          class="p7-field"
          placeholder="Event type (optional)"
          [(ngModel)]="eventType"
        />
      </div>
      <div class="p7-row">
        <input
          class="p7-field"
          placeholder="Message contains..."
          [(ngModel)]="text"
        />
        <select class="p7-field" [(ngModel)]="severity">
          <option value="">All severities</option>
          @for (s of severities; track s) {
            <option [value]="s">{{ s }}</option>
          }
        </select>
        <button class="p7-btn" [disabled]="loading()" (click)="search()">
          {{ loading() ? "Searching…" : "Search telemetry" }}</button
        ><button
          class="p7-btn"
          [disabled]="loading() || offset === 0"
          (click)="previous()"
        >
          Previous</button
        ><button
          class="p7-btn"
          [disabled]="loading() || !hasMore()"
          (click)="next()"
        >
          Next
        </button>
      </div>
      <p class="p7-muted">
        {{ results().length }} rows · offset {{ offset }} · newest first · no
        automatic polling
      </p>
    </section>
    <section class="p7-panel">
      <h3>Saved hunts</h3>
      <div class="p7-row">
        <input
          class="p7-field"
          placeholder="Save this hunt as..."
          [(ngModel)]="huntName"
        />
        <button
          class="p7-btn"
          [disabled]="!canWrite || saving() || huntName.trim().length < 3"
          (click)="saveHunt()"
        >
          Save hunt
        </button>
        <select class="p7-field" [(ngModel)]="selectedSaved">
          <option value="">Select saved hunt</option>
          @for (h of saved(); track h.id) {
            <option [value]="h.id">{{ h.name }}</option>
          }
        </select>
        <button
          class="p7-btn"
          [disabled]="!selectedSaved"
          (click)="applySaved()"
        >
          Apply</button
        ><button
          class="p7-btn"
          [disabled]="!canWrite || !selectedSaved"
          (click)="deleteSaved()"
        >
          Delete
        </button>
      </div>
    </section>
    <section class="p7-panel">
      <h3>IOC lookup</h3>
      <div class="p7-row">
        <select class="p7-field" [(ngModel)]="iocKind">
          <option value="ip">IP</option>
          <option value="domain">Domain</option>
          <option value="hash">Hash</option>
          <option value="process">Process</option>
        </select>
        <input
          class="p7-field"
          placeholder="IP, domain, hash, or process"
          [(ngModel)]="iocValue"
        /><button
          class="p7-btn"
          [disabled]="loading() || iocValue.trim().length < 2"
          (click)="searchIOC()"
        >
          Look up
        </button>
      </div>
      <p class="p7-muted">
        IOC lookup searches recorded event metadata; it does not contact or scan
        the indicator.
      </p>
    </section>
    <section class="p7-panel">
      <h3>Hunt results</h3>
      <div class="p7-scroll">
        <table class="p7-table">
          <thead>
            <tr>
              <th>TIME</th>
              <th>ASSET</th>
              <th>TYPE</th>
              <th>SEVERITY</th>
              <th>MESSAGE</th>
              <th>INVESTIGATION</th>
            </tr>
          </thead>
          <tbody>
            @for (e of results(); track e.id) {
              <tr>
                <td>{{ e.event_time }}</td>
                <td>{{ assetName(e.asset_id) }}</td>
                <td>{{ e.event_type }}</td>
                <td>{{ e.severity }}</td>
                <td>{{ e.message }}</td>
                <td>
                  @if (canWrite) {
                    <select class="p7-field" [(ngModel)]="caseChoice[e.id]">
                      <option value="">Choose same-asset incident</option>
                      @for (c of cases(); track c.id) {
                        @if (
                          c.asset_id === e.asset_id &&
                          c.status !== "resolved" &&
                          c.status !== "false_positive"
                        ) {
                          <option [value]="c.id">{{ c.title }}</option>
                        }
                      }
                    </select>
                    <button
                      class="p7-btn"
                      [disabled]="saving() || !caseChoice[e.id]"
                      (click)="attach(e)"
                    >
                      Link evidence
                    </button>
                  }
                </td>
              </tr>
            } @empty {
              <tr>
                <td colspan="6" class="p7-muted">
                  No results yet. Search a short time window first.
                </td>
              </tr>
            }
          </tbody>
        </table>
      </div>
    </section>`,
})
export class P7HuntingComponent implements OnChanges, OnDestroy {
  private http = inject(HttpClient);
  private api = "http://127.0.0.1:8000";
  private lastToken = "";
  private requests: Subscription[] = [];
  @Input() token = "";
  @Input() assets: Asset[] = [];
  @Input() canWrite = false;
  results = signal<HuntEvent[]>([]);
  saved = signal<Saved[]>([]);
  cases = signal<Case[]>([]);
  loading = signal(false);
  saving = signal(false);
  error = signal("");
  info = signal("");
  hasMore = signal(false);
  assetId = "";
  eventType = "";
  severity = "";
  text = "";
  start = "";
  end = "";
  offset = 0;
  huntName = "";
  selectedSaved = "";
  iocKind = "ip";
  iocValue = "";
  caseChoice: Record<string, string> = {};
  severities = ["info", "low", "medium", "high", "critical"];
  constructor() {
    const now = new Date();
    this.end = this.localDate(now);
    this.start = this.localDate(new Date(now.getTime() - 60 * 60 * 1000));
  }
  private localDate(d: Date) {
    const x = new Date(d.getTime() - d.getTimezoneOffset() * 60000);
    return x.toISOString().slice(0, 16);
  }
  private iso(s: string) {
    return new Date(s).toISOString();
  }
  private headers() {
    return {
      headers: new HttpHeaders({ Authorization: "Bearer " + this.token }),
    };
  }
  private report(e: any) {
    this.error.set(
      typeof e?.error?.detail === "string"
        ? e.error.detail
        : "Request failed; HTTP " + (e?.status ?? 0),
    );
  }
  assetName(id: string) {
    return this.assets.find((a) => a.id === id)?.name || id;
  }
  ngOnChanges(changes: SimpleChanges) {
    if (changes["token"] && this.token && this.lastToken !== this.token) {
      this.lastToken = this.token;
      this.loadLists();
    }
  }
  ngOnDestroy() {
    for (const s of this.requests) s.unsubscribe();
  }
  private filter() {
    return {
      start: this.iso(this.start),
      end: this.iso(this.end),
      asset_id: this.assetId || null,
      event_type: this.eventType || null,
      severity: this.severity || null,
      text: this.text || null,
      limit: 100,
      offset: this.offset,
    };
  }
  private loadLists() {
    if (!this.token) return;
    const s1 = this.http
      .get<Saved[]>(this.api + "/hunting/saved", this.headers())
      .pipe(timeout(12000))
      .subscribe({
        next: (v) => this.saved.set(v),
        error: (e) => this.report(e),
      });
    const s2 = this.http
      .get<Case[]>(this.api + "/incidents?limit=100", this.headers())
      .pipe(timeout(12000))
      .subscribe({
        next: (v) => this.cases.set(v),
        error: (e) => this.report(e),
      });
    this.requests.push(s1, s2);
  }
  private perform(url: string, body: any) {
    if (this.loading()) return;
    this.error.set("");
    this.loading.set(true);
    const s = this.http
      .post<{ events: HuntEvent[]; has_more?: boolean }>(
        this.api + url,
        body,
        this.headers(),
      )
      .pipe(
        timeout(12000),
        finalize(() => this.loading.set(false)),
      )
      .subscribe({
        next: (v) => {
          this.results.set(v.events);
          this.hasMore.set(v.has_more ?? false);
        },
        error: (e) => this.report(e),
      });
    this.requests.push(s);
  }
  search() {
    this.offset = 0;
    this.perform("/hunting/search", this.filter());
  }
  next() {
    this.offset += 100;
    this.perform("/hunting/search", this.filter());
  }
  previous() {
    this.offset = Math.max(0, this.offset - 100);
    this.perform("/hunting/search", this.filter());
  }
  searchIOC() {
    this.offset = 0;
    this.perform("/hunting/ioc", {
      kind: this.iocKind,
      value: this.iocValue,
      start: this.iso(this.start),
      end: this.iso(this.end),
      asset_id: this.assetId || null,
      limit: 100,
    });
  }
  saveHunt() {
    if (!this.canWrite || this.saving()) return;
    this.saving.set(true);
    const s = this.http
      .post(
        this.api + "/hunting/saved",
        { name: this.huntName.trim(), filters: this.filter() },
        this.headers(),
      )
      .pipe(
        timeout(12000),
        finalize(() => this.saving.set(false)),
      )
      .subscribe({
        next: () => {
          this.huntName = "";
          this.loadLists();
          this.info.set("Saved hunt");
        },
        error: (e) => this.report(e),
      });
    this.requests.push(s);
  }
  applySaved() {
    const x = this.saved().find((v) => v.id === this.selectedSaved);
    if (!x) return;
    const f = x.filters;
    this.start = this.localDate(new Date(f.start));
    this.end = this.localDate(new Date(f.end));
    this.assetId = f.asset_id || "";
    this.eventType = f.event_type || "";
    this.severity = f.severity || "";
    this.text = f.text || "";
    this.offset = 0;
    this.search();
  }
  deleteSaved() {
    if (!this.canWrite) return;
    const s = this.http
      .delete(this.api + "/hunting/saved/" + this.selectedSaved, this.headers())
      .pipe(timeout(12000))
      .subscribe({
        next: () => {
          this.selectedSaved = "";
          this.loadLists();
        },
        error: (e) => this.report(e),
      });
    this.requests.push(s);
  }
  attach(e: HuntEvent) {
    const id = this.caseChoice[e.id];
    if (!id || this.saving()) return;
    this.saving.set(true);
    const s = this.http
      .post(
        this.api + "/hunting/incidents/" + id + "/evidence",
        { event_id: e.id, note: "Linked from P7 hunt" },
        this.headers(),
      )
      .pipe(
        timeout(12000),
        finalize(() => this.saving.set(false)),
      )
      .subscribe({
        next: () => this.info.set("Evidence linked to incident"),
        error: (x) => this.report(x),
      });
    this.requests.push(s);
  }
}
