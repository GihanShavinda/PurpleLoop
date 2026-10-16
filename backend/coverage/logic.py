"""Pure, conservative detection assessment rules. No attack execution."""

def result_for(verified: bool, has_finding: bool) -> tuple[str,str]:
    if not verified:
        return ('inconclusive', 'P13 run has no verified telemetry evidence')
    if has_finding:
        return ('detected', 'P4 finding exists for the exact P13 evidence event and selected rule')
    return ('not_detected', 'P13 telemetry verified, but no P4 finding exists for that event/rule pair')

def summarize(outcomes: list[str]) -> dict:
    detected=sum(x=='detected' for x in outcomes)
    missed=sum(x=='not_detected' for x in outcomes)
    eligible=detected+missed
    return {'total':len(outcomes),'detected':detected,'not_detected':missed,
            'inconclusive':len(outcomes)-eligible,
            'observed_detection_rate_percent':round(detected*100/eligible,1) if eligible else None}
