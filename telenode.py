#!/usr/bin/env python2

import inotify.adapters
import inotify.constants
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
	try:
		response = eval("command_" + msg_command)(msg)

		if response == None:
			bot.sendMessage(msg_chat_id, "Unable to do what asked for. Sorry.", parse_mode='Markdown')
		else:
			bot.sendMessage(msg_chat_id, response, parse_mode='Markdown')
	except NameError as error:
		bot.sendMessage(msg_chat_id, "Unrecognized command: `{}`".format(msg['text']), parse_mode='Markdown')


def command_ping(msg):
	return "I'm still here. Tell me."


def command_ack(msg):
	return "`ack`: still under development."


def command_get(msg):
	return "`get`: still under development."


if 'TELEGRAM_BOT_TOKEN' not in os.environ or 'ICINGA2_API_USER' not in os.environ or 'ICINGA2_API_PWD' not in os.environ:
	print "Mandatory environment keys: TELEGRAM_BOT_TOKEN, ICINGA2_API_USER, ICINGA2_API_PWD"
	sys.exit(1)

bot = telepot.Bot(os.environ['TELEGRAM_BOT_TOKEN'])
MessageLoop(bot, sort_message).run_as_thread()

i = inotify.adapters.Inotify()
i.add_watch(sys.argv[0], mask=inotify.constants.IN_MODIFY)
for event in i.event_gen(yield_nones=False):
	print "Reloading updated bot version"
	os.execve(sys.argv[0], sys.argv, os.environ)
	sys.exit(1)
