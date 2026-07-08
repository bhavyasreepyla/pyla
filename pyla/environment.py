"""Lexical environments: a chain of scopes used for variables and closures."""


class Environment:
    def __init__(self, outer=None):
        self.store = {}
        self.outer = outer

    def get(self, name):
        """Return (value, True) if found anywhere in the chain, else (None, False)."""
        env = self
        while env is not None:
            if name in env.store:
                return env.store[name], True
            env = env.outer
        return None, False

    def define(self, name, value):
        """Create or overwrite a binding in the current scope (used by `let`)."""
        self.store[name] = value
        return value

    def assign(self, name, value):
        """Update an existing binding somewhere in the chain.

        Returns True on success, False if the name was never defined.
        """
        env = self
        while env is not None:
            if name in env.store:
                env.store[name] = value
                return True
            env = env.outer
        return False

    def child(self):
        return Environment(outer=self)
