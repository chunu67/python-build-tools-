class EnumWriter(object):
    def __init__(self):
        self.parent = None

    def get_config(self):
        return {}

    def _get_value_for(self, vpak):
        if isinstance(vpak, dict):
            return vpak['value']
        else:
            return vpak

    def _get_meaning_for(self, vpak):
        return self._get_for(vpak, 'meaning')

    def _get_for(self, vpak, key, default=''):
        if isinstance(vpak, dict):
            return vpak.get(key, default)
        else:
            return default

    def write(self, w, definition):
        return
