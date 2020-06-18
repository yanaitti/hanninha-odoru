from flask import Flask, Response, render_template
from flask_caching import Cache
import uuid
import random
import collections
import json
import os
import copy
import numpy as np
from flask_bootstrap import Bootstrap

app = Flask(__name__)
bootstrap = Bootstrap(app)


# Cacheインスタンスの作成
cache = Cache(app, config={
    'CACHE_TYPE': 'redis',
    'CACHE_REDIS_URL': os.environ.get('REDIS_URL', 'redis://localhost:6379'),
    'CACHE_DEFAULT_TIMEOUT': 60 * 60 * 2,
})


'''
第三版
カードは12種類
最初に4枚ずつ配る

勝利条件
１．「探偵カード」で犯人を当てる
２．「犬カード」で「犯人カード」を当てる
３．犯人が「犯人カード」を出す

手番でやることはカードを1枚ずつ出していく
「第一発見者」を持っている人から始める

「犯人」：
最後の１枚の場合に場に出せる。出すと勝ち

「アリバイ」：
出しても効果はないが、持っていると「犯人ではない」ということができる

「たくらみ」：
犯人の勝利条件と同じになる

「探偵」：
犯人を指名できます

「いぬ」：
犯人カードを持っていそうな人を指名し、犯人カードを当てたら勝ち

「少年」：
誰が「犯人」カードを持っているか知ることができる

「うわさ」：
全員が右隣からカードを１枚引く

「情報操作」：
全員が左側に１枚渡す

「取り引き」：
誰かと１枚交換する

「一般人」：
何もなし

「第一発見者」：
スタートプレイヤー

「目撃者」：
指名したプレイヤーの手札をすべて見ることができる

'''

mastercards = [
    {'name': '第一発見者', 'type': 0, 'stock': 1, 'status': 'started'},
    {'name': '犯人', 'type': 1, 'stock': 1, 'status': 'end'},
    {'name': '探偵', 'type': 2, 'stock': 4, 'status': 'detective'},
    {'name': 'アリバイ', 'type': 3, 'stock': 5, 'status': 'started'},
    {'name': 'たくらみ', 'type': 4, 'stock': 2, 'status': 'scheme'},

    {'name': 'いぬ', 'type': 5, 'stock': 1, 'status': 'dog'},
    {'name': 'うわさ', 'type': 6, 'stock': 4, 'status': 'rumor'},
    {'name': '情報操作', 'type': 7, 'stock': 3, 'status': 'manipulation'},
    {'name': '取り引き', 'type': 8, 'stock': 5, 'status': 'deal'},
    {'name': '一般人', 'type': 9, 'stock': 2, 'status': 'started'},
    {'name': '目撃者', 'type': 10, 'stock': 3, 'status': 'witness'},
    {'name': '少年', 'type': 11, 'stock': 1, 'status': 'boy'},
]

pattern = [
    [0, 1, 2, 3],
    [0, 1, 2, 3, 4],
    [0, 1, 2, 3, 3, 4],
    [0, 1, 2, 2, 3, 3, 4, 4],
    [0, 1, 2, 2, 3, 3, 3, 4, 4],
    [],
]

@app.route('/')
def homepage():
    return render_template('index.html')


# create the game group
@app.route('/create')
@app.route('/create/<nickname>')
def create_game(nickname=''):
    game = {
        'status': 'waiting',
        'stack': [],
        'trade': [],
        'players': []}
    player = {}

    gameid = str(uuid.uuid4())
    game['gameid'] = gameid
    player['playerid'] = gameid
    player['criminal'] = False
    player['stocks'] = []
    player['nickname'] = nickname if nickname != '' else gameid
    game['players'].append(player)

    app.logger.debug(gameid)
    app.logger.debug(game)
    cache.set(gameid, game)
    return gameid


# join the game
@app.route('/<gameid>/join')
@app.route('/<gameid>/join/<nickname>')
def join_game(gameid, nickname='default'):
    game = cache.get(gameid)
    if game['status'] == 'waiting':
        player = {}

        playerid = str(uuid.uuid4())
        player['playerid'] = playerid
        player['criminal'] = False
        player['stocks'] = []
        if nickname == 'default':
            player['nickname'] = playerid
        else:
            player['nickname'] = nickname

        game['players'].append(player)

        cache.set(gameid, game)

        return json.dumps(player)
    else:
        return 'Already started'


# start the game
@app.route('/<gameid>/start')
def start_game(gameid):
    game = cache.get(gameid)
    app.logger.debug(gameid)
    app.logger.debug(game)
    game['status'] = 'started'
    game['stack'] = []
    game['trade'] = []

    # initial card setting
    stocks = []
    tmp = []
    player_count = len(game['players'])
    pattern_panel = pattern[player_count - 3]

    for mastercard in mastercards:
        for card in range(mastercard['stock']):
            tmp.append(mastercard)

    random.shuffle(tmp)

    for idx in range(player_count * 4):
        if len(pattern_panel) > idx:
            idd = [cIdx for cIdx, card in enumerate(tmp) if card['type'] == pattern_panel[idx]][0]
            stocks.append(tmp.pop(idd))
        else:
            stocks.append(tmp.pop(0))

    random.shuffle(stocks)

    for player in game['players']:
        player['criminal'] = False
        player['stocks'] = []
        for idx in range(4):
            player['stocks'].append(stocks.pop(0))

    random.shuffle(game['players'])

    while len([card for card in game['players'][0]['stocks'] if card['type'] == 0]) == 0:
        game['players'] = np.roll(np.array(game['players']), -1).tolist()

    cache.set(gameid, game)
    return json.dumps(game)


# set the card
@app.route('/<gameid>/set/<int:stocknum>')
def set_card(gameid, stocknum):
    game = cache.get(gameid)

    if game['players'][0]['stocks'][stocknum]['type'] == 1:
        # 「犯人カード」は、最後の一枚の時にしか出せない
        if len(game['players'][0]['stocks']) > 1:
            return 'ng'
    elif game['players'][0]['stocks'][stocknum]['type'] == 2:
        # 「探偵カード」は、2ターン目から出せる
        if len(game['stack']) / len(game['players']) < 1:
            return 'ng'
    elif game['players'][0]['stocks'][stocknum]['type'] == 4:
        # 「たくらみカード」の場合、犯人と同じ側になる
        game['players'][0]['criminal'] = True
    elif game['players'][0]['stocks'][stocknum]['type'] in [6, 7]:
        # うわさ
        # 情報操作
        senders = [player['playerid'] for player in game['players']]
        receivers = np.roll(np.array(senders), -1).tolist()

        for idx in range(len(game['players'])):
            trade = {'sender': senders[idx], 'receiver': receivers[idx], 'card': None }
            game['trade'].append(trade)

    elif game['players'][0]['stocks'][stocknum]['type'] == 8:
        # 取り引き
        trade = {'sender': game['players'][0]['playerid'], 'receiver': None, 'card': None }
        game['trade'].append(trade)

    set_card = game['players'][0]['stocks'].pop(stocknum)

    game['stack'].append(set_card)
    game['status'] = set_card['status']

    cache.set(gameid, game)
    return json.dumps(game)


# nominate(detective)
@app.route('/<gameid>/nominate/detective/<playerid>')
def nominate_detective(gameid, playerid):
    game = cache.get(gameid)
    game['status'] = 'started'

    _stocks = [_player['stocks'] for _player in game['players'] if _player['playerid'] == playerid][0]
    _criminal = True if len([_card for _card in _stocks if _card['type'] == 1]) == 1 else False
    if _criminal == True:
        if len([_card for _card in _stocks if _card['type'] == 3]) < 1:
            game['status'] = 'end'

    cache.set(gameid, game)
    return json.dumps(game)


# nominate(dog)
@app.route('/<gameid>/nominate/dog/<playerid>/<int:cardnum>')
def nominate_dog(gameid, playerid, cardnum):
    game = cache.get(gameid)
    game['status'] = 'started'

    _stocks = [_player['stocks'] for _player in game['players'] if _player['playerid'] == playerid][0]
    _criminal = True if _stocks[cardnum]['type'] == 1 else False
    if _criminal == True:
        game['status'] = 'end'

    cache.set(gameid, game)
    return json.dumps(game)


# show criminal
@app.route('/<gameid>/show_criminal')
def show_criminal(gameid):
    game = cache.get(gameid)

    criminal = [_player for _player in game['players'] if len([_card for _card in _player['stocks'] if _card['type'] == 1]) > 0]

    return json.dumps(criminal)


# show other player card
@app.route('/<gameid>/show_others/<playerid>')
def show_others(gameid, playerid):
    game = cache.get(gameid)

    player = [_player for _player in game['players'] if _player['playerid'] == playerid][0]

    return json.dumps(player)


# trade card setting with player
@app.route('/<gameid>/trade/player/<get_playerid>/<int:card_num>')
def trade_card_w_player(gameid, get_playerid, card_num):
    game = cache.get(gameid)

    trades = game['trade']
    trades[0]['receiver'] = get_playerid
    trades[0]['card'] = game['players'][0]['stocks'].pop(card_num)

    trade = {'sender': get_playerid, 'receiver': game['players'][0]['playerid'], 'card': None}
    trades.append(trade)

    cache.set(gameid, game)
    return json.dumps(trades)


# trade card setting
@app.route('/<gameid>/trade/<playerid>/card/<int:card_num>')
def trade_card(gameid, playerid, card_num):
    game = cache.get(gameid)

    if game['status'] in ['deal', 'manipulation']:
        trade = [trade for trade in game['trade'] if trade['sender'] == playerid][0]
    elif game['status'] == 'rumor':
        trade = [trade for trade in game['trade'] if trade['receiver'] == playerid][0]

    player_stocks = [player['stocks'] for player in game['players'] if player['playerid'] == trade['sender']][0]
    trade['card'] = player_stocks.pop(card_num)

    cache.set(gameid, game)
    return json.dumps(game['trade'])


# next to player
@app.route('/<gameid>/next')
def next_player(gameid):
    game = cache.get(gameid)

    game['players'] = np.roll(np.array(game['players']), -1).tolist()

    for trade in game['trade']:
        player = [player for player in game['players'] if player['playerid'] == trade['receiver']][0]
        player['stocks'].append(trade['card'])

    game['trade'] = []
    game['status'] = 'started'

    cache.set(gameid, game)
    return json.dumps(game)


# all status the game
@app.route('/<gameid>/status')
def game_status(gameid):
    game = cache.get(gameid)

    return json.dumps(game)


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
    # app.run(debug=True)
