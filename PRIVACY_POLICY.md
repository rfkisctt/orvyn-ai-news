# Privacy Policy

1. Introduction

This Privacy Policy explains how the AI News Discord Bot project handles data when used with a Discord server.

2. Data Collected

The bot may access or process the following information:

- Discord bot token used for authentication
- Configured news channel ID
- RSS feed URLs defined in `config.py`
- Posted article history stored locally in `posted_news.json`
- Log outputs written for debugging
- Basic server and member counts used only for bot presence/status display

3. Data Usage

The bot uses data only to connect to Discord, post AI news embeds into the configured channel, track posted items to prevent duplicates, and display bot status.

4. Data Storage

Data is stored locally in the project files (e.g. news history, configuration files, and log files). No external database or analytics service is used by default.

5. Data Sharing

The bot does not share personal user data with third parties. It only reads public RSS feeds and posts content into your configured Discord channels.

6. Discord Data

The bot accesses Discord server and member metadata only as required by the Discord API. It does not store or expose user messages or private profile details.

7. Security

Keep your bot credentials and tokens secret. Do not publish them to public source control.

8. Your Rights

You may remove or stop using the bot at any time by removing it from your server and deleting the bot configuration.

9. Changes to Policy

This policy may be updated at any time. Changes are effective when posted in this document.

10. Contact

For privacy questions, please contact the project owner or maintainer.
