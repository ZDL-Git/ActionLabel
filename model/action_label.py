from PyQt5.QtGui import QBrush

from common.utils import Log
from presenter.CommonUnit import CommonUnit


class ActionLabel:
    def __init__(self, action: str, action_id: int, color, begin: int, end: int, timeline_row: int):
        self.action = action
        self.action_id = action_id
        if isinstance(color, QBrush):
            color = color.color()
        self.color = color
        self.begin = begin
        self.end = end
        self.timeline_row = timeline_row

    def merge(self, label_section):
        if self.action != label_section.action:
            Log.error('different actions:', self, label_section)
        elif self.begin <= label_section.begin <= self.end or self.begin <= label_section.end <= self.end:
            self.begin = min(self.begin, label_section.begin)
            self.end = max(self.end, label_section.end)
        else:
            Log.error('actions not continuous')

    def is_valid(self, checklist: list) -> bool:
        Log.debug(self)
        for attr in checklist:
            value = eval(f'self.{attr}')
            if value in [None, '', []]:
                warn_ = f"Label's attr [{attr}]  is [{value}], invalid!"
                CommonUnit.status_prompt(warn_)
                Log.warn(warn_)
                return False
        if self.begin is not None and self.end is not None and self.begin > self.end:
            warn_ = f"Label's begin[{self.begin}] exceeds end[{self.end}], invalid!"
            CommonUnit.status_prompt(warn_)
            Log.warn(warn_)
            return False
        return True

    def __repr__(self):
        return f"{self.__class__.__name__}: " \
               f"action[{self.action}] " \
               f"action_id[{self.action_id}] " \
               f"color[{self.color.getRgb()}] " \
               f"begin[{self.begin}] end[{self.end}] " \
               f"timeline_row[{self.timeline_row}]"
