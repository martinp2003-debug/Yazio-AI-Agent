import asyncio
import os

from agents import Agent, Runner, SQLiteSession
from agents.mcp import MCPServerStdio
from dotenv import load_dotenv

from agent import build_agent_instructions, create_yazio_mcp_server


# Charge les variables du fichier .env dans l'environnement.
load_dotenv()


def create_agent(yazio_mcp: MCPServerStdio) -> Agent:
    """Construit l'agent et lui injecte ses dépendances."""
    return Agent(
        name="Assistant Yazio",
        instructions=build_agent_instructions,
        mcp_servers=[yazio_mcp],
    )


async def run_conversation(agent: Agent) -> None:
    """Gère uniquement l'interface de conversation."""
    # TODO 1 : remplace cet identifiant par un identifiant propre à chaque utilisateur.
    # Sans db_path, la conversation est conservée uniquement pendant ce programme.
    session = SQLiteSession("utilisateur-demo")

    print("Discussion lancée. Tape 'quitter' pour terminer.\n")

    # TODO 2 : transforme cette boucle pour accepter aussi une commande "nouvelle"
    # qui efface la session et recommence une conversation vide.
    while True:
        user_message = await asyncio.to_thread(input, "Toi : ")

        # TODO 3 : ajoute d'autres commandes de sortie si tu le souhaites.
        command = user_message.strip().lower()

        if command == "quitter":
            print("Conversation terminée.")
            break

        if command == "nouvelle conversation":
            await session.clear_session()
            print("Nouvelle conversation démarrée.")
            continue

        if not command:
            continue

        # La même session redonne l'historique à l'agent à chaque tour.
        result = await Runner.run(agent, user_message, session=session)
        print(f"\n{agent.name} : {result.final_output}\n")


async def main() -> None:
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError(
            "OPENAI_API_KEY est absente. Copie .env.example vers .env "
            "et ajoute ta clé API."
        )

    yazio_mcp = create_yazio_mcp_server()

    # Le contexte démarre le sous-processus MCP ici et garantit sa fermeture,
    # même si la conversation lève une exception.
    async with yazio_mcp:
        agent = create_agent(yazio_mcp)
        await run_conversation(agent)


if __name__ == "__main__":
    asyncio.run(main())
