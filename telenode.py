#!/usr/bin/env python2

import inotify.adapters
import inotify.constants
import os
import requests
import sys
import time
import telepot
from telepot.loop import MessageLoop
from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton


def on_chat_message(msg):
	msg_content_type, msg_chat_type, msg_chat_id = telepot.glance(msg)
	msg_command = msg['text'].split()[0].strip().lower()
	if len(msg_command) < 1 or msg_command[0] != '/' or msg_content_type != 'text':
		return

	msg_command = msg_command.replace('/', '')
	try:
		eval("command_" + msg_command)(msg, msg_chat_id)
		# if response == None:
		# 	bot.sendMessage(msg_chat_id, "Unable to do what asked for. Sorry.", parse_mode='Markdown')
		# elif 'keyboard' in response:
		# 	bot.sendMessage(msg_chat_id, response['msg'], parse_mode='Markdown', reply_markup=response['keyboard'])
		# else:
		# 	bot.sendMessage(msg_chat_id, response['msg'], parse_mode='Markdown')
	except NameError as error:
		bot.sendMessage(msg_chat_id, "Comando `{}` non riconosciuto".format(msg['text']), parse_mode='Markdown')


def command_ping(msg, msg_chat_id):
	bot.sendMessage(msg_chat_id, "In esecuzione da {}".format('?'), parse_mode='Markdown')


def command_ack(msg, msg_chat_id):
	keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=host['display_name'], callback_data="ack:" + host['display_name'].lower())] for host in icinga_hosts()])
	bot.sendMessage(msg_chat_id, "Seleziona un host", parse_mode='Markdown', reply_markup=keyboard)


def command_get(msg, msg_chat_id):
	pass


def on_callback_query(msg):
	msg_query_id, msg_chat_id, msg_data = telepot.glance(msg, flavor='callback_query')
	try:
		eval("callback_" + msg_data.split(':')[0])(msg_data, msg_chat_id, msg_query_id)
	except NameError as error:
		bot.sendMessage(msg_chat_id, "Impossibile eseguire hook su `{}`".format(msg_data), parse_mode='Markdown')

	# bot.sendMessage(msg_chat_id, msg_data, parse_mode='Markdown')
	# bot.answerCallbackQuery(msg_query_id, text="YEAH")


def callback_ack(msg_data, msg_chat_id, msg_query_id):
	# query: 'ack:host'
	if msg_data.count(':') == 1:
		keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Stato generale', callback_data=msg_data + ':overall')]] +
										[[InlineKeyboardButton(text=service, callback_data=msg_data + ':' + service.lower())] for service in ["Service1", "Service2", "Service3"]])
		bot.sendMessage(msg_chat_id, "Seleziona un servizio", parse_mode='Markdown', reply_markup=keyboard)
	# query: 'ack:host:service'
	elif msg_data.count(':') == 2:
		bot.answerCallbackQuery(msg_query_id, text="Inviato acknowledgment per \"{}\" / \"{}\"".format(msg_data.split(':')[1], msg_data.split(':')[2]))


def callback_get(msg, msg_chat_id, msg_query_id):
	pass


def icinga_hosts():
	hosts = list()
	request_response = _icinga_request('/v1/objects/hosts', 'GET')
	for host in request_response.json()['results']:
		hosts.append({
			'display_name': str(host['attrs']['display_name'])
		})
	return sorted(hosts, key=lambda k: k['display_name'])


def icinga_host_services(host):
	return []


def _icinga_request(url, method):
	global session
	global icinga2_host
	global icinga2_api_port
	session.headers = {
		'User-Agent': 'TeleBot',
		'X-HTTP-Method-Override': method.upper(),
		'Accept': 'application/json',
	}
	request_args = {
		'url': 'https://' + icinga2_host + ':' + icinga2_api_port + url,
		'verify': False,
	}
	return session.post(**request_args)

for env_key in ['TELEGRAM_BOT_TOKEN', 'ICINGA2_API_USER', 'ICINGA2_API_PWD']:
	if env_key not in os.environ:
		print "Mandatory environment key \"{}\" is empty.".format(env_key)
		sys.exit(1)

icinga2_host = os.environ['ICINGA2_HOST'] if 'ICINGA2_HOST' in os.environ else '127.0.0.1'
icinga2_api_port = os.environ['ICINGA2_API_PORT'] if 'ICINGA2_API_PORT' in os.environ else '5665'

session = requests.Session()
session.auth = (os.environ['ICINGA2_API_USER'], os.environ['ICINGA2_API_PWD'])

bot = telepot.Bot(os.environ['TELEGRAM_BOT_TOKEN'])
bot.message_loop({'chat': on_chat_message, 'callback_query': on_callback_query})
# MessageLoop(bot, sort_message).run_as_thread()

i = inotify.adapters.Inotify()
i.add_watch(sys.argv[0], mask=inotify.constants.IN_MODIFY)
for event in i.event_gen(yield_nones=False):
	print "Reloading updated bot version"
	os.execve(sys.argv[0], sys.argv, os.environ)
	sys.exit(1)
