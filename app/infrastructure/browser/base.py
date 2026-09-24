"""Browser abstraction used by domain-facing discovery components."""

from abc import ABC, abstractmethod
from typing import Any


class BrowserBase(ABC):
    """Contract for shared browser lifecycle and navigation operations."""

    @abstractmethod
    async def start(self) -> None:
        """Start the browser runtime and create a reusable browser context."""
        ...

    @abstractmethod
    async def new_page(self) -> Any:
        """Create and return a new browser page/tab."""
        ...

    @abstractmethod
    async def navigate(self, page: Any, url: str) -> None:
        """Navigate a page to the given URL."""
        ...

    @abstractmethod
    async def close_page(self, page: Any) -> None:
        """Close a single browser page/tab."""
        ...

    @abstractmethod
    async def close(self) -> None:
        """Close the browser context, browser process, and runtime."""
        ...
