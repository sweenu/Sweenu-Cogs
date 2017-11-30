from pathlib import Path

import aiohttp
from aiohttp.web_exceptions import HTTPClientError, HTTPServerError
from discord.ext import commands


dir_root_path = Path(__file__).resolve().parent.parent
with open(dir_root_path / 'api_key') as f:
    api_key = f.read()


class League:
    """Cog that can fetch different information about League of Legends."""

    def __init__(self, bot, platform):
        self.bot = bot
        self.url = "https://{}.api.riotgames.com".format(platform)

    async def _fetch_url(self, path) -> dict:
        """Fetch info from League of Legends api."""
        url = '{}/{}?api_key={}'.format(self.url, path, api_key)
        async with aiohttp.get(url) as r:
            if r.status_code == 404:
                raise HTTPClientError()
            if int(r.status_code / 100) == 5:
                self.bot.say('A server error as occured, '
                             'please try again later')
                raise HTTPServerError
            else:
                return await r.json()

    def _get_summoner(self, summonerName):
        path = '/lol/summoner/v3/summoners/by-name/'
        try:
            return self._fetch_url(path + summonerName)
        except HTTPClientError as e:
            self.bot.say('Oops, are you sure this is a valid summoner name?')
            raise e

    def _get_activeGame(self, summonerId):
        path = '/lol/spectator/v3/active-games/by-summoner/'
        try:
            return self._fetch_url(path + str(summonerId))
        except HTTPClientError as e:
            self.bot.say('Oops, are you sure the summoner '
                         'is currently in game?')
            raise e

    def _get_position(self, summonerId):
        path = '/lol/league/v3/positions/by-summoner/'
        response = self._fetch_url(path + str(summonerId))
        if response:
            return response
        else:
            self.bot.say("Oops, are you sure the summoner is ranked?")
            raise RuntimeError

    def _get_champion(self, championId):
        path = '/lol/static-data/v3/champions/'
        return self._fetch_url(path + str(championId))

    def _get_maps(self):
        path = '/lol/static-data/v3/maps'
        return self._fetch_url(path)

    @commands.command()
    async def gameinfo(self, summonerName):
        """Fetch info about the currently active game of a summoner."""
        try:
            summoner = await self._get_summoner(summonerName)
            active_game = await self._get_activeGame(summoner['id'])
            maps = await self._get_maps()
        except (HTTPClientError, HTTPServerError):
            return

        for m in maps['data'].values():
            if m['mapId'] == active_game['mapId']:
                map_name = m['mapName']
                break

        # list of participants in the form:
        # (Summoner name, Champion, Rank solo, Rank flex)
        team1 = []
        team2 = []
        id_team1 = active_game['participants'][0]['teamId']
        for p in active_game['participants']:
            try:
                league = self._get_position(p['summonerId'])
                champion = self._get_champion(p['championId'])['name']
            except (HTTPClientError, HTTPServerError, RuntimeError):
                return

            for queue in league:
                if queue['queueType'] == 'RANKED_SOLO_5x5':
                    rank_solo = "{} {}".format(queue['tier'], queue['rank'])
                elif queue['queueType'] == 'RANKED_FLEX_SR':
                    rank_flex = "{} {}".format(queue['tier'], queue['rank'])

            info = p['summonerName'], champion, rank_solo, rank_flex
            if p['teamId'] == id_team1:
                team1.append(info)
            else:
                team2.append(info)

        table_format = '{0:16} {1:12} {2:14} {3:14}'
        unformatted_header = table_format + ' | ' + table_format + '\n'
        header = unformatted_header.format('Name', 'Champion', 'Solo', 'Flex')
        header += '-' * 120 + '\n'

        player_list = ''
        for i in range(len(team1)):
            player_list += table_format.format(*team1[i]) + ' | '
            player_list += table_format.format(*team2[i]) + ' \n '

        final_output = ('```'
                        '**{map_name}**\n'
                        '*{game_mode}*\n\n'
                        '{header}'
                        '{player_list}'
                        '```').format(map_name=map_name,
                                      game_mode=active_game['gameMode'],
                                      header=header,
                                      player_list=player_list)

        await self.bot.say(final_output)


def setup(bot):
    bot.add_cog(League(bot, 'euw1'))
