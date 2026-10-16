"""Pure evidence summarizer: no LLM, untrusted instructions or automatic actions."""

def compose(asset_name: str, observations: list[dict], correlation: dict | None = None) -> dict:
    evidence = []
    for item in observations[:25]:
        evidence.append({"kind": "anomaly_observation", "id": item["id"], "run_id": item["run_id"],
                         "bucket_start": item["bucket_start"], "event_count": item["event_count"],
                         "anomaly_score": item["anomaly_score"]})
    if correlation:
        evidence.append({"kind": "correlation_case", "id": correlation["id"],
                         "risk_score": correlation["risk_score"], "finding_count": correlation["finding_count"],
                         "indicator_count": correlation["indicator_count"]})
    return {"generator": "deterministic-evidence-v1", "asset": asset_name,
            "summary": f"Reviewed {len(observations[:25])} stored statistical outlier observations for {asset_name}." +
             (" An existing correlation case was included." if correlation else " No correlation case was supplied."),
            "evidence": evidence,
            "suggested_checks": ["Review source timestamps and verify clock synchronization.",
                                 "Compare unusual event volumes with expected lab activity.",
                                 "Inspect linked P4 findings and P8 matches, if available.",
                                 "Record an analyst determination before proposing any response."],
            "limitations": ["Statistical outliers are not proof of compromise.",
                            "This is a deterministic evidence draft, not an LLM assessment.",
                            "Unlinked events and causal attack paths were not evaluated."],
            "assessment": "undetermined"}
