class ValidationError(Exception):

    def __init__(self, message, code=None, params=None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.params = params

    def to_dict(self):
        return {
            "error_class": self.__class__.__name__,
            "message": self.message,
            "code": self.code,
            "params": self.params,
        }
