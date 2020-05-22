# additional features:
# print card ids, with option to print by list
# move dates by X amount
# update due dates
# use cached?
#
# analyze for same card names
#

# ----------------------------------------------------------------------------------
# Imports
# ----------------------------------------------------------------------------------
import json
import requests

import plotly.figure_factory as ff
import collections
import trello_api
import copy
import random
import configparser
import datetime
from datetime import datetime as date
from datetime import timedelta

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.figure_factory as ff
from plotly.subplots import make_subplots
import numpy as np
import re

# ----------------------------------------------------------------------------------
# Types
# ----------------------------------------------------------------------------------
card_template = {
    'id' : None,
    'task' : '',
    'list' : '',
    'description' : '',
    'start' : { 'date' : '1970-01-01T00:00:00.000Z' },
    'end' : { 'date' : None },
    'estimated' : { 'number' : 1 },
    'blocked' : { 'text' : None },
    'percent' : 0.0
}

class DictParser(configparser.ConfigParser):
    def optionxform(self, optionstr):
        return optionstr

    def as_dict(self):
        d = dict(self._sections)
        for k in d:
            d[k] = dict(self._defaults, **d[k])
            d[k].pop('__name__', None)
        return d

# ----------------------------------------------------------------------------------
# Globals
# ----------------------------------------------------------------------------------
new_cards = []

# ----------------------------------------------------------------------------------
# Functions
# ----------------------------------------------------------------------------------
def update_dates(card):
    if not card['blocked']['text']:
        start = date.strptime(card['start']['date'], '%Y-%m-%d')
    else:
        blocking_card = find_card_by_id(card['blocked']['text'])
        if blocking_card:
            if not blocking_card['end']['date']:
                update_dates(blocking_card)
            start = date.strptime(blocking_card['end']['date'], '%Y-%m-%d')
            card['start']['date'] = start.strftime('%Y-%m-%d')
        else:
            log('Could not find blocking card')
            start = date.strptime(card['start']['date'], '%Y-%m-%d')

    card['end']['date'] = (start + timedelta(days=card['estimated']['number'])).strftime('%Y-%m-%d')
    card['end']['date'] = account_for_weekends(card['start']['date'], card['end']['date'])


def find_card_by_id(id):
    for card in new_cards:
        if card['id'] == id:
            return card
    return None


def start_date_remove_time(card):
    start = date.strptime(card['start']['date'], '%Y-%m-%dT%H:%M:%S.%fZ')
    return start.strftime('%Y-%m-%d')


def account_for_weekends(start, end):
    SATURDAY = 5
    SUNDAY = 6
    s = date.strptime(start, '%Y-%m-%d')
    e = date.strptime(end, '%Y-%m-%d')
    delta = e - s
    weekend_count = 0
    for single_date in (s + timedelta(n) for n in range(delta.days + 1)):
        if single_date.weekday() == SATURDAY or single_date.weekday() == SUNDAY:
            weekend_count += 1
    weekend_count += (weekend_count % 2)
    # print(weekend_count)
    e = e + timedelta(weekend_count)
    return (e.strftime('%Y-%m-%d'))


def sanitize_blocked(string):
    if string:
        hash_p = re.compile('[0-9a-zA-Z]{24}')
        match = re.match(hash_p, string)
        if match:
            return string
        else:
            for card in new_cards:
                if card['task'] == string:
                    return card['id']
    return None


def log(info):
    print(info)


# ----------------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------------
# Configuration
config = DictParser()
config.read('project.ini')
project = config['project']['name']
list_colors = config.as_dict()['listColors']

# # Initialize the API, and grab the project board
# log('Requesting project board...')
# api = trello_api.TrelloAPI()
# project_board = api.get_board_with_name(project)
#
# # Only start processing if the request was a success
# if project_board:
#     project_board_id = project_board['id']
#
#     # Initialize variables for other data we are looking for
#     project_total_tasks = 0
#     project_total_complete_tasks = 0
#
#     # Get the custom field definitions for this board
#     log('Generating custom field definitions...')
#     values = api.get_custom_fields(project_board_id)
#     custom_fields = {}
#     for value in values:
#         custom_fields[value['id']] = value['name']
#
#     # Get the label definitions for this board
#     # values = api.get_boards_labels(project_board_id)
#     # labels = {}
#     # for value in values:
#     #     labels[value['id']] = value['name'].lower()
#
#     # Cached values to prevent calling the API constantly
#     lists = {}
#
#     # ------------------------------------------------------------------------------
#     # Grab the cards for the board
#     cards = api.get_all_cards(project_board_id)
#     log('Total cards: {}'.format(len(cards)))
#     log('\nBeginning card processing...')
#     cards_processed = 0
#     for card in cards:
#         new_card = copy.deepcopy(card_template)
#
#         # Save the card ID
#         new_card['id'] = card_id = card['id']
#
#         # Save the task name
#         new_card['task'] = card['name']
#
#         # Store the custom field data
#         items = api.get_custom_field_items(card_id)
#         for item in items:
#             if item['idCustomField'] in custom_fields:
#                 field = custom_fields[item['idCustomField']].lower()
#                 new_card[field] = item['value']
#                 # print('{name} - {value}'.format(name=field, value=new_card[field]))
#
#         # Sanitize custom fields
#         new_card['start']['date'] = start_date_remove_time(new_card)
#         new_card['estimated']['number'] = int(new_card['estimated']['number'])
#
#         # List name
#         if not card['idList'] in lists:
#             listData = api.get_list(card['idList'])
#             if listData:
#                 lists[card['idList']] = listData['name']
#                 new_card['list'] = listData['name']
#         else:
#             new_card['list'] = lists[card['idList']]
#
#         # Check if this card is marked complete
#         total_items = 1
#         completed_items = 0
#         if card['dueComplete']:
#             completed_items = 1
#
#         # if the complete label wasn't on the card, check how far along we are with the checklist
#         if not completed_items:
#             checklists = api.get_card_checklists(card_id)
#             for checklist in checklists:
#                 total_items = len(checklist['checkItems'])
#                 for item in checklist['checkItems']:
#                     if item['state'] == 'complete':
#                         completed_items += 1
#         if total_items:
#             new_card['percent'] = round(float(completed_items / total_items), 1)
#
#         # Update project totals
#         project_total_tasks += total_items
#         project_total_complete_tasks += completed_items
#
#         # Add card to list
#         new_cards.append(new_card)
#
#         # Logging info
#         cards_processed += 1
#         if cards_processed % 10 == 0:
#             log('{} cards have been processed...'.format(cards_processed))
#
#         # attachments = get_all_attachments(card['id'])
#         # for attachment in attachments:
#         #     delete_attachment(card['id'], attachment['id'])
#         # print('{card} - {id}'.format(card=card['name'].ljust(50, ' '), id=card['id']))
#
#     # Meta pass to update blocked information
#     log('\nUpdating blocked information...')
#     cards_processed = 0
#     for new_card in new_cards:
#         new_card['blocked']['text'] = sanitize_blocked(new_card['blocked']['text'])
#
#         cards_processed += 1
#         if cards_processed % 10 == 0:
#             log('{} cards have been processed...'.format(cards_processed))
#
#
#     # Meta pass to update all start and end dates
#     log('\nUpdating card dates...')
#     cards_processed = 0
#     for new_card in new_cards:
#         update_dates(new_card)
#
#         cards_processed += 1
#         if cards_processed % 10 == 0:
#             log('{} cards have been processed...'.format(cards_processed))

if True:
    with open('cache.json', 'r') as file:
        new_cards = json.load(file)

if len(new_cards):
    data = json.dumps(new_cards)
    with open('cache.json', 'w') as file:
        file.write(data)



    # Create the dataframe data
    log('Generating dataframe...')
    dataframe = []
    subplots = {}
    lorem = 'Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.'
    for new_card in new_cards:
        dataframe.append(dict(Task=new_card['task'],
                              Description=lorem,#new_card['description'],
                              Start=new_card['start']['date'],
                              Finish=new_card['end']['date'],
                              Resource=new_card['list'],
                              Percent=new_card['percent']))

        if new_card['list'] not in subplots:
            subplots[new_card['list']] = []
            subplots[new_card['list']].append(dict(Task=new_card['task'],
                              Description=lorem,#new_card['description'],
                              Start=new_card['start']['date'],
                              Finish=new_card['end']['date'],
                              Resource=new_card['list'],
                              Percent=new_card['percent']))
        else:
            subplots[new_card['list']].append(dict(Task=new_card['task'],
                              Description=lorem,#new_card['description'],
                              Start=new_card['start']['date'],
                              Finish=new_card['end']['date'],
                              Resource=new_card['list'],
                              Percent=new_card['percent']))

    figure = make_subplots(rows=3, cols=1, shared_yaxes=False)

    i = 1
    for subplot in subplots:
        if subplot == 'Primary Weapons': #subplot == 'Project' or subplot == 'General' or subplot == 'Primary Weapons':
            dataframe = subplots[subplot]
            temp_gantt = ff.create_gantt(df=dataframe,
                                         percent=True,
                                         colors=list_colors,
                                         index_col='Resource',
                                         show_colorbar=True,
                                         bar_width=0.2,
                                         height=600)#(30 * len(new_cards)))
            temp_gantt.show()
            break
    #         print(temp_gantt.layout)
    #         for trace in temp_gantt.data:
    #             figure.add_trace(trace, row=i, col=1)
    #             y = '' if i == 1 else str(i)
    #             figure.layout['yaxis{}'.format(y)]['ticktext'] = temp_gantt.layout['yaxis']['ticktext']
    #             figure.layout['yaxis{}'.format(y)]['range'] = temp_gantt.layout['yaxis']['range']
    #             figure.layout['yaxis{}'.format(y)]['tickvals'] = temp_gantt.layout['yaxis']['tickvals']
    #             figure.layout['yaxis{}'.format(y)]['zeroline'] = temp_gantt.layout['yaxis']['zeroline']
    #             figure.update_layout()
    #         i += 1
    #         if i >= 4:
    #             break
    #
    # print(figure.layout)

    # # Generate the Gantt chart
    # log('Generating Gantt chart...')
    #  figure = ff.create_gantt(df=dataframe,
    #                          percent=True,
    #                          colors=list_colors,
    #                          index_col='Resource',
    #                          show_colorbar=True,
    #                          bar_width=0.2,
    #                          height=(30 * len(new_cards)))

    # Add additional annotations
    log('Applying additional annotations...')
    # fig.update_traces(textposition='top center')
    #
    # fig.add_annotation(x=0.0,
    #             y=-0.15,
    #             showarrow=False,
    #             text="Custom x-axis title <br> with more text",
    #             font=dict(
    #                 family="Courier New, monospace",
    #                 size=16,
    #                 color="#000000"
    #             ),
    #             xref="paper",
    #             yref="paper")
    #
    # fig.update_xaxes(    rangebreaks=[
    #         dict(bounds=["sat", "mon"]) #hide weekends
    #     ])
    #
    #figure.update_layout(title_text='GDP and Life Expectancy (Americas, 2007)<br>', height=600 * i)

    # Display chart
    log('Displaying Gantt Chart!')
    #figure.show()


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
df = [dict(Task="Job A", Description='This is an apple', Start='2020-05-18', Finish='2020-05-22', Resource='Apple', Percent=0.5),
      dict(Task="Job B", Description='Firing a semi automatic or automatic weapon once while moving looks strange because the player quickly rotates to fire and then rotates back to the direction of movement', Start='2020-05-22', Finish='2020-05-27', Resource='Grape', Percent=0.1),
      dict(Task="Job C", Description='This is a Banana', Start='2020-05-27', Finish='2020-06-03', Resource='Banana', Percent=0.8)]

colors = ['rgb(255, 79, 79)', 'rgb(74, 255, 140)', 'rgb(249, 255, 74)']

fig = ff.create_gantt(df, percent=True, colors=colors, index_col='Resource', reverse_colors=True,
                      show_colorbar=True)
#
# fig.update_traces(textposition='top center')
#
# fig.add_annotation(x=0.0,
#             y=-0.15,
#             showarrow=False,
#             text="Custom x-axis title <br> with more text",
#             font=dict(
#                 family="Courier New, monospace",
#                 size=16,
#                 color="#000000"
#             ),
#             xref="paper",
#             yref="paper")
#
# fig.update_xaxes(    rangebreaks=[
#         dict(bounds=["sat", "mon"]) #hide weekends
#     ])
#
# fig.update_layout(title_text='GDP and Life Expectancy (Americas, 2007)<br>')



#textfont_size=14

fig.show()
#
# # # fig = ff.create_gantt(df, colors=colors, index_col='Resource', reverse_colors=True,
# # #                       show_colorbar=True, bar_width=0.1, height=(25 * len(cards)))
# # # fig.show()
#
# x = 5
# x = x + 1
