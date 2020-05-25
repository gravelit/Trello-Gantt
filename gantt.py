# additional features:
# move dates by X amount
# update due dates
#
# maybe:
# print card ids, with option to print by list
# analyze for same card names
#

# ----------------------------------------------------------------------------------
# Imports
# ----------------------------------------------------------------------------------
import argparse
import configparser
import copy
import json
import plotly.figure_factory as ff
import pytz
import re
import sys
import trello_api

from colorama import Fore, init
from collections import OrderedDict
from datetime import datetime
from datetime import timedelta
from math import ceil
from plotly.subplots import make_subplots

# ----------------------------------------------------------------------------------
# Types
# ----------------------------------------------------------------------------------
card_template = {
    'id' : None,
    'task' : '',
    'list' : '',
    'description' : '',
    'start' : { 'date' : None },
    'end' : { 'date' : None },
    'estimated' : { 'number' : 1 },
    'blocked' : { 'text' : None },
    'percent' : 0.0,
    'exclude' : False,
    'unscheduled' : False,
    'complete' : False,
    'due' : None  # Current due date from Trello
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
SATURDAY = 5
SUNDAY = 6

# ----------------------------------------------------------------------------------
# Functions
# ----------------------------------------------------------------------------------
def update_dates(card):
    # Check if this card is blocked by another task
    if not card['blocked']['text']:
        # Check if this card has a start date assigned
        if not card['start']['date']:
            # The card did not have a valid start date, so assign it
            # to today and mark it unscheduled
            card['start']['date'] = datetime.today().strftime('%Y-%m-%d')
            card['unscheduled'] = True
        start = datetime.strptime(card['start']['date'], '%Y-%m-%d')
    else:
        # Find the card blocking this card
        blocking_card = find_card_by_id(card['blocked']['text'])
        if blocking_card:
            # if the blocking card does not have an end date, recursively update that card
            if not blocking_card['end']['date']:
                update_dates(blocking_card)

            # Assign the end date of the blocking card to the start date of this card
            start = datetime.strptime(blocking_card['end']['date'], '%Y-%m-%d')
            card['start']['date'] = start.strftime('%Y-%m-%d')
        else:
            log('Error: Could not find blocking card', error=True)
            start = datetime.strptime(card['start']['date'], '%Y-%m-%d')

    card['end']['date'] = (start + timedelta(days=card['estimated']['number'])).strftime('%Y-%m-%d')
    card['start']['date'], card['end']['date'] = account_for_weekends(card['start']['date'], card['end']['date'])


def move_dates(initial, amount):
    sign = lambda a: (a > 0) - (a < 0)
    date_cards = []
    for card in new_cards:
        if card['start']['date']:
            if card['exclude']:
                log('Excluded card has start date: {}'.format(card['task']), warning=True)
            card_start = datetime.strptime(card['start']['date'], '%Y-%m-%d')
            if card_start >= initial:
                days = abs(amount)
                while days:
                    card_start = card_start + timedelta(days=1 * sign(amount))
                    if (not card_start.weekday() == SATURDAY) and (not card_start.weekday() == SUNDAY):
                        days = days - 1
                card['start']['date'] = card_start.strftime('%Y-%m-%d')
                date_cards.append(card)
    return date_cards


def update_start_dates(api, start_field_id, cards):
    for card in cards:
        if card['start']['date']:
            trello_date = make_trello_date(card['start']['date'])
            api.update_card_custom_field(card_id=card['id'], field_id=start_field_id, value=dict(date=trello_date))


def find_card_by_id(id):
    for card in new_cards:
        if card['id'] == id:
            return card
    return None


def start_date_remove_time(card):
    if card['start']['date']:
        start = datetime.strptime(card['start']['date'], '%Y-%m-%dT%H:%M:%S.%fZ')
        return start.strftime('%Y-%m-%d')
    return None


def generate_xaxis_range(subplot):
    first_date = None
    last_date = None
    for card in subplot:
        card_start = datetime.strptime(card['start']['date'], '%Y-%m-%d')
        card_end = datetime.strptime(card['end']['date'], '%Y-%m-%d')
        if not first_date and not last_date:
            first_date = card_start
            last_date = card_end
        else:
            if card_start < first_date:
                first_date = card_start
            if card_end > last_date:
                last_date = card_end
    first_date = first_date - timedelta(days=1)
    last_date = last_date + timedelta(days=1)
    return [first_date.strftime('%Y-%m-%d'), last_date.strftime('%Y-%m-%d')]


def account_for_weekends(start, end):
    s = datetime.strptime(start, '%Y-%m-%d')
    e = datetime.strptime(end, '%Y-%m-%d')

    # If start date falls on a weekend, move it to monday
    if s.weekday() == SATURDAY:
        s = s + timedelta(days=2)
        e = e + timedelta(days=2)
    if s.weekday() == SUNDAY:
        s = s + timedelta(days=1)
        e = e + timedelta(days=1)

    delta = e - s
    weekend_count = 0
    for single_date in (s + timedelta(days=n) for n in range(delta.days + 1)):
        if single_date.weekday() == SATURDAY or single_date.weekday() == SUNDAY:
            weekend_count += 1
    weekend_count += (weekend_count % 2)
    e = e + timedelta(weekend_count)

    # There is a case where the end date is on a Thursday with one weekend between
    # the start and end. In that case the end date will be moved to saturday, which is
    # incorrect.
    if e.weekday() == SATURDAY:
        e = e + timedelta(days=2)
    if e.weekday() == SUNDAY:
        e = e + timedelta(days=1)

    return s.strftime('%Y-%m-%d'), e.strftime('%Y-%m-%d')


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


def make_trello_date(date):
    tz = pytz.timezone(project_tz)
    trello_date = datetime.strptime(date, '%Y-%m-%d')
    trello_date = trello_date.replace(hour=12)  # Set time to high noon
    trello_date = tz.normalize(tz.localize(trello_date)).astimezone(pytz.utc)
    trello_date = trello_date.strftime('%Y-%m-%dT%H:%M:%S.%f')
    trello_date = trello_date[:-3] + 'Z'
    return trello_date


def log(info, error=False, warning=False):
    if error:
        print(Fore.RED + info)
    elif warning:
        print(Fore.YELLOW + info)
    else:
        print(Fore.WHITE + info)


# ----------------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------------
init(autoreset=True)  # Colorama reset color after printing in color

# Configuration
config = DictParser()
config.read('project.ini')
project = config['project']['name']
project_tz = config['project']['timezone']
list_colors = config.as_dict()['listColors']

# Args parse
parser = argparse.ArgumentParser(description='Generate a project Gantt chart based off a Trello board')
group = parser.add_mutually_exclusive_group()
group.add_argument('--cache', '-c', help='Generate Gantt from cached values', action='store_true')
group.add_argument('--move', '-m', nargs=2, metavar=('date', 'days'), help='Move all cards starting at <date> forward or backward in time by <days>')
args = parser.parse_args()

# Initialize the API, and grab the project board
log('Requesting project board...')
api = trello_api.TrelloAPI()
project_board = api.get_board_with_name(project)

# Only start processing if the request was a success
if project_board:
    project_board_id = project_board['id']

    # Initialize variables for other data we are looking for
    project_total_tasks = 0
    project_total_complete_tasks = 0

    # Get the custom field definitions for this board
    log('Generating custom field definitions...')
    values = api.get_custom_fields(project_board_id)
    custom_fields = {}
    for value in values:
        custom_fields[value['id']] = value['name']

    # Get the label definitions for this board
    log('Generating label definitions...')
    values = api.get_boards_labels(project_board_id)
    labels = {}
    for value in values:
        labels[value['id']] = value['name']

    # Ask Trello for data if we aren't using cached values
    if not args.cache:
        # ------------------------------------------------------------------------------
        # Grab the cards for the board
        cards = api.get_all_cards(project_board_id)
        log('Total cards: {}'.format(len(cards)))
        log('\nBeginning card processing...')
        cards_processed = 0

        # Cached values to prevent calling the API constantly
        lists = {}
        for card in cards:
            new_card = copy.deepcopy(card_template)

            # Save the card ID
            new_card['id'] = card_id = card['id']

            # Save the task name
            new_card['task'] = card['name']

            # Save the description
            new_card['description'] = card['desc']

            # Save the due date
            new_card['due'] = card['due']

            # Store the custom field data
            items = api.get_custom_field_items(card_id)
            for item in items:
                if item['idCustomField'] in custom_fields:
                    field = custom_fields[item['idCustomField']].lower()
                    new_card[field] = item['value']

            # Sanitize custom fields
            new_card['start']['date'] = start_date_remove_time(new_card)
            new_card['estimated']['number'] = int(new_card['estimated']['number'])

            # List name
            if not card['idList'] in lists:
                listData = api.get_list(card['idList'])
                if listData:
                    lists[card['idList']] = listData['name']
                    new_card['list'] = listData['name']
            else:
                new_card['list'] = lists[card['idList']]

            # Check if this card is marked complete
            # Completed cards are marked excluded
            total_items = 1
            completed_items = 0
            if card['dueComplete']:
                completed_items = 1
                new_card['complete'] = True

            # if the complete label wasn't on the card, check how far along we are with the checklist
            if not completed_items:
                checklists = api.get_card_checklists(card_id)
                for checklist in checklists:
                    total_items = len(checklist['checkItems'])
                    for item in checklist['checkItems']:
                        if item['state'] == 'complete':
                            completed_items += 1
            if total_items:
                new_card['percent'] = round(float(completed_items / total_items), 1)

            # Exclude cards marked "Exclude" or "Finalization"
            for label in card['idLabels']:
                if labels[label] == 'Exclude' or labels[label] == 'Finalization':
                    new_card['exclude'] = True

            # Update project totals
            project_total_tasks += total_items
            project_total_complete_tasks += completed_items

            # Add card to list
            new_cards.append(new_card)

            # Logging info
            cards_processed += 1
            if cards_processed % 10 == 0:
                log('{} cards have been processed...'.format(cards_processed))

        # Meta pass to update blocked information
        log('\nUpdating blocked information...')
        cards_processed = 0
        for new_card in new_cards:
            new_card['blocked']['text'] = sanitize_blocked(new_card['blocked']['text'])

            cards_processed += 1
            if cards_processed % 10 == 0:
                log('{} cards have been processed...'.format(cards_processed))

        # Move card dates
        if args.move:
            initial = None
            amount = None
            try:
                # Validate inputs
                log('\nValidating move from date {date} by {days} days'.format(date=args.move[0], days=args.move[1]))
                initial = datetime.strptime(args.move[0], '%Y-%m-%d')
                amount = int(args.move[1])
                if amount == 0:
                    raise Exception('Trying to move schedule by zero days')
            except:
                log('Error: invalid move arguments, please enter in format: YYYY-MM-DD X, where X '
                    'is a non-zero amount of days to move (X can be negative)', error=True)

            # Move the dates
            log('\nMoving card dates...')
            moved_cards = move_dates(initial=initial, amount=amount)

            # Send new dates back to Trello
            log('\nSending start dates to Trello...')
            date_field_id = None
            for key, value in custom_fields.items():
                if value == 'Start':
                    date_field_id = key
            update_start_dates(api, date_field_id, moved_cards)

        # Meta pass to update all start and end dates
        log('\nUpdating card dates...')
        cards_processed = 0
        for new_card in new_cards:
            update_dates(new_card)

            cards_processed += 1
            if cards_processed % 10 == 0:
                log('{} cards have been processed...'.format(cards_processed))

        # Send due dates to trello
        log('\nSending due dates to Trello...')
        cards_processed = 0
        for new_card in new_cards:
            due = make_trello_date(new_card['end']['date'])
            if not new_card['exclude'] and not new_card['complete'] and new_card['due'] and new_card['due'] != due:
                api.update_card(new_card['id'], item='due', value=due)

            cards_processed += 1
            if cards_processed % 10 == 0:
                log('{} cards have been processed...'.format(cards_processed))

        # Store data in a cache file
        data = json.dumps(new_cards)
        with open('cache.json', 'w') as file:
            file.write(data)

    # We are using the cached data
    else:
        with open('cache.json', 'r') as file:
            new_cards = json.load(file)
            if not len(new_cards):
                try:
                    sys.exit(1)
                except SystemExit as e:
                     log('Unable to read cached values', error=True)
                     raise

    # Remove excluded and completed cards
    new_cards = [card for card in new_cards if not card['exclude'] and not card['complete']]

    # Meta processing to determine percent complete, time remaining and estimated end date
    time_remaining = sum([(float(1) - card['percent']) * float(card['estimated']['number']) for card in new_cards])
    estimated_end_date = (datetime.today() + timedelta(days=ceil(time_remaining))).strftime('%B %d, %Y')
    percent_complete = '{:.2f}%'.format((sum([card['percent'] for card in new_cards]) / float(len(new_cards))) * float(100))

    # Create all the subplots
    log('Generating subplots...')
    subplots = OrderedDict()
    subplots['Full'] = []
    subplots['Unscheduled'] = []
    for new_card in new_cards:
        if not new_card['list'] in subplots:
            subplots[new_card['list']] = []

    # Add cards to subplots
    for new_card in new_cards:
        if new_card['unscheduled']:
            subplots['Unscheduled'].append(new_card)
        else:
            subplots['Full'].append(new_card)
            subplots[new_card['list']].append(new_card)

    # Generate layout domain map for subplots, this controls how tall they are on the final html
    log('Generating domains...')
    height = 0
    height_map = {}
    margin = 0
    y_margin = 80
    for i, (title, subplot) in enumerate(subplots.items()):
        if len(subplot):
            plot_height = 300  # base plot height
            plot_height += 30 * len(subplot)
            height_map[title] = plot_height
            height += plot_height
            margin += y_margin
    starting_margin = 80
    total_height = starting_margin + height + margin
    domain_map = {}
    domain = 1.0 - (float(starting_margin) / float(total_height))
    for (title, height) in height_map.items():
        start_domain = domain
        domain = domain - (float(height) / float(total_height))
        end_domain = domain
        domain_map[title] = [end_domain, start_domain]
        domain = domain - (float(y_margin) / float(total_height))
        if domain < 0.0:
            domain = 0.0

    # Create the dataframe data, and generate a Gantt chart
    log('Generating Gantt charts...')
    figure = make_subplots(rows=len(subplots), cols=1, shared_yaxes=False)
    figure.update_layout(height=total_height)
    for i, (title, subplot) in enumerate(subplots.items()):
        dataframe = []
        for new_card in subplot:
            dataframe.append(dict(Task=new_card['task'],
                                  Description=new_card['description'],
                                  Start=new_card['start']['date'],
                                  Finish=new_card['end']['date'],
                                  Resource=new_card['list'],
                                  Percent=new_card['percent']))

        if len(dataframe):
            showlegend = title == 'Full'
            gantt = ff.create_project_gantt(df=dataframe,
                                            colors=list_colors,
                                            index_col='Resource',
                                            bar_width=0.3,
                                            title=title,
                                            height=height_map[title],
                                            showlegend=showlegend)

            if showlegend:
                # Adds a black line to the Full subplot that indicates today
                today = datetime.today().strftime('%Y-%m-%d')
                figure.add_shape(type="line",
                                 xref="x",
                                 yref="paper",
                                 x0=today,
                                 y0=domain_map[title][0],  # starting domain
                                 x1=today,
                                 y1=domain_map[title][1],  # ending domain
                                 line=dict(color="Black", width=1))

            row = i + 1
            for trace in gantt.data:
                # Add the values from the Gantt chart we just generated to the subplot
                figure.add_trace(trace, row=row, col=1)
            idx = '' if row == 1 else str(row)
            figure.layout['yaxis{}'.format(idx)]['ticktext'] = gantt.layout['yaxis']['ticktext']
            figure.layout['yaxis{}'.format(idx)]['range'] = gantt.layout['yaxis']['range']
            figure.layout['yaxis{}'.format(idx)]['tickvals'] = gantt.layout['yaxis']['tickvals']
            figure.layout['yaxis{}'.format(idx)]['zeroline'] = gantt.layout['yaxis']['zeroline']
            figure.layout['yaxis{}'.format(idx)]['domain'] = domain_map[title]
            figure.layout['xaxis{}'.format(idx)]['range'] = generate_xaxis_range(subplot)
            figure.update_layout()

            # add titles to the sub plots
            figure.add_annotation(font={'size': 16},
                                  showarrow=False,
                                  text=title,
                                  x=0.5,
                                  xanchor='center',
                                  xref='paper',
                                  y=domain_map[title][1],
                                  yanchor='bottom',
                                  yref='paper')

    # Add additional annotations
    log('Applying additional annotations...')
    annotations = ['{project} Gantt Chart'.format(project=project),
                   'Estimated Completion Date: {}'.format(estimated_end_date),
                   'Remaining Time: {}'.format(time_remaining),
                   'Percentage Complete: {}'.format(percent_complete),
                   'Number of Unscheduled Tasks: {}'.format(len(subplots['Unscheduled'])) ]
    move_up_pixels = 100  # moves annotations up this many pixels
    text_height = 16
    margin = 10
    domain = 1.0 + (move_up_pixels  / float(total_height))
    domain = domain - (float(margin) / float(total_height))
    for annotation in annotations:
        figure.add_annotation(font={'size': 16},
                              showarrow=False,
                              text=annotation,
                              x=0.0,
                              xanchor='left',
                              xref='paper',
                              y=domain,
                              yanchor='top',
                              yref='paper')
        domain = domain - (float(margin + text_height) / float(total_height))

    figure.update_xaxes(showgrid=False, rangebreaks=[dict(bounds=["sat", "mon"])])  # hide weekends
    figure.update_yaxes(showgrid=False)
    figure.update_layout()

    # Display chart
    log('Displaying Completed Gantt Chart!')
    figure.show()
