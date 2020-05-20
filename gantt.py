import json
import requests
import logging
import plotly.figure_factory as ff
import collections
import random
import configparser

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.figure_factory as ff
import numpy as np

Card = collections.namedtuple('Card', 'task board list')

config = configparser.ConfigParser()
config.read('trello.ini')

trello = 'https://api.trello.com'
key = config['api']['key']
token = config['api']['token']

def get_intelligentsia_board():
    request = '{url}/1/members/me/boards?key={key}&token={token}'.format(url=trello, key=key, token=token)
    response = requests.get(url=request)
    try:
        raw = response.json()
        for board in raw:
            if board['name'] == 'Intelligentsia':
                return board
    except:
        logging.error('Failed to parse JSON, request most likely invalid')
    return None

def get_board(id):
    request = '{url}/1/boards/{board}?key={key}&token={token}'.format(url=trello, board=id, key=key, token=token)
    response = requests.get(url=request)
    raw = None
    try:
        raw = response.json()
    except:
        logging.error('Failed to parse JSON, request most likely invalid')
    return raw

def get_all_cards(id):
    request = '{url}/1/boards/{board}/cards?key={key}&token={token}'.format(url=trello, board=id, key=key, token=token)
    response = requests.get(url=request)
    raw = None
    try:
        raw = response.json()
    except:
        logging.error('Failed to parse JSON, request most likely invalid')
    return raw

def get_list(id):
    request = '{url}/1/lists/{list}?key={key}&token={token}'.format(url=trello, list=id, key=key, token=token)
    response = requests.get(url=request)
    raw = None
    try:
        raw = response.json()
    except:
        logging.error('Failed to parse JSON, request most likely invalid')
    return raw

def get_all_attachments(id):
    request = '{url}/1/cards/{card}/attachments?key={key}&token={token}'.format(url=trello, card=id, key=key, token=token)
    response = requests.get(url=request)
    raw = None
    try:
        raw = response.json()
    except:
        logging.error('Failed to parse JSON, request most likely invalid')
    return raw

def get_custom_field_items(id):
    request = '{url}/1/cards/{card}/customFieldItems?key={key}&token={token}'.format(url=trello, card=id, key=key, token=token)
    response = requests.get(url=request)
    raw = None
    try:
        raw = response.json()
    except:
        logging.error('Failed to parse JSON, request most likely invalid')
    return raw

def get_custom_fields(id):
    request = '{url}/1/boards/{board}/customFields?key={key}&token={token}'.format(url=trello, board=id, key=key, token=token)
    response = requests.get(url=request)
    raw = None
    try:
        raw = response.json()
    except:
        logging.error('Failed to parse JSON, request most likely invalid')
    return raw

def delete_attachment(card, id):
    request = '{url}/1/cards/{card}/attachments/{attachment}?key={key}&token={token}'.format(url=trello, card=card, attachment=id, key=key, token=token)
    response = requests.request(method='DELETE', url=request)
    raw = None
    try:
        raw = response.json()
    except:
        logging.error('Failed to parse JSON, request most likely invalid')
    return raw

# game_board = get_intelligentsia_board()
# if game_board:
#     game_board_id = game_board['id']
#
#     cards = get_all_cards(game_board_id)
#     custom_fields = get_custom_fields(game_board_id)
#     definitions = {}
#     for field in custom_fields:
#         definitions[field['id']] = field['name']
#
#     for card in cards:
#         fields = get_custom_field_items(card['id'])
#         for field in fields:
#             if field['idCustomField'] in definitions:
#                 print('{name} - {value}'.format(name=definitions[field['idCustomField']], value=field['value']))

        # attachments = get_all_attachments(card['id'])
        # for attachment in attachments:
        #     delete_attachment(card['id'], attachment['id'])
        # print('{card} - {id}'.format(card=card['name'].ljust(50, ' '), id=card['id']))


# def remove_all_attachments(id):
#     board =
#
# boards = {}
# lists = {}
# cards = []
# with open('D:\\gravelit\\Downloads\\game.json') as file:
#     data = json.load(file)
#
#     for card in data['cards']:
#         # Card - The task name
#         cardName = card['name']
#         print(card['name'])
#
#         # Start Date
#
#         # Estimated Time - Used for end date
#
#         # Board - extra information
#         boardName = ''
#         if not card['idBoard'] in boards:
#             boardData = get_board(card['idBoard'])
#             if boardData:
#                 boards[card['idBoard']] = boardData['name']
#                 boardName = boardData['name']
#         else:
#             boardName = boards[card['idBoard']]
#
#         # List - Used to group cards
#         listName = ''
#         if not card['idList'] in lists:
#             listData = get_list(card['idList'])
#             if listData:
#                 lists[card['idList']] = listData['name']
#                 listName = listData['name']
#         else:
#             listName = lists[card['idList']]
#
#         # Checklist/Labels - Used for Percentage
#
#         cards.append(Card(task=cardName, board=boardName, list=listName))
#
# print('\n')
# print(boards)
# print('\n')
# print(lists)
#
# # df = []
# # for card in cards:
# #     df.append(dict(Task=card.task, Start='2020-05-15', Finish='2020-05-29', Resource=card.list))
# #
# # colors = []
# # r = lambda: random.randint(0, 255)
# # for i in range(0,110):
# #     color = ('#%02X%02X%02X' % (r(), r(), r()))
# #     colors.append(color)
# #
#
df = [dict(Task="Job A", Start='2009-01-01', Finish='2009-02-01', Resource='Apple', Percent=0.5),
      dict(Task="Job B", Start='2009-03-05', Finish='2009-04-15', Resource='Grape', Percent=0.1),
      dict(Task="Job C", Start='2009-04-20', Finish='2009-09-30', Resource='Banana', Percent=0.8)]

colors = ['rgb(255, 79, 79)', 'rgb(74, 255, 140)', 'rgb(249, 255, 74)']

fig = ff.create_gantt(df, percent=True, colors=colors, index_col='Resource', reverse_colors=True,
                      show_colorbar=True)

fig.update_traces(textposition='top center')

fig.add_annotation(x=0.0,
            y=-0.15,
            showarrow=False,
            text="Custom x-axis title <br> with more text",
            font=dict(
                family="Courier New, monospace",
                size=16,
                color="#000000"
            ),
            xref="paper",
            yref="paper")

fig.update_layout(title_text='GDP and Life Expectancy (Americas, 2007)<br>')



#textfont_size=14

fig.show()

# # fig = ff.create_gantt(df, colors=colors, index_col='Resource', reverse_colors=True,
# #                       show_colorbar=True, bar_width=0.1, height=(20 * len(cards)))
# # fig.show()

x = 5
x = x + 1
