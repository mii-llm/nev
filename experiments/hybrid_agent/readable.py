"""Render recorded agent events, without inventing internal reasoning."""
import json


def render(record):
    lines = ['Simulation: local mock tools', f"User ({record['language']}): {record['message']}"]
    if record.get('ranking'):
        lines.append('Nev tool order: ' + ' > '.join(record['ranking']['names']))
    for event in record['trace']:
        lines.append(f"\nNesso turn {event['turn'] + 1}:")
        if event['parse_error']:
            lines.extend([event['assistant'], 'Parser rejected: ' + event['parse_error']])
        elif event['calls']:
            for call in event['calls']:
                lines.append('  Requested: ' + json.dumps(call, ensure_ascii=False))
            for observation in event['observations']:
                lines.append('  Result for ' + observation['call']['name'] + ': ' +
                             json.dumps(observation['result'], ensure_ascii=False))
        else:
            lines.append(event['assistant'])
    if record.get('policy_events'):
        lines.append('\nController decisions: ' + json.dumps(record['policy_events'], ensure_ascii=False))
    if record.get('answer_source', 'generator') != 'generator':
        lines.extend(['\nAnswer source: ' + record['answer_source'], record['final']])
    if record.get('blocked_reason'):
        lines.append('Deferred: ' + record['blocked_reason'])
    if record['errors']:
        lines.append('\nController errors: ' + ', '.join(record['errors']))
    lines.append(f"\nElapsed (excluding model load): {record['total_ms'] / 1000:.2f} s")
    return '\n'.join(lines)
