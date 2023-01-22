# Generate Systemd timer services from CSV (PSV).

## Usage
1. Create a configuration using the example conf_example.psv provided.
2. Run the script as administrator with the configuration: `./systemd-timer-generator.py path/to/your.psv`. This creates the .timer and .service files in /etc/systemd/system/ by default.
3. Reload Systemd files: `systemctl daemon-reload`.
4. Enable the timers: `systemctl enable --now timer_name.timer` or restart the timer: `systemctl restart timer_name.timer`.

## Extra commands
* Verify a timer config: `systemd-analyze verify timer_name.timer`.
* List timers: `systemctl list-timers --all`.
* Test calendar times: `systemd-analyze calendar 'Fri *-*-13 01:23:45' --iterations 5`.
