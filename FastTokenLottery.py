# coding=utf8

import json
import urllib2
import requests
import hashlib
import base58
import time
import logging
import random
from telegram.ext import Updater, MessageHandler, Filters

SELF_ADDRESS = "" # Your address to read tx's from the network
PK = "" # Your private key for signing tx's
TOKEN_NAME = "WIN" # Token name if you want to work with a token only for your game
CHAT_ID = -1001335094245 # fill in the chat id number from telegram
TELEGRAM_BOT_KEY = "" # API key for your telegram bot
PLAYERS_MAX = 5 # self explanatory
BASE_POT = 1000 # cause win token games are generous ;)

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

def formatGameStatus(dict, amt):
  txt = "Win Token Lottery! Draw at 10 participants \n"
  txt += "POOL: "+str(amt)+" WIN \n"
  txt += "Participants: \n"

  for key, value in dict.iteritems():
    txt += "%"+str(value / amt * 100)+ " --- "+key + " --- " + "WIN TOKENS : "+ str(value) +"\n"


  return txt

received_tx = {}
received_amount = BASE_POT
job_queue = None

def chooseRandom(players, total):
  choice = random.randrange(0, total - BASE_POT)
  for key, value in players.iteritems():
    choice -= value
    if choice < 0:
      return key

def playGame(bot, job):
  global received_tx
  global received_amount

  if len(received_tx) == 0:
    return

  winner = chooseRandom(received_tx, received_amount)
  txn_data = generateAssetTransferTxn(winner, received_amount)
  txn = json.loads(txn_data)
  print txn_data
  print "winner"
  broadcastTxnJSON(txn_data)
  winText = "Time to play!\n"+winner + " WINS " + str(received_amount) + " WIN TOKENS! \nhttps://tronscan.org/#/transaction/"+txn["txID"]+"\nGAME RESET!"

  bot.send_message(chat_id=CHAT_ID, text=winText)
  received_tx = {}
  received_amount = BASE_POT

def gameStatus(bot, job):
  global received_tx
  global received_amount
  bot.send_message(chat_id=CHAT_ID, text=formatGameStatus(received_tx, received_amount))


def announceEntry(bot, job):
  global received_tx
  global received_amount
  bot.send_message(chat_id=CHAT_ID, text=""+job.context[0][:8]+ " " + str(job.context[1]) + " WIN -- PLAYERS:"+  str(len(received_tx))+ " -- POT:"+str(received_amount))


def startGame(bot, job):
  text = "Win Token Lottery! DRAW every 5 PLAYERS. POT SEEDED WITH "+str(BASE_POT)+" WIN!\n\
  \n\
  🎊 How to enter? 🎊\n\
  \n\
  1. Reply “/tip XX WIN” this pinned message to enter the next lottery. 1 WIN == 1 ticket!\n\
  \n\
  And your done!👍🏻"

  bot.send_message(chat_id=CHAT_ID, text=text)

def checkGameStatus():
  global received_tx
  global received_amount
  global job_queue
  if len(received_tx) == PLAYERS_MAX:
    job_queue.run_once(playGame, 1)


def main():
  global received_tx
  global received_amount
  global job_queue

  updater = Updater(token=TELEGRAM_BOT_KEY)
  dispatcher = updater.dispatcher


  updater.start_polling()
  job_queue = updater.job_queue
  prev_current_block_id = 0

  job_queue.run_once(startGame, 1)

  while (True):
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
          (tx["raw_data"]["contract"][0]["parameter"]["value"]["to_address"] == hexTRONAddress(SELF_ADDRESS)) and 
          (tx["raw_data"]["contract"][0]["parameter"]["value"]["asset_name"] == TOKEN_NAME.encode("hex"))):
        print "found tx"
        print tx
        address = base58TRONAddress(tx["raw_data"]["contract"][0]["parameter"]["value"]["owner_address"])
        amount = tx["raw_data"]["contract"][0]["parameter"]["value"]["amount"]
        received_amount += amount

        if (address not in received_tx):
          received_tx[address] = 0

        received_tx[address] += amount

        job_queue.run_once(announceEntry, 1, [address, amount, received_tx, received_amount])
        # announceEntry()
        checkGameStatus()


    time.sleep(1)


main()
