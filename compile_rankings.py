#!/bin/python

import argparse
import inspect
import os
import re
import signal
import subprocess
import sys
import threading
import time

argument_parser = argparse.ArgumentParser(description='Compile UFC fighter rankings')
argument_parser.add_argument('input_file', type=argparse.FileType('r'))
argument_parser.add_argument('alias_file', type=argparse.FileType('r'))
argument_parser.add_argument('-s', '--sleep', type=int, default=30)
args = argument_parser.parse_args()

# Declare global variables
fighter_name_substitutions = re.compile("['’]")

def kill_process(pid):
	os.kill(pid, signal.SIGKILL)
	os.waitpid(-1, os.WNOHANG)
	print("Process {0} killed".format(pid))

def get_page_links(url):
	global fighter_name_substitutions

	## Retrieve the fighters web page using lynx
	cmd = "lynx -dump \"{0}\"".format(url)
	process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
	timer = threading.Timer(60.0, kill_process, args=[process.pid])

	print("Retrieving {} with lynx to extract document hyperlinks".format(url))

	timer.start()
	results = process.stdout.read()
	timer.cancel()

	results = results.decode('utf-8', 'replace')

	# Extract the list of hyperlinks from the lynx hyperlink dump
	#
	#    Visible links
    #    1. http://m.sherdog.com/fighter/AbdulKerim-Edilov-63045
    #    2. http://m.sherdog.com/fighter/AbdulKerim-Edilov-63045
    #    3. http://www.sherdog.com/news/news/list
    #    4. http://www.sherdog.com/news/news/list
    #    5. http://www.sherdog.com/boxing/
    #    6. http://www.sherdog.com/kickboxing/

	link_indices = {}
	visible_links = {}
	visible_links_title_match = False

	for line in iter(results.splitlines()):
		if not line:
			continue

		if not visible_links_title_match:
			# Attempt to parse the "Visible links" title until it is found
			visible_links_title_match = re.match("^\s+Visible links", line)
			# Look for hyperlinks in the fighter history and extract wins when found
			link_index_match = re.match("\s+win\s\[(?P<index>\d+)\](?P<value>[^\[]+)", line)
			if link_index_match:
				fighter_name = link_index_match.group('value').strip()
				fighter_name = re.sub(fighter_name_substitutions, '', fighter_name)

				link_indices[link_index_match.group('index')] = fighter_name
		else:
			visible_link_match = re.match("^\s+(?P<index>\d+)\.\s(?P<link>.*)\s*$", line)
			if visible_link_match:
				link = visible_link_match.group('link').strip()
				link = re.sub("^https?://(?:www\.)", '', link)

				visible_links[visible_link_match.group('index')] = link
			else:
				break

	fighter_links = {}
	for (index, value) in link_indices.items():
		fighter_links[value] = visible_links[index]

	return fighter_links

def get_output_files():

	cwd, script = os.path.split(os.path.abspath(__file__))
	output_directory = "{}/logs/{}".format(cwd.rstrip('/'), int(time.time()))
	output_file = "{}/output.txt".format(output_directory)
	error_file = "{}/error.txt".format(output_directory)

	try:
		print("Creating logs output directory {}".format(os.path.dirname(output_directory)))
		os.makedirs(output_directory)
		output_file = open(output_file, 'w')
		error_file = open(error_file, 'w')
	except OSError as exception:
		if exception.errno != errno.EEXIST:
			raise

	return output_file, error_file


###########################################
#                                         #
######## Main processing routine ##########
#                                         #
###########################################

output_file, error_file = get_output_files()

# iterate over sorted list of ufc fighters
input_fighter_url_map = {}
input_url_fighter_map = {}
input_fighter_ignored_mismatches = {}

for input_line in args.input_file:
	if not input_line:
		continue

	line_entries = input_line.split(',')

	fighter = line_entries[0].strip()
	url = line_entries[1].strip()
	ignore_mismatch = line_entries[2].strip() if len(line_entries) > 2 else ''

	# Remove potentially unrecognized characters from the fighter name
	fighter = re.sub(fighter_name_substitutions, '', fighter)

	if ignore_mismatch == '1':
		input_fighter_ignored_mismatches[fighter] = 1

	input_fighter_url_map[fighter] = url
	input_url_fighter_map[url] = fighter

# Parse the input list of fighter name aliases

input_fighter_aliases = {}

for input_line in args.alias_file:
	if not input_line:
		continue

	fighters = input_line.strip().split(',')
	for fighter in fighters:
		if not fighter:
			continue

		input_fighter_aliases[fighter.strip()] = fighters

processed = 0

for fighter in sorted(input_fighter_url_map):

	url = input_fighter_url_map[fighter].rstrip()
	if not url:
		print("Unrecognized url for {}".format(fighter))
		output_file.write("{0},\n".format(fighter))
		continue

	print("Searching for data on {} at {}...".format(fighter, url))
	fighter_page_links = get_page_links(url)

	## Retrieve the fighters web page using w3m for its table formatting
	cmd = "w3m -dump \"{0}\"".format(url)
	process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
	timer = threading.Timer(60.0, kill_process, args=[process.pid])

	timer.start()
	results = process.stdout.read()
	timer.cancel()

	results = results.decode('utf-8', 'replace')

	# Extract wins from the fighters web page from a table exemplified by the following
	#
	# ┌──────┬──────────────┬───────────────────────────┬────────────────────┬─┬────┐
    # │Result│Fighter       │Event                      │Method/Referee      │R│Time│
    # ├──────┼──────────────┼───────────────────────────┼────────────────────┼─┼────┤
    # │win   │Leonardo      │WFCA 3 - Grozny Battle     │TKO (Kicks)         │1│0:36│
    # │      │Gosling       │Jun / 13 / 2015            │Sergey Pelehovskiy  │ │    │
    # ├──────┼──────────────┼───────────────────────────┼────────────────────┼─┼────┤
    # │      │Tiago Monaco  │WFCA 1 - Grozny Battle     │Submission          │ │    │
    # │win   │Tosato        │Mar / 14 / 2015            │(Rear-Naked Choke)  │1│2:28│
    # │      │              │                           │Nikolay Sharipov    │ │    │
    # ├──────┼──────────────┼───────────────────────────┼────────────────────┼─┼────┤
    # │      │Stanislav     │PAC - Pancration Atrium Cup│Submission          │ │    │
    # │loss  │Molodcov      │2                          │(Rear-Naked Choke)  │1│2:11│
    # │      │              │Mar / 10 / 2010            │N/A                 │ │    │
    # └──────┴──────────────┴───────────────────────────┴────────────────────┴─┴────┘

	fighter_name = ''
	fighter_win = False
	table_row = -1
	ufc_event = False
	ufc_event_fighters = {}
	win_count = -1
	wins_processed = 0
	wins_fighter_names = []

	for line in iter(results.splitlines()):
		if not line:
			continue

		if win_count == -1:
			# attempt to parse the number of wins until it is found
			win_count_match = re.match("^Wins (?P<win_count>\d+) \d+ KO", line)
			if win_count_match:
				win_count = int(win_count_match.group('win_count'))
				if win_count == 0:
					break
		else:
			# match table row characters
			if re.match("^[┌├└][─┬┼┴]+[┐┤┘]$", line):
				table_row += 1
				if fighter_name and fighter_win:
					fighter_name = fighter_name.strip()
					fighter_name = re.sub(fighter_name_substitutions, '', fighter_name)

					wins_fighter_names.append(fighter_name)
					if ufc_event:
						ufc_event_fighters[fighter_name] = 1

					wins_processed += 1
					if wins_processed == win_count:
						# stop processing after we have found all the wins
						break
				
				fighter_name = ''
				fighter_win = False
				ufc_event = False
			
			elif table_row > 0:
				# extract a portion of the fighter's name
				fighter_name_match = re.match("^│(?P<win>win)?\s+│(?P<name>[^│]+)│(?P<ufc_event>UFC)?", line)
				if fighter_name_match:
					name = fighter_name_match.group('name').strip()
					fighter_win = fighter_win or fighter_name_match.group('win') == 'win'
					if name:
						fighter_name += name + ' '
					if fighter_name_match.group('ufc_event') == 'UFC':
						ufc_event = True

	if win_count == -1:
		error_file.write("No win count for {}\n".format(fighter))
	elif wins_processed != win_count:
		error_file.write(
			"Only {} of {} total wins were found for {}\n"
				.format(wins_processed, win_count, fighter)
		)

	output_file.write("{0},".format(fighter))
	for win_fighter_name in wins_fighter_names:

		# As wins_fighter_names and fighter_page_links are compiled from the same source, 
		#  assert their equivalence
		assert win_fighter_name in fighter_page_links, \
			"{} is not contained within {}".format(win_fighter_name, fighter_page_links)

		fighter_page_link = fighter_page_links[win_fighter_name]
		fighter_link_found = fighter_page_link in input_url_fighter_map
		win_fighter_name_found = win_fighter_name in input_fighter_url_map
		matched_fighter = False

		# If the matched fighter name is an alias, replace it with that used in the input file
		if not win_fighter_name_found and win_fighter_name in input_fighter_aliases:
			for fighter_name in input_fighter_aliases[win_fighter_name]:
				if fighter_name in input_fighter_url_map:
					win_fighter_name = fighter_name
					win_fighter_name_found = True
					break

		if not fighter_link_found and win_fighter_name_found:
			if win_fighter_name not in input_fighter_ignored_mismatches:
				error_file.write("{}: No match against {} for {}. Please review in input file and update the url\n"
					.format(fighter, win_fighter_name, fighter_page_link))
		elif fighter_link_found and not win_fighter_name_found:
			error_file.write("{}: A discrepancy exists between the listed fighter names in {} and {}. Update the fighter name\n"
				.format(fighter, input_url_fighter_map[fighter_page_link], win_fighter_name))
		elif fighter_link_found and win_fighter_name_found:
			output_file.write("{0},".format(win_fighter_name))
			matched_fighter = True

		if win_fighter_name in ufc_event_fighters and not matched_fighter:
			error_file.write("{}: Unmatched UFC fighter {}\n"
				.format(fighter, win_fighter_name))

	output_file.write("\n")

	processed += 1
	if processed % 10 == 0:
		print('Delaying for {0} seconds'.format(args.sleep))

		output_file.flush()
		error_file.flush()
		time.sleep(args.sleep)

output_file.close()
error_file.close()
