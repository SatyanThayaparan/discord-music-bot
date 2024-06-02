# discordMusicBot
 Personal music bot to listen to music, with additional features

Dependency Set up Instructions
-------------------------------

    1. Download ffmpeg file from here: https://www.ffmpeg.org/download.html (choose whichever executable for your operating system)
    2. Extract ffmpeg files using 7-zip
    3. Add a PATH to your system environment variables that point to ffmpeg/bin
    4. Open the command prompt to the project folder you have and conduct the following downloads

        pip install discord.py
        pip install ffmpeg
        pip install PyNaCl
        pip install yt_dlp
        pip install youtubesearchpython

Discord Developer Portal Instructions (05/2024)
-------------------------------------

    1. Create an application on Discord Developer Portal: https://discord.com/developers/applications
    2. Select "New Application" < Name your bot
    3. Navigate to the "Bot" tab < Go to the Privilege Gateway Intents and activate all intents < Presence Intent, Server Member Intent, Message Content Intent
    4. Navigate to the "OAuth2" tab and under "OAuth2 URL Generator" select the "bot" scope
    5. For "Bot Permissions" provide the following < read messages/view channels, send messages, manage messages, add reactions, use slash commands, connect, and speak.
    6. Copy the URL below, then add the bot to the server of your choice
    