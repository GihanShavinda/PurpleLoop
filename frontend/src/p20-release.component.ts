import { Component, Input, OnChanges, OnDestroy, SimpleChanges, inject, signal } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Subscription, timeout, finalize } from 'rxjs';

type Metric = number | null;
type Snapshot = {schema_version:number;generated_at:string;status:string;metrics:Record<string,Metric>;readiness:{id:string;state:string;detail:string}[];limitations:string[]};
@Component({selector:'app-p20-release', standalone:true, template:`
<section class="panel"><h3>P20 · Final Evaluation & Release Evidence</h3>
<small>Administrator-only, database-derived snapshot. No automated scans, no polling, no VMware changes. This is not a security certification.</small>
<p class="error" role="alert">{{error()}}</p>
<button (click)="refresh()" [disabled]="busy()">{{busy()?'Loading…':'Refresh final evidence'}}</button>
<button (click)="exportEvidence()" [disabled]="!snapshot()">Copy sanitized JSON evidence</button></section>
@if(snapshot();as s){
<section class="panel"><h3>Measured indicators</h3><small>Snapshot time {{s.generated_at}}</small>
<table><thead><tr><th>Metric</th><th>Observed value</th></tr></thead><tbody>
@for(metric of entries(s.metrics);track metric[0]){<tr><td>{{metric[0].replaceAll('_',' ')}}</td><td>{{metric[1]===null?'Not measured':metric[1]}}</td></tr>}
</tbody></table></section>
<section class="panel"><h3>Evidence availability</h3><table><thead><tr><th>Check</th><th>State</th><th>Evidence</th></tr></thead><tbody>
@for(c of s.readiness;track c.id){<tr><td>{{c.id}}</td><td>{{c.state}}</td><td>{{c.detail}}</td></tr>}
</tbody></table></section>
<section class="panel"><h3>Evaluation limitations</h3><ul>@for(l of s.limitations;track l){<li>{{l}}</li>}</ul></section>
}
`,styles:[`:host{display:block;color:#edf3ff}.panel{background:#101a2d;border:1px solid #2b4161;border-radius:10px;padding:16px;margin-bottom:12px}h3{margin:0 0 10px;font-size:15px}small{color:#a7b9d6}.error{color:#ffa0a0}button{background:#7351d4;color:white;border:0;border-radius:7px;padding:9px 12px;cursor:pointer;margin-right:10px;margin-top:12px}button:disabled{opacity:.5}table{width:100%;border-collapse:collapse;margin-top:12px;font-size:12px}td,th{text-align:left;padding:10px;border-bottom:1px solid #2a3e59;overflow-wrap:anywhere}li{margin:8px 0}`]})
export class P20ReleaseComponent implements OnChanges,OnDestroy {
 @Input() token='';private http=inject(HttpClient);private request?:Subscription;
 busy=signal(false);error=signal('');snapshot=signal<Snapshot|null>(null);
 entries(value:Record<string,Metric>):[string,Metric][]{return Object.entries(value);}
 ngOnChanges(changes:SimpleChanges){if(changes['token'] && this.token)this.refresh();}
 ngOnDestroy(){this.request?.unsubscribe();}
 refresh(){if(!this.token||this.busy())return;this.busy.set(true);this.error.set('');
  this.request=this.http.get<Snapshot>('http://127.0.0.1:8000/release/snapshot',{headers:new HttpHeaders({Authorization:'Bearer '+this.token})})
   .pipe(timeout(12000),finalize(()=>this.busy.set(false))).subscribe({next:s=>this.snapshot.set(s),error:e=>this.error.set(e.status===403?'Administrator role required':e.error?.detail||e.message||'Request failed')});}
 exportEvidence(){const s=this.snapshot();if(!s)return;
  const clean=JSON.stringify(s,null,2);
  // Avoid localStorage and data from other APIs; clipboard export keeps the component browser-neutral.
  if(navigator.clipboard?.writeText){navigator.clipboard.writeText(clean).then(()=>this.error.set('JSON evidence copied. Save it as a local file outside the public repository.')).catch(()=>this.error.set('Clipboard unavailable; use the API endpoint to export JSON.'));}
  else this.error.set('Clipboard unavailable; use the API endpoint to export JSON.');
 }
}
