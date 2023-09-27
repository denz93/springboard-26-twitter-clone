from typing import Callable
from flask import render_template, g, make_response

def auth():
  def wrapper(func: Callable):
    def handler(*args, **kwargs):
      if not g.user:
        return make_response(render_template('unauthorized.html'), 401)
      return func(*args, **kwargs)
    handler.__name__ = func.__name__
    return handler
  return wrapper