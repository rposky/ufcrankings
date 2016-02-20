#!/bin/python

import argparse
import re
import subprocess
import threading
import time

argument_parser = argparse.ArgumentParser(description='Compile UFC fighter rankings')
argument_parser.add_argument('input_file', type=argparse.FileType('r'))
args = argument_parser.parse_args()

win_count = -1
wins_processed = 0
table_row = -1
fighter_name = ''
fighter_win = False

for line in args.input_file:
	if not line:
		continue

	if win_count == -1:
		# attempt to parse the number of wins until it is found
		win_count_match = re.match("^Wins (?P<win_count>\d+) \d+ KO", line)
		if win_count_match:
			win_count = int(win_count_match.group('win_count'))
	else:
		# match table row characters
		if re.match("^[┌├][─┬┼]+[┐┤]$", line):
			table_row += 1
			if fighter_name and fighter_win:
				print("name: {}".format(fighter_name))
			fighter_name = ''
			fighter_win = False
		elif table_row > 0:
			# extract a portion of the fighter's name
			fighter_name_match = re.match("^│(?P<win>win)?\s+│(?P<name>[^│]+)│", line)
			if fighter_name_match:
				name = fighter_name_match.group('name').strip()
				fighter_win = fighter_win or fighter_name_match.group('win') == 'win'
				if name:
					fighter_name += name + ' '
