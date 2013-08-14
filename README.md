cronalarm
=========

Alarm app based on cron, capable of waking your computer from shutdown.

I wrote this in Fall 2011 as an alarm for myself because I was getting annoyed by my phone alarm. This also has the advantage of requiring me to log into my laptop to kill the alarm (at least until I realize I could just close my laptop to stop it...)

## Usage

```
usage: cronalarm.py [-h] [-p [options [options ...]]] [-a "cron entry"]
                    [-o options] [-r "cron entry"] [-l] [-c] [--log]

Cron Alarm Clock

optional arguments:
  -h, --help            show this help message and exit
  -p [options [options ...]], --play [options [options ...]]
  -a "cron entry", --add "cron entry"
  -o options, --play-options options
  -r "cron entry", --remove "cron entry"
  -l, --list
  -c, --clear
  --log
```
