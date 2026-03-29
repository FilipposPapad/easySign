import threading
from queue import Queue
import asyncio
import inspect
import traceback

class Executor:

    def __init__(self, tk_root):

        self.root = tk_root
        self.queue = Queue()

    def submit(self, func, callback=None, *args, **kwargs):

        def worker():
            try:
                result = func(*args, **kwargs)
                if inspect.iscoroutine(result):
                    result = asyncio.run(result)
                self.queue.put(("success", result))
            except Exception as e:
                self.queue.put(("error", str(e))) #+ ", trace:" + traceback.format_exc()))

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

        self.root.after(100, lambda: self._check(callback))

    def _check(self, callback):

        try:
            status, result = self.queue.get_nowait()
        except:
            self.root.after(100, lambda: self._check(callback))
            return

        if callback:
            callback(status, result)
