# TIDAL Discord Rich Presence

A Windows app that detects the track playing in the TIDAL desktop app and shares it as Discord Rich Presence. Track, artist, album, and playback progress come from the Windows media session. The app looks up artwork and TIDAL links in the TIDAL catalog. It can run from the Windows notification area and optionally start when you sign in.

## Features

- Detects TIDAL playback through Windows media controls
- Shows the artist as the activity name, plus the track, album, and playback progress
- Looks up track, artist, album, and artwork details in the TIDAL catalog
- Runs from a notification-area icon with an Exit menu item
- Runs without a command prompt window
- Optional startup when you sign in to Windows
- Writes rotating local logs for troubleshooting
- Prevents multiple instances from running at once

## Requirements

- Windows 10 or Windows 11
- Python 3.11 or later
- Discord desktop app
- TIDAL desktop app with an active media session
- A Discord application ID from the Discord Developer Portal
- TIDAL application credentials from the TIDAL Developer Portal

## Installation

Open PowerShell or Command Prompt and go to the project folder:

```powershell
cd "$env:USERPROFILE\Documents\tidal-rpc"
```

Install the dependencies:

```powershell
py -m pip install -r requirements.txt
```

> This project uses PyWinRT instead of the older `winsdk` package, avoiding the C++ build and Visual Studio requirement that can occur with Python 3.15.

Create and edit your local settings file:

```powershell
Copy-Item .env.example .env
notepad .env
```

Fill in the values in `.env`:

```dotenv
DISCORD_CLIENT_ID=your_discord_application_id
TIDAL_CLIENT_ID=your_tidal_client_id
TIDAL_CLIENT_SECRET=your_tidal_client_secret
TIDAL_COUNTRY_CODE=US
```

Find the Discord Application ID on the app's **General Information** page in the [Discord Developer Portal](https://discord.com/developers/applications). Get the TIDAL credentials from your app in the [TIDAL Developer Portal](https://developer.tidal.com/). Your TIDAL app may need catalog access enabled in the developer portal.

## Run

To run from a terminal while developing:

```powershell
py tidal_rpc.py
```

To run without a command prompt window:

```powershell
pyw tidal_rpc.py
```

Keep Discord and TIDAL open and play a track. Right-click the notification-area icon and select **Exit** to close the app.

## Start automatically with Windows

After installing dependencies and filling in `.env`, run this from PowerShell in the project folder:

```powershell
powershell -ExecutionPolicy Bypass -File .\install_autostart.ps1
```

The app will start without a command prompt when you sign in to Windows. To remove the startup shortcut, run:

```powershell
powershell -ExecutionPolicy Bypass -File .\uninstall_autostart.ps1
```

## Logs

Logs are saved to:

```text
%LOCALAPPDATA%\TidalRPC\logs\tidal-rpc.log
```

Log files rotate automatically, with up to three older files retained. Check the latest log if catalog lookup or Discord connection fails.

## Security

- Don't share `.env` .
- If a client secret is exposed, rotate it in the corresponding developer portal.
- The Discord Application ID is not a secret, but it is kept in `.env` so each user can configure their own app.

## Known limitations

- This app is designed for Windows and the TIDAL desktop media session.
- Catalog lookup requires TIDAL Developer API credentials and catalog access.
- The app sends the TIDAL artwork URL to Discord Rich Presence. Displaying external image URLs may depend on Discord client and RPC behavior; uploaded Discord application assets use a different approach.
- If a track cannot be matched in the TIDAL catalog, the app still shows the title and artist from Windows media controls, but omits artwork and TIDAL buttons.

## Suggested GitHub repository description

> A Windows system tray app that detects the current TIDAL track and shares it as Discord Rich Presence with playback progress, links, and catalog artwork lookup.

Suggested topics: `tidal`, `discord-rich-presence`, `python`, `windows`, `music`.

## Attribution

This is an independent project and is not published by or affiliated with TIDAL or Discord. Follow the [TIDAL Developer Guidelines](https://developer.tidal.com/documentation/guidelines-developer-guidelines-2_0) and applicable API terms when using TIDAL content.
