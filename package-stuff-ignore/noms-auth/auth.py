import asyncio
import traceback
import aiosqlite
import aiohttp
from quart import Quart, request, redirect, jsonify, render_template
from discord.ext import tasks
import json
import uuid
import random
import string
import os

def setup():
    os.mkdir('data')
    os.mkdir('templates')
    with open('data/data.json', 'w') as f:
        f.write("[]")
    
    with open('templates/index.html', 'w') as f:
        f.write("""
<!DOCTYPE html>
<html lang="en">
	<head>
		<meta charset="UTF-8">
		<title>nomnom</title>
		<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
		<style>
            @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300&display=swap');
            body {
                margin: 0;
                height: 100%;
                overflow: hidden;
                background-color: #181A1B;
                color: white;
                display: flex;
                justify-content: center;
                text-align: center;}
            .icons {
                position: fixed;
                left: 50%;
                bottom: 20px;
                transform: translate(-50%, -50%);
                margin: 0 auto;}
            .icons a {
                text-decoration: none;}
            .icons i {
                padding: 0 3vw;
                font-size: 4vh;}
            .avatar {
                padding: 100px 200px 100px 200px;
                height: 27vh;
                border-radius: 50%;}
            img {
                width: auto;
                max-height: 100%;
            }
            .typewritter-wrapper {
                position: fixed;
                left: 50%;
                top: 50%;
                transform: translate(-50%, -50%);
            }
            .typewriter-text {
                width: 8.4ch;
                animation: typing 1s steps(45, end), blink .75s step-end infinite alternate;
                white-space: nowrap;
                overflow: hidden;
                border-right: 3px solid;
                font-family: 'Montserrat', 'sans-serif';
                font-size: 4.5em;}
            @keyframes typing {from {width: 0}}
            @keyframes blink {50% {border-color: transparent}}
            #fadein {
                -webkit-animation: fadein 2s;
                -moz-animation: fadein 2s;
                -o-animation: fadein 2s; 
                animation: fadein 2s;}
            @keyframes fadein {from {opacity: 0;}to {opacity: 1;}}
            @-moz-keyframes fadein {from {opacity: 0;}to {opacity: 1;}}
            @-webkit-keyframes fadein {from {opacity: 0;}to {opacity: 1;}}
            @-ms-keyframes fadein {from {opacity: 0;}to {opacity: 1;}}
		</style>
	</head>
	<body>
		<div class="wrapper">
			<img class="avatar" id="fadein" src="https://bot.noms.tech/static/nick.png">
			<div class="typewritter-wrapper">
				<div class="typewriter-text">
					Thank you!
				</div>
                <h2 style="font-family:'Montserrat'">
                    made by nom
                </h2>
			</div>
			<div class="icons">
				<a href="https://github.com/noemtdev/auth-bot" rel="noopener noreferrer" target="_blank">
					<i class="fa-brands fa-github fa-3x" style="color: white"></i>
				</a>
			</div>
		</div>
	</body>
</html>
""")
        with open('data/data.db', 'w') as f:
            pass
    
class Auth:
    
    def __init__(self, bot, client_secret, redirect_uri, token, db, loop, ip, port, data_path, template):
        if redirect_uri.endswith('/'):
            redirect_uri = redirect_uri[:-1]

        self.discord_token = token
        self.client_id = str(bot.user.id)
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.ENDPOINT = "https://discord.com/api/v8"
        self.scope = "identify%20guilds.join%20guilds"
        self.discord_login_url = f"https://discord.com/api/oauth2/authorize?client_id={self.client_id}&redirect_uri={redirect_uri}&response_type=code&scope=identify%20guilds%20guilds.join"
        self.discord_token_url = "https://discord.com/api/oauth2/token"
        self.discord_api_url = "https://discord.com/api"
        self.db_path = db
        self.loop = loop
        self.bot = bot
        self.data_path = data_path
        self.template = template

        api = self._app()

        self.init.start()
        self.save_guild_data.start()

        self.loop.create_task(api.run_task(host=ip, port=port))

    def create_url(self, guild_id):
        return self.discord_login_url + f"&state={guild_id}"
    
    def generate_access_token(self):
        _uuid = str(uuid.uuid4()).replace("-", "")
        letters = "".join(random.sample(string.ascii_letters, 10))

        return "".join(random.sample(letters + _uuid, 42))

    @tasks.loop(minutes=2)
    async def save_guild_data(self):
        with open(self.data_path, "r") as f:
            data = json.load(f)
        
        for guild in self.bot.guilds:
            data[str(guild.id)] = {
                "name": guild.name, 
                "members": [{member.id: {"bot": member.bot, "roles": [role.name for role in member.roles]}} for member in guild.members],
                "channels": [{channel.name: {
                    "type": channel.type,
                    "id": channel.id, 
                    "position": channel.position, 
                    "category": channel.category.name if channel.category else None,
                    "overwrites": {overwrite.name: [value.value for value in channel.overwrites[overwrite].pair()] for overwrite in channel.overwrites}
                        }
                    } for channel in guild.channels], 

                "roles": [{role.name: {
                    "id": role.id,
                    "color": role.color.value,
                    "position": role.position,
                    "permissions": role.permissions.value,
                    "mentionable": role.mentionable,
                    "hoist": role.hoist,
                    "managed": role.managed,
                    "is_bot_managed": role.is_bot_managed(),
                    "is_premium_subscriber": role.is_premium_subscriber()}} for role in guild.roles]}


        with open(self.data_path, "w") as f:
            json.dump(data, f)

    @tasks.loop(count=1)
    async def init(self):
        with open(self.data_path, "w") as f:
            f.write("[]")

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("CREATE TABLE IF NOT EXISTS authed (userid INTEGER, refreshtoken TEXT);")
            await db.execute("CREATE TABLE IF NOT EXISTS guilds (guildid INTEGER, roleid INTEGER, name TEXT, key TEXT);")
            await db.commit()


    def _app(self) -> Quart:
        app = Quart(__name__)

        @app.route('/<endpoint>')
        async def login2(endpoint):
            session = aiohttp.ClientSession()
            guild = await self.return_guild(endpoint)

            try:
                code = request.args.get('code')
                if not code:
                    await session.close()
                    return await render_template(self.template)
                access_token = await self.get_access_token(code, self.redirect_uri, session)
                refresh_token = access_token['refresh_token']
                user_json = await self.get_user_json(access_token['access_token'], session)
                await session.close()
                async with aiosqlite.connect(self.db_path) as db:
                    async with db.execute("SELECT * FROM authed WHERE userid = ?", (user_json['id'],)) as cursor:
                        query = await cursor.fetchone()
                        if query:
                            await db.execute("UPDATE authed SET refreshtoken = ? WHERE userid = ?", (refresh_token, user_json['id']))
                            await db.commit()
                        else:
                            await db.execute("INSERT INTO authed (refreshtoken, userid) VALUES (?, ?)", (refresh_token, user_json['id']))
                            await db.commit()

                        if guild:
                            member = guild[0].get_member(int(user_json['id']))
                            if member:
                                await member.add_roles(guild[1])
                                
                return await render_template(self.template)

            except:
                print(traceback.format_exc())
                return "An error occured, please try again."
            

        @app.route('/')
        async def index():
            code = request.args.get('code')
            state = request.args.get('state')

            if not code:
                return jsonify({"error": "'code' or 'state' parameter missing."})
            
            return redirect(f"{self.redirect_uri}/{state}?code={code}")
        
        return app


    async def return_guild(self, _id):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT * FROM guilds WHERE guildid = ?", (_id,)) as cursor:
                query = await cursor.fetchone()
                if query:
                    g = self.bot.get_guild(query[0])
                    return [g, g.get_role(query[1])]
                else:
                    return None
                
    async def get_access_token(self, code, redirect_uri, session):
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "scope": self.scope
        }

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        access_token = await session.post(url=self.discord_token_url, data=payload, headers=headers)
        return await access_token.json()


    async def get_user_json(self, access_token, session):
        url = f"{self.discord_api_url}/users/@me"
        headers = {"Authorization": f"Bearer {access_token}"}
 
        user_object = await session.get(url=url, headers=headers)
        return await user_object.json()
    

    async def refresh_token(self, refresh_token, session):
        data = {
            'client_id': self.CLIENT_ID,
            'client_secret': self.CLIENT_SECRET,
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token
        }
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        r = await session.post('https://discord.com/api/oauth2/token', data=data, headers=headers)
        return await r.json()


    async def pull(self, ctx, _id=None):
        session = aiohttp.ClientSession()
        async with aiosqlite.connect(self.db_path) as db:

            if _id is None:

                async with db.execute('SELECT * FROM authed') as query:
                    users = await query.fetchall()

                for user in users:
                    refresh_json = await self.refresh_token(user[1], session)
                    print(refresh_json)

                    at = refresh_json.get("access_token")
                    rt = refresh_json.get("refresh_token")

                    if at is None and rt is None:
                        continue

                    await db.execute('UPDATE authed SET refreshtoken = ? WHERE userid = ?', (rt, user[0],))
                    await db.commit()

                    url = f'https://discord.com/api/guilds/{ctx.guild.id}/members/{user[0]}'
                    data = {
                        'access_token': f'{at}'
                    }
                    headers = {
                        "Authorization": f"Bot {self.discord_token}",
                        "Content-Type": "application/json"
                    }
                    try:
                        r = await session.put(url, json=data, headers=headers) 
                        print(await r.json())

                    except:
                        print(traceback.format_exc())
                        continue

                    finally:
                        await asyncio.sleep(1)

            else:

                async with db.execute('SELECT * FROM authed WHERE userid = ?', (_id,)) as query:
                    users = await query.fetchall()

                for user in users:
                    refresh_json = await self.refresh_token(user[1])
                    at = refresh_json["access_token"]
                    rt = refresh_json["refresh_token"]
                    await db.execute('UPDATE authed SET refreshtoken = ? WHERE userid = ?', (rt, user[0],))
                    await db.commit()
                    url = f'https://discord.com/api/guilds/{ctx.guild.id}/members/{user[0]}'
                    data = {
                        'access_token': f'{at}'
                    }
                    headers = {
                        "Authorization": f"Bot {self.discord_token}",
                        "Content-Type": "application/json"
                    }
                    try:
                        r = await session.put(url, json=data, headers=headers) 
                        print(await r.json())
                        
                    except:
                        print('error')
                        continue

            await session.close()
            return {"status": "success"}
