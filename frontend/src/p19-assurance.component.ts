import { Component, Input, OnChanges, OnDestroy, SimpleChanges, inject, signal } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Subscription, timeout, finalize } from 'rxjs';
type Check={id:string;passed:boolean;reason:string};
type Posture={generated_at:string;checks:Check[];summary:{passed:number;total:number;attention_required:number};limitations:string[]};
@Component({selector:'app-p19-assurance',standalone:true,template:`
<section class="panel"><h3>P19 · Security Assurance</h3><small>Administrator-only, configuration-only posture review. No active scanning, no polling, no VM actions.</small>
<p class="error" role="alert">{{error()}}</p><button (click)="refresh()" [disabled]="busy()">{{busy()?'Checking…':'Refresh security posture'}}</button></section>
@if(data();as d){
<section class="panel"><h3>Posture snapshot</h3><p>{{d.summary.passed}} of {{d.summary.total}} checks passed · {{d.summary.attention_required}} need review</p>
<table><thead><tr><th>Control</th><th>Status</th><th>Meaning</th></tr></thead><tbody>
@for(c of d.checks;track c.id){<tr><td>{{c.id}}</td><td>{{c.passed?'Pass':'Review'}}</td><td>{{c.reason}}</td></tr>}
</tbody></table><small>Generated: {{d.generated_at}}</small></section>
<section class="panel"><h3>Manual verification still required</h3><ul>@for(x of d.limitations;track x){<li>{{x}}</li>}</ul></section>}
`,styles:[`:host{display:block;color:#ecf1ff}.panel{background:#101a2d;border:1px solid #2b4161;border-radius:10px;padding:16px;margin-bottom:12px}h3{margin:0 0 9px;font-size:15px}small{color:#a8bbda}.error{color:#ff9999}button{background:#7351d4;color:white;border:0;border-radius:7px;padding:10px;cursor:pointer}button:disabled{opacity:.5}table{width:100%;border-collapse:collapse;margin:14px 0;font-size:12px}td,th{text-align:left;padding:10px;border-bottom:1px solid #2a3e59}li{margin:8px 0}`]})
export class P19AssuranceComponent implements OnChanges,OnDestroy{
 @Input() token='';private http=inject(HttpClient);private request?:Subscription;
 busy=signal(false);error=signal('');data=signal<Posture|null>(null);
 ngOnChanges(changes:SimpleChanges){if(changes['token'] && this.token)this.refresh();}
 ngOnDestroy(){this.request?.unsubscribe();}
 refresh(){if(!this.token||this.busy())return;this.busy.set(true);this.error.set('');
  this.request=this.http.get<Posture>('http://127.0.0.1:8000/assurance/posture', {headers:new HttpHeaders({Authorization:'Bearer '+this.token})})
    .pipe(timeout(12000),finalize(()=>this.busy.set(false))).subscribe({next:r=>this.data.set(r),error:e=>this.error.set(e.status===403?'Administrator role required':e.error?.detail||e.message||'Unable to load posture')});}
}
