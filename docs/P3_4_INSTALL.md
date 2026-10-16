# PurpleForge AI P3.4 — Native network telemetry runbook

**Scope:** Adds file-based Suricata EVE and Zeek JSON connection-log shipping. Does NOT alter P1–P3.3, run attacks, configure switch mirroring, or require containers. Run commands in the marked operating system.

## 0. Before starting
- VMnet1 remains isolated. Ubuntu sensor `192.168.37.20` (interface `ens33`); Windows host Caddy `https://192.168.37.1:8443`. Never connect Metasploitable2/Windows 7 to NAT/bridged networking.
- Keep the Ubuntu journald collector and Windows scheduled collectors running.
- Ubuntu must have enough disk space. Suricata/Zeek logs can grow quickly; keep this a low-rate lab deployment and establish retention.
- **Important capture limit:** a sensor on an ordinary switched VMnet1 may not see unicast traffic between other VMs. It can still see traffic to/from Ubuntu. Do not claim whole-lab packet visibility without confirming mirroring, an inline sensor, or equivalent placement.
- For package installation, temporarily use the previously verified Ubuntu NAT + DHCP workflow, then restore VMnet1 static `192.168.37.20/24`. Stop after `apt` succeeds; do not keep lab NAT attached during capture.

## 1. Verify traffic visibility (Ubuntu terminal)
```
ip -br addr
ip route
sudo apt install -y tcpdump   # do this only when internet/package source is available
sudo timeout 20 tcpdump -ni ens33 -c 10
```
In a separate terminal on Windows host, generate benign traffic **to Ubuntu**, e.g. `Test-NetConnection 192.168.37.20 -Port 22`. This confirms what Ubuntu receives; it does NOT establish that it observes Kali-to-target unicast.

## 2. Native packages (Ubuntu, temporary NAT ONLY when needed)
```
sudo apt update
sudo apt install -y suricata tcpdump python3
suricata --build-info | head
sudo suricata -T -c /etc/suricata/suricata.yaml
```
Restore VMnet1 afterward, confirm `ip -4 addr show ens33` shows `192.168.37.20/24`, and verify HTTPS certificate communication to Caddy.

Zeek availability varies by Ubuntu repository. Test `apt-cache policy zeek`. If no installable candidate, use the official supported Zeek native package/build instructions for Ubuntu 24.04; do not install from an untrusted repository. **Do not enable Zeek shipper until Zeek exists and produces JSON-formatted `conn.log`.** You may start with Suricata only.

## 3. Configure Suricata (Ubuntu)
Back up the YAML and inspect capture interface/output settings:
```
sudo cp /etc/suricata/suricata.yaml /etc/suricata/suricata.yaml.p34.bak
sudo grep -n -E 'af-packet:|interface:|eve-log:|filename: eve.json' /etc/suricata/suricata.yaml
sudo nano /etc/suricata/suricata.yaml
```
Set the capture interface to `ens33` in the appropriate `af-packet` section, and ensure `eve-log` is enabled with filename `eve.json` and useful event types (`alert`, `flow`, `dns`, `http`, `tls`). YAML indentation matters; edit rather than blindly appending duplicate sections.
```
sudo suricata -T -c /etc/suricata/suricata.yaml
sudo systemctl enable --now suricata
sudo systemctl status suricata --no-pager
sudo tail -n 3 /var/log/suricata/eve.json
```
If `suricata` shows no logs, verify the service configuration and traffic visibility before installing the shipper.

## 4. Register TWO source identities (Windows HOST Angular)
Open http://localhost:4200 → Telemetry → Register native collector.
- Asset: `ubuntu2404`, type: `suricata`, name: `Ubuntu Suricata P3.4`.
- Asset: `ubuntu2404`, type: `zeek`, name: `Ubuntu Zeek P3.4` **only after Zeek is installed**.
Save each key independently and do not paste them into chat. Disable any accidental duplicate sources.

## 5. Transfer the new P3.4 files (Windows HOST PowerShell)
After extracting the ZIP into `F:\My_Projects\PurpleLoop\PurpleLoop`:
```
cd 'F:\My_Projects\PurpleLoop\PurpleLoop'
scp .\collectors\network\network_shipper.py gihan@192.168.37.20:~/
scp .\collectors\network\purpleforge-suricata-shipper.service gihan@192.168.37.20:~/
scp .\collectors\network\purpleforge-zeek-shipper.service gihan@192.168.37.20:~/
```

## 6. Install shipper (Ubuntu terminal)
```
sudo install -m 0755 ~/network_shipper.py /opt/purpleforge/network_shipper.py
sudo install -d -m 0750 -o purpleforge-collector -g purpleforge-collector /var/lib/purpleforge-network
sudo install -m 0644 ~/purpleforge-suricata-shipper.service /etc/systemd/system/purpleforge-suricata-shipper.service
sudo install -m 0644 ~/purpleforge-zeek-shipper.service /etc/systemd/system/purpleforge-zeek-shipper.service
sudo systemctl daemon-reload
```
Configure the existing HTTPS endpoint (non-secret):
```
printf 'PURPLEFORGE_API_URL=https://192.168.37.1:8443\n' | sudo tee /etc/purpleforge/network-suricata.env > /dev/null
sudo chown root:purpleforge-collector /etc/purpleforge/network-suricata.env
sudo chmod 0640 /etc/purpleforge/network-suricata.env
```
To write **only** the new Suricata API key in a protected file:
```
sudo nano /etc/purpleforge/suricata.key
sudo chown root:purpleforge-collector /etc/purpleforge/suricata.key
sudo chmod 0640 /etc/purpleforge/suricata.key
```
The new shipper needs read permissions on `/var/log/suricata/eve.json`; **avoid making the entire log directory world-readable**. Confirm with:
```
sudo -u purpleforge-collector test -r /var/log/suricata/eve.json && echo readable
```
If unreadable, check real ownership and permissions, then grant **targeted read access** using ACLs (`sudo apt install acl` if unavailable). Example, adjust to actual file and parent directory paths:
```
sudo setfacl -m u:purpleforge-collector:rx /var/log/suricata
sudo setfacl -m u:purpleforge-collector:r /var/log/suricata/eve.json
sudo setfacl -m d:u:purpleforge-collector:r /var/log/suricata
```
For rotations, use the correct file/group ACL policy of your native Suricata installation. Do not enable the service until it can read the file.

## 7. Start and validate Suricata forwarding (Ubuntu)
```
sudo systemctl enable --now purpleforge-suricata-shipper
sudo systemctl status purpleforge-suricata-shipper --no-pager
sudo journalctl -u purpleforge-suricata-shipper -n 30 --no-pager
```
The first run starts at end-of-file, skipping old events. Generate benign traffic involving Ubuntu, then look for `accepted: N` and check Angular `Suricata` source state becomes Receiving. If state stays Configured, check the EVE file grows, permissions, API key and network reachability.

## 8. Zeek optional phase (Ubuntu)
Zeek's installation and log path vary by native installation. A simple local lab flow, *after verifying your Zeek installation*:
```
zeek --version
sudo install -d -m 0750 -o purpleforge-collector -g purpleforge-collector /var/log/purpleforge-zeek
```
To generate JSON logs, ensure Zeek is configured to load `policy/tuning/json-logs` (or equivalent `LogAscii::use_json=T` setting) before running on `ens33`. Use your installed Zeek's native systemd or zeekctl configuration to write `conn.log` into `/var/log/purpleforge-zeek/`, and ensure the collector user can read it. Zeek must capture real traffic; copying an empty placeholder does not verify collection.

Create Zeek key and environment on Ubuntu, after registering source:
```
printf 'PURPLEFORGE_API_URL=https://192.168.37.1:8443\n' | sudo tee /etc/purpleforge/network-zeek.env > /dev/null
sudo chown root:purpleforge-collector /etc/purpleforge/network-zeek.env
sudo chmod 0640 /etc/purpleforge/network-zeek.env
sudo nano /etc/purpleforge/zeek.key
sudo chown root:purpleforge-collector /etc/purpleforge/zeek.key
sudo chmod 0640 /etc/purpleforge/zeek.key
sudo -u purpleforge-collector test -r /var/log/purpleforge-zeek/conn.log && echo readable
sudo systemctl enable --now purpleforge-zeek-shipper
sudo journalctl -u purpleforge-zeek-shipper -n 30 --no-pager
```
The Zeek shipper reads *only* conn.log by default; DNS/HTTP logs need separate per-file checkpoints and dedicated source credentials or an extended multisource configuration in a later milestone.

## 9. Tests on Windows HOST (no live DB needed)
```
cd 'F:\My_Projects\PurpleLoop\PurpleLoop'
.\backend\.venv\Scripts\python.exe -m unittest discover -s tests -p 'test_p34_*.py' -v
```

## Known limitations
- This is **a native file-ingestion integration**, not a full capture deployment or traffic-mirroring solution.
- The shipper uses file inode/offset and at-least-once requests; lost response may cause duplicates. Log rotation or restart can lose unprocessed records when the input file is replaced/truncated (new files start at EOF). Production deployments need persistent rotation-aware cursors, queue/backpressure, deduplication and retention.
- Only selected safe metadata is forwarded; event payloads omit packet bodies, secrets and complete raw records. Audit your DNS hostname values before shipping production traffic.
- Sources become Receiving only after real events are accepted, not when registered.
- Existing Ubuntu Journald, Sysmon and Windows Security collectors remain unchanged.
