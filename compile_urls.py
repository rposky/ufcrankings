#!/bin/python

import argparse
import os
import signal
import subprocess
import threading
import time
from urllib.parse import urlparse

################################################################################
# Argument inputs include:
#
# input_file: A list of search entries, separated by newline
# context: An additional search value to append to all queries
# domain: The sought site resource domain, used to filter viable search results
# engine: The search engine to use
# sleep: The length of time to pause between processing chunks of 10
#
#################################################################################

argument_parser = argparse.ArgumentParser(description='Compile UFC fighter rankings')
argument_parser.add_argument('input_file', type=argparse.FileType('r'))
argument_parser.add_argument('-c', '--context', default='')
argument_parser.add_argument('-d', '--domain', default='sherdog.com')
argument_parser.add_argument('-e', '--engine', default='https://duckduckgo.com')
argument_parser.add_argument('-s', '--sleep', type=int, default=30)

args = argument_parser.parse_args()

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

def kill_process(pid):
	os.kill(pid, signal.SIGKILL)
	os.waitpid(-1, os.WNOHANG)
	print("Process {0} killed".format(pid))

###########################################
#                                         #
######## Main processing routine ##########
#                                         #
###########################################

output_file, error_file = get_output_files()

# iterate over sorted list of ufc fighters

processed = 0
for fighter in args.input_file:
	if not fighter:
		continue

	fighter = fighter.strip()
	print("Searching for link to {}...".format(fighter))

	# code derived by example: http://blog.quibb.org/2010/11/crawling-the-web-with-lynx/

	url = "{0}?q={1}".format(args.engine, "{} {} {}".format(args.domain, fighter, args.context))
	cmd = "lynx -dump -nolist -notitle \"{0}\"".format(url)
	
	process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
	timer = threading.Timer(60.0, kill_process, args=[process.pid])

	timer.start()
	results = process.stdout.read()
	timer.cancel()

	results = results.decode('utf-8', 'replace')

	found_link = False
	for line in iter(results.splitlines()):
		print(line)
		try:
			parsed_url = urlparse('//' + line.strip())
			if parsed_url.netloc == args.domain:
				output_file.write("{0},{1}\n"
					.format(
						fighter, 
						parsed_url.netloc + parsed_url.path
					)
				)

				found_link = True
				break
		except ValueError:
			continue

	if not found_link:
		print("Unable to find link to {0}".format(fighter))
		output_file.write("{0},\n".format(fighter))
		error_file.write(fighter + "\n")

	processed += 1
	if processed % 10 == 0:
		print('Delaying for {0} seconds'.format(args.sleep))
		time.sleep(args.sleep)
