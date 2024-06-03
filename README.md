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
        pip install google-api-python-client
        pip install pytube
        pip install spotipy

Discord Developer Portal Instructions (05/2024)
-------------------------------------

    1. Create an application on Discord Developer Portal: https://discord.com/developers/applications
    2. Select "New Application" < Name your bot
    3. Navigate to the "Bot" tab < Go to the Privilege Gateway Intents and activate all intents < Presence Intent, Server Member Intent, Message Content Intent
    4. Navigate to the "OAuth2" tab and under "OAuth2 URL Generator" select the "bot" scope
    5. For "Bot Permissions" provide the following < read messages/view channels, send messages, manage messages, embed links, add reactions, use slash commands, connect, and speak.
    6. Copy the URL below, then add the bot to the server of your choice

Get Youtube API KEY: REDACTED_YOUTUBE_API_KEY
-------------------------------------------------------------

To get a YouTube API key, follow these steps:

Create a Google Cloud Project:

Go to the Google Cloud Console.
Sign in with your Google account.
Click on the project dropdown at the top of the page and select "New Project".
Enter a name for your project and click "Create".
Enable the YouTube Data API:

With your project selected, go to the APIs & Services Dashboard.
Click on "Enable APIs and Services" at the top.
Search for "YouTube Data API v3" and select it from the list.
Click "Enable" to enable the API for your project.
Create API Credentials:

Go to the Credentials page.
Click "Create Credentials" and select "API Key".
Your new API key will be displayed. Copy it and keep it secure, as it allows access to your project's APIs.
(Optional) Restrict Your API Key:

For security reasons, it’s recommended to restrict your API key to specific IP addresses, HTTP referrers, or applications.
To do this, click on the API key name in the credentials list, and then under "API restrictions" and "Application restrictions", set the necessary restrictions based on your use case.
Now you have a YouTube API key that you can use to make requests to the YouTube Data API.


Get Spotify Client ID: REDACTED_SPOTIFY_CLIENT_ID   Client Secret: REDACTED_SPOTIFY_CLIENT_SECRET        

To access the Spotify API, you need to create a Spotify Developer account and register your application. Here's how you can get started:

Sign Up for a Spotify Developer Account:

Go to the Spotify Developer Dashboard: Spotify for Developers
Click on the "Log in" button if you already have a Spotify account, or sign up for a new one.
Once logged in, you'll be redirected to the Spotify Developer Dashboard.
Create a New Application:

In the Spotify Developer Dashboard, click on the "Create an App" button.
Fill in the required information for your application, including the name, description, and website.
After filling in the details, click on the "Create" button.
Retrieve Your Client ID and Client Secret:

Once your application is created, you'll see your Client ID and Client Secret on the application dashboard. These are needed for authenticating your application when making requests to the Spotify API.
Set Up Redirect URIs (Optional):

If your application requires user authentication (e.g., for accessing user playlists), you'll need to set up Redirect URIs in the application settings. These URIs are used to redirect users back to your application after they've authenticated with Spotify.
Read the Documentation:

Familiarize yourself with the Spotify API documentation, which provides information on endpoints, authentication methods, rate limits, and more. You can find the documentation on the Spotify for Developers website.
Start Building:

With your Client ID and Client Secret, you can now start integrating the Spotify API into your application. Follow the documentation and guidelines provided to ensure that your application functions correctly and complies with Spotify's terms of service.
    