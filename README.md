This is a little program that displays the current track from Amarok and
lets you move to prev/next tracks, or change volume, using the arrow keys.

It looks something like this:

    [9] No se empezar
    El Amarillito Vol 14
    Dadalu
    =======================================

and only requries a few lines for the display, so you can place it in a
little terminal window somewhere out of the way.  If the window is very
small it will compress and scroll the contents to help you see everything.

It can be used over ssh to control your music remotely, but you must set
the DISPLAY variable appropriately.  For example:

    > ssh desktop
    password: *****
    > DISPLAY=:0.0 ./amcl.py

On OpenSuse you need to have the following packages installed:
* python3
* python3-curses
* dbus-1-python3
  
Please send any bug reports to andrew@acooke.org
(c) Andrew Cooke 2012, released under the GPL v3.
