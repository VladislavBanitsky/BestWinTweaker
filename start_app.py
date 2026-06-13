# Стартер приложения

import multiprocessing

from BestWinTweaker import *


if __name__ == "__main__":
    # Pyinstaller fix
    multiprocessing.freeze_support()
    app = BestWinTweaker()
    app.run()