# Yelder: A Lightweight Tool for Text Annotation

This repo builds off of [Jie Yang](https://jiesutd.github.io)'s [YEDDA](https://github.com/jiesutd/YEDDA) project at Singapore University of Technology and Design (SUTD) between January of 2016 and May of 2018. 

Yelder is stripped down version of YEDDA that's been rebuilt to support multiline, multitag annotations and adding new tags on the fly. Yelder also exports `.pkl` files containing the annotations and tags for each document (as a list of dictionaries).

Yelder no longer supports tag recommendations or entity highlighting, although we hope to add back that functionality in the future. We have also removed the adminstrator tools for this first iteration.


## Get Started

Before running the app, open `settings.py` and edit the `key_tag_map` to create shortcuts for your tags. It's okay if you don't know all of the tags that you will use before you begin annotating - you can always add more from inside the app. 

To run the app, type `python annotator.py` and use the Open button to load your text file. Highlight the text you want to annotate and use the shortcut keys to add your tag. Once you've tagged a section, you can add more tags by placing the cursor at the right edge of your selection and clicking another keyboard shortcut. However, this method only works when the previous selection was on the same text. Therefore, in the event that you want to add another tag to a section of text that was not the very last section you tagged, you must highlight the section first. Also, `ctrl-z` or `cmd-z` will undo the most recent modification.
