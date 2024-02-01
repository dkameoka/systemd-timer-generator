# Generate Systemd timer services from CSV (PSV).

## Usage
1. Create a configuration using the example conf_example.psv provided.
2. Run the script as administrator with the configuration: `./systemd-timer-generator.py --conf path/to/your.psv`. This creates the .timer and .service files in /etc/systemd/system/ by default.

## Extra commands
* Verify a timer config: `systemd-analyze verify timer_name.timer`.
* List timers: `systemctl list-timers --all`.
* Test calendar times: `systemd-analyze calendar 'Fri *-*-13 01:23:45' --iterations 5`.
