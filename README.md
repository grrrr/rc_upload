# rc_upload

## Introduction

The `rc_upload.py` script transfers contents of a folder structure containing text and media files to an existing [Research Catalogue ("RC")](https://www.researchcatalogue.net) exposition.

Call `rc_upload.py --help` for a list of options.

Compulsory arguments to the script are:

- `rc_site_id`: This is the ID of the RC exposition. In the case of an URL `https://www.researchcatalogue.net/view/1283942/1340975` this would be `1283942`.
- `rc_user`: Your RC login (an email address).
- `rc_pw`: Your RC password.
- `source_dir`: The folder where the text and media files to be transferred are located.

Internally, the [`rcedit`](https://github.com/grrrr/rcedit) python module is used to modify the exposition.


## Data structure

For each page in the RC exposition to be populated, there is a subfolder of `source_dir` with matching name or numerical weave ID, e.g. `default page` or `1340975`.

The contents of `*.css` files therein are injected into the `rawcss` fields of the respective RC page.
The contents of `*.bib` files are collected for bibliography references.

The contents of `*.html` or `*.txt` files are injected into the html tool object with matching names or numerical item identifier in the respective page. E.g., the contents of a repo file `default page/intro.html` would be injected into the html tool with the common name `intro` on the RC page named `default page`.

The same applies for `*.md` files, only that they are converted to HTML using `pandoc` before being injected.

Site-wide CSS settings are collected from the `*.css` files in the project root folder.
Global bibliography entries are collected from the `*.bib` files in the project root folder.


## Scripting

All of the file types above have scripting abilities, currently using `bash` and `python`.
If file extensions `.sh` or `.py` are appended to a file (e.g. resulting in `*.css.py`), the contents will be generated by the outputs to stdout of the executed script.

This can, for instance, be used to generate `base64` encoding for images or fonts as CSS elements.


## TODO

A global `abstract.txt` should be injected into the exposition abstract. 
At the moment, this functionality is not supported by `rcedit`.

Images and rich media files are not yet supported.
