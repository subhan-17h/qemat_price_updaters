# Price updater VM deployment

The production checkout is `/home/ubuntu/apps/qemat_price_updaters` and the VM uses UTC.
The timer starts at Saturday 21:00 UTC, which is Sunday 02:00 PKT.

## Runtime preparation

Install Google Chrome from Google's signed apt repository and confirm `google-chrome --version` works.
Create a persistent 2 GiB `/swapfile`, enable it with `swapon`, and add it to `/etc/fstab`.

Generated `products.csv` and `consolidated.csv` are intentionally ignored by Git. Before the first pull
that contains this change, move both files to a temporary backup directory, pull `main`, then restore them.

## Alert configuration

Create `/etc/qemat/alerts.env` without committing the Gmail App Password:

```text
SMTP_USERNAME=subhanamir102@gmail.com
SMTP_APP_PASSWORD=replace-with-gmail-app-password
ALERT_TO=subhanamir102@gmail.com
```

Set ownership to `root:ubuntu` and mode `0640`.

## Install

Copy the three files in `deploy/systemd/` to `/etc/systemd/system/`, then run:

```bash
sudo systemd-analyze verify /etc/systemd/system/qemat-*.service /etc/systemd/system/qemat-*.timer
sudo systemctl daemon-reload
sudo systemctl enable --now qemat-price-update.timer
```

Useful checks:

```bash
systemctl list-timers qemat-price-update.timer
sudo systemctl status qemat-price-update.timer
sudo journalctl -u qemat-price-update.service -n 200 --no-pager
```
