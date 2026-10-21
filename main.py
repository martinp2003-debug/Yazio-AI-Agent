import asyncio
import os
from pathlib import Path

from agents import Agent, Runner, SQLiteSession
from agents.mcp import MCPServerStdio
from dotenv import load_dotenv

from agent import build_agent_instructions, create_yazio_mcp_server
from data import SessionRecord
from services import ObservabilityService, SessionStoreService


# Charge les variables du fichier .env dans l'environnement.
load_dotenv()


def create_agent(yazio_mcp: MCPServerStdio) -> Agent:
    """Construit l'agent et lui injecte ses dépendances."""
    return Agent(
        name="Assistant Yazio",
        instructions=build_agent_instructions,
        mcp_servers=[yazio_mcp],
    )


async def prompt_new_session(store: SessionStoreService) -> SessionRecord:
    title = await asyncio.to_thread(input, "Titre (facultatif) : ")
    return store.create_session(title)


async def select_session(store: SessionStoreService) -> SessionRecord | None:
    """Propose de créer une conversation ou d'en recharger une."""
    while True:
        print("\n1. Nouvelle conversation")
        print("2. Recharger une conversation")
        print("q. Quitter")
        choice = (await asyncio.to_thread(input, "Choix : ")).strip().lower()

        if choice == "1":
            return await prompt_new_session(store)

        if choice == "2":
            sessions = store.list_sessions()
            if not sessions:
                print("Aucune conversation enregistrée.")
                continue

            for index, conversation in enumerate(sessions, start=1):
                updated_at = conversation.updated_at.astimezone().strftime(
                    "%Y-%m-%d %H:%M"
                )
                print(
                    f"{index}. {conversation.title} "
                    f"({conversation.session_id[:8]}, {updated_at})"
                )

            selected = (
                await asyncio.to_thread(input, "Numéro de la conversation : ")
            ).strip()
            if not selected.isdigit() or not 1 <= int(selected) <= len(sessions):
                print("Sélection invalide.")
                continue

            return sessions[int(selected) - 1]

        if choice == "q":
            return None

        print("Choix invalide.")


async def run_conversation(
    agent: Agent,
    store: SessionStoreService,
    conversation: SessionRecord,
    observability: ObservabilityService,
) -> None:
    """Gère l'interface et le changement de conversation."""
    session: SQLiteSession = store.open_session(conversation.session_id)

    print(f"\nConversation : {conversation.title}")
    print(f"Session : {conversation.session_id}")
    print("Tape 'nouvelle conversation' ou 'quitter'.\n")

    try:
        while True:
            user_message = await asyncio.to_thread(input, "Toi : ")
            command = user_message.strip().lower()

            if command == "quitter":
                print("Conversation terminée.")
                break

            if command == "nouvelle conversation":
                session.close()
                conversation = await prompt_new_session(store)
                session = store.open_session(conversation.session_id)
                print(f"Nouvelle conversation : {conversation.title}")
                print(f"Session : {conversation.session_id}\n")
                continue

            if not command:
                continue

            with observability.observe_turn(session.session_id):
                result = await Runner.run(agent, user_message, session=session)
            store.mark_session_used(session.session_id)
            print(f"\n{agent.name} : {result.final_output}\n")
    finally:
        session.close()


async def main() -> None:
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError(
            "OPENAI_API_KEY est absente. Copie .env.example vers .env "
            "et ajoute ta clé API."
        )

    db_path = Path(os.getenv("AGENT_DB_PATH", "storage/conversations.db"))
    store = SessionStoreService(db_path)
    observability = ObservabilityService.from_env()

    try:
        conversation = await select_session(store)
        if conversation is None:
            return

        yazio_mcp = create_yazio_mcp_server()
        async with yazio_mcp:
            agent = create_agent(yazio_mcp)
            await run_conversation(
                agent,
                store,
                conversation,
                observability,
            )
    finally:
        observability.flush()


if __name__ == "__main__":
    asyncio.run(main())
