"""Application policy for explicitly single-read requests, not an intent detector.

The caller must establish that this endpoint accepts exactly one supported
read operation. Validation and agreement with Nev do not prove user intent.
"""
import re


def select_call(calls, allowed_names, message, ranking, validate):
    events, valid = [], []
    for call in calls:
        error = validate(call, allowed_names, message)
        if error:
            events.append({'action': 'reject', 'call': call, 'reason': error})
        elif call in valid:
            events.append({'action': 'deduplicate', 'call': call, 'reason': 'duplicate_call'})
        else:
            valid.append(call)
    if len(valid) != 1:
        return None, events, 'need_exactly_one_valid_call'
    call = valid[0]
    if not ranking or call['name'] != ranking['names'][0]:
        return None, events, 'nev_generator_disagreement'
    # Multiple explicit entities need clarification even if the generator emits
    # only one call. This is intentionally narrower than conversation grounding.
    refs = set(re.findall(r'(?<![A-Za-z0-9-])(?:ORD-\d{4}|[A-Z]{2}-\d|2026-(?:0[1-9]|1[0-2]))(?![A-Za-z0-9-])', message))
    if len(refs) != 1:
        return None, events, 'need_one_explicit_reference'
    return call, events, None


def render_result(name, result, language):
    """Use returned fields, never gold labels, invented values or model prose."""
    it = language == 'it'
    if name == 'get_order_status':
        status = {'in_transit': 'in transito' if it else 'in transit'}.get(result['status'], result['status'])
        return (f"Ordine {result['order_id']}: {status}. Riferimento di tracciamento: {result['tracking_reference']}." if it else
                f"Order {result['order_id']}: {status}. Tracking reference: {result['tracking_reference']}.")
    if name == 'get_invoice':
        return (f"La fattura dell’ordine {result['order_id']} è {result['filename']}." if it else
                f"The invoice for order {result['order_id']} is {result['filename']}.")
    if name == 'search_help_center':
        return (f"Il riferimento della guida del prodotto {result['product']} è {result['guide_reference']}." if it else
                f"The guide reference for product {result['product']} is {result['guide_reference']}.")
    if name == 'list_transactions':
        def money(value):
            text = f'{value:.2f}'
            return text.replace('.', ',') if it else text
        payments = ', '.join(money(value) + ' ' + result['currency'] for value in result['payments'])
        total = money(result['total']) + ' ' + result['currency']
        return (f"Pagamenti di {result['month']}: {payments}. Totale: {total}." if it else
                f"Payments for {result['month']}: {payments}. Total: {total}.")
    raise ValueError('No renderer for this tool')
