#!/usr/bin/env python3
# Renders the waybar clock tooltip: a calendar box with appointment markers and a "denne uge" meetings box

import csv
import datetime
import json
import re
import sys

text      = sys.argv[1]
calendar  = sys.argv[2]
tsv_file  = sys.argv[3]
cal_month = int(sys.argv[4])
cal_year  = int(sys.argv[5])

now        = datetime.datetime.now()
today_date = now.date()
today      = today_date.day
viewing_current_month = (cal_month == today_date.month and cal_year == today_date.year)

danish_days   = ['mandag', 'tirsdag', 'onsdag', 'torsdag', 'fredag', 'lørdag', 'søndag']
danish_months = ['januar', 'februar', 'marts', 'april', 'maj', 'juni',
                 'juli', 'august', 'september', 'oktober', 'november', 'december']


def date_label(d):
    delta = (d - today_date).days
    if delta == 0:       return 'I dag'
    if delta == 1:       return 'I morgen'
    if 1 < delta <= 6:   return danish_days[d.weekday()].capitalize()
    return f'{d.day}. {danish_months[d.month - 1]}'


def strip_markup(s):
    return re.sub(r'<[^>]+>', '', s)


def make_box(lines):
    """Wraps a list of (optionally Pango-marked-up) strings in a box."""
    width = max((len(strip_markup(l)) for l in lines), default=0)
    h = '─' * (width + 2)
    rows = ['┌' + h + '┐']
    for line in lines:
        pad = ' ' * (width - len(strip_markup(line)))
        rows.append('│ ' + line + pad + ' │')
    rows.append('└' + h + '┘')
    return '<tt>' + '\n'.join(rows) + '</tt>'


# --- Parse TSV cache ---
events = []  # list of (date, datetime_or_None, title)
try:
    with open(tsv_file) as f:
        for row in csv.DictReader(f, delimiter='\t'):
            sd    = row.get('start_date', '').strip()
            st    = row.get('start_time', '').strip()
            title = row.get('title', '').strip()[:30]
            if not sd or not title:
                continue
            try:
                edate = datetime.datetime.strptime(sd, '%Y-%m-%d').date()
            except ValueError:
                continue
            edt = None
            if st:
                try:
                    edt = datetime.datetime.strptime(f'{sd} {st}', '%Y-%m-%d %H:%M')
                except ValueError:
                    pass
            events.append((edate, edt, title))
except OSError:
    pass


# Days in the viewed month that have events (shown as underlined in calendar).
# Today is excluded since it already has its own green highlight.
appointment_days = {
    edate.day for edate, edt, _ in events
    if edate.month == cal_month
    and edate.year == cal_year
    and not (viewing_current_month and edate.day == today)
}

# Events this week (Mon–Sun), from now onwards
end_of_week = datetime.datetime.combine(
    today_date + datetime.timedelta(days=(6 - today_date.weekday())),
    datetime.time(23, 59, 59)
)
upcoming = [
    (edate, edt, title) for edate, edt, title in events
    if (edt is not None and now <= edt <= end_of_week)
    or (edt is None and today_date <= edate <= end_of_week.date())
]


# --- Calendar box ---
today_markup = f'<span foreground="#9ECE6A"><b><u>{today}</u></b></span>'

cal_lines = []
for raw_line in calendar.split('\n'):
    line = raw_line
    m = re.match(r'^( *\d+) ', line)
    if m:
        week_num = m.group(1).strip()
        rest = line[m.end():]
        for day in appointment_days:
            appt_markup = f'<span foreground="#7AA2F7"><u>{day}</u></span>'
            rest = re.sub(r'(?<!\d)' + str(day) + r'(?!\d)', appt_markup, rest, count=1)
        if viewing_current_month:
            rest = re.sub(r'(?<!\d)' + str(today) + r'(?!\d)', today_markup, rest, count=1)
        # Pad single-digit week numbers so columns stay aligned (e.g. "U1" → "U 1")
        pad = ' ' if len(week_num) == 1 else ''
        line = f'<span foreground="#888888">U{week_num}{pad}</span> ' + rest
    elif re.match(r'^\s+[a-zA-ZÆæØøÅå]', line):
        line = ' ' + line
    cal_lines.append(line)


# --- Meetings box ---
rows = []
current_label = None
for edate, edt, title in upcoming:
    label = date_label(edate)
    if label != current_label:
        current_label = label
        rows.append(f'<b>{label}</b>')
    time_str = edt.strftime('%H:%M') if edt is not None else 'Hele dagen'
    rows.append(f'• {time_str} - {title}')

meetings_lines = ['<b>Denne uge:</b>'] + (rows or ['Ingen aftaler'])

tooltip = make_box(cal_lines) + '\n\n' + make_box(meetings_lines)
print(json.dumps({'text': text, 'tooltip': tooltip}))
