#!/usr/bin/env python3

from rcedit import RCEdit
import sys, os
import tempfile
from glob import glob
from collections import defaultdict


def is_num(s):
	try:
		int(s)
	except:
		return False
	return True


def get_id(element_dict, element_id):
	element_name_id = {v:k for k,v in element_dict.items()}

	if is_num(element_id):
		if not element_id in element_dict:
			print(f"Element '{element_id}' not found", file=sys.stderr)
			return None
	else:
		try:
			element_id = element_name_id[element_id]
		except KeyError:
			print(f"Element '{element_id}' not found", file=sys.stderr)
			return None

	return element_id


if __name__ == "__main__":
	from argparse import ArgumentParser
	parser = ArgumentParser()

	parser.add_argument("rc_site_id", type=str, help="RC site ID")
	parser.add_argument("rc_user", type=str, help="RC username")
	parser.add_argument("rc_pw", type=str, help="RC password")
	parser.add_argument("source_dir", type=str, help="Source folder")
	parser.add_argument("-V", "--verbose", action='store_true', help="Verbose output")

	args = parser.parse_args()

	filenames = []
	filenames += glob(os.path.join(args.source_dir, '.', '*.css'))
	filenames += glob(os.path.join(args.source_dir, '*', '*.css'))
	filenames += glob(os.path.join(args.source_dir, '*', '*.html'))
	filenames += glob(os.path.join(args.source_dir, '*', '*.md'))

	print("Files:", filenames)

	rc = RCEdit(args.rc_site_id) # RS intro
	rc.login(username=args.rc_user, password=args.rc_pw)

	# get pages
	pages = rc.page_list()

	# consolidate data locations
	elements = defaultdict(lambda: defaultdict(dict))
	for filename in filenames:
		path, item_id_and_ext = os.path.split(filename)
		path = path.split(os.path.sep)[-1]
		page_id = get_id(pages, path) if path != '.' else path
		item_id, file_ext = os.path.splitext(item_id_and_ext)
		elements[page_id][file_ext][item_id] = filename

	# collect global data
	css_global = ""
	page_elements = elements.get('.', None)
	if page_elements is not None:
		if args.verbose:
			print(f"Collecting global data")
		for item_ext, items in page_elements.items():
			# work on CSS files
			if item_ext == '.css':
				# concatenate all available css files
				for item_id, filename in items.items():
					with open(filename, 'r') as f:
						css_global += f.read()
		del elements['.']

	# walk through pages
	for page_id, page_elements in elements.items():
		if args.verbose:
			print(f"Working on page {page_id}")

		css_content = str(css_global)

		for item_ext, items in page_elements.items():

			if item_ext in ('.html', '.md', '.txt'):
				# work on text files

				item_list = rc.item_list(page_id)
				item_dict = {k:v[-1] for k,v in item_list.items()}

				for item_id, filename in items.items():
					item_id = get_id(item_dict, item_id)

					# Convert .md to .html with pandoc
					if item_ext == '.md':
						with tempfile.NamedTemporaryFile(delete=False) as fp:
							fp.close()
							os.system(f"pandoc '{filename}' -t html -o '{fp.name}'")
							with open(fp.name, 'r') as f:
								content = f.read()
							os.remove(fp.name)
					else:
						with open(filename, 'r') as f:
							content = f.read()

					item_type, item_data = rc.item_get(item_id)
					if item_type == 'html':
						item_data['media']['textcontent'] = content
						rc.item_set(item_id, **item_data)
						if args.verbose:
							print(f"\tModified item {item_id}")
					else:
						if args.verbose:
							print(f"\tItem {item_id} type is not HTML")

			# work on CSS files
			elif item_ext == '.css':
				# concatenate all available css files
				for item_id, filename in items.items():
					with open(filename, 'r') as f:
						css_content += f.read()


		# Set CSS
		if css_content:
			# get page options
			_, page_data = rc.page_options_get(page_id)
			# add css entry
			page_data['style']['rawcss'] = css_content
			# set page options
			rc.page_options_set(page_id, **page_data)
			if args.verbose:
				print(f"\tSet page rawcss")


	rc.logout()
