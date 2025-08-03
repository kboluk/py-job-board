class EventEmitter:
    def __init__(self):
        self._listeners = {}

    def on(self, event, handler):
        print(f"[EventEmitter] on('{event}') → {handler}")
        self._listeners.setdefault(event, []).append(handler)

    def off(self, event, handler):
        print(f"[EventEmitter] off('{event}') → {handler}")
        if event in self._listeners:
            self._listeners[event].remove(handler)

    def emit(self, event, *args, **kwargs):
        for handler in self._listeners.get(event, []):
            print(f"[EventEmitter] Emitting '{event}' → {handler}")
            handler(*args, **kwargs)

__all__ = ["EventEmitter"]