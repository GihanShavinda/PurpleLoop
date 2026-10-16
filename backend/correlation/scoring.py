"""Pure, explainable scoring; not a prediction or confirmed attack chain."""
SEVERITY={'info':0,'low':5,'medium':12,'high':20,'critical':30}
CRITICALITY={'low':0,'medium':5,'high':10,'critical':15}
def score(findings, confidences, criticality):
    """Return bounded score and transparent factors, with deduplicated inputs."""
    levels=[SEVERITY.get(str(s).lower(),0) for s in findings]
    unique_conf=[max(0,min(100,int(x))) for x in confidences]
    finding_points=min(50,sum(sorted(levels,reverse=True)[:4]))
    intel_points=min(25,sum(sorted((round(x/10) for x in unique_conf),reverse=True)[:3]))
    asset_points=CRITICALITY.get(str(criticality).lower(),0)
    risk=min(100,finding_points+intel_points+asset_points)
    return risk,{'finding_points':finding_points,'intelligence_points':intel_points,'asset_points':asset_points,
                 'note':'Observed same-asset evidence only; chronology does not establish causality'}
