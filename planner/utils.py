from datetime import timedelta
from dateutil.rrule import rrulestr


def expand_events_for_range(events, start_range, end_range):
    """Expand a queryset/list of Event objects into concrete occurrences within range.

    Returns a list of dicts: {
        'event': Event instance,
        'start_time': datetime,
        'end_time': datetime,
        'title': str,
        'description': str,
        'category': Category or None,
        'is_cancelled': bool,
        'original_start': datetime or None,
    }
    """
    occurrences = []
    for ev in events:
        # Non-recurring events: include if in range
        if not ev.rrule:
            if ev.start_time <= end_range and ev.end_time >= start_range:
                occurrences.append({
                    'event': ev,
                    'start_time': ev.start_time,
                    'end_time': ev.end_time,
                    'title': ev.title,
                    'description': ev.description,
                    'category': ev.category,
                    'is_cancelled': False,
                    'original_start': None,
                })
            continue

        # Recurring event: build rrule and iterate
        try:
            rule = rrulestr(ev.rrule, dtstart=ev.start_time)
        except Exception:
            continue

        # Determine occurrences within window
        # Add a small buffer to include events that start before but end after start_range
        occs = rule.between(start_range - timedelta(days=1), end_range + timedelta(days=1), inc=True)
        duration = ev.end_time - ev.start_time

        # Load exceptions for this event into a dict by original_start
        exc_map = {ex.original_start: ex for ex in getattr(ev, 'exceptions', []).all()} if hasattr(ev, 'exceptions') else {}

        for occ in occs:
            # Apply recurrence_end if set
            if ev.recurrence_end and occ > ev.recurrence_end:
                continue
            start_dt = occ
            end_dt = occ + duration

            # Skip if outside desired window
            if end_dt < start_range or start_dt > end_range:
                continue

            ex = exc_map.get(start_dt)
            if ex and ex.is_cancelled:
                # skip cancelled occurrence
                continue

            if ex:
                # apply overrides
                occurrence = {
                    'event': ev,
                    'start_time': ex.override_start_time or start_dt,
                    'end_time': ex.override_end_time or end_dt,
                    'title': ex.override_title or ev.title,
                    'description': ex.override_description or ev.description,
                    'category': ev.category,
                    'is_cancelled': False,
                    'original_start': start_dt,
                }
            else:
                occurrence = {
                    'event': ev,
                    'start_time': start_dt,
                    'end_time': end_dt,
                    'title': ev.title,
                    'description': ev.description,
                    'category': ev.category,
                    'is_cancelled': False,
                    'original_start': start_dt,
                }
            occurrences.append(occurrence)

    # Sort by start_time
    occurrences.sort(key=lambda o: o['start_time'])
    return occurrences
