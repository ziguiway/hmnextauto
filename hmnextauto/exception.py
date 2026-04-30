# -*- coding: utf-8 -*-

class ElementNotFoundError(Exception):
    pass


class ElementFoundTimeout(Exception):
    pass


class XmlElementNotFoundError(Exception):
    pass


class HmDriverError(Exception):
    pass


class DeviceNotFoundError(Exception):
    pass


class HdcError(Exception):
    pass


class InvokeHypiumError(Exception):
    pass


class InvokeCaptures(Exception):
    pass


class InjectGestureError(Exception):
    pass


class ScreenRecordError(Exception):
    pass


class AppNameNotFoundError(HmDriverError):
    """No installed app matches the given display / software name."""


class AppNameAmbiguousError(HmDriverError):
    """
    More than one installed app matches the given name.

    The ``matches`` list contains ``(package_name, display_name)`` tuples.
    """

    def __init__(self, message: str, matches):
        super().__init__(message)
        self.matches = matches
