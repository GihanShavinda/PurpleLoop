SEVERITIES = ('low', 'medium', 'high', 'critical')
STATUSES = ('open', 'investigating', 'contained', 'resolved', 'false_positive')

def validate_transition(current: str, target: str) -> bool:
    if current not in STATUSES or target not in STATUSES:
        return False
    if current == target:
        return True
    allowed = {
        'open': ('investigating', 'false_positive'),
        'investigating': ('contained', 'resolved', 'false_positive'),
        'contained': ('investigating', 'resolved'),
        'resolved': ('investigating',),
        'false_positive': ('investigating',)
    }
    return target in allowed[current]

def related_finding_ids(rows, asset_id, existing_ids, limit=25):
    """Bounded, deterministic matching: same asset, no already-linked findings."""
    ids = []
    known = set(existing_ids)
    for finding_id, candidate_asset in rows:
        if candidate_asset == asset_id and finding_id not in known:
            ids.append(finding_id)
            known.add(finding_id)
            if len(ids) >= limit:
                break
    return ids
