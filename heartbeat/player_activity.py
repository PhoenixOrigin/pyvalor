import asyncio
import aiohttp
from db import Connection
from network import Async
from .task import Task
import time
import datetime

class PlayerActivityTask(Task):
    def __init__(self, sleep):
        super().__init__(sleep)
        
    def stop(self):
        self.finished = True
        self.continuous_task.cancel()

    def run(self):
        self.finished = False
        async def player_activity_task():
            print(datetime.datetime.now().ctime(), "PLAYER ACTIVITY TRACK START")
            start = time.time()
            URL = "https://api.wynncraft.com/public_api.php?action=guildStats&command="
            online_all = await Async.get("https://api.wynncraft.com/public_api.php?action=onlinePlayers")
            online_all = {y for x in online_all for y in online_all[x] if not "request" in x}

            inserts = []
            member_cache_refresh = []

            guilds = {g[0] for g in Connection.execute("SELECT * FROM guild_list")}

            for guild in guilds:
                g = await Async.get(URL+guild)
                try:
                    members = {x["name"]: x["uuid"] for x in g["members"] if "name" in x}
                except:
                    print(guild, "does not exist?")
                    continue
                for name in members:
                    member_cache_refresh.append((guild, name))
                    if name in online_all:
                        rank = g["members"][name]["rank"]
                        inserts.append(f"(\"{name}\", \"{guild}\", {int(time.time())}, \"{members[name]}\", \"{rank}\")")

            Connection.execute(f"INSERT INTO activity_members VALUES {','.join(inserts)}")

            # clear the cache
            Connection.execute(f"DELETE FROM guild_member_cache")
            Connection.execute(f"INSERT INTO guild_member_cache VALUES "+ ','.join(f"(\"{x[0]}\", \"{x[1]}\")" for x in member_cache_refresh))

            end = time.time()
            print(datetime.datetime.now().ctime(), "PLAYER ACTIVITY TASK", end-start, "s")
            
            await asyncio.sleep(self.sleep)

        self.continuous_task = asyncio.get_event_loop().create_task(self.continuously(player_activity_task))
        