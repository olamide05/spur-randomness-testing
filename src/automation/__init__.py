def __init__(self, config: STSConfig):
    self.config = config
    self._validate_config()
    