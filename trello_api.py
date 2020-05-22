import requests
import logging
import configparser

class TrelloAPI:
    def __init__(self):
        config = configparser.ConfigParser()
        config.read('trello.ini')

        self.trello = 'https://api.trello.com'
        self.key = config['api']['key']
        self.token = config['api']['token']


    def get_board_with_name(self, name):
        request = '{url}/1/members/me/boards?key={key}&token={token}'.format(url=self.trello, key=self.key, token=self.token)
        response = requests.get(url=request)
        try:
            raw = response.json()
            for board in raw:
                if board['name'] == name:
                    return board
        except:
            logging.error('Failed to parse JSON, request most likely invalid')
        return None
    
    
    def get_board(self, id):
        request = '{url}/1/boards/{board}?key={key}&token={token}'.format(url=self.trello, board=id, key=self.key, token=self.token)
        response = requests.get(url=request)
        raw = None
        try:
            raw = response.json()
        except:
            logging.error('Failed to parse JSON, request most likely invalid')
        return raw
    
    
    def get_all_cards(self, id):
        request = '{url}/1/boards/{board}/cards?key={key}&token={token}'.format(url=self.trello, board=id, key=self.key, token=self.token)
        response = requests.get(url=request)
        raw = None
        try:
            raw = response.json()
        except:
            logging.error('Failed to parse JSON, request most likely invalid')
        return raw
    
    
    def get_list(self, id):
        request = '{url}/1/lists/{list}?key={key}&token={token}'.format(url=self.trello, list=id, key=self.key, token=self.token)
        response = requests.get(url=request)
        raw = None
        try:
            raw = response.json()
        except:
            logging.error('Failed to parse JSON, request most likely invalid')
        return raw
    
    
    def get_all_attachments(self, id):
        request = '{url}/1/cards/{card}/attachments?key={key}&token={token}'.format(url=self.trello, card=id, key=self.key, token=self.token)
        response = requests.get(url=request)
        raw = None
        try:
            raw = response.json()
        except:
            logging.error('Failed to parse JSON, request most likely invalid')
        return raw
    
    
    def get_custom_field_items(self, id):
        request = '{url}/1/cards/{card}/customFieldItems?key={key}&token={token}'.format(url=self.trello, card=id, key=self.key, token=self.token)
        response = requests.get(url=request)
        raw = None
        try:
            raw = response.json()
        except:
            logging.error('Failed to parse JSON, request most likely invalid')
        return raw
    
    
    def get_custom_fields(self, id):
        request = '{url}/1/boards/{board}/customFields?key={key}&token={token}'.format(url=self.trello, board=id, key=self.key, token=self.token)
        response = requests.get(url=request)
        raw = None
        try:
            raw = response.json()
        except:
            logging.error('Failed to parse JSON, request most likely invalid')
        return raw


    def get_card_checklists(self, id):
        request = '{url}/1/cards/{card}/checklists?key={key}&token={token}'.format(url=self.trello, card=id, key=self.key, token=self.token)
        response = requests.get(url=request)
        raw = None
        try:
            raw = response.json()
        except:
            logging.error('Failed to parse JSON, request most likely invalid')
        return raw


    def get_boards_labels(self, id):
        request = '{url}/1/boards/{board}/labels?key={key}&token={token}'.format(url=self.trello, board=id, key=self.key, token=self.token)
        response = requests.get(url=request)
        raw = None
        try:
            raw = response.json()
        except:
            logging.error('Failed to parse JSON, request most likely invalid')
        return raw
    
    
    def delete_attachment(self, card, id):
        request = '{url}/1/cards/{card}/attachments/{attachment}?key={key}&token={token}'.format(url=self.trello, card=card, attachment=id, key=self.key, token=self.token)
        response = requests.request(method='DELETE', url=request)
        raw = None
        try:
            raw = response.json()
        except:
            logging.error('Failed to parse JSON, request most likely invalid')
        return raw
