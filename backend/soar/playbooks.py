"""P11 deliberately contains NO real response adapters or arbitrary commands."""
PLAYBOOKS = {
  'triage_checklist': {'name':'Analyst triage checklist','description':'Produce a human verification checklist'},
  'containment_plan': {'name':'Containment planning (advisory)','description':'Draft reversible containment considerations without making changes'},
  'evidence_preservation': {'name':'Evidence preservation plan','description':'Suggest evidence to collect without accessing endpoints'},
}
def simulate(key: str, justification: str) -> dict:
    if key not in PLAYBOOKS:
        raise ValueError('Unsupported playbook')
    checklist = {
       'triage_checklist':['Verify source timestamps and affected asset','Correlate relevant P4 findings','Record analyst disposition'],
       'containment_plan':['Confirm asset ownership and authorized maintenance window','Document proposed reversible isolation and rollback','Request separate authorization for any future real action'],
       'evidence_preservation':['Identify relevant event IDs and timestamps','Document collection ownership and chain of custody','Preserve existing records using approved organizational procedures'],
    }[key]
    return {'mode':'dry_run','playbook':key,'performed_actions':[], 'steps':checklist,
            'source_justification':justification, 'message':'Simulation only: no systems, firewall rules, or VMs were changed.'}
