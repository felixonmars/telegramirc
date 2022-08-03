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

TODO
====

- [ ] List online users in channel
- [ ] DCC File transfer and other IRC extensions
