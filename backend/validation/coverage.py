"""Pure validation logic: a recorded matching finding is evidence, not a simulated success."""
import re
ATTACK_ID = re.compile(r'^T[0-9]{4}(?:\.[0-9]{3})?$')

def valid_technique(value: str) -> bool:
    return bool(ATTACK_ID.fullmatch(value))

def outcome(finding_ids: list[str], complete: bool = True) -> str:
    if not complete:
        return 'inconclusive'
    return 'passed' if finding_ids else 'failed'

def coverage_stats(scenarios, latest_runs):
    """Coverage is observed passing validation by scenario, not global ATT&CK coverage."""
    eligible=[s for s in scenarios if s.enabled]
    latest={r.scenario_id:r for r in latest_runs}
    tested=[s for s in eligible if s.id in latest and latest[s.id].status in ('passed','failed')]
    passed=[s for s in tested if latest[s.id].status=='passed']
    return {'enabled_scenarios':len(eligible),'tested_scenarios':len(tested),
            'passed_scenarios':len(passed),'coverage_percent':round(100*len(passed)/len(eligible),1) if eligible else 0.0}
