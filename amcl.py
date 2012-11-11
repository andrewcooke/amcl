#!/usr/bin/python3

'''
This is a little program that displays the current track from Amarok and
lets you move to prev/next tracks, or change volume, using the cursor 
(arrow) keys.

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

Full control list:
  left/right keys: lower/raise volume
  up/down keys: prev/next track
  q: quit
  </>: skip backwards/forwards
  space: pause
  p/P: set/clear A/B listening point
  A/B/C/D: store volume for A/B listening point
  a/b/c/d: set volume and return to listening point

To do A/B listening, set the volume for each device using A,B,.. and the
start of the music to compare with p.  Then press a,b,... to return to that
point with the volume for the appropriate device.  This lets you listen to
the same fragment of music, at the same output volume, when comparing
different devices.  Pressing P sets the comparison point to the track start.
  
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
        self.__length = None
        self.__current = self.current

    @property
    def metadata(self):
        return self.__amarok.GetMetadata()

    @property
    def track_data(self):
        metadata = self.metadata
        return (str(metadata.get('tracknumber', '-')),
                metadata.get('title', 'S/T'),
                metadata.get('album', 'Single'),
                metadata.get('artist', 'Unknown'))

    @property
    def position(self):
        return self.__amarok.PositionGet()

    @position.setter
    def position(self, position):
        self.__amarok.PositionSet(position)

    @property
    def progress(self):
        return self.__amarok.PositionGet() / self.metadata.get('mtime', 1e10)

    @property
    def volume(self):
        return self.__amarok.VolumeGet()

    @volume.setter
    def volume(self, volume):
        self.__amarok.VolumeSet(volume)

    def volume_down(self):
        self.volume = max(0, self.volume - 1)

    def volume_up(self):
        self.volume = min(100, self.volume + 1)

    def prev_track(self):
        self.__amarok.Prev()

    def next_track(self):
        self.__amarok.Next()

    def pause(self):
        self.__amarok.PlayPause()

    def forward(self):
        self.position += 1000

    def backward(self):
        self.position -= 1000

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
        self.refresh(True)

    def refresh(self, full=True):
        if self.__text:
            m = self.__max_x - 1
            text = self.__text
            scroll = len(text) > m
            if scroll or full:
                if scroll:
                    t2 = text + '  ' + text
                    if self.__marquee == len(text) + 2: self.__marquee = 0
                    text = t2[self.__marquee:self.__marquee + m]
                    self.__marquee += 1
                text += ' ' * (m - len(text))
                self.__window.addstr(self.__y, 0, text)


class BarLine:

    def __init__(self, window, y, max_x, volume, progress):
        self.__window = window
        self.__y = y
        self.__max_x = max_x
        self.__volume = volume
        self.progress = progress
        self.refresh(True)

    def refresh(self, full=True):
        m = self.__max_x - 1
        volume = min(int(self.__volume * m / 100.0), m)
        text = '=' * volume + ' ' * (m - volume)
        progress = min(int(self.progress * (m-1)), m-1)
        text = text[:progress] + '|' + text[progress+1:]
        self.__window.addstr(self.__y, 0, text)


PRESETS = 'abcd'

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
        if y < 4:
            track = track + ' by ' + artist
            artist = None
        if y < 3:
            track = track + ' from ' + album
            album = None
        self.__track = TextLine(self.__window, 0, x, track)
        self.__album = TextLine(self.__window, 1, x, album)
        self.__artist = TextLine(self.__window, 2, x, artist)
        self.__volume = BarLine(self.__window, min(y-1, 3), x, 
                                self.__amarok.volume, self.__amarok.progress)
        self.__window.refresh()

    def refresh(self):
        if self.__amarok.changed:
            self.layout()
        else:
            self.__track.refresh(False)
            self.__album.refresh(False)
            self.__artist.refresh(False)
            self.__volume.progress = self.__amarok.progress
            self.__volume.refresh()
            self.__window.refresh()

    def run(self):
        self.layout()
        preset_volume = {preset: self.__amarok.volume for preset in PRESETS}
        preset_position = 1
        idle = 0
        while True:
            key = self.__window.getch()
            if key == ord('q'):
                return
            if key == ord(' '):
                self.__amarok.pause()
            if key == ord('>'):
                self.__amarok.forward()
                self.layout()
            if key == ord('<'):
                self.__amarok.backward()
                self.layout()
#            if key == ord('m'):
#                metadata = self.__amarok.metadata
#                for key in metadata: print(key, metadata[key])
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
            elif key == ord('p'):
                preset_position = self.__amarok.position
            elif key == ord('P'):
                preset_position = 1
            elif key in (ord(preset.lower()) for preset in PRESETS):
                self.__amarok.volume = preset_volume[chr(key)]
                self.__amarok.position = preset_position
                self.layout()
            elif key in (ord(preset.upper()) for preset in PRESETS):
                preset_volume[chr(key).lower()] = self.__amarok.volume
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

