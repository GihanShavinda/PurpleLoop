import {Component, Input, OnChanges, SimpleChanges, OnDestroy, inject, signal} from '@angular/core';
import {HttpClient, HttpHeaders} from '@angular/common/http';
import {FormsModule} from '@angular/forms';
import {Subscription, finalize, timeout, forkJoin} from 'rxjs';

type Asset={id:string;name:string};
type Run={id:string;asset_id:string;event_count:number;bucket_count:number;anomaly_count:number;window_start:string;window_end:string;created_at:string;parameters:{model:string};status:string};
type Observation={id:string;bucket_start:string;anomaly_score:number;event_count:number;explanation:{principal_feature:string;observed:Record<string,number>;baseline_mean:Record<string,number>;warning:string}};
@Component({selector:'app-p15-anomaly',standalone:true,imports:[FormsModule],template:`
<section class="panel"><h3>P15 · Explainable Anomaly Detection</h3><small>Historical per-asset Isolation Forest · maximum 24h/5,000 events · one click · no polling or auto-response.</small>
<p style="color:#ffa9a9">{{error()}}</p>
<button (click)="refresh()" [disabled]="busy()">Refresh analysis</button></section>
<section class="panel"><h3>Analyze asset telemetry</h3>
<div class="p15fields"><select [(ngModel)]="assetId" [disabled]="busy()"><option value="">Select asset</option>@for(a of assets();track a.id){<option [value]="a.id">{{a.name}}</option>}</select>
<label>Lookback hours <input type="number" min="1" max="24" [(ngModel)]="hours"></label>
<label>Bucket minutes <select [(ngModel)]="bucket"><option [ngValue]="5">5</option><option [ngValue]="10">10</option><option [ngValue]="15">15</option><option [ngValue]="30">30</option><option [ngValue]="60">60</option></select></label>
<label>Contamination <select [(ngModel)]="contamination"><option [ngValue]="0.05">5%</option><option [ngValue]="0.08">8%</option><option [ngValue]="0.1">10%</option></select></label>
<button (click)="analyze()" [disabled]="busy() || !assetId">Run analysis</button></div>
<small>Requires at least 12 buckets and 30 events. A statistical outlier is not proof of an attack.</small></section>
<section class="panel"><h3>Analysis history</h3><table><thead><tr><th>Time</th><th>Asset</th><th>Events</th><th>Buckets</th><th>Outliers</th><th>Action</th></tr></thead><tbody>@for(r of runs();track r.id){<tr><td>{{r.created_at}}</td><td>{{assetName(r.asset_id)}}</td><td>{{r.event_count}}</td><td>{{r.bucket_count}}</td><td>{{r.anomaly_count}}</td><td><button (click)="inspect(r)" [disabled]="busy()">Inspect</button></td></tr>}@empty{<tr><td colspan="6">No analyses yet</td></tr>}</tbody></table></section>
@if(selected()){<section class="panel"><h3>Outliers · {{selected()!.id.slice(0,8)}}</h3><p>Events: {{selected()!.event_count}} · Outliers: {{selected()!.anomaly_count}} · Model: {{selected()!.parameters.model}}</p><table><thead><tr><th>Window start</th><th>Anomaly score</th><th>Events</th><th>Explanation</th></tr></thead><tbody>@for(o of observations();track o.id){<tr><td>{{o.bucket_start}}</td><td>{{o.anomaly_score}}</td><td>{{o.event_count}}</td><td>{{o.explanation.principal_feature}} · {{o.explanation.warning}}</td></tr>}@empty{<tr><td colspan="4">No outliers in this run</td></tr>}</tbody></table></section>}
`,styles:[`:host{display:block}.panel{background:#101a2d;border:1px solid #2e4161;border-radius:10px;padding:16px;margin-bottom:12px;color:#eaf2ff}.panel h3{margin:0 0 10px;font-size:15px}.panel small{display:block;color:#a4badb;margin-bottom:12px}.p15fields{display:flex;gap:10px;flex-wrap:wrap;align-items:center}button,select,input{background:#111b30;color:white;border:1px solid #395073;border-radius:7px;padding:9px}button{background:#6b48c7;cursor:pointer}button:disabled{opacity:.5;cursor:default}label{display:flex;align-items:center;gap:5px}input{max-width:80px}table{width:100%;border-collapse:collapse;font-size:12px}td,th{padding:8px;border-bottom:1px solid #2e4161;text-align:left}`]})
export class P15AnomalyComponent implements OnChanges,OnDestroy {
 @Input() token=''; @Input() canWrite=false;
 private http=inject(HttpClient); private sub?:Subscription;
 assets=signal<Asset[]>([]);runs=signal<Run[]>([]);selected=signal<Run|null>(null);observations=signal<Observation[]>([]);error=signal('');busy=signal(false);
 assetId='';hours=6;bucket=15;contamination=.08;
 private headers(){return {headers:new HttpHeaders({Authorization:'Bearer '+this.token})};}
 ngOnChanges(changes:SimpleChanges){if(changes['token'] && this.token){this.refresh();}}
 ngOnDestroy(){this.sub?.unsubscribe();}
 assetName(id:string){return this.assets().find(a=>a.id===id)?.name||id.slice(0,8);}
 refresh(){if(this.busy() || !this.token)return;this.busy.set(true);this.error.set('');
 this.sub=forkJoin({assets:this.http.get<Asset[]>('http://127.0.0.1:8000/anomaly/assets',this.headers()),runs:this.http.get<Run[]>('http://127.0.0.1:8000/anomaly/runs',this.headers())}).pipe(timeout(12000),finalize(()=>this.busy.set(false))).subscribe({next:d=>{this.assets.set(d.assets);this.runs.set(d.runs);},error:e=>this.error.set(e.error?.detail||e.message||'Unable to load')});}
 analyze(){if(this.busy()||!this.canWrite||!this.assetId)return;this.busy.set(true);this.error.set('');
 this.sub=this.http.post<Run>('http://127.0.0.1:8000/anomaly/run',{asset_id:this.assetId,lookback_hours:this.hours,bucket_minutes:this.bucket,contamination:this.contamination},this.headers()).pipe(timeout(25000),finalize(()=>this.busy.set(false))).subscribe({next:r=>{this.runs.update(x=>[r,...x]);this.inspect(r);},error:e=>this.error.set(e.error?.detail||e.message||'Analysis failed')});}
 inspect(r:Run){this.selected.set(r);this.observations.set([]);this.sub=this.http.get<Observation[]>('http://127.0.0.1:8000/anomaly/runs/'+r.id+'/observations',this.headers()).pipe(timeout(12000)).subscribe({next:x=>this.observations.set(x),error:e=>this.error.set(e.error?.detail||e.message||'Cannot load observations')});}
}
