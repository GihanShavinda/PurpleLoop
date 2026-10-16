"""Pure P10 evidence-based SOC summaries. Not an LLM or an attack verdict."""
from collections import Counter

MAX_EVIDENCE = 50

def build_report(case, evidence: list[dict]) -> dict:
    """Never invent an ATT&CK mapping, root cause, attacker, or remediation proof."""
    bounded = evidence[:MAX_EVIDENCE]
    counts = dict(Counter(str(e['kind']) for e in bounded))
    timeline = [
        {'event_id': str(e['event_id']), 'timestamp': str(e['timestamp']),
         'kind': str(e['kind']), 'event_type': str(e.get('event_type') or ''),
         'description': str(e.get('message') or '')[:240]}
        for e in bounded
    ]
    score = int(case['risk_score'])
    summary = (f"Asset {case['asset_label']} has {len(timeline)} linked evidence records "
               f"in a correlation window; correlation risk score {score}/100. "
               "This is an evidence association, not proof of compromise.")
    caveats = ['Correlation does not demonstrate causality or confirm an attack chain.',
               'Risk is a heuristic from P9; not a calibrated probability.',
               'Only attached correlation evidence was reviewed; absence of other events is not evidence of safety.']
    if not timeline: caveats.append('No attached evidence: manual investigation required.')
    return {
        'title': 'Evidence-grounded SOC investigation draft',
        'summary': summary, 'risk_score': score, 'evidence_count': len(timeline),
        'kind_counts': counts, 'timeline': timeline,
        'observed': [f"{kind}: {count} linked record(s)" for kind,count in sorted(counts.items())],
        'hypotheses': ['Review whether the observed events have a benign operational explanation.'] if timeline else [],
        'recommended_checks': ['Verify the source event and its host context.',
                                'Review neighboring events and related P6 incidents.',
                                'Confirm whether any detection rule represents a validated threat behavior.'],
        'attack_techniques': [], 'limitations': caveats,
        'generator': 'deterministic-evidence-v1', 'requires_human_review': True,
    }
