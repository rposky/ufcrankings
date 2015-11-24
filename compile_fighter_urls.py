#!/bin/python

import argparse
import subprocess
import threading
import time
from urllib.parse import urlparse

argument_parser = argparse.ArgumentParser(description='Compile UFC fighter rankings')
argument_parser.add_argument('input_file', type=argparse.FileType('r'))
argument_parser.add_argument('output_file', type=argparse.FileType('w'))
argument_parser.add_argument('error_file', type=argparse.FileType('w'))
argument_parser.add_argument('-e', '--engine', default='https://duckduckgo.com')
argument_parser.add_argument('-s', '--sleep', type=int, default=30)
args = argument_parser.parse_args()

def kill_process(pid):
	os.kill(pid, signal.SIGKILL)
	os.waitpid(-1, os.WNOHANG)
	print("Process {0} killed".format(pid))

# iterate over sorted list of ufc fighters

processed = 0
for fighter in args.input_file:
	if not fighter:
		continue

	fighter = fighter.strip()
	print("Searching for link to {}...".format(fighter))

	# code derived by example: http://blog.quibb.org/2010/11/crawling-the-web-with-lynx/

	url = "{0}?q={1}".format(args.engine, fighter)
	cmd = "lynx -dump -nolist -notitle \"{0}\"".format(url)
	
	process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
	timer = threading.Timer(60.0, kill_process, args=[process.pid])

	timer.start()
	results = process.stdout.read()
	timer.cancel()

	results = results.decode('utf-8', 'replace')

	found_link = False
	for line in iter(results.splitlines()):
		try:
			parsed_url = urlparse('//' + line.strip())
			if parsed_url.netloc == 'sherdog.com':
				args.output_file.write("{0},{1}\n"
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
		args.output_file.write("{0},\n".format(fighter))
		args.error_file.write(fighter + "\n")

	processed += 1
	if processed % 10 == 0:
		print('Delaying for {0} seconds'.format(args.sleep))
		time.sleep(args.sleep)
