import os
import unittest
import tempfile
import main
import json
import collections
import random

class MainTestCase(unittest.TestCase):

    def setUp(self):
        main.app.config['TESTING'] = True
        self.app = main.app.test_client()

    def create_game(self):
        return self.app.get('/create', follow_redirects=True)

    def join_game(self, gameid):
        return self.app.get(gameid + '/join', follow_redirects=True)

    def join_game_w_name(self, gameid, nickname):
        return self.app.get(gameid + '/join/' + nickname, follow_redirects=True)

    def start_game(self, gameid):
        return self.app.get(gameid + '/start', follow_redirects=True)

    def set_card(self, gameid, stocknum):
        return self.app.get(gameid + '/set/' + str(stocknum), follow_redirects=True)

    def next(self, gameid):
        return self.app.get(gameid + '/next', follow_redirects=True)

    def nominate_detective(self, gameid, playerid):
        return self.app.get(gameid + '/nominate/detective/' + playerid, follow_redirects=True)

    def nominate_dog(self, gameid, playerid, cardnum):
        return self.app.get(gameid + '/nominate/dog/' + playerid + '/' + str(cardnum), follow_redirects=True)

    def show_criminal(self, gameid):
        return self.app.get(gameid + '/show_criminal', follow_redirects=True)



    def test_all_scenario(self):
        random.seed(2)

        players = []

        ###########################################################
        # Create Game
        rv = self.create_game()
        assert '' != rv.get_data()
        gameid = str(rv.get_data().decode())
        # print(gameid)
        players.append(gameid)

        ###########################################################
        # Join Game
        for i in range(7):
            if i == 1:
                rv = self.join_game_w_name(gameid, '太郎')
                data = json.loads(rv.get_data())
                assert data['nickname'] != data['playerid'] and data['nickname'] == '太郎'
            else:
                rv = self.join_game(gameid)
                data = json.loads(rv.get_data())
                assert data['nickname'] == data['playerid']

        ###########################################################
        # Start Game
        print('# Start #############################')

        rv = self.start_game(gameid)
        data = json.loads(rv.get_data())
        # print(data)

        print(data)
        for player in data['players']:
            assert 4 == len(player['stocks'])

        print('#####################################')
        print(data['players'][0])

        # Set the card
        rv = self.set_card(gameid, 2)
        data = json.loads(rv.get_data())
        print(data['stack'])
        print(data['players'][0])

        rv = self.next(gameid)
        data = json.loads(rv.get_data())

        ###########################################################
        # Next player
        print('#- NEXT -############################')
        print(data['players'][0])

        # Set the card
        rv = self.set_card(gameid, 0)
        assert b'ng' == rv.get_data()

        # Set the card
        rv = self.set_card(gameid, 2)
        data = json.loads(rv.get_data())
        print(data['stack'])
        print(data['players'][0])

        # no criminal player
        criminal_playerid = data['players'][2]['playerid']

        rv = self.nominate_detective(gameid, criminal_playerid)
        data = json.loads(rv.get_data())
        assert 'starting' == data['status']

        # it's criminal player but there is alibi
        criminal_playerid = data['players'][1]['playerid']

        rv = self.nominate_detective(gameid, criminal_playerid)
        data = json.loads(rv.get_data())
        assert 'starting' == data['status']

        # it's criminal card
        criminal_playerid = data['players'][1]['playerid']

        rv = self.nominate_dog(gameid, criminal_playerid, 1)
        data = json.loads(rv.get_data())
        assert 'end' == data['status']

        # it's not criminal card
        criminal_playerid = data['players'][1]['playerid']

        rv = self.nominate_dog(gameid, criminal_playerid, 0)
        data = json.loads(rv.get_data())
        assert 'starting' == data['status']

        rv = self.next(gameid)
        data = json.loads(rv.get_data())

        ###########################################################
        # Next player 犯人のターン
        print('#- NEXT -############################')
        print(data['players'][0])

        # Set the card
        rv = self.set_card(gameid, 2) # アリバイ
        data = json.loads(rv.get_data())

        rv = self.next(gameid)
        data = json.loads(rv.get_data())

        ###########################################################
        # Next player
        print('#- NEXT -############################')
        print(data['players'][0])

        # it's criminal player but there is alibi
        criminal_playerid = data['players'][-1]['playerid']

        rv = self.nominate_detective(gameid, criminal_playerid)
        data = json.loads(rv.get_data())
        assert 'end' == data['status']

        rv = self.show_criminal(gameid)
        data = json.loads(rv.get_data())
        print('#- who is criminal -#################')
        print(data)

# うわさ
# 情報操作
# 取り引き



if __name__ == '__main__':
    unittest.main()
