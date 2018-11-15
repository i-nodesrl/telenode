#!/usr/bin/env python2

import inotify.adapters
import inotify.constants
import json
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

	if msg_command == 'start':
		return
	try:
		eval("command_" + msg_command)(msg, msg_chat_id)
	except NameError as error:
		bot.sendMessage(msg_chat_id, "Comando `{}` non eseguito: ```{}```".format(msg['text'], str(error)), parse_mode='Markdown')


def command_ping(msg, msg_chat_id):
	bot.sendMessage(msg_chat_id, "In esecuzione da {}".format('?'), parse_mode='Markdown')


def command_ack(msg, msg_chat_id):
	problems = icinga_get_problems()
	if len(problems) > 0:
		keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=problem['display_name'], callback_data="ack:" + problem['problem_name'])] for problem in problems])
		bot.sendMessage(msg_chat_id, "Seleziona un problema", parse_mode='Markdown', reply_markup=keyboard)
	else:
		bot.sendMessage(msg_chat_id, "Nessun problema rilevato.", parse_mode='Markdown')


def command_get(msg, msg_chat_id):
	pass


def command_broadcast(msg, msg_chat_id):
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
	msg_data = ':'.join(msg_data.split(':')[1:])
	action_response = icinga_do_ack(msg_data)
	bot.answerCallbackQuery(msg_query_id, text="Inviato acknowledgment di {} su {}".format(msg_data.split("!")[1], msg_data.split("!")[0]))


def callback_get(msg, msg_chat_id, msg_query_id):
	pass


def callback_broadcast(msg, msg_chat_id, msg_query_id):
	pass


def icinga_do_ack(problem):
	request_data = {
		'author': 'Telebot',
		'comment': 'Acknowledgement (via Telegram Bot)',
		'notify': True,
		'type': 'Service',
		'filter': 'service.__name == "{}"'.format(problem)
	}
	return _icinga_request('/v1/actions/acknowledge-problem', 'POST', json.dumps(request_data))


def icinga_get_hosts():
	hosts = list()
	request_response = _icinga_request('/v1/objects/hosts', 'GET')
	for host in request_response.json()['results']:
		hosts.append({
			'display_name': str(host['attrs']['display_name'])
		})
	return sorted(hosts, key=lambda k: k['display_name'])


def icinga_get_problems():
	# TODO: remove already acknowledged
	request_data = {
		'filter': 'service.state != service_state && service.acknowledgement == service_ack && host.acknowledgement != host_ack',
		'filter_vars': {
			'service_state': 0.0,
			'service_ack': 0,
			'host_ack': 2
		}
	}
	request_results = [{'display_name': problem['attrs']['__name'].replace('!', ': '), 'problem_name': problem['attrs']['__name']}
					   for problem in _icinga_request('/v1/objects/services', 'GET', json.dumps(request_data)).json()['results']]
	return sorted(request_results, key=lambda k: k['display_name'])


def icinga_host_services(host):
	return []


def _icinga_request(url, method, data={}):
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
		'data': data,
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
