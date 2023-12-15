import contextlib


@contextlib.contextmanager
def assert_raises(exctype, msg: str = None):
    try:
        yield
    except exctype:
        pass
    except Exception as e:
        text = f"Expected {exctype}, got {type(e)}"
        if msg is not None:
            text += f": {msg}"
        assert False, text
    else:
        text = f"Expected {exctype}, but no exception was raised"
        if msg is not None:
            text += f": {msg}"
        assert False, text
