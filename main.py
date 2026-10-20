import asyncio
from datetime import datetime
import os
import shlex
from zoneinfo import ZoneInfo

from agents import Agent, Runner, SQLiteSession
from agents.mcp import MCPServerStdio
from dotenv import load_dotenv


# Charge les variables du fichier .env dans l'environnement.
load_dotenv()


def build_agent_instructions(_context, _agent) -> str:
    """Génère les instructions avec une date fraîche à chaque tour."""
    timezone_name = os.getenv("YAZIO_TIMEZONE", "Europe/Paris")
    now = datetime.now(ZoneInfo(timezone_name))

    return f"""
Tu es un assistant spécialisé dans le suivi alimentaire YAZIO.

Contexte temporel de ce tour :
- Date locale actuelle : {now:%Y-%m-%d}
- Heure locale actuelle : {now:%H:%M:%S}
- Fuseau horaire : {timezone_name}

Ta mission est d'aider l'utilisateur à enregistrer dans YAZIO les aliments,
repas et boissons qu'il a réellement consommés.

Règles concernant la date :
- Si aucune date n'est indiquée, utilise la date locale actuelle ci-dessus.
- Interprète "aujourd'hui", "hier" et "demain" relativement à cette date.
- Convertis toujours la date destinée aux outils alimentaires au format YYYY-MM-DD.
- Ne choisis jamais une autre date sans indication explicite de l'utilisateur.
- Si l'expression temporelle reste réellement ambiguë, pose une seule question concise.

Pour enregistrer un aliment :
1. Identifie l'aliment, la quantité, l'unité et le repas concerné.
2. Recherche l'aliment avec les outils MCP YAZIO.
3. Utilise les informations exactes renvoyées par les outils ; n'invente aucune
   valeur nutritionnelle ni aucun identifiant de produit.
4. Enregistre la consommation avec la date résolue au format YYYY-MM-DD.
5. Ne confirme l'enregistrement que si l'outil d'écriture l'a confirmé.

Les repas valides sont breakfast, lunch, dinner et snack. Si une information
indispensable à l'outil manque ou est ambiguë, pose une seule question de
clarification. Réponds en français, clairement et brièvement.
""".strip()


def create_yazio_mcp_server() -> MCPServerStdio:
    """Prépare le processus MCP YAZIO, sans encore le démarrer."""
    command = os.getenv("YAZIO_MCP_COMMAND")
    raw_args = os.getenv("YAZIO_MCP_ARGS")
    cwd = os.getenv("YAZIO_MCP_CWD")

    missing_variables = [
        name
        for name, value in {
            "YAZIO_MCP_COMMAND": command,
            "YAZIO_MCP_ARGS": raw_args,
            "YAZIO_MCP_CWD": cwd,
        }.items()
        if not value
    ]
    if missing_variables:
        raise RuntimeError(
            "Configuration MCP incomplète : " + ", ".join(missing_variables)
        )

    return MCPServerStdio(
        name="MCP YAZIO",
        params={
            "command": command,
            "args": shlex.split(raw_args),
            "cwd": cwd,
        },
        # La liste des outils ne change normalement pas pendant l'exécution.
        cache_tools_list=True,
    )


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
        if user_message.lower() == "quitter":
            print("Conversation terminée.")
            break
        
        if user_message.lower() == "nouvelle conversation":
            await session.clear_session()
            print("Conversation terminée, nouvelle conversation arrive.")
            continue

        if not user_message:
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
