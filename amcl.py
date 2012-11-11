#!/usr/bin/python3

'''
This is a little program that displays the current track from Amarok and
lets you move to prev/next tracks, or change volume, using the arrow keys.

It only requries a few lines for the display, so you can place it in a
little terminal window somewhere out of the way.  If the window is very
small it will compress and scroll the contents to help you see everything.

It can be used over ssh to control your music remotely, but you must set
the DISPLAY variable appropriately.  For example:
  > ssh desktop
  password: *****
  > DISPLAY=:0.0 ./amcl.py

On OpenSuse you need to have the following packages installed:
  python3
  python3-curses
  dbus-1-python3
  
Please send any bug reports to andrew@acooke.org
(c) Andrew Cooke 2012, released under the GPL v3.
'''


import curses as c
import dbus as d
from time import sleep


class Amarok:

    def __init__(self):
        sbus = d.SessionBus()
        self.__amarok = sbus.get_object('org.kde.amarok', '/Player')
        self.__current = self.current

    @property
    def track_data(self):
        metadata = self.__amarok.GetMetadata()
        return (str(metadata.get('tracknumber', '-')),
                metadata.get('title', 'S/T'),
                metadata.get('album', 'Single'),
                metadata.get('artist', 'Unknown'))

    @property
    def volume(self):
        return self.__amarok.VolumeGet()

    def volume_down(self):
        self.__amarok.VolumeSet(max(0, self.__amarok.VolumeGet() - 2))

    def volume_up(self):
        self.__amarok.VolumeSet(min(100, self.__amarok.VolumeGet() + 2))

    def prev_track(self):
        self.__amarok.Prev()

    def next_track(self):
        self.__amarok.Next()

    def pause(self):
        self.__amarok.Pause()

    @property
    def current(self):
        return hash(self.track_data)

    @property
    def changed(self):
        current = self.current
        if current != self.__current:
            self.__current = current
            return True
        else:
            return False


class TextLine:

    def __init__(self, window, y, max_x, text):
        self.__window = window
        self.__y = y
        self.__max_x = max_x
        self.__text = text
        self.__marquee = 0
        self.refresh()

    def refresh(self):
        if self.__text:
            m = self.__max_x - 1
            text = self.__text
            if len(text) > m:
                t2 = text + '  ' + text
                if self.__marquee == len(text) + 2: self.__marquee = 0
                text = t2[self.__marquee:self.__marquee + m]
                self.__marquee += 1
            text += ' ' * (m - len(text))
            self.__window.addstr(self.__y, 0, text)


class BarLine:

    def __init__(self, window, y, max_x, percent):
        self.__window = window
        self.__y = y
        self.__max_x = max_x
        self.__percent = percent
        self.refresh()

    def refresh(self):
        m = self.__max_x - 1
        l = min(int(self.__percent * m / 100.0), m)
        text = '=' * l + ' ' * (m - l)
        self.__window.addstr(self.__y, 0, text)


class Screen:

    def __init__(self, amarok):
        self.__amarok = amarok
        self.__window = c.initscr()
        c.noecho()
        c.cbreak()
        self.__window.keypad(1)
        self.__cursor = c.curs_set(0)
        self.__window.nodelay(1)

    def close(self):
        self.__window.keypad(0)
        c.nocbreak()
        c.echo()
        c.endwin()
        c.curs_set(self.__cursor)

    def layout(self):
        y, x = self.__window.getmaxyx()
        if y < 2: raise Exception('window not long enough')
        if x < 10: raise Exception('window not wide enough')
        number, track, album, artist = self.__amarok.track_data
        track = '[' + number + '] ' + track
        if y == 2:
            track = track + ' from ' + album + ' by ' + artist
            album = None
            artist = None
        elif y == 3:
            album = album + ' by ' + artist
            artist = None
        self.__track = TextLine(self.__window, 0, x, track)
        self.__album = TextLine(self.__window, 1, x, album)
        self.__artist = TextLine(self.__window, 2, x, artist)
        self.__volume = BarLine(self.__window, min(y-1, 3), x, 
                                self.__amarok.volume)
        self.__window.refresh()

    def refresh(self):
        if self.__amarok.changed:
            self.layout()
        else:
            self.__track.refresh()
            self.__album.refresh()
            self.__artist.refresh()
            self.__volume.refresh()
            self.__window.refresh()

    def run(self):
        self.layout()
        idle = 0
        while True:
            key = self.__window.getch()
            if key == ord('q'):
                return
            if key == ord(' '):
                self.__amarok.pause()
            elif key == c.KEY_LEFT:
                self.__amarok.volume_down()
                self.layout()
            elif key == c.KEY_RIGHT:
                self.__amarok.volume_up()
                self.layout()
            elif key == c.KEY_UP:
                self.__amarok.prev_track()
                self.layout()
            elif key == c.KEY_DOWN:
                self.__amarok.next_track()
                self.layout()
            elif key == c.KEY_RESIZE:
                self.layout()
            elif key == c.KEY_REFRESH:
                self.layout()
            elif key == -1:
                sleep(0.01)
                idle += 1
            if idle > 10:
                self.refresh()
                idle = 0

class Amcl:

    def __enter__(self):
        self.__screen = Screen(Amarok())
        return self.__screen

    def __exit__(self, type, value, traceback):
        self.__screen.close()


if __name__ == '__main__':
    with Amcl() as amcl:
        amcl.run()

