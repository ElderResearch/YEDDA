# -*- coding: utf-8 -*-
# @Author: Sam Ballerini from Elder Research, Inc.
# @Date:   2018-Sept-24
# @Last Modified by:   Sam Ballerini,     Contact: sam.ballerini@elderresearch.com
# !/usr/bin/env python

from tkinter import *
from tkinter.ttk import Frame, Button, Label, Scrollbar
from tkinter.filedialog import Open
from tkinter.font import Font
from collections import deque
import pickle
import os.path
import platform
import json
from random import choice
import re


class Example(Frame):
    def __init__(self, parent):
        Frame.__init__(self, parent)
        self.Version = "Yelder v1.0"
        self.OS = platform.system().lower()
        self.parent = parent
        self.fileName = ""
        self.anno_file_path = './annotations/'
        self.debug = False
        self.show_annotations = True
        self.history = deque(maxlen=20)
        self.currentContent = deque(maxlen=1)
        self.prev_selection_index = None

        with open('key_tag_map.json', 'rb') as json_file:
            self.key_tag_map = json.load(json_file)

        self.allKey = "0123456789abcdefghijklmnopqrstuvwxyz,./;'[]\-=`'"
        self.controlCommand = {'q': "unTag", 'ctrl+z': 'undo'}
        self.labelEntryList = []
        self.shortcutLabelList = []
        self.annotations = []

        # default GUI display parameter
        if len(self.key_tag_map) > 20:
            self.textRow = len(self.key_tag_map)
        else:
            self.textRow = 20
        self.textColumn = 5

        self.configFile = "config"
        self.entityRe = r'\[\@[\w\W]*?\#[\w\W]*?\*\](?!\#)'

        # configure color
        self.selectColor = 'light salmon'
        self.textFontStyle = "Times"
        self.initUI()

    def initUI(self):
        """ Build out the tkinter UI (called only upon initialization)

            Args:
                None

            Returns:
                None
        """
        self.parent.title(self.Version)
        self.pack(fill=BOTH, expand=True)

        for idx in range(0, self.textColumn):
            self.columnconfigure(idx, weight=2)
        self.columnconfigure(self.textColumn+2, weight=1)
        self.columnconfigure(self.textColumn+4, weight=1)
        for idx in range(0, 16):
            self.rowconfigure(idx, weight=1)

        self.lbl = Label(self, text="File: no file is opened")
        self.lbl.grid(sticky=W, pady=4, padx=5)
        self.fnt = Font(family=self.textFontStyle, size=self.textRow, weight="bold", underline=0)
        # self.text = Text(self, font=self.fnt, selectbackground=self.selectColor)
        self.text = Text(self, font=self.fnt)
        self.text.grid(row=1, column=0, columnspan=self.textColumn, rowspan=self.textRow, padx=12, sticky=E+W+S+N)

        self.sb = Scrollbar(self)
        self.sb.grid(row=1, column=self.textColumn, rowspan=self.textRow, padx=0, sticky=E+W+S+N)
        self.text['yscrollcommand'] = self.sb.set
        self.sb['command'] = self.text.yview

        abtn = Button(self, text="Open", command=self.onOpen)
        abtn.grid(row=1, column=self.textColumn + 1)

        cbtn = Button(self, text="Quit", command=self.quit)
        cbtn.grid(row=2, column=self.textColumn + 1, pady=4)

        sbtn = Button(self, text="Save", command=self.save_and_load_next)
        sbtn.grid(row=3, column=self.textColumn + 1, pady=4)

        for idx in range(0, len(self.allKey)):
            press_key = self.allKey[idx]
            self.text.bind(press_key, self.textReturnEnter)
            simplePressKey = "<KeyRelease-" + press_key + ">"
            self.text.bind(simplePressKey, self.deleteTextInput)

        self.text.bind('<Control-Key-z>', self.undo)
        self.text.bind('<Command-Key-z>', self.undo)

        # disable the default copy behavior for right clicking. On OSX, right
        # click is button2 whereas on other systems it's button3
        self.text.bind('<Button-2>', self.rightClick)
        self.text.bind('<Button-3>', self.rightClick)

        self.setMapShow()

    def rightClick(self, event):
        """ Event handler for right clicking the textbox (disables typical
            right click copy behavior)

            Args:
                event (Event): keyboard event passed by the mainloop

            Returns:
                None
        """
        if self.debug:
            print("Action Track: rightClick")
        pass

    def onOpen(self):
        """ Event handler for clicking the Open button

            Args:
                None

            Returns:
                None
        """
        ftypes = [('all files', '.*'),
                  ('text files', '.txt'),
                  ('ann files', '.ann')]
        dlg = Open(self, filetypes=ftypes)
        fl = dlg.show()
        if fl != '':
            self.text.delete("1.0", END)
            text = self.readFile(fl)
            self.text.insert(END, text)
            self.lbl.config(text="File: " + fl)
            self.autoLoadNewFile(self.fileName, "1.0")
            self.text.mark_set(INSERT, "1.0")

    def readFile(self, filename):
        """ Read the text in from the file

            Args:
                filename (str): the name of the file

            Returns:
                text (str): the text of the file
        """
        f = open(filename, "rU")
        text = f.read()
        self.fileName = filename
        self.doc_id = ''.join([d for d in self.fileName if d.isdigit()])
        return text

    def setFont(self, value):
        """ Set the font-related characteristics

            Args:
                event (Event): keyboard event passed by the mainloop

            Returns:
                None
        """
        _family = self.textFontStyle
        _size = value
        _weight = "bold"
        _underline = 0
        fnt = Font(family=_family, size=_size, weight=_weight, underline=_underline)
        Text(self, font=fnt)

    def textReturnEnter(self, event):
        """ Event handler for annotation keyboard shortcuts.

            Args:
                event (Event): keyboard event passed by the mainloop

            Returns:
                press_key (str): character of the keyboard event
        """
        press_key = event.char
        if self.debug:
            print("Action Track: textReturnEnter")
            print("event: ", press_key)
        self.pushToHistory()
        self.executeCursorCommand(press_key.lower())
        return press_key

    def undo(self, event):
        """ Reset the text to it's previous state and remove the last annotation

            Args:
                event (Event): keyboard event passed by the mainloop

            Returns:
                None
        """
        if self.debug:
            print("Action Track: undo")
        if len(self.history) > 0:
            historyCondition = self.history.pop()
            historyContent = historyCondition[0]
            cursorIndex = historyCondition[1]
            self.annotations = self.annotations[:-1]
            self.writeFile(self.fileName, historyContent, cursorIndex)
        else:
            print("History is empty!")
        self.text.insert(INSERT, 'p')

    def getText(self):
        textContent = self.text.get("1.0", "end-1c")
        textContent = textContent.encode('utf-8')
        return textContent

    def executeCursorCommand(self, command):
        """ Annotate a section of text according to the command (shortcut char)

            Args:
                command (str): lowercase keyboard shortcut character

            Returns:
                None
        """
        if self.debug:
            print("Action Track: executeCursorCommand")

        if command == "q":
            print('q: remove entity label')
            return

        elif command not in self.key_tag_map:
            return

        content = self.getText()

        # try to get highlighted text, if nothing is highlighted catch the error
        try:
            first_cursor_index = self.text.index(SEL_FIRST)
            cursor_index = self.text.index(SEL_LAST)
            self.prev_selection_index = first_cursor_index

            # break doc into sections
            above_content = self.text.get('1.0', first_cursor_index)
            raw_text = self.text.selection_get()
            below_content = self.text.get(cursor_index, "end-1c")

        except TclError:

            # nothing has been highlighted and we are not adding to a previous
            # annotation
            # TODO: Find a better way to handle this
            if self.prev_selection_index is None:
                return

            first_cursor_index = self.prev_selection_index
            cursor_index = self.text.index(INSERT)

            [line_id, column_id] = cursor_index.split('.')
            [prev_line_id, prev_column_id] = first_cursor_index.split('.')

            # Get all of the text up to the selection
            # at the beginning of a line
            if int(prev_column_id) == 0:
                # at the beginning of the first line of the document
                if int(prev_line_id) == 1:
                    above_content = ''
                else:  # at the beginning of some line (not the first)
                    above_content = self.text.get('1.0', str(int(prev_line_id) - 1) + '.end') + '\n'
            else:  # somewhere in a line (not the beginning)
                above_content = self.text.get('1.0', str(int(prev_line_id)) + '.' + str(int(prev_column_id)))

            # Get all of the text after the selection
            # need the index of the last character of the last line
            [last_line_id, last_column_id] = self.text.index('end-1c').split('.')
            # need the index of the last character of the selection's last line
            [temp_line_id, temp_column_id] = self.text.index(prev_line_id + '.end').split('.')

            # at the end of a line
            if column_id == temp_column_id:
                # at the end of the last line
                if line_id == last_line_id:
                    below_content = ''
                else:  # at the end of some line (not the last)
                    below_content = '\n' + self.text.get(str(int(line_id) + 1) + '.0', 'end-1c')
            else:  # somewhere in a line (not the end)
                below_content = self.text.get(line_id + '.' + str(int(column_id)), 'end-1c')

            # extract the text
            raw_text = self.text.get(self.prev_selection_index, line_id + '.' + str(int(column_id)))

        old_commands = []
        # detect if the selected text is already annotated
        if re.match(self.entityRe, raw_text) is not None:
            if self.debug:
                print("ENTITY DETECTED")

            # parse the selected text into original text and old entities
            # TODO: Add support for overlapping annotations
            parsed_string = [x.strip('*]') for x in raw_text.strip('[@*]').split('#')]
            raw_text = parsed_string[0]
            old_entities = [x.strip() for x in parsed_string[1:]]
            print("OLD ENTITIES")
            print(old_entities)
            old_commands = [list(self.key_tag_map.keys())[list(self.key_tag_map.values()).index(entity)] for entity in old_entities]

        # annotate the text
        if len(raw_text) > 0:
            entity_content, cursor_index = self.replaceString(raw_text, self.prev_selection_index, command, old_commands)

        if self.show_annotations:
            content = above_content + entity_content + below_content
        else:
            content = above_content + raw_text + below_content

        content = content.encode('utf-8')
        self.writeFile(self.fileName, content, cursor_index)
        print(self.annotations)

    def deleteTextInput(self, event):
        """ Delete the keyboard shortcut text from the textbox

            Args:
                event (Event): the keyboard shortcut

            Returns:
                None
        """
        if self.debug:
            print("Action Track: deleteTextInput")
        get_insert = self.text.index(INSERT)
        insert_list = get_insert.split('.')
        last_insert = insert_list[0] + "." + str(int(insert_list[1])-1)
        get_input = self.text.get(last_insert, get_insert)
        aboveHalf_content = self.text.get('1.0', last_insert).encode('utf-8')
        followHalf_content = self.text.get(last_insert, "end-1c")
        if len(get_input) > 0:
            followHalf_content = followHalf_content.replace(get_input, '', 1)
        content = aboveHalf_content + followHalf_content.encode('utf-8')
        self.writeFile(self.fileName, content, last_insert)

    def replaceString(self, content, cursor_index, new_key, keys=[]):
        """ Replace a string with the annotated string and move the cursorName

            Args:
                content (str): the string to format
                string (str): also the string to format? not sure why this is
                    being passed twice
                replaceType ([str]): list of lowercase keyboard shortcut
                    characters
                cursor_index (str): location of the cursor in the text box

            Returns:
                content (str): the annotated string
                newcursor_index (str): the recalculated cursor location after
                    inserting the string
        """
        assert new_key is not None, "new_key cannot be None"

        [line_id, column_id] = cursor_index.split('.')
        if (new_key not in keys):
            keys += [new_key]

        if all(k in self.key_tag_map for k in keys):
            self.annotations.append({'doc_id': self.doc_id, 'text': self.parse_tags(content), 'tag': self.key_tag_map[new_key]})
            ann_string = ' '.join(['#' + self.key_tag_map[k] for k in keys])
            if new_key is None:
                ann_string = ' ' + ann_string
            content = "[@" + content + ann_string + "*]"
            nlines = content.count('\n')
            if nlines == 0:
                new_cursor_index = line_id + "." + str(int(column_id) + len(content))
            else:
                overhang = len(content.splitlines()[-1])
                new_cursor_index = str(int(line_id) + nlines) + "." + str(overhang)
        else:
            print("Invalid command!")
            return content, cursor_index
        return content, new_cursor_index

    def parse_tags(self, s):
        """ Utility function for stripping out annotation characters

            Args:
                s (str): the annotation to strip

            Returns:
                s (str): the stripped annotation
        """
        s = re.sub(r'#(.*?)\*]', '', s)
        s = re.sub(r'\[*', '', s)
        return s

    def writeFile(self, fileName, content, newcursor_index):
        """ Write the annotated document to a file

            Args:
                fileName (str): the name of the file being operated on
                content (str): the updated contents of the file
                newcursor_index (str): where the cursor should be located when
                    the new file is reloaded

            Returns:
                None
        """
        if self.debug:
                print("Action track: writeFile")

        if len(fileName) > 0:
            if ".ann" in fileName:
                new_name = fileName
                ann_file = open(new_name, 'wb')
                ann_file.write(content)
                ann_file.close()
            else:
                new_name = fileName + '.ann'
                ann_file = open(new_name, 'wb')
                ann_file.write(content)
                ann_file.close()
            self.autoLoadNewFile(new_name, newcursor_index)
            self.text.tag_remove(SEL, "1.0", END)
        else:
            print("Don't write to empty file!")

    def autoLoadNewFile(self, fileName, newcursor_index):
        """ Automatically load the updated file so that we are always working
            on the most recent copy

            Args:
                fileName (str): name of the file
                newcursor_index (str): where to put the cursor after opening
                    the new file

            Returns:
                None
        """
        if self.debug:
            print("Action Track: autoLoadNewFile")
        if len(fileName) > 0:
            self.text.delete("1.0", END)
            text = self.readFile(fileName)
            self.text.insert("end-1c", text)
            self.lbl.config(text="File: " + fileName)
            self.text.mark_set(INSERT, newcursor_index)
            self.text.see(newcursor_index)
            # self.setCursorLabel(newcursor_index)

    def pushToHistory(self):
        """ Push a snapshot of the current text and cursor position to
            a double sided history queue

            Args:
                None

            Returns:
                None

        """

        if self.debug:
            print("Action Track: pushToHistory")
        currentList = []
        content = self.getText()
        cursorPosition = self.text.index(INSERT)
        currentList.append(content)
        currentList.append(cursorPosition)
        self.history.append(currentList)

    def setMapShow(self):
        """ Generate labels and entries for the tag options

            Args:
                None

            Returns:
                None
        """
        if os.path.isfile(self.configFile):
            with open(self.configFile, 'rb') as fp:
                self.key_tag_map = pickle.load(fp)
        row = 0
        mapLabel = Label(self, text="Shortcuts map Labels", foreground="blue", font=(self.textFontStyle, 14, "bold"))
        mapLabel.grid(row=0, column=self.textColumn + 2, columnspan=2, rowspan=1, padx=10)
        self.labelEntryList = []
        self.shortcutLabelList = []
        for key in sorted(self.key_tag_map):
            row += 1
            symbolLabel = Label(self, text=key + ": ", foreground="blue", font=(self.textFontStyle, 14, "bold"))
            symbolLabel.grid(row=row, column=self.textColumn + 2, columnspan=1, rowspan=1, padx=3)
            self.shortcutLabelList.append(symbolLabel)

            labelEntry = Entry(self, foreground="blue", font=(self.textFontStyle, 14, "bold"))
            labelEntry.insert(0, self.key_tag_map[key])
            labelEntry.grid(row=row, column=self.textColumn + 3, columnspan=1, rowspan=1)
            self.labelEntryList.append(labelEntry)

        self.command_box_lbl = Label(self, text="Add a command: ", foreground="Blue", font=(self.textFontStyle, 14, "bold"))
        self.command_box_lbl.grid(row=row+1, column=self.textColumn + 2, columnspan=1, rowspan=1, padx=4)
        self.add_command_box = Entry(self, foreground="blue", font=(self.textFontStyle, 14, "bold"))
        self.add_command_box.grid(row=row + 1, column=self.textColumn + 3, columnspan=1, rowspan=1)
        self.add_command_box.bind('<Return>', self.add_command)

    def add_command(self, event):
        """ Event handler for pressing enter inside the new command entry

            Args:
                event (Event): keyboard event passed by the mainloop

            Returns:
                None
        """
        text = self.add_command_box.get()
        command = self.get_key()
        # command = chr(ord('a') + len(self.key_tag_map))
        self.key_tag_map[command] = text
        self.save_key_tag_map()
        row = len(self.key_tag_map)

        self.command_box_lbl.grid(row=row+1, column=self.textColumn + 2, columnspan=1, rowspan=1, padx=4)
        self.add_command_box.grid(row=row+1, column=self.textColumn + 3, columnspan=1, rowspan=1)
        self.add_command_box.bind('<Return>', self.add_command)
        self.add_command_box.delete(0, 'end')

        symbolLabel = Label(self, text=command + ": ", foreground="blue", font=(self.textFontStyle, 14, "bold"))
        symbolLabel.grid(row=row, column=self.textColumn + 2, columnspan=1, rowspan=1, padx=3)
        self.shortcutLabelList.append(symbolLabel)

        labelEntry = Entry(self, foreground="blue", font=(self.textFontStyle, 14, "bold"))
        labelEntry.insert(0, self.key_tag_map[command])
        labelEntry.grid(row=row, column=self.textColumn + 3, columnspan=1, rowspan=1)
        self.labelEntryList.append(labelEntry)

    def get_key(self):
        all_keys = set(self.allKey)
        used_keys = list(self.key_tag_map.keys()) + ['q']
        keys = list(all_keys.difference(used_keys))
        assert keys != {}, "No shortcuts left to assign!"
        return choice(keys)

    def save_key_tag_map(self):
        with open('key_tag_map.json', 'w') as out_file:
            json.dump(self.key_tag_map, out_file)

    def save_and_load_next(self):
        with open(self.anno_file_path + self.doc_id + '.pkl', 'wb') as f:
            pickle.dump(self.annotations, f)

        self.annotations = []
        self.prev_selection_index = None
        self.onOpen()  # open a dialogue box to select a new file


def main():
    root = Tk()
    root.geometry("2600x1400")
    app = Example(root)
    app.setFont(17)
    root.mainloop()


if __name__ == '__main__':
    main()
