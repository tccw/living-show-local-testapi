class App:
    __conf = {
        "LOGGER_NAME": "snow-api",
        "SQLITE_DATABASE": "data.db",
    }

    @staticmethod
    def config(name):
        return App.__conf[name]
