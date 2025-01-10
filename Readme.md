# Classficone Bot

With my friends, we started this fun chat where we share new music during the year, and then we met at the ned of the year to rank our favorite albums and talk about music and stuff. This tools help up in two keeping track of what we shared. In particular it can 1) add the most *popular*<sup>1</sup> song to a Spotify playlist, and 2) add info about the album on a Google Sheet. 

# How to run
1) You need some credentials and stuff that you can fill in the `.credentials` file. You can find a template on the repository. Google authentication is instead placed in `.google-creds.json`, which is directly downloaded from the API dashboard. 
2) (Optional but reccomended) Create a virtual environment: `python3 -m venv venv` and activate it `source venv/bin/activate`
3) Install requirements `pip3 install -r requirements.txt`
4) Run the program: `python3 main.py`

Logs are saved in `log/main.log`. At the first run both Spotify and Google will ask for authentication. 
I usually run it inside a screen so I don't need to keep my terminal open.

# Possible improvements and issues
- I would love to automatically add the nationality of the artist in the google list, but it is not provided by the APIs.
- Adding the most *x* popular song for each album.
- You tell me!

---

<sup>1</sup>: popular in the obscure sense of Spotify, [since they are not willing to provide tracks plays via official APIs](https://community.spotify.com/t5/Spotify-for-Developers/Songs-Play-count/td-p/4992536), but for our scope it is more than enough.