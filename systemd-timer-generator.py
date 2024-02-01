#!/usr/bin/env python3

# pylint: disable=invalid-name,missing-docstring,too-many-arguments

import argparse
import csv
import subprocess
from pathlib import Path


class SystemdTimerWriterExc(Exception):
    """ SystemdTimer Exception """


class SystemdTimerWriter:
    """ Writes Systemd .service and .timer files """


    def __init__(self, outdir, name, cals, exec_):
        self.outdir = Path(outdir)
        self.name = self.validate_name(name)
        self.cals = self._validate_cals(cals)
        self.exec = self._validate_exec(exec_)


    @staticmethod
    def _validate_exec(exec_):
        exec_ = exec_.strip()
        if len(exec_) == 0:
            raise SystemdTimerWriterExc('Exec is empty')
        path = Path(exec_.split(' ')[0])
        if not path.is_absolute():
            raise SystemdTimerWriterExc(f'Exec path "{exec_}" is not absolute')
        if not path.exists():
            raise SystemdTimerWriterExc(f'Exec path "{exec_}" doesn\'t exist')
        return exec_


    @staticmethod
    def validate_name(name):
        name = name.strip()
        name_len = len(name)
        name_max = 256 - len('.service')  # implicitly shorter than with ".timer" suffix.
        if name_len == 0 or name_len > name_max:
            raise SystemdTimerWriterExc(f'Name "{name_len}" is empty or longer than {name_max}')
        for char in name:
            if not char.isalnum() and char not in [':', '-', '_', '.', '\\']:
                raise SystemdTimerWriterExc(f'Name "{name}" has an invalid character "{char}"')
        return name


    @staticmethod
    def _validate_cal(cal):
        cal = cal.strip()
        try:
            subprocess.run(['systemd-analyze', 'calendar', cal, '--iterations', '0'], check=True)
        except subprocess.CalledProcessError as exc:
            raise SystemdTimerWriterExc(f'Calendar datetime "{cal}" is invalid') from exc
        except FileNotFoundError:
            print('systemd-analyze is missing. Skipping calendar validation.')
        return cal


    def _validate_cals(self, cals):
        cals = cals.split(';')
        if len(cals) == 0:
            raise SystemdTimerWriterExc('Empty calendar')
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
        with outpath.open('w') as file_:
            file_.write(self.service())
        print(f'Wrote {outpath}')


class _Main:


    def __init__(self, args):
        self.args = args


    def clear_timers(self):
        for path_ in self.args.outdir.glob('*'):
            if not path_.stem.startswith(self.args.prefix):
                continue
            if path_.suffix == '.timer':
                subprocess.run(['systemctl', 'disable', '--now', f'{path_.name}'], check=True)
            path_.unlink(missing_ok=True)


    def process_row(self, row):
        timer = SystemdTimerWriter(self.args.outdir, self.args.prefix + row['name'],
            row['cals'], row['exec'])
        timer.timer_write()
        timer.service_write()
        subprocess.run(['systemctl', 'daemon-reload'], check=True)
        subprocess.run(['systemctl', 'enable', '--now', f'{timer.name}.timer'], check=True)


    def load_conf(self):
        if self.args.disable:
            return
        with self.args.conf.open('r', newline='') as file:
            fieldnames = ('name', 'cals', 'exec')
            for row in csv.DictReader(file, fieldnames=fieldnames, delimiter='|', restval=''):
                name = row['name']
                try:
                    self.process_row(row)
                except SystemdTimerWriterExc as exc:
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


def _prefix_type(value):
    try:
        return SystemdTimerWriter.validate_name(value)
    except SystemdTimerWriterExc as exc:
        raise argparse.ArgumentTypeError(exc)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Generates persistent Systemd timer services')

    parser.add_argument(
        '-c', '--conf',
        dest='conf',
        type=_file_type,
        default=Path(__file__).parent.resolve() / 'conf.psv',
        help='Path to PSV config with: name | cals[;] | exec. Default: ./conf.psv')

    parser.add_argument(
        '-o', '--outdir',
        dest='outdir',
        type=_dir_type,
        default=Path('/etc/systemd/system/'),
        help='Output path. Default: /etc/systemd/system/')

    parser.add_argument(
        '-p', '--prefix',
        dest='prefix',
        type=_prefix_type,
        default='gentimer_',
        help=('File name prefix for .service and .timer files. If this value is changed, '
            'old .service and .timer files must be removed manually. Default: gentimer_'))

    parser.add_argument(
        '-d', '--disable',
        dest='disable',
        action='store_true',
        help='Skips the generation of .service and .timer files')

    main = _Main(parser.parse_args())
    main.clear_timers()
    main.load_conf()
