#!/usr/bin/env python3
from __future__ import print_function

from datetime import datetime, timedelta, timezone

import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import click
from prettytable import PrettyTable

@click.group()
def commands():
	pass
	
SCOPES = ['https://www.googleapis.com/auth/calendar']

def _create_service():
	creds = None
	if os.path.exists('token.json'):
		creds = Credentials.from_authorized_user_file('token.json', SCOPES)
	if not creds or not creds.valid:
		if creds and creds.expired and creds.refresh_token:
			creds.refresh(Request())
		else:
			flow = InstalledAppFlow.from_client_secrets_file(
							'credentials.json', SCOPES)
			creds = flow.run_local_server(port=0)
			with open('token.json', 'w') as token:
				token.write(creds.to_json())
				
	try:
		return build('calendar', 'v3', credentials=creds)
	except HttpError as error:
		print(f'An error occurred: {error}')


def _get_local_timezone_name():
	now = datetime.now()
	local_now = now.astimezone()
	local_tz = local_now.tzinfo
	return local_tz.tzname(local_now)


def _pretty_print_table(item_list: list):
	item_list.insert(0, ['start', 'id', 'title'])
	table = PrettyTable(item_list[0])
	table.add_rows(item_list[1:])
	print(table)
	

@click.command()
@click.argument('num', type=int, default=10)
def list_upcoming_events(num):
	service = _create_service()
	try:		
		now = datetime.utcnow().isoformat() + 'Z'
		print(f'Getting the upcoming {num} events')
		events_result = service.events().list(calendarId='primary', 
												timeMin=now, 
												maxResults=num,
												singleEvents=True,
												orderBy='startTime').execute()
		events = events_result.get('items', [])
		
		if not events:
			print('No upcoming events found.')
			return
		
		event_list = [(event['start'].get('dateTime', event['start'].get('date')),  event['id'], event['summary']) for event in events]
		_pretty_print_table(event_list)
		
	except HttpError as error:
		print(f'An error occurred: {error}')

		
		
@click.command()
@click.option('-y', '--year', type=int, default=datetime.now().year)
@click.option('-m', '--month', type=int, default=datetime.now().month)
def list_events_for_month(year, month):
	assert(month >= 1 and month <= 12)
	
	service = _create_service()
	try:
		start_date = datetime(year, month, 1).astimezone()
		
		if month < 12:
			month += 1
		else:
			month = 1
			year += 1
			
		end_date = datetime(year, month, 1).astimezone() - timedelta(milliseconds=1)
		print(f"Getting the events in \nfrom:{start_date.isoformat()} \n  to:{end_date.isoformat()}")
		events_result = service.events().list(calendarId='primary', 
												timeMin=start_date.isoformat(), 
												timeMax=end_date.isoformat(),
												singleEvents=True,
												orderBy='startTime').execute()
		events = events_result.get('items', [])

		if not events:
			print('No upcoming events found.')
			return
		
		event_list = [(event['start'].get('dateTime', event['start'].get('date')),  event['id'], event['summary']) for event in events]
		_pretty_print_table(event_list)
	except HttpError as error:
		print(f'An error occurred: {error}')


@click.command()
@click.option('-t', '--title', required=True)
@click.option('-sd', '--start_datetime', required=True, help="format example: 2022-10-10 18:00")
@click.option('-ed', '--end_datetime', required=True, help="format example: 2022-10-10 18:00")
@click.option('-tz', '--timezone', default=_get_local_timezone_name())
@click.option('-l', '--location', default='Unknown')
@click.option('-d', '--description', default='No description')
def add_event(title, start_datetime, end_datetime, timezone, location, description):
	service = _create_service()
	start = datetime.strptime(start_datetime, '%Y-%m-%d %H:%M')
	end = datetime.strptime(end_datetime, '%Y-%m-%d %H:%M')

	event = {
		'summary': title,
		'location': location,
		'description': description,
		'start': {
			'dateTime': start.isoformat(),
			'timeZone': timezone
		},
		'end': {
			'dateTime': end.isoformat(),
			'timeZone': timezone
		},
		'attendees': []
	}
	
	event = service.events().insert(calendarId='primary', body=event).execute()
	print(f"Event created successfully: {event.get('htmlLink')}")
	

@click.command()
@click.option('-i', '--id', required=True, help="ID of the calendar event")
def delete_event(id):
	service = _create_service()
	event = service.events().get(calendarId='primary', eventId=id).execute()
	if click.confirm(f"Do you want to delete this event: {event['start'].get('dateTime', event['start'].get('date'))}: {event['summary']}?"):
		service.events().delete(calendarId='primary', eventId=id).execute()
		print(f"Event has been deleted successfully: {event['start'].get('dateTime', event['start'].get('date'))}: {event['summary']}")
	else:
		print("You did not delete the event.")


commands.add_command(list_events_for_month)
commands.add_command(list_upcoming_events)
commands.add_command(add_event)
commands.add_command(delete_event)


if __name__ == '__main__':
	commands()