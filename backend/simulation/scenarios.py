"""Explicit allowlist of harmless scenarios. No command execution by backend."""
SCENARIOS = {
    'ubuntu_journal_marker': {
        'label': 'Ubuntu Journald marker verification',
        'supported_os': 'linux',
        'description': 'Operator manually emits a synthetic systemd journal event on an authorized Ubuntu lab VM.',
        'event_type': 'linux_journal',
    },
}

def render_command(scenario_key: str, marker: str) -> str:
    if scenario_key not in SCENARIOS:
        raise ValueError('Unsupported lab scenario')
    if not marker.startswith('PF13-') or not all(c.isalnum() or c=='-' for c in marker):
        raise ValueError('Invalid marker')
    return f'logger -t purpleforge-p13 "{marker}"'
