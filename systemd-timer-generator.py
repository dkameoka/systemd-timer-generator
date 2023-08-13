#!/usr/bin/env python3

# pylint: disable=invalid-name,missing-docstring,too-many-arguments

import argparse
import csv
import subprocess
from pathlib import Path


class SystemdTimerExc(Exception):
    """ SystemdTimer Exception """


class SystemdTimer:

    def __init__(self, outdir, name, cals, exec_, force):
        self.outdir = Path(outdir)
        self.name = self._validate_name(name)
        self.cals = self._validate_cals(cals)
        self.exec = self._validate_exec(exec_)
        self.force = force

    @staticmethod
    def _validate_exec(exec_):
        exec_ = exec_.strip()
        if len(exec_) == 0:
            raise SystemdTimerExc('Exec is empty')
        path = Path(exec_.split(' ')[0])
        if not path.is_absolute():
            raise SystemdTimerExc(f'Exec path "{exec_}" is not absolute')
        if not path.exists():
            raise SystemdTimerExc(f'Exec path "{exec_}" doesn\'t exist')
        return exec_

    @staticmethod
    def _validate_name(name):
        name = name.strip()
        name_len = len(name)
        name_max = 256 - len('.service')  # implicitly shorter than with ".timer" suffix.
        if name_len == 0 or name_len > name_max:
            raise SystemdTimerExc(f'Name "{name_len}" is empty or longer than {name_max}')
        for char in name:
            if not char.isalnum() and char not in [':', '-', '_', '.', '\\']:
                raise SystemdTimerExc(f'Name "{name}" has an invalid character "{char}"')
        return name

    @staticmethod
    def _validate_cal(cal):
        cal = cal.strip()
        try:
            subprocess.run(['systemd-analyze', 'calendar', cal, '--iterations', '0'], check=True)
        except subprocess.CalledProcessError as exc:
            raise SystemdTimerExc(f'Calendar datetime "{cal}" is invalid') from exc
        except FileNotFoundError:
            print('systemd-analyze is missing. Skipping calendar validation.')
        return cal

    def _validate_cals(self, cals):
        cals = cals.split(';')
        if len(cals) == 0:
            raise SystemdTimerExc('Empty calendar')
        return list(map(self._validate_cal, cals))

    def timer(self):
        return (
            '[Unit]\n' +
            'Description=Automatically generated\n' +
            '[Timer]\n' +
            '\n'.join([f'OnCalendar={cal}' for cal in self.cals]) + '\n' +
            'Persistent=true\n' +
            '[Install]\n' +
            'WantedBy=timers.target\n')

    def timer_write(self):
        outpath = self.outdir / f'{self.name}.timer'
        if outpath.exists() and not self.force:
            print(f'Skipped writing {outpath}')
            return
        with outpath.open('w') as file_:
            file_.write(self.timer())
        print(f'Wrote {outpath}')

    def service(self):
        return (
            '[Unit]\n'
            f'Description=Automatically generated\n'
            'After=network.target\n\n'
            '[Service]\n'
            'Type=oneshot\n'
            f'ExecStart={self.exec}\n')

    def service_write(self):
        outpath = self.outdir / f'{self.name}.service'
        if outpath.exists() and not self.force:
            print(f'Skipped writing {outpath}')
            return
        with outpath.open('w') as file_:
            file_.write(self.service())
        print(f'Wrote {outpath}')


class _Main:

    def __init__(self, conf, outdir, force):
        self.conf = conf
        self.outdir = outdir
        self.force = force

    def process_row(self, row):
        timer = SystemdTimer(self.outdir, row['name'], row['cals'], row['exec'], self.force)
        timer.timer_write()
        timer.service_write()

    def load_conf(self):
        with self.conf.open('r', newline='') as file:
            fieldnames = ('name', 'cals', 'exec')
            for row in csv.DictReader(file, fieldnames=fieldnames, delimiter='|', restval=''):
                name = row['name']
                try:
                    self.process_row(row)
                except SystemdTimerExc as exc:
                    print(f'"{name}" error: {exc}')


def _file_type(value):
    path = Path(value)
    if not path.is_file():
        raise argparse.ArgumentTypeError(f'{value} is not a file path')
    return path


def _dir_type(value):
    path = Path(value)
    if not path.is_dir():
        raise argparse.ArgumentTypeError(f'{value} is not a directory path')
    return path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Generates persistent Systemd timer services')
    parser.add_argument(
        dest='conf',
        type=_file_type,
        help='PSV config with: name | cals[;] | exec')
    parser.add_argument(
        '-o', '--outdir',
        dest='outdir',
        type=_dir_type,
        default=Path('/etc/systemd/system/'),
        help='Output path. Default: /etc/systemd/system/')
    parser.add_argument(
        '-f', '--force',
        dest='force',
        action='store_true',
        help='Overwrite existing timer and service files')

    args = parser.parse_args()

    main = _Main(args.conf, args.outdir, args.force)
    main.load_conf()
