class Controller:
    def __init__(self, model, view):
        self.model = model
        self.view = view
        self.done = False

    def input(self, event):
        # Dummy input handler
        pass

    def update(self):
        self.model.update()
        self.view.render(self.model.get_state())
