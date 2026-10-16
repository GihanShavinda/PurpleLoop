import { bootstrapApplication } from "@angular/platform-browser";
import { provideHttpClient } from "@angular/common/http";
import { Component, computed, inject, signal } from "@angular/core";
import {
  HttpClient,
  HttpHeaders,
  HttpErrorResponse,
} from "@angular/common/http";
import { FormsModule } from "@angular/forms";
import { P5ValidationComponent } from "./p5-validation.component";
import { P6IncidentsComponent } from "./p6-incidents.component";
import { P7HuntingComponent } from "./p7-hunting.component";
import { P8IntelligenceComponent } from "./p8-intelligence.component";
import { P9CorrelationComponent } from "./p9-correlation.component";
import { P10AnalystComponent } from "./p10-analyst.component";
import { P11SoarComponent } from "./p11-soar.component";
import { P12ResponseComponent } from "./p12-response.component";
import { P13SimulationComponent } from "./p13-simulation.component";
import { P14CoverageComponent } from "./p14-coverage.component";
import { P15AnomalyComponent } from "./p15-anomaly.component";
import { P16InvestigationComponent } from "./p16-investigation.component";
import { P17VmwareRangeComponent } from "./p17-vmware-range.component";
import { P18OperationsComponent } from "./p18-operations.component";

const API = "http://127.0.0.1:8000";
type Page = "dashboard" | "inventory" | "labs" | "topology" | "telemetry" | "detections" | "validation" | "incidents" | "hunting" | "intelligence" | "correlation" | "analyst" | "soar" | "response" | "simulation" | "coverage" | "anomaly" | "investigation" | "vmware-range" | "operations";
type Criticality = "low" | "medium" | "high" | "critical";
interface Lab {
  id: string;
  name: string;
  description: string | null;
}
interface Asset {
  id: string;
  lab_id: string;
  hostname: string;
  ip_address: string | null;
  mac_address: string | null;
  operating_system: string | null;
  asset_type: string;
  environment: string;
  criticality: Criticality;
  owner: string | null;
  vm_name: string | null;
  vmware_network: string | null;
  monitoring_enabled: boolean;
  created_at: string;
  updated_at: string;
}
interface TelemetrySource {
  id: string;
  asset_id: string;
  name: string;
  source_type: string;
  enabled: boolean;
  last_seen_at: string | null;
  state: string;
}
interface TelemetryEvent {
  id: string;
  asset_id: string;
  source_id: string;
  event_time: string;
  event_type: string;
  severity: string;
  message: string;
  payload: Record<string, unknown>;
}
interface TelemetrySummary {
  sources: number;
  receiving: number;
  events: number;
}
interface Summary {
  labs: number;
  assets: number;
  monitored: number;
  critical: number;
}
interface User {
  id: string;
  email: string;
  role_name: string;
  is_active: boolean;
}
interface AssetForm {
  lab_id: string;
  hostname: string;
  ip_address: string;
  mac_address: string;
  operating_system: string;
  asset_type: string;
  environment: string;
  criticality: Criticality;
  owner: string;
  vm_name: string;
  vmware_network: string;
  monitoring_enabled: boolean;
}
const blankAsset = (): AssetForm => ({
  lab_id: "",
  hostname: "",
  ip_address: "",
  mac_address: "",
  operating_system: "",
  asset_type: "Endpoint",
  environment: "lab",
  criticality: "medium",
  owner: "",
  vm_name: "",
  vmware_network: "",
  monitoring_enabled: false,
});
const assetTypes = [
  "Attacker",
  "Target",
  "Monitoring Sensor",
  "Domain Controller",
  "Server",
  "Endpoint",
  "Web Application",
  "Database Server",
  "Security Appliance",
  "VMware Host",
  "VMware Guest",
];
@Component({
  selector: "app-root",
  standalone: true,
  imports: [FormsModule, P5ValidationComponent, P6IncidentsComponent, P7HuntingComponent, P8IntelligenceComponent, P9CorrelationComponent, P10AnalystComponent, P11SoarComponent, P12ResponseComponent, P13SimulationComponent, P14CoverageComponent, P15AnomalyComponent, P16InvestigationComponent, P17VmwareRangeComponent, P18OperationsComponent],
  styles: [`
    :host .shell > aside.sidebar {
      position: sticky;
      top: 0;
      height: 100vh;
      height: 100dvh;
      max-height: 100dvh;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      min-height: 0;
    }
    :host .shell > aside.sidebar .sidebar-brand {
      flex: 0 0 auto;
    }
    :host .shell > aside.sidebar .nav-section {
      flex: 0 0 auto;
    }
    :host .shell > aside.sidebar nav {
      flex: 1 1 auto;
      min-height: 0;
      overflow-y: auto;
      overflow-x: hidden;
      overscroll-behavior: contain;
      scrollbar-width: thin;
      scrollbar-color: #575078 transparent;
      padding-bottom: 12px;
    }
    :host .shell > aside.sidebar nav::-webkit-scrollbar { width: 6px; }
    :host .shell > aside.sidebar nav::-webkit-scrollbar-thumb {
      background: #575078;
      border-radius: 6px;
    }
    :host .shell > aside.sidebar .sidebar-footer {
      flex: 0 0 auto;
    }
    @media (max-width: 768px) {
      :host .shell > aside.sidebar {
        height: 100dvh;
        max-height: 100dvh;
      }
    }
  `],
  template: `
    @if (!token()) {
      <div class="auth-layout">
        <div class="auth-card">
          <div class="brand-mark">✦</div>
          <div class="eyebrow">PURPLE TEAM OPERATIONS</div>
          <h1>PurpleForge <span>AI</span></h1>
          <p class="muted">VMware cyber-range operations · P5</p>
          <form (ngSubmit)="login()">
            <label
              >Email<input
                type="email"
                name="email"
                [(ngModel)]="email"
                required
                autocomplete="username" /></label
            ><label
              >Password<input
                type="password"
                name="password"
                [(ngModel)]="password"
                required
                autocomplete="current-password" /></label
            ><button class="primary full" type="submit" [disabled]="busy()">
              {{ busy() ? "Signing in…" : "Sign in →" }}
            </button>
          </form>
          @if (error()) {
            <div class="error-banner">{{ error() }}</div>
          }
          <p class="auth-note">Native services · No containers required</p>
        </div>
      </div>
    } @else {
      <div class="shell">
        <aside class="sidebar">
          <div class="sidebar-brand">
            <span class="brand-mark sm">✦</span
            ><span>PurpleForge <b>AI</b></span>
          </div>
          <div class="nav-section">WORKSPACE</div>
          <nav>
            <button
              [class.active]="page() === 'dashboard'"
              (click)="go('dashboard')"
            >
              <span>◫</span> Overview</button
            ><button
              [class.active]="page() === 'inventory'"
              (click)="go('inventory')"
            >
              <span>▤</span> Inventory</button
            ><button [class.active]="page() === 'labs'" (click)="go('labs')">
              <span>⬡</span> Labs</button
            ><button
              [class.active]="page() === 'topology'"
              (click)="go('topology')"
            >
              <span>◇</span> Network Topology
            </button>
            <button
              [class.active]="page() === 'telemetry'"
              (click)="go('telemetry')"
            >
              <span>⌁</span> Telemetry
            </button>
            <button
              [class.active]="page() === 'detections'"
              (click)="go('detections')"
            >
              <span>◈</span> Detections
            </button>
            <button
              [class.active]="page() === 'validation'"
              (click)="go('validation')"
            >
              <span>◎</span> Validation
            </button>
            <button [class.active]="page() === 'incidents'" (click)="go('incidents')"><span>⚑</span> Incidents</button>
            <button [class.active]="page() === 'hunting'" (click)="go('hunting')"><span>⌕</span> Threat Hunting</button>
            <button [class.active]="page() === 'intelligence'" (click)="go('intelligence')"><span>◉</span> Threat Intelligence</button>
            <button [class.active]="page() === 'correlation'" (click)="go('correlation')"><span>⌘</span> Correlation</button>
            <button [class.active]="page() === 'analyst'" (click)="go('analyst')"><span>◉</span> AI Analyst</button>
            <button [class.active]="page() === 'soar'" (click)="go('soar')"><span>◇</span> SOAR</button>
            <button [class.active]="page() === 'response'" (click)="go('response')"><span>↺</span> Response Lab</button>
            <button [class.active]="page() === 'simulation'" (click)="go('simulation')"><span>◎</span> Lab Simulation</button>
            <button [class.active]="page() === 'coverage'" (click)="go('coverage')"><span>◈</span> Detection Coverage</button>
            <button [class.active]="page() === 'anomaly'" (click)="go('anomaly')"><span>◉</span> Anomaly Detection</button>
            <button [class.active]="page() === 'investigation'" (click)="go('investigation')"><span>◇</span> Investigation Assistant</button>
            <button [class.active]="page() === 'vmware-range'" (click)="go('vmware-range')"><span>▣</span> VMware Range</button>
            <button [class.active]="page() === 'operations'" (click)="go('operations')"><span>▤</span> Operations Center</button>
          </nav>

          <div class="sidebar-footer">
            <span class="status-dot"></span> Local platform
            <span class="pill tiny">P5</span>
            <div class="muted small">VMware-first • No Docker</div>
          </div>
        </aside>
        <div class="workspace">
          <header class="topbar">
            <div class="breadcrumbs">
              PURPLEFORGE / <b>{{ pageLabel() }}</b>
            </div>
            <div class="top-right">
              <span class="live"><i></i> API connected</span
              ><span class="user-avatar">{{
                email.charAt(0).toUpperCase()
              }}</span
              ><span class="user-email">{{ email }}</span
              ><button class="text-button" (click)="logout()">Sign out</button>
            </div>
          </header>
          <main class="content">
            <div class="page-heading">
              <div>
                <div class="eyebrow">CYBER RANGE CONTROL CENTER</div>
                <h1>{{ pageLabel() }}</h1>
                <p class="muted">
                  Manage your isolated VMware lab and security assets.
                </p>
              </div>
              <button class="outline" (click)="load()">↻ Refresh data</button>
            </div>
            @if (error()) {
              <div class="error-banner">
                {{ error() }} <button (click)="error.set('')">×</button>
              </div>
            }
            @if (page() === "dashboard") {
              <div class="metric-grid">
                <div class="metric violet">
                  <div class="metric-label">Total labs <span>⬡</span></div>
                  <strong>{{ summary().labs }}</strong
                  ><small>Isolated environments</small>
                </div>
                <div class="metric blue">
                  <div class="metric-label">
                    Registered assets <span>▤</span>
                  </div>
                  <strong>{{ summary().assets }}</strong
                  ><small>VMs and services</small>
                </div>
                <div class="metric cyan">
                  <div class="metric-label">
                    Monitoring configured <span>◉</span>
                  </div>
                  <strong>{{ summary().monitored }}</strong
                  ><small>Inventory flag, not live health</small>
                </div>
                <div class="metric orange">
                  <div class="metric-label">Critical assets <span>⚑</span></div>
                  <strong>{{ summary().critical }}</strong
                  ><small>Criticality classification</small>
                </div>
              </div>
              <div class="dual">
                <section class="panel">
                  <div class="panel-head">
                    <div>
                      <h2>Lab overview</h2>
                      <p>VMware lab environments</p>
                    </div>
                    <button class="subtle" (click)="go('labs')">
                      Manage →
                    </button>
                  </div>
                  @for (l of labs(); track l.id) {
                    <div class="item-row">
                      <div class="icon-tile">⬡</div>
                      <div class="grow">
                        <b>{{ l.name }}</b
                        ><small>{{ l.description || "No description" }}</small>
                      </div>
                      <span class="pill">{{ countInLab(l.id) }} assets</span>
                    </div>
                  } @empty {
                    <div class="empty">
                      No labs created yet.
                      <button class="link" (click)="openLab()">
                        Create your first lab →
                      </button>
                    </div>
                  }
                </section>
                <section class="panel">
                  <div class="panel-head">
                    <div>
                      <h2>Network segments</h2>
                      <p>VMware networks in inventory</p>
                    </div>
                    <button class="subtle" (click)="go('topology')">
                      View map →
                    </button>
                  </div>
                  @for (n of networks(); track n.name) {
                    <div class="item-row">
                      <div class="icon-tile cyan-icon">◇</div>
                      <div class="grow">
                        <b>{{ n.name }}</b
                        ><small>Recorded VMnet or segment</small>
                      </div>
                      <span class="pill">{{ n.assets.length }} assets</span>
                    </div>
                  } @empty {
                    <div class="empty">
                      Add assets with a VMware network label to populate this
                      panel.
                    </div>
                  }
                </section>
              </div>
              <section class="panel">
                <div class="panel-head">
                  <div>
                    <h2>Recently registered assets</h2>
                    <p>Showing up to 5 inventory items</p>
                  </div>
                  <button class="subtle" (click)="go('inventory')">
                    Full inventory →
                  </button>
                </div>
                <div class="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>ASSET</th>
                        <th>ROLE</th>
                        <th>IP ADDRESS</th>
                        <th>CRITICALITY</th>
                        <th>MONITORING</th>
                      </tr>
                    </thead>
                    <tbody>
                      @for (a of assets().slice(0, 5); track a.id) {
                        <tr>
                          <td>
                            <span class="asset-name">{{ a.hostname }}</span
                            ><span class="subline">{{
                              a.operating_system || "OS unspecified"
                            }}</span>
                          </td>
                          <td>{{ a.asset_type }}</td>
                          <td class="mono">{{ a.ip_address || "—" }}</td>
                          <td>
                            <span
                              class="pill"
                              [class.danger]="a.criticality === 'critical'"
                              [class.warn]="a.criticality === 'high'"
                              >{{ a.criticality }}</span
                            >
                          </td>
                          <td>
                            <span
                              class="pill"
                              [class.good]="a.monitoring_enabled"
                              >{{
                                a.monitoring_enabled ? "Enabled" : "Not enabled"
                              }}</span
                            >
                          </td>
                        </tr>
                      } @empty {
                        <tr>
                          <td colspan="5" class="empty">
                            No registered assets yet.
                          </td>
                        </tr>
                      }
                    </tbody>
                  </table>
                </div>
              </section>
            }
            @if (page() === "inventory") {
              <div class="panel">
                <div class="panel-head">
                  <div>
                    <h2>
                      Asset inventory
                      <span class="heading-count">{{
                        filteredAssets().length
                      }}</span>
                    </h2>
                    <p>Registered VMware guests, hosts, sensors and targets</p>
                  </div>
                  @if (canEdit()) {
                    <button class="primary" (click)="openAsset()">
                      + Add asset
                    </button>
                  }
                </div>
                <div class="filters">
                  <input
                    placeholder="⌕  Search hostname, IP, VM…"
                    [(ngModel)]="search"
                    name="search"
                  /><select [(ngModel)]="filterLab" name="lab">
                    <option value="">All labs</option>
                    @for (l of labs(); track l.id) {
                      <option [value]="l.id">{{ l.name }}</option>
                    }</select
                  ><select [(ngModel)]="filterType" name="type">
                    <option value="">All types</option>
                    @for (t of assetTypes; track t) {
                      <option [value]="t">{{ t }}</option>
                    }</select
                  ><select [(ngModel)]="filterCritical" name="critical">
                    <option value="">Any criticality</option>
                    @for (t of criticalities; track t) {
                      <option [value]="t">{{ t }}</option>
                    }
                  </select>
                </div>
                <div class="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>ASSET</th>
                        <th>TYPE</th>
                        <th>NETWORK</th>
                        <th>IP ADDRESS</th>
                        <th>CRITICALITY</th>
                        <th>MONITORING</th>
                        <th>ACTIONS</th>
                      </tr>
                    </thead>
                    <tbody>
                      @for (a of filteredAssets(); track a.id) {
                        <tr>
                          <td>
                            <div class="asset-cell">
                              <div class="device-icon">▣</div>
                              <div>
                                <b>{{ a.hostname }}</b
                                ><span class="subline">{{
                                  a.operating_system || "Unknown OS"
                                }}</span>
                              </div>
                            </div>
                          </td>
                          <td>{{ a.asset_type }}</td>
                          <td>{{ a.vmware_network || "—" }}</td>
                          <td class="mono">{{ a.ip_address || "—" }}</td>
                          <td>
                            <span
                              class="pill"
                              [class.danger]="a.criticality === 'critical'"
                              [class.warn]="a.criticality === 'high'"
                              >{{ a.criticality }}</span
                            >
                          </td>
                          <td>
                            <span
                              class="pill"
                              [class.good]="a.monitoring_enabled"
                              >{{
                                a.monitoring_enabled ? "Enabled" : "Disabled"
                              }}</span
                            >
                          </td>
                          <td>
                            <div class="table-actions">
                              <button (click)="viewAsset(a)">View</button>
                              @if (canEdit()) {
                                <button (click)="openAsset(a)">Edit</button>
                              }
                              @if (canManage()) {
                                <button class="red" (click)="removeAsset(a)">
                                  Delete
                                </button>
                              }
                            </div>
                          </td>
                        </tr>
                      } @empty {
                        <tr>
                          <td colspan="7" class="empty">
                            No assets match your filters. Add a VM to begin.
                          </td>
                        </tr>
                      }
                    </tbody>
                  </table>
                </div>
                <div class="table-foot">
                  Showing {{ filteredAssets().length }} of
                  {{ assets().length }} loaded assets · first 200 records
                </div>
              </div>
            }
            @if (page() === "labs") {
              <div class="panel">
                <div class="panel-head">
                  <div>
                    <h2>VMware laboratories</h2>
                    <p>Organize isolated cyber-range environments</p>
                  </div>
                  @if (canManage()) {
                    <button class="primary" (click)="openLab()">
                      + Create lab
                    </button>
                  }
                </div>
                <div class="lab-grid">
                  @for (l of labs(); track l.id) {
                    <article class="lab-card">
                      <div class="lab-symbol">⬡</div>
                      <h3>{{ l.name }}</h3>
                      <p class="muted">
                        {{ l.description || "No description provided" }}
                      </p>
                      <div class="lab-bottom">
                        <span class="pill">{{ countInLab(l.id) }} assets</span>
                        <div class="table-actions">
                          @if (canManage()) {
                            <button (click)="openLab(l)">Edit</button
                            ><button class="red" (click)="removeLab(l)">
                              Delete
                            </button>
                          }
                          <button (click)="openLabInventory(l.id)">
                            Assets →
                          </button>
                        </div>
                      </div>
                    </article>
                  } @empty {
                    <div class="empty">
                      No laboratories. Create one to group your VMware assets.
                    </div>
                  }
                </div>
              </div>
            }
            @if (page() === "topology") {
              <section class="panel">
                <div class="panel-head">
                  <div>
                    <h2>VMware topology explorer</h2>
                    <p>
                      Logical grouping from registered VMnet labels — not a live
                      network scan
                    </p>
                  </div>
                  <select [(ngModel)]="topologyLab" name="topologyLab">
                    <option value="">All labs</option>
                    @for (l of labs(); track l.id) {
                      <option [value]="l.id">{{ l.name }}</option>
                    }
                  </select>
                </div>
                <div class="topology">
                  <div class="topology-source">
                    <span class="topo-icon">▦</span><b>VMware Workstation</b
                    ><small>Inventory visualization</small>
                  </div>
                  <div class="network-grid">
                    @for (net of topologyNetworks(); track net.name) {
                      <div class="network-group">
                        <div class="network-title">
                          <span>◇</span> {{ net.name }}
                          <small>{{ net.assets.length }} assets</small>
                        </div>
                        <div class="node-grid">
                          @for (a of net.assets; track a.id) {
                            <button class="network-node" (click)="viewAsset(a)">
                              <span class="node-icon">▣</span
                              ><b>{{ a.hostname }}</b
                              ><small>{{ a.asset_type }}</small
                              ><span class="mono">{{
                                a.ip_address || "No IP"
                              }}</span>
                            </button>
                          }
                        </div>
                      </div>
                    } @empty {
                      <div class="empty">
                        No network topology to display. Register assets and set
                        their VMware network.
                      </div>
                    }
                  </div>
                </div>
                <div class="topology-foot">
                  Lines and actual traffic paths are intentionally not inferred.
                  Network grouping is based only on saved asset metadata.
                </div>
              </section>
            }
      @if(page()==='operations'){
        <app-p18-operations [token]="token()" />
      }
      @if(page()==='vmware-range'){
        <app-p17-vmware-range [token]="token()" [canWrite]="canManage()" />
      }
      @if(page()==='investigation'){
        <app-p16-investigation [token]="token()" [canWrite]="canManage()" />
      }
      @if(page()==='anomaly'){
        <app-p15-anomaly [token]="token()" [canWrite]="canManage()" />
      }
      @if(page()==='coverage'){
        <app-p14-coverage [token]="token()" [canWrite]="canManage()" />
      }
      @if(page()==='simulation'){
        <app-p13-simulation [token]="token()" [assets]="validationAssets()" [canWrite]="canManage()" />
      }
      @if(page()==='response'){
        <app-p12-response [token]="token()" [canApprove]="canManage()" />
      }
      @if(page()==='soar'){
        <app-p11-soar [token]="token()" [canWrite]="canIncidentWrite()" [canApprove]="canManage()" />
      }
      @if(page()==='analyst'){
        <app-p10-analyst [token]="token()" [assets]="validationAssets()" [canWrite]="canIncidentWrite()" />
      }
      @if(page()==='correlation'){
        <app-p9-correlation [token]="token()" [assets]="validationAssets()" [canWrite]="canIncidentWrite()" />
      }
      @if(page()==='intelligence'){
        <app-p8-intelligence [token]="token()" [assets]="validationAssets()" [canWrite]="canIncidentWrite()" />
      }
      @if(page()==='hunting'){
        <app-p7-hunting [token]="token()" [assets]="validationAssets()" [canWrite]="canIncidentWrite()" />
      }
      @if(page()==='incidents'){
        <app-p6-incidents [token]="token()" [assets]="validationAssets()" [canWrite]="canIncidentWrite()" />
      }
      @if(page()==='validation'){
        <app-p5-validation [token]="token()" [assets]="validationAssets()" [canWrite]="canEdit()" />
      }
      @if(page()==='detections'){
        <div class="metric-grid"><div class="metric violet"><div class="metric-label">Rules</div><strong>{{detectionSummary().rules}}</strong><small>Registered</small></div><div class="metric cyan"><div class="metric-label">Enabled</div><strong>{{detectionSummary().enabled}}</strong><small>Active predicates</small></div><div class="metric orange"><div class="metric-label">Findings</div><strong>{{detectionSummary().findings}}</strong><small>Deduplicated telemetry matches</small></div></div>
        <section class="panel"><div class="panel-head"><div><h2>Rule management</h2><p>Deterministic Sigma-inspired event predicates · advisory only</p></div><button class="outline" (click)="loadDetections()">Refresh</button></div>
        @if(canEdit()){
        <div class="filters"><input placeholder="Rule name" [(ngModel)]="ruleName"><select [(ngModel)]="ruleKind"><option value="sigma">Sigma-style</option><option value="suricata">Suricata event</option><option value="yara">YARA metadata (no scanning)</option></select><select [(ngModel)]="ruleSeverity"><option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option><option value="critical">Critical</option></select></div>
        <div class="filters"><input placeholder="Event type, optional (e.g. sysmon.1)" [(ngModel)]="ruleEventType"><select [(ngModel)]="ruleField">@for(f of detectionFields;track f){<option [value]="f">{{f}}</option>}</select><select [(ngModel)]="ruleOperator"><option value="contains">Contains</option><option value="equals">Equals</option><option value="startswith">Starts with</option><option value="endswith">Ends with</option></select><input placeholder="Expected value" [(ngModel)]="ruleExpected"><button class="primary" [disabled]="busy()" (click)="createDetectionRule()">Create rule</button></div>
        <div class="filters"><button class="primary" [disabled]="busy()" (click)="runDetectionEvaluation()">Evaluate latest 500 events</button><span class="muted">{{detectionResult()}}</span></div>
        }
        <div class="table-scroll"><table><thead><tr><th>RULE</th><th>KIND</th><th>MATCH</th><th>SEVERITY</th><th>STATUS</th><th>ACTION</th></tr></thead><tbody>@for(r of detectionRules();track r.id){<tr><td>{{r.name}}</td><td>{{r.rule_kind}}</td><td class="mono">{{r.field_name}} {{r.operator}} {{r.expected_value}}</td><td>{{r.severity}}</td><td><span class="pill" [class.good]="r.enabled">{{r.enabled?'Enabled':'Disabled'}}</span></td><td>@if(canEdit()){<button class="subtle" (click)="toggleDetectionRule(r)">{{r.enabled?'Disable':'Enable'}}</button>}</td></tr>}@empty{<tr><td colspan="6" class="empty">No detection rules yet.</td></tr>}</tbody></table></div></section>
        <section class="panel"><div class="panel-head"><div><h2>Detection findings</h2><p>Matched telemetry evidence — no automated actions</p></div></div><div class="table-scroll"><table><thead><tr><th>RULE</th><th>ASSET</th><th>SEVERITY</th><th>EVIDENCE</th><th>STATUS</th></tr></thead><tbody>@for(f of detectionFindings();track f.id){<tr><td>{{f.rule_name}}</td><td>{{assetLabel(f.asset_id)}}</td><td>{{f.severity}}</td><td>{{f.event_message}}</td><td>{{f.status}}</td></tr>}@empty{<tr><td colspan="5" class="empty">No findings; create a rule and evaluate stored telemetry.</td></tr>}</tbody></table></div></section>
      }

            @if (page() === "telemetry") {
              <div class="metric-grid">
                <div class="metric violet">
                  <div class="metric-label">Telemetry Sources</div>
                  <strong>{{ telemetrySummary().sources }}</strong
                  ><small>Registered collector identities</small>
                </div>
                <div class="metric cyan">
                  <div class="metric-label">Receiving</div>
                  <strong>{{ telemetrySummary().receiving }}</strong
                  ><small>Last event within 10 minutes</small>
                </div>
                <div class="metric blue">
                  <div class="metric-label">Stored Events</div>
                  <strong>{{ telemetrySummary().events }}</strong
                  ><small>PostgreSQL event records</small>
                </div>
              </div>
              @if (canManage()) {
                <section class="panel">
                  <div class="panel-head">
                    <div>
                      <h2>Register native collector</h2>
                      <p>
                        Bind one source to one VMware lab asset. Key shown only
                        once.
                      </p>
                    </div>
                  </div>
                  <div class="filters">
                    <select [(ngModel)]="sourceAsset" name="sourceAsset">
                      <option value="">Select asset</option>
                      @for (a of assets(); track a.id) {
                        <option [value]="a.id">{{ a.hostname }}</option>
                      }
                    </select>
                    <select [(ngModel)]="sourceType" name="sourceType">
                      @for (t of sourceTypes; track t) {
                        <option [value]="t">{{ t }}</option>
                      }
                    </select>
                    <input
                      [(ngModel)]="sourceName"
                      name="sourceName"
                      placeholder="Source name (e.g. ubuntu journal)"
                    /><button
                      class="primary"
                      [disabled]="busy() || !sourceAsset || !sourceName.trim()"
                      (click)="createSource()"
                    >
                      Create source
                    </button>
                  </div>
                  @if (issuedKey()) {
                    <div class="key-notice">
                      <b
                        >New collector key (copy and store securely; shown
                        once):</b
                      ><code>{{ issuedKey() }}</code
                      ><button class="outline" (click)="issuedKey.set('')">
                        Dismiss
                      </button>
                    </div>
                  }
                </section>
              }
              <section class="panel">
                <div class="panel-head">
                  <div>
                    <h2>Collector health</h2>
                    <p>
                      State based on verified event receipts, not inventory
                      flags
                    </p>
                  </div>
                  <button class="outline" (click)="loadTelemetry()">
                    Refresh telemetry
                  </button>
                </div>
                <div class="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>SOURCE</th>
                        <th>ASSET</th>
                        <th>TYPE</th>
                        <th>STATE</th>
                        <th>LAST EVENT</th>
                        <th>ACTION</th>
                      </tr>
                    </thead>
                    <tbody>
                      @for (src of telemetrySources(); track src.id) {
                        <tr>
                          <td>{{ src.name || src.id }}</td>
                          <td>{{ assetLabel(src.asset_id) }}</td>
                          <td>{{ src.source_type }}</td>
                          <td>
                            <span
                              class="pill"
                              [class.good]="src.state === 'receiving'"
                              [class.warn]="src.state === 'stale'"
                              >{{ src.state }}</span
                            >
                          </td>
                          <td>{{ src.last_seen_at || "Never" }}</td>
                          <td>
                            @if (canManage()) {
                              <button
                                class="subtle"
                                (click)="switchSource(src)"
                              >
                                {{ src.enabled ? "Disable" : "Enable" }}
                              </button>
                            }
                          </td>
                        </tr>
                      } @empty {
                        <tr>
                          <td colspan="6" class="empty">
                            No collectors registered yet.
                          </td>
                        </tr>
                      }
                    </tbody>
                  </table>
                </div>
              </section>
              <section class="panel">
                <div class="panel-head">
                  <div>
                    <h2>Security event explorer</h2>
                    <p>Latest 100 ingested events</p>
                  </div>
                  <select
                    [(ngModel)]="eventAsset"
                    name="eventAsset"
                    (ngModelChange)="loadTelemetry()"
                  >
                    <option value="">All assets</option>
                    @for (a of assets(); track a.id) {
                      <option [value]="a.id">{{ a.hostname }}</option>
                    }
                  </select>
                </div>
                <div class="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>EVENT TIME</th>
                        <th>ASSET</th>
                        <th>TYPE</th>
                        <th>SEVERITY</th>
                        <th>MESSAGE</th>
                      </tr>
                    </thead>
                    <tbody>
                      @for (ev of telemetryEvents(); track ev.id) {
                        <tr>
                          <td class="mono">{{ ev.event_time }}</td>
                          <td>{{ assetLabel(ev.asset_id) }}</td>
                          <td>{{ ev.event_type }}</td>
                          <td>
                            <span
                              class="pill"
                              [class.warn]="ev.severity === 'high'"
                              [class.danger]="ev.severity === 'critical'"
                              >{{ ev.severity }}</span
                            >
                          </td>
                          <td>{{ ev.message }}</td>
                        </tr>
                      } @empty {
                        <tr>
                          <td colspan="5" class="empty">
                            No events received. Start a native collector to
                            populate the explorer.
                          </td>
                        </tr>
                      }
                    </tbody>
                  </table>
                </div>
              </section>
            }
            <footer>
              PurpleForge AI · P5 Detection Validation · P4 Detection Engineering ·
              Native Windows/Linux services
            </footer>
          </main>
        </div>
      </div>
      @if (showLabForm()) {
        <div class="modal-backdrop" (click)="closeForms()">
          <div class="modal" (click)="$event.stopPropagation()">
            <div class="modal-head">
              <h2>{{ editingLabId ? "Edit" : "Create" }} lab</h2>
              <button (click)="closeForms()">✕</button>
            </div>
            <form (ngSubmit)="saveLab()">
              <label
                >Lab name<input
                  [(ngModel)]="labName"
                  name="labName"
                  required
                  maxlength="150" /></label
              ><label
                >Description<textarea
                  [(ngModel)]="labDescription"
                  name="description"
                  rows="3"
                ></textarea>
              </label>
              <div class="modal-actions">
                <button type="button" class="outline" (click)="closeForms()">
                  Cancel</button
                ><button type="submit" class="primary" [disabled]="busy()">
                  Save lab
                </button>
              </div>
            </form>
          </div>
        </div>
      }
      @if (showAssetForm()) {
        <div class="modal-backdrop" (click)="closeForms()">
          <div class="modal wide" (click)="$event.stopPropagation()">
            <div class="modal-head">
              <h2>{{ editingAssetId ? "Edit" : "Register" }} asset</h2>
              <button (click)="closeForms()">✕</button>
            </div>
            <form (ngSubmit)="saveAsset()">
              <div class="form-grid">
                <label
                  >Lab<select
                    name="lab_id"
                    [(ngModel)]="assetForm.lab_id"
                    required
                    [disabled]="!!editingAssetId"
                  >
                    @for (l of labs(); track l.id) {
                      <option [value]="l.id">{{ l.name }}</option>
                    }
                  </select></label
                ><label
                  >Hostname<input
                    name="hostname"
                    [(ngModel)]="assetForm.hostname"
                    required
                    maxlength="255" /></label
                ><label
                  >Asset type<select
                    name="asset_type"
                    [(ngModel)]="assetForm.asset_type"
                  >
                    @for (t of assetTypes; track t) {
                      <option [value]="t">{{ t }}</option>
                    }
                  </select></label
                ><label
                  >Operating system<input
                    name="operating_system"
                    [(ngModel)]="assetForm.operating_system"
                    placeholder="Ubuntu 24.04, Windows 11…" /></label
                ><label
                  >IP address<input
                    name="ip_address"
                    [(ngModel)]="assetForm.ip_address"
                    placeholder="192.168.56.10" /></label
                ><label
                  >MAC address<input
                    name="mac_address"
                    [(ngModel)]="assetForm.mac_address"
                    placeholder="aa:bb:cc:dd:ee:ff" /></label
                ><label
                  >VM name<input
                    name="vm_name"
                    [(ngModel)]="assetForm.vm_name"
                    placeholder="Name in VMware Workstation" /></label
                ><label
                  >VMware network<input
                    name="vmware_network"
                    [(ngModel)]="assetForm.vmware_network"
                    placeholder="VMnet2 / Attack LAN" /></label
                ><label
                  >Environment<input
                    name="environment"
                    [(ngModel)]="assetForm.environment" /></label
                ><label
                  >Owner<input
                    name="owner"
                    [(ngModel)]="assetForm.owner" /></label
                ><label
                  >Criticality<select
                    name="criticality"
                    [(ngModel)]="assetForm.criticality"
                  >
                    @for (t of criticalities; track t) {
                      <option [value]="t">{{ t }}</option>
                    }
                  </select></label
                ><label class="checkline"
                  ><input
                    type="checkbox"
                    name="monitoring_enabled"
                    [(ngModel)]="assetForm.monitoring_enabled"
                  />
                  Monitoring configured</label
                >
              </div>
              <div class="modal-actions">
                <button type="button" class="outline" (click)="closeForms()">
                  Cancel</button
                ><button type="submit" class="primary" [disabled]="busy()">
                  Save asset
                </button>
              </div>
            </form>
          </div>
        </div>
      }
      @if (selectedAsset()) {
        <div class="modal-backdrop" (click)="selectedAsset.set(null)">
          <div class="modal" (click)="$event.stopPropagation()">
            <div class="modal-head">
              <h2>Asset details</h2>
              <button (click)="selectedAsset.set(null)">✕</button>
            </div>
            <h3>{{ selectedAsset()!.hostname }}</h3>
            <div class="detail-list">
              <div>
                <span>Role</span><b>{{ selectedAsset()!.asset_type }}</b>
              </div>
              <div>
                <span>IP address</span
                ><b>{{ selectedAsset()!.ip_address || "—" }}</b>
              </div>
              <div>
                <span>MAC address</span
                ><b>{{ selectedAsset()!.mac_address || "—" }}</b>
              </div>
              <div>
                <span>VMware network</span
                ><b>{{ selectedAsset()!.vmware_network || "—" }}</b>
              </div>
              <div>
                <span>Operating system</span
                ><b>{{ selectedAsset()!.operating_system || "—" }}</b>
              </div>
              <div>
                <span>VM name</span><b>{{ selectedAsset()!.vm_name || "—" }}</b>
              </div>
              <div>
                <span>Criticality</span
                ><b>{{ selectedAsset()!.criticality }}</b>
              </div>
              <div>
                <span>Monitoring configured</span
                ><b>{{ selectedAsset()!.monitoring_enabled ? "Yes" : "No" }}</b>
              </div>
            </div>
          </div>
        </div>
      }
    }
  `,
})
class App {
  private http = inject(HttpClient);
  email = "";
  password = "";
  token = signal("");
  refreshToken = signal("");
  error = signal("");
  busy = signal(false);
  page = signal<Page>("dashboard");
  user = signal<User | null>(null);
  labs = signal<Lab[]>([]);
  assets = signal<Asset[]>([]);
  summary = signal<Summary>({ labs: 0, assets: 0, monitored: 0, critical: 0 });
  telemetrySources = signal<TelemetrySource[]>([]);
  telemetryEvents = signal<TelemetryEvent[]>([]);
  telemetrySummary = signal<TelemetrySummary>({
    sources: 0,
    receiving: 0,
    events: 0,
  });
  detectionRules=signal<any[]>([]); detectionFindings=signal<any[]>([]); detectionSummary=signal({rules:0,enabled:0,findings:0}); detectionResult=signal('');
  ruleName='';ruleKind='sigma';ruleSeverity='medium';ruleEventType='';ruleField='message';ruleOperator='contains';ruleExpected='';
  detectionFields=['message','event_type','severity','payload.EventID','payload.EventId','payload.event_type','payload.Image','payload.CommandLine','payload.DestinationIp','payload.DestinationPort','payload.QueryName','payload.alert.signature','payload.alert.signature_id','payload.proto','payload.src_ip','payload.dest_ip'];
  loadDetections(){
    this.http.get<any[]>(API+'/detections/rules',this.auth()).subscribe({next:v=>this.detectionRules.set(v),error:e=>this.error.set(this.explain(e))});
    this.http.get<any[]>(API+'/detections/findings',this.auth()).subscribe({next:v=>this.detectionFindings.set(v),error:e=>this.error.set(this.explain(e))});
    this.http.get<{rules:number;enabled:number;findings:number}>(API+'/detections/summary',this.auth()).subscribe({next:v=>this.detectionSummary.set(v),error:e=>this.error.set(this.explain(e))});
  }
  createDetectionRule(){if(!this.ruleName.trim()||!this.ruleExpected.trim())return;this.busy.set(true);const body={name:this.ruleName.trim(),rule_kind:this.ruleKind,severity:this.ruleSeverity,event_type:this.ruleEventType.trim()||null,field_name:this.ruleField,operator:this.ruleOperator,expected_value:this.ruleExpected.trim(),enabled:true};this.http.post(API+'/detections/rules',body,this.auth()).subscribe({next:()=>{this.busy.set(false);this.ruleName='';this.loadDetections()},error:e=>{this.busy.set(false);this.error.set(this.explain(e))}});}
  toggleDetectionRule(r:any){this.http.patch(API+'/detections/rules/'+r.id+'?enabled='+(!r.enabled),{},this.auth()).subscribe({next:()=>this.loadDetections(),error:e=>this.error.set(this.explain(e))});}
  runDetectionEvaluation(){this.busy.set(true);this.http.post<{new_findings:number;enabled_rules:number;evaluated_events:number}>(API+'/detections/evaluate?limit=500',{},this.auth()).subscribe({next:r=>{this.busy.set(false);this.detectionResult.set(`Checked ${r.evaluated_events} events against ${r.enabled_rules} rules; created ${r.new_findings} findings.`);this.loadDetections()},error:e=>{this.busy.set(false);this.error.set(this.explain(e))}});}

  sourceAsset = "";
  sourceType = "linux_journal";
  sourceName = "";
  issuedKey = signal("");
  eventAsset = "";
  sourceTypes = [
    "sysmon",
    "windows_event",
    "auditd",
    "linux_journal",
    "suricata",
    "zeek",
    "osquery",
    "pcap",
    "custom",
  ];
  loadTelemetry() {
    this.http
      .get<TelemetrySource[]>(API + "/telemetry/sources", this.auth())
      .subscribe({
        next: (v) => this.telemetrySources.set(v),
        error: (e) => this.error.set(this.explain(e)),
      });
    this.http
      .get<TelemetrySummary>(API + "/telemetry/summary", this.auth())
      .subscribe({
        next: (v) => this.telemetrySummary.set(v),
        error: (e) => this.error.set(this.explain(e)),
      });
    this.http
      .get<
        TelemetryEvent[]
      >(API + "/telemetry/events?limit=100" + (this.eventAsset ? "&asset_id=" + encodeURIComponent(this.eventAsset) : ""), this.auth())
      .subscribe({
        next: (v) => this.telemetryEvents.set(v),
        error: (e) => this.error.set(this.explain(e)),
      });
  }
  createSource() {
    if (!this.sourceAsset || !this.sourceName.trim()) return;
    this.busy.set(true);
    this.issuedKey.set("");
    this.http
      .post<{
        collector_key: string;
      }>(API + "/telemetry/sources", { asset_id: this.sourceAsset, source_type: this.sourceType, name: this.sourceName.trim() }, this.auth())
      .subscribe({
        next: (v) => {
          this.issuedKey.set(v.collector_key);
          this.busy.set(false);
          this.loadTelemetry();
        },
        error: (e) => {
          this.busy.set(false);
          this.error.set(this.explain(e));
        },
      });
  }
  switchSource(src: TelemetrySource) {
    this.http
      .patch(
        API + "/telemetry/sources/" + src.id + "?enabled=" + !src.enabled,
        {},
        this.auth(),
      )
      .subscribe({
        next: () => this.loadTelemetry(),
        error: (e) => this.error.set(this.explain(e)),
      });
  }
  validationAssets = computed(() => this.assets().map(a => ({ id: a.id, name: a.hostname })));
  assetLabel(id: string) {
    return this.assets().find((a) => a.id === id)?.hostname || id;
  }
  search = "";
  filterLab = "";
  filterType = "";
  filterCritical = "";
  topologyLab = "";
  assetTypes = assetTypes;
  criticalities: Criticality[] = ["low", "medium", "high", "critical"];
  showLabForm = signal(false);
  showAssetForm = signal(false);
  selectedAsset = signal<Asset | null>(null);
  editingLabId = "";
  labName = "";
  labDescription = "";
  editingAssetId = "";
  assetForm: AssetForm = blankAsset();
  pageLabel = computed(
    () =>
      ({
        dashboard: "Dashboard",
        inventory: "Asset Inventory",
        labs: "VMware Labs",
        topology: "Network Topology",
        telemetry: "Telemetry Center",
        detections: "Detection Engineering",
        validation: "Detection Validation",
        incidents: "Incident Triage",
        hunting: "Threat Hunting",
        intelligence: "Threat Intelligence",
        correlation: "Correlation Analysis",
        analyst: "SOC Analyst Workspace",
        soar: "SOAR Approval Center",
        response: "Response Rehearsal",
        simulation: "Lab Simulation",
        coverage: "Detection Coverage",
        operations: "Purple Team Operations",
        "vmware-range": "VMware Range",
        investigation: "Investigation Assistant",
        anomaly: "Anomaly Detection",
      })[this.page()],
  );
  filteredAssets() {
    const term = this.search.toLowerCase().trim();
    return this.assets().filter(
      (a) =>
        (!term ||
          [a.hostname, a.ip_address, a.vm_name, a.operating_system].some((v) =>
            v?.toLowerCase().includes(term),
          )) &&
        (!this.filterLab || a.lab_id === this.filterLab) &&
        (!this.filterType || a.asset_type === this.filterType) &&
        (!this.filterCritical || a.criticality === this.filterCritical),
    );
  }
  networks = computed(() => this.groupNetworks(this.assets()));
  topologyNetworks() {
    return this.groupNetworks(
      this.assets().filter(
        (a) => !this.topologyLab || a.lab_id === this.topologyLab,
      ),
    );
  }
  private groupNetworks(assets: Asset[]) {
    const groups = new Map<string, Asset[]>();
    for (const a of assets) {
      const name = a.vmware_network?.trim() || "Unassigned network";
      groups.set(name, [...(groups.get(name) || []), a]);
    }
    return Array.from(groups, ([name, assets]) => ({ name, assets }));
  }
  canManage() {
    return ["Administrator", "Purple Team Engineer"].includes(
      this.user()?.role_name || "",
    );
  }
  canEdit() {
    return [
      "Administrator",
      "Purple Team Engineer",
      "Detection Engineer",
    ].includes(this.user()?.role_name || "");
  }
  canIncidentWrite() { return ["Administrator", "Purple Team Engineer", "SOC Analyst", "Detection Engineer"].includes(this.user()?.role_name || ""); }
  countInLab(id: string) {
    return this.assets().filter((a) => a.lab_id === id).length;
  }
  go(page: Page) {
    this.page.set(page);
    this.error.set("");
    if (page === "telemetry") this.loadTelemetry();
    if (page === "detections") this.loadDetections();
  }
  auth() {
    return {
      headers: new HttpHeaders({ Authorization: "Bearer " + this.token() }),
    };
  }
  explain(e: HttpErrorResponse) {
    const d = e.error?.detail;
    return typeof d === "string"
      ? d
      : Array.isArray(d)
        ? d.map((x: any) => x.msg).join("; ")
        : `Request failed (HTTP ${e.status}).`;
  }
  login() {
    this.error.set("");
    this.busy.set(true);
    this.http
      .post<{
        access_token: string;
        refresh_token: string;
      }>(API + "/auth/login", { email: this.email, password: this.password })
      .subscribe({
        next: (t) => {
          this.token.set(t.access_token);
          this.refreshToken.set(t.refresh_token);
          this.password = "";
          this.busy.set(false);
          this.http
            .get<User>(API + "/auth/me", this.auth())
            .subscribe({
              next: (u) => this.user.set(u),
              error: () => this.error.set("Cannot fetch account role"),
            });
          this.load();
        },
        error: (e) => {
          this.busy.set(false);
          this.error.set(this.explain(e));
        },
      });
  }
  load() {
    this.error.set("");
    this.http
      .get<Lab[]>(API + "/labs", this.auth())
      .subscribe({
        next: (v) => this.labs.set(v),
        error: (e) => this.error.set(this.explain(e)),
      });
    this.http
      .get<Asset[]>(API + "/assets?limit=200", this.auth())
      .subscribe({
        next: (v) => this.assets.set(v),
        error: (e) => this.error.set(this.explain(e)),
      });
    this.http
      .get<Summary>(API + "/inventory/summary", this.auth())
      .subscribe({
        next: (v) => this.summary.set(v),
        error: (e) => this.error.set(this.explain(e)),
      });
  }
  logout() {
    this.http
      .post(
        API + "/auth/logout",
        { refresh_token: this.refreshToken() },
        this.auth(),
      )
      .subscribe({ next: () => this.clear(), error: () => this.clear() });
  }
  clear() {
    this.token.set("");
    this.refreshToken.set("");
    this.user.set(null);
    this.labs.set([]);
    this.assets.set([]);
    this.summary.set({ labs: 0, assets: 0, monitored: 0, critical: 0 });
  }
  closeForms() {
    this.showLabForm.set(false);
    this.showAssetForm.set(false);
  }
  openLab(l?: Lab) {
    if (!this.canManage()) return;
    this.editingLabId = l?.id || "";
    this.labName = l?.name || "";
    this.labDescription = l?.description || "";
    this.showLabForm.set(true);
  }
  saveLab() {
    if (!this.canManage()) return;
    this.busy.set(true);
    const body = {
      name: this.labName.trim(),
      description: this.labDescription.trim() || null,
    };
    const req = this.editingLabId
      ? this.http.patch(API + "/labs/" + this.editingLabId, body, this.auth())
      : this.http.post(API + "/labs", body, this.auth());
    req.subscribe({
      next: () => {
        this.busy.set(false);
        this.closeForms();
        this.load();
      },
      error: (e) => {
        this.busy.set(false);
        this.error.set(this.explain(e));
        this.closeForms();
      },
    });
  }
  removeLab(l: Lab) {
    if (
      !this.canManage() ||
      !confirm(`Delete lab "${l.name}"? Assets must be removed first.`)
    )
      return;
    this.http
      .delete(API + "/labs/" + l.id, this.auth())
      .subscribe({
        next: () => this.load(),
        error: (e) => this.error.set(this.explain(e)),
      });
  }
  openLabInventory(id: string) {
    this.filterLab = id;
    this.go("inventory");
  }
  openAsset(a?: Asset) {
    if (!this.canEdit()) return;
    if (!a && !this.labs().length) {
      this.error.set("Create a lab first.");
      return;
    }
    this.editingAssetId = a?.id || "";
    this.assetForm = a
      ? {
          lab_id: a.lab_id,
          hostname: a.hostname,
          ip_address: a.ip_address || "",
          mac_address: a.mac_address || "",
          operating_system: a.operating_system || "",
          asset_type: a.asset_type,
          environment: a.environment,
          criticality: a.criticality,
          owner: a.owner || "",
          vm_name: a.vm_name || "",
          vmware_network: a.vmware_network || "",
          monitoring_enabled: a.monitoring_enabled,
        }
      : { ...blankAsset(), lab_id: this.filterLab || this.labs()[0].id };
    this.showAssetForm.set(true);
  }
  saveAsset() {
    if (!this.canEdit()) return;
    this.busy.set(true);
    const raw = this.assetForm;
    const body: any = {
      ...raw,
      hostname: raw.hostname.trim(),
      ip_address: raw.ip_address.trim() || null,
      mac_address: raw.mac_address.trim() || null,
      operating_system: raw.operating_system.trim() || null,
      owner: raw.owner.trim() || null,
      vm_name: raw.vm_name.trim() || null,
      vmware_network: raw.vmware_network.trim() || null,
    };
    if (this.editingAssetId) delete body.lab_id;
    const req = this.editingAssetId
      ? this.http.patch(
          API + "/assets/" + this.editingAssetId,
          body,
          this.auth(),
        )
      : this.http.post(API + "/assets", body, this.auth());
    req.subscribe({
      next: () => {
        this.busy.set(false);
        this.closeForms();
        this.load();
      },
      error: (e) => {
        this.busy.set(false);
        this.error.set(this.explain(e));
        this.closeForms();
      },
    });
  }
  removeAsset(a: Asset) {
    if (!this.canManage() || !confirm(`Delete asset "${a.hostname}"?`)) return;
    this.http
      .delete(API + "/assets/" + a.id, this.auth())
      .subscribe({
        next: () => this.load(),
        error: (e) => this.error.set(this.explain(e)),
      });
  }
  viewAsset(a: Asset) {
    this.selectedAsset.set(a);
  }
}
bootstrapApplication(App, { providers: [provideHttpClient()] }).catch(
  console.error,
);
