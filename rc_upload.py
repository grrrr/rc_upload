#!/usr/bin/env python3

from rcedit import RCEdit
import sys, os, stat
import tempfile
from glob import glob
from collections import defaultdict
from copy import copy
from functools import reduce
import subprocess
import yaml
import pdb
import re
from datetime import datetime

def is_num(s):
	try:
		int(s)
	except:
		return False
	return True


def get_id(element_dict, element_id):
	element_name_id = {v: k for k,v in element_dict.items()}

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
cfg_exts = ['.yml', '.yaml']
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

cfg_ext_plus_scripts = reduce(lambda x,y: x+y, (ext_plus_scripts(ext) for ext in cfg_exts))


def read_or_exec(fn, ext):
	content = b''
	if ext in ext_scripts(ext):
#		print(f"Executing {fn}")
		# execute script
		if False:
			try:
				st = os.stat(fn)
				os.chmod(fn, st.st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
#				os.chmod(fn, stat.S_IEXEC+stat.S_ISUID) # make executable for owner (SUID)
				os.chdir(os.path.split(fn)[0])
				with os.popen(f"'{fn}'") as f:
					content = f.read().encode("utf-8")
			except IOError:
				print(f"Cannot execute {fn}", file=sys.stderr)
		else:
			try:
				st = os.stat(fn)
				os.chmod(fn, st.st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
				result = subprocess.run([fn], capture_output=True, text=True, check=True)
				content = result.stdout.encode("utf-8")
			except IOError:
				print(f"Cannot execute {fn}", file=sys.stderr)
	else:
#		print(f"Reading {fn}")
		with open(fn, 'rb') as f:
			content = f.read()

	# convert content depending on format
	if ext in ('.yml', '.yaml'):
		content = yaml.safe_load(content)

	return content


def yaml_headers(content: str) -> dict:
	"""
	Extract YAML header data from a pandoc markdown file
	"""
	m = re.match(rb'^---\n(.*?)\n---\n', content, re.DOTALL)
	if m is not None:
	    return yaml.safe_load(m.group(1))
	else:
		return {}


class ModTime:
	def __init__(self):
		self.timestamp = float('inf')
	def update(self, fn):
		self.timestamp = min(self.timestamp, os.path.getmtime(fn))
	def get(self):
		try:
			return datetime.fromtimestamp(self.timestamp)
		except OverflowError:
			return datetime.max


if __name__ == "__main__":
	from argparse import ArgumentParser
	parser = ArgumentParser()

	parser.add_argument("rc_site_id", type=str, help="RC site ID")
	parser.add_argument("rc_user", type=str, help="RC username")
	parser.add_argument("rc_pw", type=str, help="RC password")
	parser.add_argument("source_dir", type=str, help="Source folder")
	parser.add_argument("-U", "--update", action='store_true', help="Update only (compare source with RC modification date)")
	parser.add_argument("-V", "--verbose", action='store_true', help="Verbose output")

	args = parser.parse_args()
	verbose = args.verbose

	# for scripts, change current to `source_dir`
	os.chdir(args.source_dir)

	# collect files
	filenames = []
	# files to consider in root dir
	for ext in aux_exts+script_exts+cfg_exts:
		filenames += glob(os.path.join(args.source_dir, '.', f'*{ext}'))
	# files to consider in page dirs
	for ext in text_exts+aux_exts+script_exts+cfg_exts:
		filenames += glob(os.path.join(args.source_dir, '*', f'*{ext}'))

	# log into RC
	rc = RCEdit(args.rc_site_id) # RS intro
	rc.login(username=args.rc_user, password=args.rc_pw)

	# get basic info
	info = rc.info_get()
	last_modified = datetime.strptime(info['last modified'], "%d/%m/%Y").date()
	if verbose:
		print(f"Last modified: {last_modified}", )

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
	css_globals = []
	cfg_global = {}
	bib_global = b""

	cfg_mod_date = ModTime()
	bib_mod_date = ModTime()
	css_mod_date = ModTime()

	global_elements = elements.get('.', None)
	if global_elements:
		# Global data
		if verbose:
			print(f"Collecting global data")
		for item_ext, items in global_elements.items():
			# work on CSS files
			if item_ext in ext_plus_scripts('.css'):
				# concatenate all available css files
				for _, filename in items.items():
					if verbose:
						print(f"\tUsing CSS file '{filename}' globally")
					css_mod_date.update(filename)
					css_globals.append((filename, read_or_exec(filename, item_ext)))
			elif item_ext in ext_plus_scripts('.bib'):
				# concatenate all available bib files
				for _, filename in items.items():
					if verbose:
						print(f"\tUsing bibtex file '{filename}' globally")
					bib_mod_date.update(filename)
					bib_global += read_or_exec(filename, item_ext)
			elif item_ext in cfg_ext_plus_scripts:
				# concatenate all available cfg files
				for _, filename in items.items():
					if verbose:
						print(f"\tUsing cfg file '{filename}' globally")
					cfg_mod_date.update(filename)
					cfg_global.update(read_or_exec(filename, item_ext))

		del elements['.']
		css_mod_date = css_mod_date.get()
		bib_mod_date = bib_mod_date.get()
		cfg_mod_date = cfg_mod_date.get()

	if cfg_global:
		_,meta = rc.meta_get()
		meta.update(cfg_global)
		rc.meta_set(**meta)

	# walk through pages
	for page_id, page_elements in elements.items():
		page_name = pages[str(page_id)]
		if verbose:
			print(f"Working on page {page_name}({page_id})")

		css_contents = []
		cfg_content = {}
		bib_content = copy(bib_global)

		css_page_mod = ModTime()
		bib_page_mod = ModTime()
		cfg_page_mod = ModTime()

		# work on CSS, bib and cfg first
		for item_ext, items in page_elements.items():
			# work on CSS files
			if item_ext in ext_plus_scripts('.css'):
				# concatenate all available css files
				for _, filename in items.items():
					if verbose:
						print(f"\tIncluding CSS file '{filename}'")
					css_page_mod.update(filename)
					css_contents.append((filename, read_or_exec(filename, item_ext)))
			elif item_ext in ext_plus_scripts('.bib'):
				# concatenate all available bib files
				for _, filename in items.items():
					if verbose:
						print(f"\tIncluding bibtex file '{filename}'")
					bib_page_mod.update(filename)
					bib_content += read_or_exec(filename, item_ext)
			elif False and item_ext in cfg_ext_plus_scripts:
				# concatenate all available cfg files
				for _, filename in items.items():
					if verbose:
						print(f"\tIncluding cfg file '{filename}'")
					cfg_page_mod.update(filename)
					cfg_content.update(read_or_exec(filename, item_ext))

		css_page_date = css_page_mod.get()
		bib_page_date = bib_page_mod.get()
		cfg_page_date = cfg_page_mod.get()

		# Set config
		if False and cfg_content:
			_,o = rc.page_options_get(page_id)
			o.update(cfg_content)
			rc.page_options_set(page_id, **o)

		# Set CSS
		if css_globals or css_contents:

			# get page options
			_, page_data = rc.page_options_get(page_id)

			# concatenate ordered (by filename) CSS definitions
			css_content = b''.join(v for _,v in sorted(css_contents, key=lambda x: x[0]))
			# add CSS entry
			page_data['style[rawCss][rawCss]'] = css_content
			if verbose:
				print(f"\tSet page rawCss")

			if css_globals:
				# concatenate ordered (by filename) CSS definitions
				css_global = b''.join(v for _,v in sorted(css_globals, key=lambda x: x[0]))
				# add site-wide CSS (only once)
				page_data['style[rawCss][expositionRawCss]'] = css_global
				if verbose:
					print(f"\tSet exposition-wide rawCss")
				css_globals = []

			# set page options
			rc.page_options_set(page_id, **page_data)

		# Make bib file
		if bib_content:
			with tempfile.NamedTemporaryFile('wb', delete=False, suffix='.bib') as fp:
				bib_fn = fp.name
				fp.write(bib_content)
				fp.close()

		item_list = dict(rc.item_list(page_id).items())
		item_dict = {k:v[1] for k,v in item_list.items()}

		# get config
		config = {}
		for item_ext, items in page_elements.items():
			if item_ext in cfg_ext_plus_scripts:
				for item_name, filename in items.items():
					config[item_name] = read_or_exec(filename, item_ext)

		for item_ext, items in page_elements.items():
			if item_ext in text_plus_script_exts:
				# work on text files

				for item_name, filename in items.items():
					item_id = get_id(item_dict, item_name)
					if item_id is None:
						print(f"\tItem '{item_name}' not found in page {page_id}", file=sys.stderr)
						continue

					item_mod_date = os.path.getmtime(filename)

					_, item_data = rc.item_get(page_id, item_id)
					item_type = item_list[item_id][0]
					# item types are: text (i.e., html), simpletext, picture, audio, video, slideshow, pdf, shape, note, embed

					# set config
					item_cfg = config.get(item_name, None)
					if item_cfg:
						item_data.update(item_cfg)

					if item_type in ('text', 'simpletext'):
						if item_ext in ext_plus_scripts('.html'):
							# no need to convert html input for html item
							content = read_or_exec(filename, item_ext)
						else:
							# Convert to .html with pandoc

							# if we have a script, we first need to generate the source
							content = read_or_exec(filename, item_ext)
							if item_ext in ext_scripts(item_ext):
								extext = os.path.splitext(item_ext)[0]

								with tempfile.NamedTemporaryFile('wb', delete=False, suffix=extext) as fp:
									fp.write(content)
									filename = fp.name
								genname = filename
							else:
								extext = item_ext
								genname = None

							# check for yaml config
							if extext == '.md':
								cfg = yaml_headers(content)
								item_data.update(cfg)

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
						# ATT: it is textContent for text and textcontent for simpletext... we need to explore
						keyname = "textContent" if item_type == 'text' else "textcontent"
						item_data[f'media[{keyname}]'] = content
						rc.item_set(page_id, item_id, **item_data)
						if verbose:
							print(f"\tModified item {item_name}({item_id}) from '{filename}'")

					else:
						# item type not handled
						if verbose:
							print(f"\tItem {item_id} type ({item_type}) currently not handled")

		if bib_content:
		# Delete page-specific bib file
			os.remove(bib_fn)

	rc.logout()
