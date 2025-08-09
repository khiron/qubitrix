class InputController:
    def __init__(self):
        self.subscribers = []

    def subscribe(self, callback):
        self.subscribers.append(callback)

    def emit(self, event):
        for callback in self.subscribers:
            callback(event)
