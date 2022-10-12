import sys
import json
import requests
from csv import DictReader
from pathlib import Path
from datetime import datetime
from pprint import pp
from collections import namedtuple

from matplotlib import pyplot as plt
# from adjustText import adjust_text


# if len(sys.argv)<2:
#     print("Please provide your diary number(e.g. 12345/123/1234\") as the first argument.")
#     exit(1)

# DIARY_NUMBER = sys.argv[1]
DIARY_NUMBER = "31275/110/2022"

CURRENT_DIR = Path(__file__).parent
QUERY_LOG_FILE = CURRENT_DIR / 'enter_finland_queue_position.log'
ALL_POSITIONS_VISUALIZATION_FILE = CURRENT_DIR / 'enter_finland_queue_position.svg'
UNIQUE_POSITIONS_VISUALIZATION_FILE = CURRENT_DIR / 'enter_finland_queue_unique_position.png'

DATETIME_CTIME_FORMAT_STRING = "%a %b %d %H:%M:%S %Y"

URL = "https://networkmigri.boost.ai/api/chat/v2"
HEADERS = {
  "accept": "application/json, text/plain, */*",
  "accept-language": "en-GB,en;q=0.5",
  "content-type": "application/json",
  "sec-fetch-dest": "empty",
  "sec-fetch-mode": "cors",
  "sec-fetch-site": "cross-site",
  "sec-gpc": "1",
  "Referer": "https://migri.fi/",
  "Referrer-Policy": "strict-origin-when-cross-origin"
}
CONVERSATION_ID = ''
ACTION_ID = ''


def get_conversation_and_action_ids():
  global CONVERSATION_ID, ACTION_ID
  body = {
    'command': 'START',
    'filter_values': ['migri', 'english_start_language'],
    'language': 'en-US'
  }
  resp = requests.post(URL, json.dumps(body), headers=HEADERS)
  data = json.loads(resp.text)
  CONVERSATION_ID = data['conversation']['id']
  ACTION_ID = data['response']['elements'][-1]['payload']['links'][-1]['id']


def initiate_action(conversation_id=CONVERSATION_ID, action_id=ACTION_ID):
  body = {
    'command': 'POST',
    'type': 'action_link',
    'id': action_id,
    'conversation_id': conversation_id,
    'filter_values': ['migri', 'english_start_language']
  }
  resp = requests.post(URL, json.dumps(body), headers=HEADERS)
  if resp.status_code==200:
    print("Query initiated!")
  else:
    print("Query initiation failed!")
  

def get_application_position_in_queue(conversation_id=CONVERSATION_ID):
  BODY = {
    'command': 'POST',
    'type': 'text',
    'conversation_id': conversation_id,
    'value': DIARY_NUMBER,
    'filter_values': ['migri', 'english_start_language'],
    'client_timezone': 'Asia/Dhaka'
  }

  resp = requests.post(URL, json.dumps(BODY), headers=HEADERS)
  data = json.loads(resp.text)
  if resp.status_code==200:
    data = data['response']['elements']
    position_in_queue = data[1]['payload']['json']['data']['counterValue']
    print(f"Your current position in queue is {position_in_queue}.")
    with open(QUERY_LOG_FILE, 'a+') as log:
      log_time = datetime.now().strftime(DATETIME_CTIME_FORMAT_STRING)
      log.write(f"{position_in_queue},{log_time}\n")
  else:
    pp(data)



PlotPoint = namedtuple('PlotPoint', ['query_time', 'position'])

def get_sudo_date(query_time:datetime):
  return query_time.strftime('%b %d %Y')
def get_sudo_position(position:int):
  return str(position)
def get_sudo_key(plot_point:PlotPoint):
  return f"{get_sudo_position(plot_point.position)}-{get_sudo_date(plot_point.query_time)}"

def get_unique_plot_values(log_file_path=QUERY_LOG_FILE):
  with open(log_file_path, 'r') as log_file:
    logs = DictReader(log_file)
    date_position_map = {} # {'sudo_position': [PlotPoint]}

    for log in logs:
      position = int(log['Position'])
      query_time = datetime.strptime(log['Query Time'], DATETIME_CTIME_FORMAT_STRING)
      plot_point = PlotPoint(query_time=query_time, position=position)
      
      sudo_date = get_sudo_date(query_time)
      
      if sudo_date not in date_position_map:
        date_position_map[sudo_date] = [plot_point]
      elif date_position_map[sudo_date][-1].position!=position:
        date_position_map[sudo_date].append(plot_point)
      else:
        date_position_map[sudo_date].pop()
        date_position_map[sudo_date].append(plot_point)


  plot_position_values = []
  plot_date_values = []
  plotted_dates = set()

  for sudo_date, plot_points in date_position_map.items():
    for plot_point in plot_points:
      query_time = plot_point.query_time
      position = plot_point.position

      if len(plot_date_values)!=0:
        last_date = plot_date_values[-1]
        last_position = plot_position_values[-1]
        delta = query_time-last_date

      if len(plot_position_values)==0:
        pass
      elif position!=last_position:
        pass
      elif get_sudo_date(query_time)!=get_sudo_date(last_date):
        if delta.days>=1 or delta.seconds>(60*60*24)-60:pass
        else: continue
        # elif 4<=round(delta.total_seconds()/60/60)<=5:
        #   continue
      else:
        continue
      plot_position_values.append(position)
      plot_date_values.append(query_time)
      plotted_dates.add(get_sudo_date(query_time))

  return (plot_date_values, plot_position_values)


def create_plot(file_path, plot_x_values, plot_y_values, dpi=300):
  plt.clf()
  figure_width = len(plot_x_values)*0.5 # inches
  figure_height = (max(plot_y_values)-min(plot_y_values))//16 # inches
  plt.figure(figsize=(figure_width, figure_height))

  x_label_date_format = '%a %d %b'
  # Initialize visualization
  transformed_plot_x_values = [x_val.strftime(x_label_date_format) for x_val in plot_x_values]
  plt.plot(transformed_plot_x_values, plot_y_values,
    color='g', linestyle='dashed', marker='o')
  
  # Add position labels
  plot_text_labels = []
  for plot_position, plot_date, query_time in zip(plot_y_values, plot_x_values, transformed_plot_x_values):
    label = plt.text(query_time, plot_position+0.3, f"{plot_position}")
    plot_text_labels.append(label)
    label.set_fontsize(8)

  # Customize plot
  plt.title("Queue Positions vs Dates", fontsize=16)
  plt.xticks(rotation=90, fontsize=10)
  plt.yticks(fontsize=10)
  plt.xlabel('Dates')
  plt.ylabel('Positions')
  plt.grid()
  # plt.legend()
  plt.savefig(file_path, bbox_inches='tight', dpi=dpi)


def create_visualization_for_unique_positions(log_file_path=QUERY_LOG_FILE, visual_file=UNIQUE_POSITIONS_VISUALIZATION_FILE):
  plot_date_values, plot_position_values = get_unique_plot_values(log_file_path)
  create_plot(visual_file, plot_date_values, plot_position_values)


get_conversation_and_action_ids()
initiate_action(CONVERSATION_ID, ACTION_ID)
get_application_position_in_queue(CONVERSATION_ID)
create_visualization_for_unique_positions()
