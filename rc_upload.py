#!/usr/bin/env python3

from rcedit import RCEdit
import sys, os, stat
import tempfile
from glob import glob
from collections import defaultdict
from copy import copy


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
			return None
	else:
		try:
			element_id = element_name_id[element_id]
		except KeyError:
			return None

	return element_id

text_exts = ['.html', '.md', '.txt']
aux_exts = ['.css', '.bib']
script_exts = ['.sh', '.py']

def ext_scripts(ext):
	extb = os.path.splitext(ext)[0]
	return [f"{extb}{s}" for s in script_exts]

def ext_plus_scripts(ext):
	return [ext]+ext_scripts(ext)

text_plus_script_exts = []
for t in text_exts:
	text_plus_script_exts += ext_plus_scripts(t)
text_plus_script_exts = set(text_plus_script_exts)

def read_or_exec(fn, ext):
	if ext in ext_scripts(ext):
#		print(f"Executing {fn}")
		# execute script
		try:
			os.chmod(fn, stat.S_IEXEC+stat.S_ISUID) # make executable for owner (SUID)
			with os.popen(fn) as f:
				return f.read().encode("utf-8")
		except IOError:
			print(f"Cannot execute {fn}", file=sys.stderr)
	else:
#		print(f"Reading {fn}")
		with open(fn, 'rb') as f:
			return f.read()


if __name__ == "__main__":
	from argparse import ArgumentParser
	parser = ArgumentParser()

	parser.add_argument("rc_site_id", type=str, help="RC site ID")
	parser.add_argument("rc_user", type=str, help="RC username")
	parser.add_argument("rc_pw", type=str, help="RC password")
	parser.add_argument("source_dir", type=str, help="Source folder")
	parser.add_argument("-V", "--verbose", action='store_true', help="Verbose output")

	args = parser.parse_args()
	verbose = args.verbose

	# for scripts, change current to `source_dir`
	os.chdir(args.source_dir)

	# collect files
	filenames = []
	# files to consider in root dir
	for ext in aux_exts+script_exts:
		filenames += glob(os.path.join(args.source_dir, '.', f'*{ext}'))
	# files to consider in page dirs
	for ext in text_exts+aux_exts+script_exts:
		filenames += glob(os.path.join(args.source_dir, '*', f'*{ext}'))

	# log into RC
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
		if page_id is not None:
			item_id, file_ext = os.path.splitext(item_id_and_ext)
			if file_ext in script_exts:
				script_ext = file_ext
				item_id, file_ext = os.path.splitext(item_id)
				if file_ext == '': # only script extension, assume html output
					file_ext = '.html'
				file_ext = file_ext+script_ext # e.g., .html.py
			elements[page_id][file_ext][item_id] = filename
		else:
			print(f"Page '{path}' not found", file=sys.stderr)

	# collect global data
	css_global = b""
	bib_global = b""
	page_elements = elements.get('.', None)
	if page_elements is not None:
		if verbose:
			print(f"Collecting global data")
		for item_ext, items in page_elements.items():
			# work on CSS files
			if item_ext in ext_plus_scripts('.css'):
				# concatenate all available css files
				for item_id, filename in items.items():
					if verbose:
						print(f"\tUsing CSS file '{filename}' globally")
					css_global += read_or_exec(filename, item_ext)
			elif item_ext in ext_plus_scripts('.bib'):
				# concatenate all available bib files
				for item_id, filename in items.items():
					if verbose:
						print(f"\tUsing bibtex file '{filename}' globally")
					bib_global += read_or_exec(filename, item_ext)
		del elements['.']

	# walk through pages
	for page_id, page_elements in elements.items():
		if verbose:
			print(f"Working on page {page_id}")

		css_content = b""
		bib_content = copy(bib_global)

		# work on bib and CSS first
		for item_ext, items in page_elements.items():
			# work on CSS files
			if item_ext in ext_plus_scripts('.css'):
				# concatenate all available css files
				for item_id, filename in items.items():
					if verbose:
						print(f"\tIncluding CSS file '{filename}'")
					css_content += read_or_exec(filename, item_ext)
			elif item_ext in ext_plus_scripts('.bib'):
				# concatenate all available css files
				for item_id, filename in items.items():
					if verbose:
						print(f"\tIncluding bibtex file '{filename}'")
					bib_content += read_or_exec(filename, item_ext)

		# Set CSS
		if css_global or css_content:
			# get page options
			_, page_data = rc.page_options_get(page_id)

			# add css entry
			page_data['style']['rawcss'] = css_content
			if verbose:
				print(f"\tSet page rawcss")

			if css_global:
				# add site-wide css (only once)
				page_data['style']['expositionrawcss'] = css_global
				if verbose:
					print(f"\tSet exposition-wide rawcss")
				css_global = b""

			# set page options
			rc.page_options_set(page_id, **page_data)

		# Make bib file
		if bib_content:
			with tempfile.NamedTemporaryFile('wb', delete=False, suffix='.bib') as fp:
				bib_fn = fp.name
				fp.write(bib_content)
				fp.close()

		for item_ext, items in page_elements.items():

			if item_ext in text_plus_script_exts:
				# work on text files

				item_list = rc.item_list(page_id)
				item_dict = {k:v[-1] for k,v in item_list.items()}

				if False:
					# list all items
					for item_id,item_name in item_dict.items():
						item_type, item_data = rc.item_get(item_id)

				for item_name, filename in items.items():
					item_id = get_id(item_dict, item_name)
					if item_id is None:
						print(f"\tItem '{item_name}' not found", file=sys.stderr)
						continue

					item_type, item_data = rc.item_get(item_id)
					# item types are: html, text, picture, audio, video, slideshow, pdf, shape, note, embed

					if item_type in ('html', 'text'): #, 'note'):
						if item_ext in ext_plus_scripts('.html'):
							content = read_or_exec(filename, item_ext)
						else:
							# Convert to .html with pandoc

							# if we have a script, we first need to generate the source
							if item_ext in ext_scripts(item_ext):
								content = read_or_exec(filename, item_ext)
								extext = os.path.splitext(item_ext)[0]
								with tempfile.NamedTemporaryFile('wb', delete=False, suffix=extext) as fp:
									fp.write(content)
									filename = fp.name
								genname = filename
							else:
								genname = None

							# now work on the read/generated source
							with tempfile.NamedTemporaryFile(delete=False, suffix='.html') as fp:
								fp.close()
								bib = f"--bibliography='{bib_fn}'" if bib_content else ""
								os.system(f"pandoc '{filename}' --citeproc {bib} -t html -o '{fp.name}'")
								with open(fp.name, 'rb') as f:
									content = f.read()
								os.remove(fp.name)

							if genname is not None:
								os.remove(genname)

						# set item
						item_data['media']['textcontent'] = content
						rc.item_set(item_id, **item_data)
						if verbose:
							print(f"\tModified item {item_id} from '{filename}'")

					else:
						# item type not handled
						if verbose:
							print(f"\tItem {item_id} type ({item_type}) currently not handled")

		if bib_content:
		# Delete page-specific bib file
			os.remove(bib_fn)

	rc.logout()
