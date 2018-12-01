import os
from trufont import __version__
from trufont.windows.fontWindow import FontWindow, prepareNewFont
from typing import List, Optional
from tfont.converters import TFontConverter, UFOConverter
from tfont.objects import Font
from weakref import WeakSet
import wx
from wx import GetTranslation as tr

# drawingTools, with a tracker

# extensions?

# menu API to add to all windows?

# register wx.GetApplication() as part of factory reg
# trufont.Application or trufont.TruFont

# deserialize JSON settings and call dict.update() on that
# serialize on app exit


class Application:
    __slots__ = "_app", "_observers", "_settings"

    def __init__(self, app):
        self._app = app
        self._settings = {
            "backgroundStrokeColor": (210, 210, 210, 255),
            "componentFillColor": (90, 90, 90, 135),
            "fillColor": (244, 244, 244, 77),
            "selectionColor": (145, 170, 196, 155),
            "strokeColor": (34, 34, 34, 255),
            "foregroundShowPoints": True,
            "foregroundShowGuidelines": True,
            "foregroundShowImages": True,
            "showAnchors": True,
            "showBackground": True,
            "showCoordinates": False,
            "showFill": True,
            "showGuidelines": True,
            "showMetrics": True,
            "showPoints": True,
            "showSelection": True,
            "showSelectionBounds": False,
            "showStroke": True,
            "showTextCursor": False,
            "showTextMetrics": False,
        }
        self._observers = {
            "drawBackground": WeakSet(),
            "drawForeground": WeakSet(),
            "drawInactive": WeakSet(),
            "fontOpened": WeakSet(),
            "fontSaved": WeakSet(),
            "mouseMoved": WeakSet(),
            "tabOpened": WeakSet(),
            "tabWillClose": WeakSet(),
            "updateUI": WeakSet(),
        }

    def __repr__(self):
        return "%s(%s, %d fonts)" % (
            self._app.GetAppDisplayName(),
            __version__,
            len(self.fonts),
        )

    @property
    def font(self) -> Optional[Font]:
        # in order to do this properly, FontWindows should store a timestamp
        # when they acquire focus, then here we can maximize focus
        for window in wx.GetTopLevelWindows():
            if isinstance(window, FontWindow):
                return window._font
        return None

    @property
    def fonts(self) -> List[Font]:
        fonts = []
        for window in wx.GetTopLevelWindows():
            if isinstance(window, FontWindow):
                fonts.append(window._font)
        return fonts

    @property
    def settings(self):
        return self._settings

    def addObserver(self, key, observer):
        # make sure the key is in our records
        observers = self._observers[key]
        # make sure observer has the relevant callback
        callbackName = f"On{key.capitalize()}"
        if not hasattr(observer, callbackName) and (
            key == "updateUI" and not hasattr(observer, "Refresh")
        ):
            raise ValueError(
                "observer {!r} does not implement {!r} method".format(
                    observer, callbackName
                )
            )
        observers.add(observer)

    def newFont(self) -> Font:
        font = Font()
        prepareNewFont(font)
        FontWindow(None, font).Show()
        return font

    def openFont(self, path=None) -> Optional[Font]:
        if path is None:
            with wx.FileDialog(
                None,
                tr("Load Font File"),
                wildcard=(
                    "Font Files (*.tfont)|*.tfont|"
                    "UFOs (*.ufo, *.ufoz, metainfo.plist)|*.ufo;*.ufoz;metainfo.plist"
                ),
                style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
            ) as dialog:
                if dialog.ShowModal() == wx.ID_CANCEL:
                    return None
                path = dialog.GetPath()

        if path.endswith(".tfont"):
            for window in wx.GetTopLevelWindows():
                if isinstance(window, FontWindow):
                    if window._path == path:
                        window.Raise()
                        return None
            font = TFontConverter().open(path)
        elif path.endswith((".ufo", ".ufoz")):
            font = UFOConverter().open(path)
        elif path.endswith("metainfo.plist"):
            path = os.path.dirname(path)
            font = UFOConverter().open(path)
        else:
            raise ValueError("Tried to import unknown file format.")

        wx.GetApp().fileHistory.AddFileToHistory(path)
        # Importing and then saving should prompt the user to save in the native format.
        if not path.endswith(".tfont"):
            path = None
        FontWindow(None, font, path).Show()
        return font

    def removeObserver(self, key, observer):
        self._observers[key].remove(observer)

    def updateUI(self):
        for observer in self._observers["updateUI"]:
            try:
                observer.OnUpdateUI()
            except AttributeError:
                observer.Refresh()

    # buildNumber/versionNumber?
    # buildNumber is a single number always going up, whereas
    # versionNumber is incr. with larger changes (somewhat arbitrarily)
    @property
    def version(self):
        return __version__

    # then one can call window(font).currentTab.view etc.
    # font.window as a convenience property could make sense I think
    def window(self, font):
        for window in wx.GetTopLevelWindows():
            if isinstance(window, FontWindow):
                if window._font == font:
                    return window
        return None
