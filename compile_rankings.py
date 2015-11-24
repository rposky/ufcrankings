#!/bin/python

import argparse
import re
import subprocess
import threading
import time

argument_parser = argparse.ArgumentParser(description='Compile UFC fighter rankings')
argument_parser.add_argument('input_file', type=argparse.FileType('r'))
argument_parser.add_argument('output_file', type=argparse.FileType('w'))
argument_parser.add_argument('error_file', type=argparse.FileType('w'))
args = argument_parser.parse_args()

def kill_process(pid):
	os.kill(pid, signal.SIGKILL)
	os.waitpid(-1, os.WNOHANG)
	print("Process {0} killed".format(pid))

# Parses the fighter name and the event name from a 
# string containing both, separated by spaces
# ex: Leonardo Gosling WFCA 3 
def parse_fighter_event(fighter_event):
	return fighter_event, ""

# iterate over sorted list of ufc fighters

for input_line in args.input_file:
	if not input_line:
		continue

	fighter, url = input_line.split(',', 1)
	print("Searching for data on {} at {}...".format(fighter, url))

	# TODO: Change to w3m for table support, e.g. w3m -dump {url}
	# See: http://www.microhowto.info/howto/convert_from_html_to_formatted_plain_text.html
	cmd = "lynx -dump -nolist -notitle \"{0}\"".format(url)
	
	process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
	timer = threading.Timer(60.0, kill_process, args=[process.pid])

	timer.start()
	results = process.stdout.read()
	timer.cancel()

	results = results.decode('utf-8', 'replace')
	print(results)

	win_count = -1
	wins_processed = 0

	for line in iter(results.splitlines()):
		if not line:
			continue

		if win_count == -1:
			# attempt to parse the number of wins until it is found
			win_count_match = re.match("\s+Wins (?P<win_count>\d+) \d+ KO", line)
			if win_count_match:
				win_count = int(win_count_match.group('win_count'))
		else:
			# attempt to parse the win events until all are found
			win_event_match = re.match("\s+win (?P<fighter_event>(?:[\w-]+ )+)- ", line)
			if win_event_match:
				fighter_event = win_event_match.group('fighter_event')
				match_fighter, event = parse_fighter_event(fighter_event)

				print(match_fighter)
				
				wins_processed += 1

				# stop processing after we have found all the wins
				if wins_processed == win_count:
					break

	if win_count == -1:
		args.error_file.write("No win count for {}\n".format(fighter))
	elif wins_processed != win_count:
		args.error_file.write(
			"Only {} of {} total wins were found for {}\n"
				.format(wins_processed, win_count, fighter)
		)

	break
