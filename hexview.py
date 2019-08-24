import string
import sys

import curses

from disk import Disk
from drive_utils import DriveUtils


SECTOR_SIZE = 512
LABEL_GOTO = "goto: "
GOTO_X = 1
GOTO_Y = 0

NONE_INPUT_MODE = 0
HEX_INPUT_MODE = 16
DECIMAL_INPUT_MODE = 10

gdebug = False;

class CursesView:
    def __init__(self, mycurses):
        self.mycurses = mycurses
        size = self.mycurses.size()
        self.h = size[0]
        self.w = size[1]

    def clear(self):
        self.mycurses.clear()

    def refresh(self):
        self.mycurses.refresh()

    def update(self, lines, start, end):
        self.clear()
        if end - start + 1 > self.h - 2:
            end = start + self.h - 2

        if len(lines) < end - start + 1:
            return

        for i in range(start, end):
            self.mycurses.addstr(i-start+1, 1, lines[i])

    def add_string(self, y, x, string):
        self.mycurses.addstr(y, x, string)


class CursesController:
    def __init__(self, mycurses):
        self.mycurses = mycurses

    def getch(self):
        try:
            key = self.mycurses.getch()
            return key
        except:
            return 0


class MyCurses:
    def __init__(self):
        self.screen = curses.initscr()
        self.view = CursesView(self)
        self.controller = CursesController(self)
        self.init()
        self._size = self.size()

    def getch(self):
        return self.screen.getch()

    def init(self):
        self.screen.border(0)
        self.screen.keypad(1)
        curses.noecho()


    def addstr(self, y, x, value):
        self.screen.addstr(y, x, value)

    def size(self):
        return self.screen.getmaxyx()

    def height(self):
        return self._size[0]

    def width(self):
        return self._size[1]

    def clear(self):
        self.screen.clear()
        self.screen.border(0)
    
    def refresh(self):
        self.screen.refresh()

    def close(self):
        curses.endwin()


class DebugCurses:
    def __init__(self):
        self.view = CursesView(self)
        self.controller = CursesController(self)
        pass

    def getch(self):
        return self.screen.getch()

    def init(self):
        pass

    def addstr(self, y, x, value):
        print("{y}:{x} - {value}\n".format(y=y, x=x, value=value))

    def size(self):
        return (80, 60)

    def clear(self):
        print("\n")
    
    def refresh(self):
        print("\n")

    def close(self):
        pass

    def height(self):
        return 60

    def width(self):
        return 80



class HexScrollViewSink:
    SECTOR_BLOCK_COUNT=12
    BEFORE_BLOCK_COUNT=4

    def __init__(self, max_line, total, callback):
        self.current_line_pos = 0
        self.current_pos_in_block = 0
        self.last_line_pos = total * 32 -1
        self.total_sec = total
        self.lines = None

        self.max_line = max_line - 2
        self.callback = callback

    def init(self, sec):
        block_count = HexScrollViewSink.SECTOR_BLOCK_COUNT
        if sec + HexScrollViewSink.SECTOR_BLOCK_COUNT > self.total_sec - 1:
            block_count = self.total_sec - sec

        fill_buffer_sec = sec
        if sec > 0:
            fill_buffer_sec = sec - HexScrollViewSink.BEFORE_BLOCK_COUNT
            if fill_buffer_sec < 0:
                fill_buffer_sec = 0 

            block_count += (sec - fill_buffer_sec)

        self.lines = self.fill_buffer(fill_buffer_sec, block_count)

        self.current_contain_start_sec = fill_buffer_sec 
        self.current_contain_end_sec = fill_buffer_sec + block_count
        self.current_line_pos = sec * 32
        self.current_pos_in_block = (sec - fill_buffer_sec) * 32
        self.current_sec_start_line_pos = block_count * 32

    def buffer_to_lines(self, buf, sec):
        arr = []
        size = len(buf)
        line = "{0:016x}".format(sec*512)
        vline = " "
        mod = size % 16
        for i in range(size):
            if i != 0 and i % 16 == 0:
                line += vline

                arr.append(line)
                line = "{0:016x}".format(sec*512+i)
                line += " "
                vline = " "
            else:
                line += " "

            val = buf[i]
            v = "{0:02x}".format(val)
            line += v

            if val < 32 or val > 126:
                cv = "."
            else:
                cv = chr(val)

            vline += cv

        if mod != 0:
            for i in range(16-mod):
                line += " 00"
                vline += "."

        if len(line) != 0:
            line += vline
            arr.append(line)

        return arr

    def fill_buffer(self, sec, size):
        buf = self.callback.callback(sec, size)
        lines = self.buffer_to_lines(buf, sec)
        return lines

    def is_in_buffers(self, pos):
        target_start_pos = self.current_line_pos + pos
        if target_start_pos < 0:
            target_start_pos = 0

        target_end_pos = self.current_line_pos + pos + 32
        if target_end_pos > self.last_line_pos:
            target_end_pos = self.last_line_pos

        start_pos = self.current_contain_start_sec * 32
        end_pos = self.current_contain_end_sec * 32

        if (target_start_pos >= start_pos and target_start_pos < end_pos):
            if (target_end_pos < end_pos):
                return True

        return False

    def need_fill_buffers(self, pos):
        if self.is_in_buffers(pos):
            return 0

        if pos > 0:
            return 4

        else:
            return -4

    def update(self, pos):
        n = self.need_fill_buffers(pos)
        if n != 0:
            if n > 0:
                target_sec = self.current_contain_end_sec
            else:
                target_sec = self.current_contain_start_sec - 4

            lines = self.fill_buffer(target_sec, 4)
            self.current_contain_start_sec += n
            self.current_contain_end_sec += n

            if n < 0:
                tmp = self.lines
                self.lines = lines
                for line in tmp:
                    self.lines.append(line)

                self.lines = self.lines[:-(32*4)]
                self.current_pos_in_block += 128

            if n > 0:
                for line in lines:
                    self.lines.append(line)

                self.lines = self.lines[32*4:]
                self.current_pos_in_block -= 128

        absolute_pos = self.current_line_pos + pos
        if absolute_pos < 0:
            pos = 0

        target_line_pos = self.current_pos_in_block + pos
        end_target_line_pos = target_line_pos+32
        if self.current_line_pos + 32 > self.last_line_pos :
            end_target_line_pos = target_line_pos + (self.last_line_pos - self.current_line_pos)

        self.current_pos_in_block = target_line_pos
        self.current_line_pos += pos
        return (self.lines, target_line_pos, end_target_line_pos)



class HexScrollView:
    def __init__(self, view, sink):
        self.view = view
        self.sink = sink

        self.sink.init(0)
        self.update(0)

    def init(self, sec):
        self.sink.init(sec)

    def update(self, pos):
        lines, start, end = self.sink.update(pos)
        self.view.update(lines, start, end)


class DiskCallback:
    def __init__(self, disk):
        self.disk = disk

    def callback(self, sec, number):
        return self.disk.read(sec, number)


def run_loop(my, fileinfo):
    filename = fileinfo[0]
    disksize = fileinfo[2]

    disk = Disk(SECTOR_SIZE, filename, disksize)
    mycallback = DiskCallback(disk)

    max_line = my.height()
    sink = HexScrollViewSink(max_line, disk.block_count(), mycallback)
    view = HexScrollView(my.view, sink)
    controller = my.controller

    input_mode = False
    goto = ""
    while True:
        key = controller.getch()
        if key == ord('q') and not input_mode:
            break
        if key == ord('g'):
            input_mode = DECIMAL_INPUT_MODE
            my.view.add_string(GOTO_Y, GOTO_X, LABEL_GOTO)
        if key == ord('h'):
            input_mode = HEX_INPUT_MODE
            my.view.add_string(GOTO_Y, GOTO_X, LABEL_GOTO)
        elif key >= ord('0') and key <= ord('9') and input_mode:
            goto += chr(key)
            my.view.add_string(GOTO_Y, GOTO_X, LABEL_GOTO + goto)
        elif ((key >= ord('a') and key <= ord('f')) or \
              (key >= ord('A') and key <= ord('F'))) and \
              input_mode == HEX_INPUT_MODE:
            goto += chr(key)
            my.view.add_string(GOTO_Y, GOTO_X, LABEL_GOTO + goto)
        elif (key == curses.KEY_ENTER or key == 10) and input_mode != NONE_INPUT_MODE:
            try:
                igoto = int(goto, input_mode)
                goto = ""
                view.init(igoto)
                view.update(0)
            except:
                pass
            finally:
                input_mode = NONE_INPUT_MODE
            
        elif key == 27:
            break
        elif key == curses.KEY_UP:
            view.update(-1)
        elif key == curses.KEY_DOWN:
            view.update(1)
        elif key == 127 and input_mode:
            if len(goto) > 0:
                view.update(0)
                goto = goto[0:-1]
                my.view.add_string(GOTO_Y, GOTO_X, LABEL_GOTO + goto)


if __name__ == '__main__':
    my = MyCurses()
    e = None

    try:
        du = DriveUtils()
        fi = du.info(sys.argv[1])
        run_loop(my, fi)
    except:
        e = sys.exc_info()

    my.close()

    if e:
        print(e)
