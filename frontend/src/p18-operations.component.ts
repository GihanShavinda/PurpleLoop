import {Component, Input, OnChanges, OnDestroy, SimpleChanges, inject, signal} from '@angular/core';
import {HttpClient, HttpHeaders} from '@angular/common/http';
import {Subscription, timeout, finalize} from 'rxjs';
type AssetState = {id:string;hostname:string;criticality:string;vmware_network:string|null;last_receipt:string|null;receiving:boolean;manual_ready:boolean|null;readiness_checked_at:string|null};
type Overview = {generated_at:string;window_hours:number;assets:number;sources_enabled:number;sources_recent:number;events_24h:number;findings_24h:number;open_incidents:number;correlations_24h:number;coverage:{detected:number;not_detected:number;inconclusive:number;rate_percent:number|null};anomaly_runs_24h:number;outliers_24h:number;investigations:Record<string,number>;lab_assets:AssetState[];limitations:string[]};
@Component({selector:'app-p18-operations',standalone:true,template:`
<section class="panel"><h3>P18 · Purple Team Operations Center</h3><small>Read-only operational snapshot · bounded SQL aggregation · no background polling or response execution.</small><p class="error">{{error()}}</p><button (click)="refresh()" [disabled]="busy()">{{busy()?'Loading…':'Refresh operational metrics'}}</button></section>
@if(data();as d){
<section class="panel"><h3>Operational metrics <span class="sub">· past {{d.window_hours}} hours unless stated otherwise</span></h3><div class="metrics">
<div class="tile"><label>Registered assets</label><strong>{{d.assets}}</strong></div>
<div class="tile"><label>Enabled collectors / recently seen</label><strong>{{d.sources_recent}} / {{d.sources_enabled}}</strong></div>
<div class="tile"><label>Ingested events · 24h</label><strong>{{d.events_24h}}</strong></div>
<div class="tile"><label>Detection findings · 24h</label><strong>{{d.findings_24h}}</strong></div>
<div class="tile"><label>Open / investigating incidents</label><strong>{{d.open_incidents}}</strong></div>
<div class="tile"><label>Correlation cases · 24h</label><strong>{{d.correlations_24h}}</strong></div>
<div class="tile"><label>ML analyses / outliers · 24h</label><strong>{{d.anomaly_runs_24h}} / {{d.outliers_24h}}</strong></div>
<div class="tile"><label>Observed P14 detection rate</label><strong>{{d.coverage.rate_percent===null?'N/A':d.coverage.rate_percent+'%'}}</strong><small>{{d.coverage.detected}} detected · {{d.coverage.not_detected}} not detected</small></div>
</div></section>
<section class="panel"><h3>P16 investigation reviews</h3><div class="chips">@for(k of keys(d.investigations);track k){<span>{{k}}: {{d.investigations[k]}}</span>}@empty{<span>No investigation drafts recorded</span>}</div></section>
<section class="panel"><h3>Lab readiness and telemetry receipts</h3><div class="table-wrap"><table><thead><tr><th>Asset</th><th>Criticality</th><th>VMnet</th><th>Event within 10 min</th><th>Last receipt</th><th>Operator readiness</th></tr></thead><tbody>@for(a of d.lab_assets;track a.id){<tr><td>{{a.hostname}}</td><td>{{a.criticality}}</td><td>{{a.vmware_network||'—'}}</td><td>{{a.receiving?'Yes':'No'}}</td><td>{{a.last_receipt||'Never'}}</td><td>{{a.manual_ready===null?'Not assessed':a.manual_ready?'Ready for manual validation':'Review required'}}</td></tr>}@empty{<tr><td colspan="6">No registered assets.</td></tr>}</tbody></table></div></section>
<section class="panel"><h3>Measurement limitations</h3><ul>@for(note of d.limitations;track note){<li>{{note}}</li>}</ul><small>Snapshot generated {{d.generated_at}}. Refresh is always manual.</small></section>
}
`,styles:[`:host{display:block;color:#e7edff}.panel{background:#101a2d;border:1px solid #2b4161;border-radius:10px;padding:16px;margin:0 0 12px}.panel h3{margin:0 0 12px;font-size:15px}.panel small,.sub{font-size:11px;color:#9eb5d9}.error{color:#ff9b9b}.metrics{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px}.tile{padding:14px;border:1px solid #34496c;border-radius:9px;background:#152039}.tile label{display:block;font-size:11px;color:#a8c2ed}.tile strong{display:block;font-size:22px;margin:9px 0}.tile small{display:block}.chips{display:flex;gap:10px;flex-wrap:wrap}.chips span{padding:10px;border:1px solid #354b6d;border-radius:8px}button{background:#7351d4;color:white;padding:10px;border:0;border-radius:7px;cursor:pointer}button:disabled{opacity:.5}.table-wrap{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:12px}td,th{padding:10px;text-align:left;border-bottom:1px solid #2a3e59;white-space:nowrap}li{margin:7px 0}`]})
export class P18OperationsComponent implements OnChanges,OnDestroy{
 @Input() token=''; private http=inject(HttpClient);private request?:Subscription;
 busy=signal(false);error=signal('');data=signal<Overview|null>(null);
 ngOnChanges(changes:SimpleChanges){if(changes['token']&&this.token)this.refresh();}
 ngOnDestroy(){this.request?.unsubscribe();}
 keys(value:Record<string,number>){return Object.keys(value);}
 refresh(){if(this.busy()||!this.token)return;this.busy.set(true);this.error.set('');this.request=this.http.get<Overview>('http://127.0.0.1:8000/operations/overview',{headers:new HttpHeaders({Authorization:'Bearer '+this.token})}).pipe(timeout(12000),finalize(()=>this.busy.set(false))).subscribe({next:r=>this.data.set(r),error:e=>this.error.set(e.error?.detail||e.message||'Dashboard could not load')});}
}
