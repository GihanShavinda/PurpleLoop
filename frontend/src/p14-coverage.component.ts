import {Component,Input,OnChanges,OnDestroy,SimpleChanges,inject,signal} from '@angular/core';
import {HttpClient,HttpHeaders} from '@angular/common/http';
import {FormsModule} from '@angular/forms';
import {Subscription,timeout,finalize,forkJoin} from 'rxjs';
type Run={id:string;asset_id:string;marker:string;event_id:string;started_at:string};
type Rule={id:string;name:string;enabled:boolean};
type Assessment={id:string;simulation_run_id:string;rule_id:string;event_id:string;finding_id:string|null;outcome:string;explanation:string;assessed_at:string};
type Summary={total:number;detected:number;not_detected:number;inconclusive:number;observed_detection_rate_percent:number|null;scope:string};
@Component({selector:'app-p14-coverage',standalone:true,imports:[FormsModule],styles:[`
.panel{border:1px solid #293c5a;border-radius:12px;background:#101a2d;color:#edf2ff;padding:18px;margin:12px 0}.row{display:flex;gap:10px;flex-wrap:wrap;align-items:center}.field{min-width:210px;flex:1;background:#081428;color:white;padding:10px;border:1px solid #384a68;border-radius:7px}.btn{background:#7154d5;border:0;border-radius:7px;padding:10px;color:white;cursor:pointer}.btn:disabled{opacity:.5}.muted{color:#a7b9dc;font-size:12px}.error{color:#ff9b9b}.good{color:#8ce6b9}table{width:100%;border-collapse:collapse;font-size:12px}td,th{text-align:left;padding:10px;border-bottom:1px solid #273850;overflow-wrap:anywhere}.scroll{overflow-x:auto}
`],template:`
<section class="panel"><h2>P14 · Detection Coverage Validation</h2><p class="muted">Explicit P13→P4 evidence comparison, one-time evaluation only. No polling, no attack execution, no claims of ATT&CK-wide coverage.</p>
@if(error()){<p class="error">{{error()}}</p>}@if(info()){<p class="good">{{info()}}</p>}
<button class="btn" [disabled]="loading()||busy()" (click)="refresh()">{{loading()?'Loading...':'Refresh evidence'}}</button></section>
<section class="panel"><h3>Assess a verified P13 run against a P4 rule</h3><div class="row">
<select class="field" [(ngModel)]="runId"><option value="">Select verified lab run</option>@for(r of runs();track r.id){<option [value]="r.id">{{r.marker}} · {{r.started_at}}</option>}</select>
<select class="field" [(ngModel)]="ruleId"><option value="">Select detection rule</option>@for(r of rules();track r.id){<option [value]="r.id">{{r.name}} {{r.enabled?'':'(disabled)'}}</option>}</select>
<button class="btn" [disabled]="!canWrite||busy()||loading()||!runId||!ruleId" (click)="assess()">{{busy()?'Assessing...':'Assess exact evidence'}}</button></div>
<p class="muted">Run P4 evaluation first if a matching P4 finding has not yet been created. An observed journal event alone does not mean a detection fired.</p></section>
<section class="panel"><h3>Observed validation outcomes</h3>@if(summary();as s){<p>Assessed: {{s.total}} · Detected: {{s.detected}} · Not detected: {{s.not_detected}} · Inconclusive: {{s.inconclusive}}</p><p class="good">Observed detection rate: {{s.observed_detection_rate_percent===null?'N/A':s.observed_detection_rate_percent+'%'}}</p><p class="muted">{{s.scope}}</p>}@else{<p class="muted">No summary loaded.</p>}</section>
<section class="panel scroll"><h3>Evidence-linked assessment history</h3><table><thead><tr><th>P13 RUN</th><th>RULE</th><th>OUTCOME</th><th>EVIDENCE EVENT</th><th>P4 FINDING</th><th>EXPLANATION</th></tr></thead><tbody>
@for(a of assessments();track a.id){<tr><td>{{a.simulation_run_id.slice(0,8)}}</td><td>{{ruleName(a.rule_id)}}</td><td>{{a.outcome}}</td><td>{{a.event_id}}</td><td>{{a.finding_id||'None'}}</td><td>{{a.explanation}}</td></tr>}@empty{<tr><td colspan="6">No assessments yet.</td></tr>}</tbody></table></section>
`})
export class P14CoverageComponent implements OnChanges,OnDestroy{
 @Input() token='';@Input() canWrite=false;private http=inject(HttpClient);private base='http://127.0.0.1:8000';private lastToken='';private subscriptions:Subscription[]=[];
 loading=signal(false);busy=signal(false);error=signal('');info=signal('');runs=signal<Run[]>([]);rules=signal<Rule[]>([]);assessments=signal<Assessment[]>([]);summary=signal<Summary|null>(null);runId='';ruleId='';
 ngOnChanges(changes:SimpleChanges){if(changes['token']&&this.token&&this.token!==this.lastToken){this.lastToken=this.token;this.refresh();}}
 ngOnDestroy(){for(const s of this.subscriptions)s.unsubscribe();}
 options(){return {headers:new HttpHeaders({Authorization:'Bearer '+this.token})};}
 failure(e:any){this.error.set(typeof e?.error?.detail==='string'?e.error.detail:`Request failed (HTTP ${e?.status??0})`);}
 ruleName(id:string){return this.rules().find(x=>x.id===id)?.name||id;}
 refresh(){if(this.loading()||this.busy()||!this.token)return;this.loading.set(true);this.error.set('');const options=this.options();const s=forkJoin({runs:this.http.get<Run[]>(this.base+'/coverage/runs',options),rules:this.http.get<Rule[]>(this.base+'/coverage/rules',options),assessments:this.http.get<Assessment[]>(this.base+'/coverage/assessments',options),summary:this.http.get<Summary>(this.base+'/coverage/summary',options)}).pipe(timeout(12000),finalize(()=>this.loading.set(false))).subscribe({next:v=>{this.runs.set(v.runs);this.rules.set(v.rules);this.assessments.set(v.assessments);this.summary.set(v.summary);},error:e=>this.failure(e)});this.subscriptions.push(s);}
 assess(){if(!this.canWrite||this.busy()||!this.runId||!this.ruleId)return;this.busy.set(true);this.error.set('');const s=this.http.post<Assessment>(this.base+'/coverage/assess',{simulation_run_id:this.runId,rule_id:this.ruleId},this.options()).pipe(timeout(12000),finalize(()=>{this.busy.set(false);this.refresh();})).subscribe({next:a=>this.info.set(`Assessment ${a.outcome}: ${a.explanation}`),error:e=>this.failure(e)});this.subscriptions.push(s);}
}
