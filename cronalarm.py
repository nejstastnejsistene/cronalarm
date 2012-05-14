#!/usr/bin/env python

import argparse
from commands import getoutput
from datetime import datetime, timedelta

import cron


# make sure there's a way of recognizing that only
# one user can have this installed at a time

# in /etc/rc.local
# chown $LOGNAME /sys/class/rtc/rtc0/wakealarm

PROGRAM_NAME = '/home/peter/code/cronalarm/cronalarm.py'
PLAY_COMMAND = '%s -p' % PROGRAM_NAME
WAKEUP_OFFSET = timedelta(minutes=1)

class CronAlarm:

    def __init__(self):
        self.update()

    def read_entries(self):
        global DATA_PATH
        self.entries = []
        with open(DATA_PATH) as f:
            for line in f:
                line = line.strip()
                if line:
                    entry = cron.CronEntry(line)
                    self.entries.append(entry)

    def write_entries(self):
        global DATA_PATH
        with open(DATA_PATH, 'w') as f:
            for entry in self.entries:
                f.write('%s\n' % entry)

    def update(self):

        # read entries from file and update crontab
        self.read_entries()
        self.update_crontab()

        # calculate next alarm and set wakealarm
        if self.entries:
            self.next_alarm = min(map(next, self.entries))
        else:
            self.next_alarm = None
        set_wakealarm(self.next_alarm)
        
        # whether wakealarm is set correctly
        self.wakealarm_sync = get_wakealarm() == self.next_alarm

    def update_crontab(self):
        crontab = cron.CronTab()

        # add entries not in crontab
        for entry in self.entries:
            if entry not in crontab.entries:
                crontab.add_entry(entry)

        # remove entries not in file
        for entry in crontab.entries:
            if entry.command.startswith(PROGRAM_NAME):
                if entry not in self.entries:
                    crontab.remove_entry(entry)
        crontab.commit()

    def format_entry(self, entry):
        return ' '.join(entry.split())

    def format_entry(self, entry):
        return '%s %s -p' % (' '.join(entry.split()), PROGRAM_NAME)

    def add_entry(self, entry, play_options):
        entry = self.format_entry(entry)
        play_options = play_options.strip()
        for e in self.entries:
            if e.entry.startswith(entry):

                # duplicate if play options are the same
                if e.entry[len(entry)+1:] == play_options:
                    log('duplicate entry, entry not added')
                    return
                else:
                    log('duplicate entry, replacing play options')
                    self.entries.remove(e)
                    break
        if play_options:
            entry += ' ' + play_options
        log('adding entry: %s' % entry)
        self.entries.append(cron.CronEntry(entry))
        self.write_entries()
        self.update()

    def remove_entry(self, entry):
        entry = self.format_entry(entry)
        log('removing entry: %s' % entry)
        for e in self.entries:
            if e.entry.startswith(entry):
                self.entries.remove(e)
                break
        self.write_entries()
        self.update()

    def clear(self):
        log('clearing alarms')
        self.entries = []
        self.write_entries()
        self.update()

    def get_message(self):
        if self.next_alarm is not None:
            dt = self.next_alarm - datetime.now()
            days = dt.days
            hours = dt.seconds / 3600
            minutes = dt.seconds / 60 % 60
            def pluralize(word, amt):
                return '%d %s%s' % (amt, word, '' if amt == 1 else 's')
            output = 'The alarm is set for '
            if days > 0:
                output += '%s ' % pluralize('day', days)
            if hours > 0:
                output += '%s and ' % pluralize('hour', hours)
            output += '%s from now.' % pluralize('minute', minutes)
            return output
        else:
            return 'No alarm is set.'

    def __repr__(self):
        return '\n'.join(map(str, self.entries))


def set_wakealarm(dt):
    assert not getoutput('echo 0 > /sys/class/rtc/rtc0/wakealarm')
    if dt is not None:
        seconds = getoutput('date -u --date "%s" +%%s' % (dt - WAKEUP_OFFSET))
        assert not getoutput('echo %s > /sys/class/rtc/rtc0/wakealarm' % seconds)

def get_wakealarm():
    output = getoutput('cat /proc/driver/rtc | grep alrm')
    output = [line[line.index(':') + 1:].strip() \
        for line in output.split('\n')]
    dt_string = ' '.join([output[0], output[1]])
    dt = datetime.strptime(dt_string, '%H:%M:%S %Y-%m-%d')
    return dt + WAKEUP_OFFSET

def log(message):
    print message
    with open(LOG_PATH, 'a+') as f:
        f.write('%s %s\n' % (datetime.now(), message))


if __name__ == '__main__':
    import os

    DATA_DIR = os.path.join(os.environ.get('HOME'), '.local/share/cronalarm')
    DATA_PATH = os.path.join(DATA_DIR, 'entries')
    LOG_PATH = os.path.join(DATA_DIR, 'log')
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
    if not os.path.exists(DATA_PATH):
        with open(DATA_PATH, 'w+'): pass

    parser = argparse.ArgumentParser(description='Cron Alarm Clock')
    parser.add_argument('-p', '--play', nargs='*', metavar='options')
    parser.add_argument('-a', '--add', metavar='"cron entry"')
    parser.add_argument('-o', '--play-options', default='', metavar='options')
    parser.add_argument('-r', '--remove', metavar = '"cron entry"')
    parser.add_argument('-l', '--list', action='store_true')
    parser.add_argument('-c', '--clear', action='store_true')
    parser.add_argument('--log', action='store_true')
    args = parser.parse_args()

    alarm = CronAlarm()

    if args.play_options and args.add is None:
        parser.print_usage()
        parser.exit()

    # play alarm
    if args.play is not None:
        log('playing alarm')
        getoutput('/home/peter/code/cronalarm/maximize-volume.sh')
        getoutput('/home/peter/code/cronalarm/play-alarm.sh')

    # add alarm
    if args.add is not None:
        alarm.add_entry(args.add, args.play_options)

    # remove alarm
    if args.remove is not None:
        alarm.remove_entry(args.remove)

    if args.list:
        for entry in alarm.entries:
            print entry
        print

    if args.clear:
        alarm.clear()

    if args.log:
        print getoutput('tail %s' % LOG_PATH)
        print

    print alarm.get_message()
    if not alarm.wakealarm_sync:
        print 'warning: wakealarm is not synchronized'
        
