import asyncio

from bootstrap import build_application
from interfaces.cli import run_cli


async def main() -> None:
    container = build_application()
    async with container.lifespan():
        await run_cli(container.chat_service, container.agent_name)


if __name__ == "__main__":
    asyncio.run(main())
