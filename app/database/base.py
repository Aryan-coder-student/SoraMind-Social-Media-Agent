"""Database connection lifecycle contract shared across backends."""

from abc import ABC, abstractmethod


class DatabaseConnection(ABC):
    """Common lifecycle boundary for a configured database backend."""

    @abstractmethod
    def connect(self) -> object:
        """Open or return the backend connection resource."""
        ...

    @abstractmethod
    def close(self) -> None:
        """Release backend connection resources."""
        ...
