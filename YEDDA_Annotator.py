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
        self.colorAllChunk = True
        self.history = deque(maxlen=20)
        self.currentContent = deque(maxlen=1)
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

        '''
        For exporting sequence, if self.seged is True then split words with a
        space, else split characters without a space. For example, if your data
        is segmentated Chinese (or English) with words seperated by a space,
        you need to set this flag to True. If your data is Chinese without
        segmentation, you need to set this flag to False.
        '''
        self.seged = True
        self.configFile = "config"
        self.entityRe = r'\[\@.*?\#.*?\*\](?!\#)'
        self.insideNestEntityRe = r'\[\@\[\@(?!\[\@).*?\#.*?\*\]\#'

        # configure color
        self.entityColor = "SkyBlue1"
        self.insideNestEntityColor = "light slate blue"
        # self.recommendColor = 'lightgreen'
        self.selectColor = 'light salmon'
        self.textFontStyle = "Times"
        self.initUI()

    def initUI(self):

        self.parent.title(self.Version)
        self.pack(fill=BOTH, expand=True)

        for idx in range(0, self.textColumn):
            self.columnconfigure(idx, weight=2)
        # self.columnconfigure(0, weight=2)
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

    # TODO: select entity by double left click
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
        # self.clearCommand()
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
        print("Command:"+command)
        try:
            firstSelection_index = self.text.index(SEL_FIRST)
            cursor_index = self.text.index(SEL_LAST)
            aboveHalf_content = self.text.get('1.0', firstSelection_index)
            followHalf_content = self.text.get(firstSelection_index, "end-1c")  # contains the selected string
            selected_string = self.text.selection_get()
            if re.match(self.entityRe, selected_string) is not None:
                # if the selected string has been selected before (exactly)
                new_string_list = selected_string.strip('[@]').rsplit('#', 1)
                new_string = new_string_list[0]
                followHalf_content = followHalf_content.replace(selected_string, new_string, 1)
                selected_string = new_string
                cursor_index = cursor_index.split('.')[0]+"."+str(int(cursor_index.split('.')[1])-len(new_string_list[1])+4)
            afterEntity_content = followHalf_content[len(selected_string):]

            if command == "q":
                print 'q: remove entity label'
            else:
                if len(selected_string) > 0:
                    entity_content, cursor_index = self.replaceString(selected_string, selected_string, cursor_index, command)
            aboveHalf_content += entity_content
            content = aboveHalf_content + afterEntity_content
            content = content.encode('utf-8')
            self.writeFile(self.fileName, content, cursor_index)

        except TclError:
            print "TCL ERROR"
            # if the text hasn't been explicitly highlighted
            # cursor can still be next to the previously highlighted text
            cursor_index = self.text.index(INSERT)
            [line_id, column_id] = cursor_index.split('.')
            aboveLine_content = self.text.get('1.0', str(int(line_id)-1) + '.end')
            belowLine_content = self.text.get(str(int(line_id) + 1) + '.0', "end-1c")
            line = self.text.get(line_id + '.0', line_id + '.end')
            matched_span = (-1, -1)
            detected_entity = -1  # detected entity type:－1 not detected, 1 detected gold, 2 detected recommend
            for match in re.finditer(self.entityRe, line):
                if self.debug:
                    print "GOLD"
                # if the cursor position is inside (inclusive) of the selected
                # text
                if match.span()[0] <= int(column_id) & int(column_id) <= match.span()[1]:
                    matched_span = match.span()
                    detected_entity = 1
                    break
            if detected_entity == -1:
                if self.debug:
                    print "NOT DETECTED"

            line_before_entity = line
            line_after_entity = ""
            # if the right side of matched string is not left aligned
            if matched_span[1] > 0:
                selected_string = line[matched_span[0]:matched_span[1]]
                if detected_entity == 1:
                    new_string_list = selected_string.strip('[@*]').split('#')
                new_string = new_string_list[0]
                old_entity_type = [x.strip() for x in new_string_list[1:]]
                line_before_entity = line[:matched_span[0]]
                line_after_entity = line[matched_span[1]:]
                selected_string = new_string
                entity_content = selected_string
                cursor_shift = ' '.join(['#' + string for string in new_string_list[1:]])
                cursor_index = line_id + '.' + str(int(matched_span[1]) - (len(cursor_shift) + 3))
                old_keys = [self.pressCommand.keys()[self.pressCommand.values().index(entity)] for entity in old_entity_type]
                if command == "q":
                    print 'q: remove entity label'
                else:
                    if len(selected_string) > 0:
                        if command in self.pressCommand:
                            entity_content, cursor_index = self.replaceString(selected_string, selected_string, cursor_index, command, old_keys)
                        else:
                            return
                line_before_entity += entity_content
            if aboveLine_content != '':
                aboveHalf_content = aboveLine_content + '\n' + line_before_entity
            else:
                aboveHalf_content = line_before_entity

            if belowLine_content != '':
                followHalf_content = line_after_entity + '\n' + belowLine_content
            else:
                followHalf_content = line_after_entity

            content = aboveHalf_content + followHalf_content
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
        # print "get_input: ", get_input
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

        if (new_key not in keys):
            keys += [new_key]

        if all(k in self.pressCommand for k in keys):
            ann_string = ' '.join(['#' + self.pressCommand[k] for k in keys])
            print "CURSOR INDEX"
            print cursor_index
            print "ANN_STRING"
            print ann_string
            if new_key is None:
                ann_string = ' ' + ann_string
            new_string = "[@" + string + ann_string + "*]"
            newcursor_index = cursor_index.split('.')[0] + "." + str(int(cursor_index.split('.')[1]) + len(ann_string)+3)
        else:
            print "Invaild command!"
            print "cursor index: ", self.text.index(INSERT)
            return content, cursor_index
        content = content.replace(string, new_string, 1)
        return content, newcursor_index

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
            pos = self.text.search(self.entityRe, "matchEnd", "searchLimit", count=countVar, regexp=True)
            if pos == "":
                break
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
