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



    def test_all_scenario(self):
        random.seed(1)

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
        print('#####################################')

        rv = self.start_game(gameid)
        data = json.loads(rv.get_data())
        # print(data)

        for player in data['players']:
            assert 4 == len(player['stocks'])

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
        print('#####################################')
        print(data['players'][0])

        # Set the card
        rv = self.set_card(gameid, 2)
        data = json.loads(rv.get_data())
        print(data['stack'])
        print(data['players'][0])

        rv = self.next(gameid)
        data = json.loads(rv.get_data())

if __name__ == '__main__':
    unittest.main()
