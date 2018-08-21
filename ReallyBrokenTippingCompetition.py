# coding=utf8

import json
import urllib2
import requests
import hashlib
import base58
import time
import logging
import random
import threading
import sys, traceback
from telegram.ext import Updater, MessageHandler, Filters

SELF_ADDRESS = ""
PK = ""
TOKEN_NAME = ""
CHAT_ID = 
TELEGRAM_BOT_KEY = ""
PLAYERS_MAX = 5
BASE_POT = 1000


# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)


def hexTRONAddress(address):
  return base58.b58decode_check(address.encode()).encode("hex")

def base58TRONAddress(address):
  return base58.b58encode_check(str(bytearray.fromhex( address )))

def broadcastTxnJSON(data):
  # SIGN DATA

  data_dict = json.loads(data)
  sign_dict = {'transaction':data_dict, 'privateKey':PK}
  post_data = json.dumps(sign_dict, separators=(',',':'))

  url = "http://127.0.0.1:8090/wallet/gettransactionsign"
  r = requests.post(url, data=post_data, allow_redirects=True)

  # BROADCASTS DATA

  broadcast_url = "http://127.0.0.1:8090/wallet/broadcasttransaction"
  r2 = requests.post(broadcast_url, data=r.content, allow_redirects=True)

def generateTransferTxn(sendAddress, amount):

  post_dict = {'owner_address':hexTRONAddress(SELF_ADDRESS), 'to_address':hexTRONAddress(sendAddress), 'amount':amount}

  post_data = json.dumps(post_dict, separators=(',',':'))
  url = "http://127.0.0.1:8090/wallet/createtransaction"

  r = requests.post(url, data=post_data, allow_redirects=True)
  return r.content

def generateAssetTransferTxn(sendAddress, amount):

  post_dict = {'owner_address':hexTRONAddress(SELF_ADDRESS), 'to_address':hexTRONAddress(sendAddress), 'asset_name':TOKEN_NAME.encode("hex"), 'amount':amount}

  post_data = json.dumps(post_dict, separators=(',',':'))
  url = "http://127.0.0.1:8090/wallet/transferasset"

  r = requests.post(url, data=post_data, allow_redirects=True)
  return r.content

def getNowBlockTxn():
  url = "http://127.0.0.1:8090/wallet/getnowblock"

  r = requests.post(url, allow_redirects=True)
  return r.content

def formatGameStatus(map):
  txt = "LEADERBOARDS \n"
  txt += "Participants: Unique 100 WIN TIPS\n"


  for key, value in sorted(map.iteritems(), key=lambda (k,v): (v,k), reverse=True):
    print "%s: %s" % (key, value)
    txt += "%s: %s" % (key, len(value)) +"\n"

  # for key, value in map.iteritems():
  #   txt += "%"+str(value / amt * 100)+ " --- "+key + " --- " + "WIN TOKENS : "+ str(value) +"\n"
  return txt

received_tx = {}
sent_map = {} #maps sender -> array of receipients

received_amount = BASE_POT
job_queue = None

last_update_hash = None

IS_RUNNING = True

# def chooseRandom(players, total):
#   choice = random.randrange(0, total - BASE_POT)
#   for key, value in players.iteritems():
#     choice -= value
#     if choice < 0:
#       return key

# def playGame(bot, job):
#   global received_tx
#   global received_amount

#   if len(received_tx) == 0:
#     return

#   winner = chooseRandom(received_tx, received_amount)
#   txn_data = generateAssetTransferTxn(winner, received_amount)
#   txn = json.loads(txn_data)
#   print txn_data
#   print "winner"
#   broadcastTxnJSON(txn_data)
#   winText = "Time to play!\n"+winner + " WINS " + str(received_amount) + " WIN TOKENS! \nhttps://tronscan.org/#/transaction/"+txn["txID"]+"\nGAME RESET!"

#   bot.send_message(chat_id=CHAT_ID, text=winText)
#   received_tx = {}
#   received_amount = BASE_POT

def gameStatus(bot, job):
  global last_update_hash
  global sent_map
  global IS_RUNNING

  if not IS_RUNNING:
    return
  new_hash = hash(json.dumps(sent_map, sort_keys=True))
  print new_hash
  if new_hash != last_update_hash:
    last_update_hash = new_hash
    if len(sent_map) > 0:
      bot.send_message(chat_id=CHAT_ID, text=formatGameStatus(sent_map))


# def announceEntry(bot, job):
#   global received_tx
#   global received_amount
#   bot.send_message(chat_id=CHAT_ID, text=""+job.context[0][:8]+ " " + str(job.context[1]) + " WIN -- PLAYERS:"+  str(len(received_tx))+ " -- POT:"+str(received_amount))

def startGame(bot, job):
  text = "WIN Token TIPPING Contest! WIN 1,000,000 WIN TOKENS and 500 TRX!!\n\
  \n\
  🎊 How to enter? 🎊\n\
  \n\
  1. Reply “/tip 100 WIN” to the most number of different people in the next 1 HOURS to WIN!.\
  \n\
  2. Check the leaderboards here!"

  bot.send_message(chat_id=CHAT_ID, text=text)

def gameOver(bot, job):
  text = formatGameStatus(sent_map) + "\n"
  text += "Games Over! Congrats to the winner!\n @kookiekrak will send awards when he's back"

  bot.send_message(chat_id=CHAT_ID, text=text)

def checkGameStatus():
  global job_queue
  global IS_RUNNING

  if not IS_RUNNING:
    return
  threading.Timer(30.0, checkGameStatus).start()
  # global received_tx
  # global received_amount
  # if len(received_tx) == PLAYERS_MAX:
  job_queue.run_once(gameStatus, 1)

def endGame():
  global IS_RUNNING
  job_queue.run_once(gameOver, 1)
  IS_RUNNING = False
  print "gameover"



def main():
  # global received_tx
  # global received_amount
  global job_queue
  global sent_map
  global IS_RUNNING

  updater = Updater(token=TELEGRAM_BOT_KEY)
  dispatcher = updater.dispatcher


  updater.start_polling()
  job_queue = updater.job_queue
  prev_current_block_id = 0

  job_queue.run_once(startGame, 1)
  # job_minute = job_queue.run_repeating(gameStatus, interval=60, first=0)

  checkGameStatus()

  # End game
  # threading.Timer(30.0, checkGameStatus).start()
  threading.Timer(3600.0, endGame).start()
  # 21600


  while (IS_RUNNING):
    # Get current block
    current_block_data = getNowBlockTxn()

    current_block = json.loads(current_block_data)
    # print current_block
    current_block_id = current_block["block_header"]["raw_data"]["number"]

    if current_block_id == prev_current_block_id:
      continue

    print current_block_id
    # Watch All blocks from now for incoming TXN's
    prev_current_block_id = current_block_id

    if "transactions" not in current_block:
      continue

    for tx in current_block["transactions"]:
      if ((tx["raw_data"]["contract"][0]["type"] == "TransferAssetContract") and 
          # (tx["raw_data"]["contract"][0]["parameter"]["value"]["to_address"] == hexTRONAddress(SELF_ADDRESS)) and 
          (tx["raw_data"]["contract"][0]["parameter"]["value"]["asset_name"] == TOKEN_NAME.encode("hex"))):
        # print "found tx"
        # print tx
        address = base58TRONAddress(tx["raw_data"]["contract"][0]["parameter"]["value"]["owner_address"])
        amount = tx["raw_data"]["contract"][0]["parameter"]["value"]["amount"]

        if "data" in tx["raw_data"] and amount >= 100:
          data = str(bytearray.fromhex(tx["raw_data"]["data"]))
          adtl_data = json.loads(data)

          print adtl_data
          # {u'user_to': u'Mervin', u'platform': u'telegram', u'user_from': u'kookiekrak'}

          user_from = adtl_data['user_from']
          user_to = adtl_data['user_to']

          if user_from not in sent_map:
            sent_map[user_from] = [user_to]
          else:
            if user_to not in sent_map[user_from]:
              sent_map[user_from].append(user_to)

        # received_amount += amount

        # if (address not in received_tx):
        #   received_tx[address] = 0

        # received_tx[address] += amount

        # job_queue.run_once(announceEntry, 1, [address, amount, received_tx, received_amount])
        # # announceEntry()
        # checkGameStatus()


    time.sleep(1)


main()





