#!/usr/bin/env python2

import os
import sys
import time
import telepot
from telepot.loop import MessageLoop


def sort_message(msg):
	msg_content_type, msg_chat_type, msg_chat_id = telepot.glance(msg)
	if msg_content_type != 'text':
		return

	msg_command = msg['text'].split()[0].replace('/', '').strip().lower()
	if msg_command in ['ack', 'get']:
		response = None
		if msg_command == 'ack':
			response = command_ack(msg)
		elif msg_command == 'get':
			response = command_get(msg)

		if response == None:
			bot.sendMessage(msg_chat_id, "Unable to do what asked for. Sorry.")
		else:
			bot.sendMessage(msg_chat_id, response)
	elif msg_command == 'start':
		return
	else:
		bot.sendMessage(msg_chat_id, "Unrecognized command: `{}`".format(msg['text']), parse_mode='Markdown')


def command_ack(msg):
	return "Still in WIP"


def command_get(msg):
	return "Still in WIP"


if 'TELEGRAM_BOT_TOKEN' not in os.environ or 'ICINGA2_API_USER' not in os.environ or 'ICINGA2_API_PWD' not in os.environ:
	print "Mandatory environment keys: TELEGRAM_BOT_TOKEN, ICINGA2_API_USER, ICINGA2_API_PWD"
	sys.exit(1)

bot = telepot.Bot(os.environ['TELEGRAM_BOT_TOKEN'])
MessageLoop(bot, sort_message).run_as_thread()

while 1:
	time.sleep(10)
