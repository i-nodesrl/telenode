#!/usr/bin/env python2

import inotify.adapters
import inotify.constants
import json
import os
import pickle
import requests
import sys
import time
import telepot
from telepot.loop import MessageLoop
from telepot.namedtuple import ForceReply, InlineKeyboardMarkup, InlineKeyboardButton


def on_chat_message(msg):
	msg_content_type, msg_chat_type, msg_chat_id = telepot.glance(msg)

	global bot_users
	global bot_users_dump

	if msg_chat_id not in bot_users:
		print 'Registering {} ID to users library'.format(msg_chat_id)
		bot_users.add(msg_chat_id)
		print 'Writing {} users library to disk at {}'.format(list(bot_users), bot_users_dump)
		json.dump(list(bot_users), open(bot_users_dump, 'wb'))

	if 'reply_to_message' in msg:
		print '[{}] Command callback for handwritted message'.format(msg_chat_id)
		command_callback = msg['reply_to_message']['text'].split(':')[0].lower()
		print '[{}] Command detected: {}'.format(msg_chat_id, command_callback)
		try:
			eval("callback_" + command_callback)(msg, msg_chat_id, None)
		except NameError as error:
			print '[{}] Unable to fire function {}'.format(msg_chat_id, "callback_" + command_callback)
		return

	msg_command = msg['text'].split()[0].strip().lower()
	if len(msg_command) < 1 or msg_command[0] != '/' or msg_content_type != 'text':
		return

	msg_command = msg_command.replace('/', '')

	if msg_command == 'start':
		return
	try:
		print '[{}] Command recognized {}'.format(msg_chat_id, msg_command)
		eval("command_" + msg_command)(msg, msg_chat_id)
	except NameError as error:
		print '[{}] Unable to fire function {}'.format(msg_chat_id, "command_" + msg_command)
		bot.sendMessage(msg_chat_id, "Comando `{}` non eseguito: ```{}```".format(msg['text'], str(error)), parse_mode='Markdown')


def on_callback_query(msg):
	msg_query_id, msg_chat_id, msg_data = telepot.glance(msg, flavor='callback_query')
	try:
		eval("callback_" + msg_data.split(':')[0])(msg_data, msg_chat_id, msg_query_id)
	except NameError as error:
		bot.sendMessage(msg_chat_id, "Impossibile eseguire hook su `{}`".format(msg_data), parse_mode='Markdown')


def command_ping(msg, msg_chat_id):
	global bot_start_time
	delta = time.time() - bot_start_time
	delta_h = delta // 3600
	delta_m = delta // 60
	delta_s = delta - (delta_m * 60)
	bot.sendMessage(msg_chat_id, "Attivo. Tempo di esecuzione: {:02}:{:02}:{:02}.".format(int(delta_h), int(delta_m), int(delta_s)), parse_mode='Markdown')


def command_ack(msg, msg_chat_id):
	problems = icinga_get_problems()
	if len(problems) > 0:
		keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=problem['display_name'], callback_data="ack:" + problem['problem_name'])] for problem in problems])
		bot.sendMessage(msg_chat_id, "Seleziona un problema", parse_mode='Markdown', reply_markup=keyboard)
	else:
		bot.sendMessage(msg_chat_id, "Nessun problema rilevato.", parse_mode='Markdown')


def command_status(msg, msg_chat_id):
	problems = icinga_get_problems()
	if len(problems) > 0:
		keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=problem['display_name'], callback_data="status:" + problem['problem_name'])] for problem in problems])
		bot.sendMessage(msg_chat_id, "Sono stati rilevati i seguenti problemi", parse_mode='Markdown', reply_markup=keyboard)
	else:
		bot.sendMessage(msg_chat_id, "Nessun problema rilevato.", parse_mode='Markdown')


def command_broadcast(msg, msg_chat_id):
	markup = ForceReply()
	bot.sendMessage(msg_chat_id, 'Broadcast: inserire un messaggio da inviare.', reply_markup=markup)


def callback_ack(msg_data, msg_chat_id, msg_query_id):
	msg_data = ':'.join(msg_data.split(':')[1:])
	action_response = icinga_do_ack(msg_data)
	if '!' in msg_data:  # is a service
		bot.answerCallbackQuery(msg_query_id, text="Inviato acknowledgment di {} su {}".format(msg_data.split("!")[1], msg_data.split("!")[0]))
	else:  # is an host
		bot.answerCallbackQuery(msg_query_id, text="Inviato acknowledgment di {}".format(msg_data))


def callback_status(msg_data, msg_chat_id, msg_query_id):
	pass


def callback_broadcast(msg_data, msg_chat_id, msg_query_id):
	broadcast_sender = msg_data['chat']['first_name']
	if 'last_name' in msg_data['chat']:
		broadcast_sender += ' ' + msg_data['chat']['last_name']
	broadcast_sender_username = msg_data['chat']['username']
	broadcast_content = msg_data['text']

	global bot_users
	for mid in bot_users:
		if mid != msg_chat_id:
			print '[{}] Sending broadcast message to {}'.format(msg_chat_id, mid)
			bot.sendMessage(mid, "Messaggio da {} ({}):\n```{}```".format(broadcast_sender, broadcast_sender_username, broadcast_content), parse_mode='Markdown')
	bot.sendMessage(msg_chat_id, "Messaggio broadcast inviato a {} contatto/i.".format(len(bot_users) - 1), parse_mode='Markdown')


def icinga_do_ack(problem):
	if '!' in problem:  # is a service
		request_data = {
			'author': 'Telebot',
			'comment': 'Acknowledgement (via Telegram Bot)',
			'notify': True,
			'type': 'Service',
			'filter': 'service.__name == "{}"'.format(problem)
		}
	else:  # is an host
		request_data = {
			'author': 'Telebot',
			'comment': 'Acknowledgement (via Telegram Bot)',
			'notify': True,
			'type': 'Host',
			'filter': 'host.__name == "{}"'.format(problem)
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
	# services problems
	request_data = {
		'filter': 'service.state != service_state && host.state == host_state && service.acknowledgement == service_ack && host.acknowledgement != host_ack',
		'filter_vars': {
			'service_state': 0.0,  # ServiceOK
			'host_state': 0,  # HostUP
			'service_ack': 0,  # un-acknowledged
			'host_ack': 2  # acknowledged
		}
	}
	request_results = [{
		'display_name': problem['attrs']['__name'].replace('!', ': '),
		'problem_name': problem['attrs']['__name'],
	}
		for problem in _icinga_request('/v1/objects/services', 'GET', json.dumps(request_data)).json()['results']]
	# hosts problems
	request_data = {
		'filter': 'host.state != host_state && host.acknowledgement != host_ack',
		'filter_vars': {
			'host_state': 0,  # HostUP
			'host_ack': 1  # acknowledged
		}
	}
	request_results += [{
		'display_name': '{}: down'.format(problem['attrs']['__name']),
		'problem_name': problem['attrs']['__name'],
	}
		for problem in _icinga_request('/v1/objects/hosts', 'GET', json.dumps(request_data)).json()['results']]
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
		'timeout': 1,
		'verify': False,
	}
	while True:
		try:
			return session.post(**request_args)
		except Exception as e:
			print "Request error: " + str(e) + ". Retrying..."

for env_key in ['TELEGRAM_BOT_TOKEN', 'ICINGA2_API_USER', 'ICINGA2_API_PWD']:
	if env_key not in os.environ:
		print "Mandatory environment key \"{}\" is empty.".format(env_key)
		sys.exit(1)

proc_path = os.path.abspath(os.path.dirname(sys.argv[0]))

icinga2_host = os.environ['ICINGA2_HOST'] if 'ICINGA2_HOST' in os.environ else '127.0.0.1'
icinga2_api_port = os.environ['ICINGA2_API_PORT'] if 'ICINGA2_API_PORT' in os.environ else '5665'

session = requests.Session()
session.auth = (os.environ['ICINGA2_API_USER'], os.environ['ICINGA2_API_PWD'])

bot = telepot.Bot(os.environ['TELEGRAM_BOT_TOKEN'])
bot_users = set()
bot_users_dump = "{}/{}".format(proc_path, '.users.json')

print "Script is in {}".format(proc_path)
if os.path.isfile(bot_users_dump):
	print 'Reloading users library at {}'.format(bot_users_dump)
	bot_users = set(json.load(open(bot_users_dump, 'rb')))
	print 'Users library members: {}'.format(len(bot_users))

bot_start_time = time.time()
bot.message_loop({'chat': on_chat_message, 'callback_query': on_callback_query})

i = inotify.adapters.Inotify()
i.add_watch(sys.argv[0], mask=inotify.constants.IN_MODIFY)
i.add_watch(bot_users_dump, mask=inotify.constants.IN_MODIFY)
for event in i.event_gen(yield_nones=False):
	print "Reloading updated bot version"
	os.execve(sys.argv[0], sys.argv, os.environ)
	sys.exit(1)
