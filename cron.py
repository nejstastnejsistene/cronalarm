import commands
import os
import tempfile
from calendar import monthrange
from datetime import datetime

FIELDS = MINUTE, HOUR, DOM, MONTH, DOW = range(5)

MONTH_NAMES = 'JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC'.split()
DOW_NAMES = 'SUN MON TUE WED THU FRI SAT SUN'.split()

MINUTE_INFO = 0, 59, None
HOUR_INFO = 0, 23, None
DOM_INFO = 1, 31, None
MONTH_INFO = 1, 12, MONTH_NAMES
DOW_INFO = 0, 7, DOW_NAMES

FIELD_INFO = MINUTE_INFO, HOUR_INFO, DOM_INFO, MONTH_INFO, DOW_INFO

REBOOT = '@reboot'
PREDEFINED = {
    '@yearly': '0 0 1 1 *',
    '@anually': '0 0 1 1 *',
    '@monthly': '0 0 1 * *',
    '@weekly': '0 0 * * 0',
    '@hourly': '0 * * * *',
    }

REBOOT_FLAG = 1
DOM_DOW_STAR_FLAG = 2

class CronTab:

    def __init__(self):
        self.tab = []
        self.entries = []
        self.update()

    def update(self):
        output = commands.getoutput('crontab -l')
        username = os.environ.get('LOGNAME')
        if output != 'no crontab for %s' % username:
            self.tab = output.split('\n')
            self.entries = []
            for line in self.tab:
                line = line.strip()
                if line and not line.startswith('#'):
                    self.entries.append(CronEntry(line))

    def commit(self):
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            for line in self.tab:
                tmp.write(line + '\n')
        commands.getoutput('crontab %s' % tmp.name)
        os.unlink(tmp.name)

    def remove_entry(self, entry):
        if entry in self.entries:
            self.entries.remove(entry)
            self.tab.remove(str(entry))

    def add_entry(self, entry):
        if entry in self.entries:
            raise ValueError, 'duplicate entry'
        self.entries.append(entry)
        self.tab.append(str(entry))


class CronEntry:

    def __init__(self, entry):
        self.entry = entry
        self.fields = {}
        self.flags = 0
        self.parse(entry)

    def parse(self, entry):

        # reboot flag is a special case
        if entry.startswith(REBOOT):
            self.command = entry.replace(REBOOT, '', 1).strip()
            self.flags |= REBOOT_FLAG
        else:
            return self._parse(entry)

    def _parse(self, entry):

        # replace predefined strings
        if entry.startswith('@'):
            token = entry.split()[0]
            entry = entry.replace(token, PREDEFINED[token], 1)

        # parse fields
        for expr, field in zip(entry.split(), FIELDS):
            entry = entry.replace(expr, '', 1)
            self.parse_field(expr.upper(), field)

        # command
        self.command = entry.strip()

    def parse_field(self, expr, field):
        lo, hi, names = FIELD_INFO[field]
        bits = [0 for i in range(hi - lo + 1)]

        # replace names
        if names is not None:
            for i in range(len(names)):
                if names[i] in expr:
                    expr = expr.replace(names[i], str(lo + i))

        # iterate through comma separated values
        for v in expr.split(','):
            
            # slash changes the step amount
            if '/' in v:
                v, step = v.split('/')
                step = int(step)
            else:
                step = 1

            # asterisk means include all values
            if v == '*':
                if field in (DOM, DOW):
                    self.flags |= DOM_DOW_STAR_FLAG
                start, stop = lo, hi

            # dash indicates a range of values
            elif '-' in v:
                start, stop = map(int, v.split('-'))

            # only a single number, not a range
            else:
                bits[int(v) - lo] = 1
                continue

            # set all values in the range
            for i in range(start, stop + 1, step):
                bits[i - lo] = 1

        # both 0 and 7 are Sunday
        if field == DOW and (bits[0] or bits[7]):
            bits[0] = bits[7] = 1

        self.fields[field] = bits

    # iterate through the matching values for this field
    def iter_field(self, field):
        lo = FIELD_INFO[field][0]
        for i in range(len(self.fields[field])):
            if self.fields[field][i]:
                yield lo + i

    # find next date this entry will run
    def next(self):
        now = datetime.now()
        year = now.year
        DOM_LO, DOM_HI, _ = FIELD_INFO[DOM]
        while True:
            same_year = year == now.year
            for month in self.iter_field(MONTH):
                if same_year and month < now.month:
                    continue
                same_month = same_year and month == now.month

                # iterate through all doms, check later
                # see comment below
                for dom in range(DOM_LO, DOM_HI + 1):
                    num_days = monthrange(year, month)[1]
                    if dom > num_days or same_month and dom < now.day:
                        continue
                    same_day = same_year and dom == now.day
                    for hour in self.iter_field(HOUR):
                        if same_day and hour < now.hour:
                            continue
                        same_hour = same_day and hour == now.hour
                        for minute in self.iter_field(MINUTE):
                            if same_hour and minute < now.minute + 1:
                                continue
                            dt = datetime(year, month, dom, hour, minute)
                            dow = dt.isoweekday()

    # comment from Paul Vixie's original code:
    #/* the dom/dow situation is odd.  '* * 1,15 * Sun' will run on the
    # * first and fifteenth AND every Sunday;  '* * * * Sun' will run *only*
    # * on Sundays;  '* * 1,15 * *' will run *only* the 1st and 15th.  this
    # * is why we keep 'e->dow_star' and 'e->dom_star'.  yes, it's bizarre.
    # * like many bizarre things, it's the standard.
    # */
                            valid_dom = dom in self.iter_field(DOM)
                            valid_dow = dow in self.iter_field(DOW)
                            if self.flags & DOM_DOW_STAR_FLAG:
                                valid = valid_dom and valid_dow
                            else:
                                valid = valid_dom or valid_dow

                            if valid:
                                return dt

            # try next year
            year += 1

    def __eq__(self, other):
        return self.entry == other.entry

    def __str__(self):
        return self.entry

    def __repr__(self):
        return 'CronEntry(%r)' % self.entry

