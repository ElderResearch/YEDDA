# -*- coding: utf-8 -*-
# @Author: Jie Yang from SUTD
# @Date:   2016-Jan-06 17:11:59
# @Last Modified by:   Jie Yang,     Contact: jieynlp@gmail.com
# @Last Modified time: 2018-07-15 20:33:40
# !/usr/bin/env python
# coding=utf-8

from Tkinter import *
from ttk import *  # Frame, Button, Label, Style, Scrollbar
import tkFileDialog
import tkFont
import re
from collections import deque, OrderedDict
import pickle
import os.path
import platform
import tkMessageBox


class Example(Frame):
    def __init__(self, parent):
        Frame.__init__(self, parent)
        self.Version = "YEDDA-V1.0 Annotator"
        self.OS = platform.system().lower()
        self.parent = parent
        self.fileName = ""
        self.debug = True
        self.colorAllChunk = False
        self.history = deque(maxlen=20)
        self.currentContent = deque(maxlen=1)
        self.prev_selection_index = None
        # TODO: Adding new categories/shortcuts on the fly
        self.pressCommand = {'a': "Artifical",
                             'b': "Event",
                             'c': "Fin-Concept",
                             'd': "Location",
                             'e': "Organization",
                             'f': "Person",
                             'g': "Sector",
                             'h': "Other"
                             }
        self.allKey = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
        self.controlCommand = {'q': "unTag", 'ctrl+z': 'undo'}
        self.labelEntryList = []
        self.shortcutLabelList = []

        # default GUI display parameter
        if len(self.pressCommand) > 20:
            self.textRow = len(self.pressCommand)
        else:
            self.textRow = 20
        self.textColumn = 5
        self.tagScheme = "BMES"
        self.onlyNP = False  # for exporting sequence

        self.configFile = "config"
        # self.entityRe = r'\[\@.*?\#.*?\*\](?!\#)'
        # self.entityRe = r'\[\@{\w\W}*?\#{\w\W}*?\*\](?!\#)'
        self.entityRe = r'\[\@[\w\W]*?\#[\w\W]*?\*\](?!\#)'
        self.tclEntityRe = r'\[\@{\w\W}*\#{\w\W}*\*\](?!\#)'
        self.insideNestEntityRe = r'\[\@\[\@(?!\[\@).*?\#.*?\*\]\#'

        # configure color
        self.entityColor = "SkyBlue1"
        self.insideNestEntityColor = "light slate blue"
        self.selectColor = 'light salmon'
        self.textFontStyle = "Times"
        self.initUI()

    def initUI(self):

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
        self.fnt = tkFont.Font(family=self.textFontStyle, size=self.textRow, weight="bold", underline=0)
        self.text = Text(self, font=self.fnt, selectbackground=self.selectColor)
        self.text.grid(row=1, column=0, columnspan=self.textColumn, rowspan=self.textRow, padx=12, sticky=E+W+S+N)

        self.sb = Scrollbar(self)
        self.sb.grid(row=1, column=self.textColumn, rowspan=self.textRow, padx=0, sticky=E+W+S+N)
        self.text['yscrollcommand'] = self.sb.set
        self.sb['command'] = self.text.yview
        # self.sb.pack()

        abtn = Button(self, text="Open", command=self.onOpen)
        abtn.grid(row=1, column=self.textColumn + 1)

        ubtn = Button(self, text="ReMap", command=self.renewPressCommand)
        ubtn.grid(row=2, column=self.textColumn + 1, pady=4)

        # exportbtn = Button(self, text="Export", command=self.generateSequenceFile)
        # exportbtn.grid(row=3, column=self.textColumn + 1, pady=4)

        cbtn = Button(self, text="Quit", command=self.quit)
        cbtn.grid(row=3, column=self.textColumn + 1, pady=4)

        self.cursorName = Label(self, text="Cursor: ", foreground="Blue", font=(self.textFontStyle, 14, "bold"))
        self.cursorName.grid(row=9, column=self.textColumn + 1, pady=4)
        self.cursorIndex = Label(self, text=("row: %s\ncol: %s" % (0, 0)), foreground="red", font=(self.textFontStyle, 14, "bold"))
        self.cursorIndex.grid(row=10, column=self.textColumn + 1, pady=4)

        for idx in range(0, len(self.allKey)):
            press_key = self.allKey[idx]

            self.text.bind(press_key, self.textReturnEnter)
            simplePressKey = "<KeyRelease-" + press_key + ">"
            self.text.bind(simplePressKey, self.deleteTextInput)
            if self.OS != "windows":
                controlPlusKey = "<Control-Key-" + press_key + ">"
                self.text.bind(controlPlusKey, self.keepCurrent)
                altPlusKey = "<Command-Key-" + press_key + ">"
                self.text.bind(altPlusKey, self.keepCurrent)

        self.text.bind('<Control-Key-z>', self.backToHistory)

        '''
        disable the default  copy behaivour when right click. For MacOS, right
        click is button 2, other systems are button3
        '''
        self.text.bind('<Button-2>', self.rightClick)
        self.text.bind('<Button-3>', self.rightClick)

        self.text.bind('<Double-Button-1>', self.doubleLeftClick)
        self.text.bind('<ButtonRelease-1>', self.singleLeftClick)

        self.setMapShow()

    # cursor index show with the left click
    def singleLeftClick(self, event):
        if self.debug:
            print "Action Track: singleLeftClick"
        cursor_index = self.text.index(INSERT)
        row_column = cursor_index.split('.')
        cursor_text = ("row: %s\ncol: %s" % (row_column[0], row_column[-1]))
        self.cursorIndex.config(text=cursor_text)

    def doubleLeftClick(self, event):
        if self.debug:
            print "Action Track: doubleLeftClick"
        pass

    # Disable right click default copy selection behaviour
    def rightClick(self, event):
        if self.debug:
            print "Action Track: rightClick"
        try:
            firstSelection_index = self.text.index(SEL_FIRST)
            cursor_index = self.text.index(SEL_LAST)
            content = self.text.get('1.0', "end-1c").encode('utf-8')
            self.writeFile(self.fileName, content, cursor_index)
        except TclError:
            pass

    def onOpen(self):
        ftypes = [('all files', '.*'),
                  ('text files', '.txt'),
                  ('ann files', '.ann')]
        dlg = tkFileDialog.Open(self, filetypes=ftypes)
        fl = dlg.show()
        if fl != '':
            self.text.delete("1.0", END)
            text = self.readFile(fl)
            self.text.insert(END, text)
            self.setNameLabel("File: " + fl)
            self.autoLoadNewFile(self.fileName, "1.0")
            self.text.mark_set(INSERT, "1.0")
            self.setCursorLabel(self.text.index(INSERT))

    def readFile(self, filename):
        f = open(filename, "rU")
        text = f.read()
        self.fileName = filename
        return text

    def setFont(self, value):
        _family = self.textFontStyle
        _size = value
        _weight = "bold"
        _underline = 0
        fnt = tkFont.Font(family=_family, size=_size, weight=_weight, underline=_underline)
        Text(self, font=fnt)

    def setNameLabel(self, new_file):
        self.lbl.config(text=new_file)

    def setCursorLabel(self, cursor_index):
        if self.debug:
            print "Action Track: setCursorLabel"
        row_column = cursor_index.split('.')
        cursor_text = ("row: %s\ncol: %s" % (row_column[0], row_column[-1]))
        print cursor_text
        self.cursorIndex.config(text=cursor_text)

    def textReturnEnter(self, event):
        """ Event handler for annotation keyboard shortcuts.

            Args:
                event (Event): keyboard event passed by the mainloop

            Returns:
                press_key (str): character of the keyboard event
        """
        press_key = event.char
        if self.debug:
            print "Action Track: textReturnEnter"
        self.pushToHistory()
        print "event: ", press_key
        self.executeCursorCommand(press_key.lower())
        return press_key

    def backToHistory(self, event):
        if self.debug:
            print "Action Track: backToHistory"
        if len(self.history) > 0:
            historyCondition = self.history.pop()
            historyContent = historyCondition[0]
            cursorIndex = historyCondition[1]
            self.writeFile(self.fileName, historyContent, cursorIndex)
        else:
            print "History is empty!"
        self.text.insert(INSERT, 'p')

    def keepCurrent(self, event):
        if self.debug:
            print "Action Track: keepCurrent"
        print("keep current, insert:%s" % (INSERT))
        print "before:", self.text.index(INSERT)
        self.text.insert(INSERT, 'p')
        print "after:", self.text.index(INSERT)

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
            print "Action Track: executeCursorCommand"

        content = self.getText()
        # try to get highlighted text, if nothing is highlighted catch the error
        try:
            first_cursor_index = self.text.index(SEL_FIRST)
            cursor_index = self.text.index(SEL_LAST)
            self.prev_selection_index = first_cursor_index

            # break doc into sections
            above_content = self.text.get('1.0', first_cursor_index)
            selected_string = self.text.selection_get()
            below_content = self.text.get(cursor_index, "end-1c")
            entity_content = ''

            old_commands = []
            if re.match(self.entityRe, selected_string) is not None:  # update old annotation
                if self.debug:
                    print "ENTITY DETECTED"

                # parse the selected text into original text and old entities
                parsed_string = selected_string.strip('[@*]').split('#')
                selected_string = parsed_string[0]
                old_entities = [x.strip() for x in parsed_string[1:]]
                old_commands = [self.pressCommand.keys()[self.pressCommand.values().index(entity)] for entity in old_entities]

            if command == "q":
                print 'q: remove entity label'
            else:
                if len(selected_string) > 0:
                    if command in self.pressCommand:
                        entity_content, cursor_index = self.replaceString(selected_string, selected_string, first_cursor_index, command, old_commands)
                    else:
                        return
            content = above_content + entity_content + below_content
            content = content.encode('utf-8')
            self.writeFile(self.fileName, content, cursor_index)

        except TclError:

            # nothing has been highlighted and we are not adding to a previous
            # annotation
            if self.prev_selection_index is None:
                return

            cursor_index = self.text.index(INSERT)
            [line_id, column_id] = cursor_index.split('.')
            [prev_line_id, prev_column_id] = self.prev_selection_index.split('.')

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

            # find the old entity inside the selected text
            text = self.text.get(self.prev_selection_index, line_id + '.' + str(int(column_id)))
            matched_span = (-1, -1)
            entity_detected = False
            for match in re.finditer(self.entityRe, text):
                if self.debug:
                    print "ENTITY DETECTED"
                # if the cursor position is inside (inclusive) of the selected text
                matched_span = match.span()
                entity_detected = True
                break

            text_before_entity = text
            text_after_entity = ""
            # if the entity match doesn't end at the beginning of a line
            if matched_span[1] > 0:
                selected_string = text[matched_span[0]:matched_span[1]]
                if entity_detected:
                    new_string_list = selected_string.strip('[@*]').split('#')
                new_string = new_string_list[0]
                old_entity_type = [x.strip() for x in new_string_list[1:]]
                text_before_entity = text[:matched_span[0]]
                text_after_entity = text[matched_span[1]:]
                selected_string = new_string
                entity_content = selected_string
                cursor_shift = ' '.join(['#' + string for string in new_string_list[1:]])
                old_keys = [self.pressCommand.keys()[self.pressCommand.values().index(entity)] for entity in old_entity_type]
                if command == "q":
                    print 'q: remove entity label'
                else:
                    if len(selected_string) > 0:
                        if command in self.pressCommand:
                            entity_content, cursor_index = self.replaceString(selected_string, selected_string, self.prev_selection_index, command, old_keys)
                        else:
                            return
                text_before_entity += entity_content

            content = above_content + text_before_entity + below_content
            content = content.encode('utf-8')
            self.writeFile(self.fileName, content, cursor_index)

    def deleteTextInput(self, event):
        if self.debug:
            print "Action Track: deleteTextInput"
        get_insert = self.text.index(INSERT)
        print "delete insert:", get_insert
        insert_list = get_insert.split('.')
        last_insert = insert_list[0] + "." + str(int(insert_list[1])-1)
        print last_insert
        get_input = self.text.get(last_insert, get_insert).encode('utf-8')
        aboveHalf_content = self.text.get('1.0', last_insert).encode('utf-8')
        followHalf_content = self.text.get(last_insert, "end-1c").encode('utf-8')
        if len(get_input) > 0:
            followHalf_content = followHalf_content.replace(get_input, '', 1)
        content = aboveHalf_content + followHalf_content
        self.writeFile(self.fileName, content, last_insert)

    def replaceString(self, content, string, cursor_index, new_key, keys=[]):
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

        if all(k in self.pressCommand for k in keys):
            ann_string = ' '.join(['#' + self.pressCommand[k] for k in keys])
            if new_key is None:
                ann_string = ' ' + ann_string
            new_string = "[@" + string + ann_string + "*]"
            nlines = new_string.count('\n')
            if nlines == 0:
                new_cursor_index = line_id + "." + str(int(column_id) + len(new_string))
            else:
                overhang = len(new_string.splitlines()[-1])
                new_cursor_index = str(int(line_id) + nlines) + "." + str(overhang)
        else:
            print "Invaild command!"
            print "cursor index: ", self.text.index(INSERT)
            return content, cursor_index
        content = content.replace(string, new_string, 1)
        return content, new_cursor_index

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
                print "Action track: writeFile"

        if len(fileName) > 0:
            if ".ann" in fileName:
                new_name = fileName
                ann_file = open(new_name, 'w')
                ann_file.write(content)
                ann_file.close()
            else:
                new_name = fileName + '.ann'
                ann_file = open(new_name, 'w')
                ann_file.write(content)
                ann_file.close()
            self.autoLoadNewFile(new_name, newcursor_index)
        else:
            print "Don't write to empty file!"

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
            print "Action Track: autoLoadNewFile"
        if len(fileName) > 0:
            self.text.delete("1.0", END)
            text = self.readFile(fileName)
            self.text.insert("end-1c", text)
            self.setNameLabel("File: " + fileName)
            self.text.mark_set(INSERT, newcursor_index)
            self.text.see(newcursor_index)
            self.setCursorLabel(newcursor_index)
            self.setColorDisplay()

    def setColorDisplay(self):
        if self.debug:
            print "Action Track: setColorDisplay"
        self.text.config(insertbackground='red', insertwidth=4, font=self.fnt)

        countVar = StringVar()
        currentCursor = self.text.index(INSERT)
        lineStart = currentCursor.split('.')[0] + '.0'
        lineEnd = currentCursor.split('.')[0] + '.end'

        if self.colorAllChunk:
            self.text.mark_set("matchStart", "1.0")
            self.text.mark_set("matchEnd", "1.0")
            self.text.mark_set("searchLimit", 'end-1c')
        else:
            self.text.mark_set("matchStart", lineStart)
            self.text.mark_set("matchEnd", lineStart)
            self.text.mark_set("searchLimit", lineEnd)
        while True:
            self.text.tag_configure("catagory", background=self.entityColor)
            self.text.tag_configure("edge", background=self.entityColor)
            # pos = self.text.search(self.entityRe, "matchEnd", "searchLimit", count=countVar, regexp=True)
            pos = self.text.search(self.tclEntityRe, "matchEnd", "searchLimit", count=countVar, regexp=True)
            if pos == "":
                break
            print "POS"
            print pos
            self.text.mark_set("matchStart", pos)
            self.text.mark_set("matchEnd", "%s+%sc" % (pos, countVar.get()))

            first_pos = pos
            second_pos = "%s+%sc" % (pos, str(1))
            lastsecond_pos = "%s+%sc" % (pos, str(int(countVar.get())-1))
            last_pos = "%s + %sc" % (pos, countVar.get())

            self.text.tag_add("catagory", second_pos, lastsecond_pos)
            self.text.tag_add("edge", first_pos, second_pos)
            self.text.tag_add("edge", lastsecond_pos, last_pos)

        # color the most inside span for nested span, scan from begin to end
        if self.colorAllChunk:
            self.text.mark_set("matchStart", "1.0")
            self.text.mark_set("matchEnd", "1.0")
            self.text.mark_set("searchLimit", 'end-1c')
        else:
            self.text.mark_set("matchStart", lineStart)
            self.text.mark_set("matchEnd", lineStart)
            self.text.mark_set("searchLimit", lineEnd)
        while True:
            self.text.tag_configure("insideEntityColor", background=self.insideNestEntityColor)
            pos = self.text.search(self.insideNestEntityRe, "matchEnd", "searchLimit",  count=countVar, regexp=True)
            if pos == "":
                break
            self.text.mark_set("matchStart", pos)
            self.text.mark_set("matchEnd", "%s+%sc" % (pos, countVar.get()))
            first_pos = "%s + %sc" % (pos, 2)
            last_pos = "%s + %sc" % (pos, str(int(countVar.get())-1))
            self.text.tag_add("insideEntityColor", first_pos, last_pos)

    def pushToHistory(self):
        """ Push a snapshot of the current text and cursor position to
            a double sided history queue

            Args:
                None

            Returns:
                None

        """

        if self.debug:
            print "Action Track: pushToHistory"
        currentList = []
        content = self.getText()
        cursorPosition = self.text.index(INSERT)
        currentList.append(content)
        currentList.append(cursorPosition)
        self.history.append(currentList)

    def pushToHistoryEvent(self, event):
        if self.debug:
            print "Action Track: pushToHistoryEvent"
        currentList = []
        content = self.getText()
        cursorPosition = self.text.index(INSERT)
        currentList.append(content)
        currentList.append(cursorPosition)
        self.history.append(currentList)

    # update shortcut map
    def renewPressCommand(self):
        if self.debug:
            print "Action Track: renewPressCommand"
        seq = 0
        new_dict = {}
        listLength = len(self.labelEntryList)
        delete_num = 0
        for key in sorted(self.pressCommand):
            label = self.labelEntryList[seq].get()
            if len(label) > 0:
                new_dict[key] = label
            else:
                delete_num += 1
            seq += 1
        self.pressCommand = new_dict
        for idx in range(1, delete_num+1):
            self.labelEntryList[listLength-idx].delete(0, END)
            self.shortcutLabelList[listLength-idx].config(text="NON= ")
        with open(self.configFile, 'wb') as fp:
            pickle.dump(self.pressCommand, fp)
        self.setMapShow()
        tkMessageBox.showinfo("Remap Notification", "Shortcut map has been updated!\n\nConfigure file has been saved in File:" + self.configFile)

    # show shortcut map
    def setMapShow(self):
        if os.path.isfile(self.configFile):
            with open(self.configFile, 'rb') as fp:
                self.pressCommand = pickle.load(fp)
        hight = len(self.pressCommand)
        width = 2
        row = 0
        mapLabel = Label(self, text="Shortcuts map Labels", foreground="blue", font=(self.textFontStyle, 14, "bold"))
        mapLabel.grid(row=0, column=self.textColumn + 2, columnspan=2, rowspan=1, padx=10)
        self.labelEntryList = []
        self.shortcutLabelList = []
        for key in sorted(self.pressCommand):
            row += 1
            symbolLabel = Label(self, text=key.upper() + ": ", foreground="blue", font=(self.textFontStyle, 14, "bold"))
            symbolLabel.grid(row=row, column=self.textColumn + 2, columnspan=1, rowspan=1, padx=3)
            self.shortcutLabelList.append(symbolLabel)

            labelEntry = Entry(self, foreground="blue", font=(self.textFontStyle, 14, "bold"))
            labelEntry.insert(0, self.pressCommand[key])
            labelEntry.grid(row=row, column=self.textColumn + 3, columnspan=1, rowspan=1)
            self.labelEntryList.append(labelEntry)

    def getCursorIndex(self):
        return self.text.index(INSERT)


def main():
    print("SUTDAnnotator launched!")
    print(("OS: %s") % (platform.system()))
    root = Tk()
    root.geometry("1300x700+200+200")
    app = Example(root)
    app.setFont(17)
    root.mainloop()


if __name__ == '__main__':
    main()
