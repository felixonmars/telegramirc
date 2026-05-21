telegramirc
===========

Telegram as your IRC client.

Features
========

- Tailored for using Telegram as your personal IRC client. This is not a group <=> channel forwarding bridge like many other projects.
- Single Telegram Bot for Multiple IRC channels (with different Telegram groups)
- Always online and search your IRC history with Telegram's builtin search.
- Direct messages (/msg) and action (/me)
- SASL Login
- Password-protected IRC channels

Dependencies
============

- aiogram (Telegram library)
- pydle (IRC library)
- tenacity
- toml

Usage
=====

- Ask @BotFather for a Telegram bot, save its token
- Copy telegramirc_example.toml to telegramirc.toml
- Fill in an initial value (for example, 0) as telegram.fallback_chatid and comment out [channel.*]
- Run telegramirc with your initial configuration (python telegramirc.py)
- Talk to your bot on telegram, use /chatid to get your fallback chatid
- Now for each channel you want to join, create a telegram group with you and your bot. Use /chatid inside the group for the corresponding chatid in [channel.*] sections below.

Installation (virtualenv)
=========================

A `requirements.txt` is provided for pip-based installs. Tested on Debian 12
(Python 3.11) in addition to Arch Linux.

```
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

Running as a systemd service
============================

A sample unit file `telegramirc.service` is included. It runs as a dedicated
unprivileged user `telegramirc` with the deployment located at
`/opt/telegramirc`.

```
sudo adduser --system --group --home /opt/telegramirc --shell /usr/sbin/nologin telegramirc
cd /opt/telegramirc
sudo -u telegramirc git clone https://github.com/felixonmars/telegramirc.git .
sudo -u telegramirc python3 -m venv .venv
sudo -u telegramirc .venv/bin/pip install -r requirements.txt

sudo -u telegramirc cp telegramirc_example.toml telegramirc.toml
sudo chmod 600 telegramirc.toml
sudo $EDITOR telegramirc.toml

sudo cp telegramirc.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now telegramirc.service
sudo journalctl -u telegramirc -f
```

TODO
====

- [ ] List online users in channel
- [ ] DCC File transfer and other IRC extensions
