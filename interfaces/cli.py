import asyncio
from data import Conversation
from services import ChatService


async def prompt_new_session(chat_service: ChatService) -> Conversation:
    title = await asyncio.to_thread(input, "Titre (facultatif) : ")
    return chat_service.create_conversation(title)


async def select_session(chat_service: ChatService) -> Conversation | None:
    """Propose de créer une conversation ou d'en recharger une."""
    while True:
        print("\n1. Nouvelle conversation")
        print("2. Recharger une conversation")
        print("q. Quitter")
        choice = (await asyncio.to_thread(input, "Choix : ")).strip().lower()

        if choice == "1":
            return await prompt_new_session(chat_service)

        if choice == "2":
            sessions = chat_service.list_conversations()
            if not sessions:
                print("Aucune conversation enregistrée.")
                continue

            for index, conversation in enumerate(sessions, start=1):
                updated_at = conversation.updated_at.astimezone().strftime(
                    "%Y-%m-%d %H:%M"
                )
                print(
                    f"{index}. {conversation.title} "
                    f"({conversation.conversation_id[:8]}, {updated_at})"
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
    chat_service: ChatService,
    conversation: Conversation,
    assistant_name: str,
) -> None:
    """Gère l'interface et le changement de conversation."""
    print(f"\nConversation : {conversation.title}")
    print(f"Session : {conversation.conversation_id}")
    print("Tape 'nouvelle conversation' ou 'quitter'.\n")

    while True:
        user_message = await asyncio.to_thread(input, "Toi : ")
        command = user_message.strip().lower()

        if command == "quitter":
            print("Conversation terminée.")
            break

        if command == "nouvelle conversation":
            conversation = await prompt_new_session(chat_service)
            print(f"Nouvelle conversation : {conversation.title}")
            print(f"Session : {conversation.conversation_id}\n")
            continue

        if not command:
            continue

        response = await chat_service.send_message(
            conversation.conversation_id,
            user_message,
            channel="cli",
        )
        print(f"\n{assistant_name} : {response}\n")


async def run_cli(chat_service: ChatService, assistant_name: str) -> None:
    """Lance l'interface terminal avec les services déjà assemblés."""
    conversation = await select_session(chat_service)
    if conversation is None:
        return

    await run_conversation(chat_service, conversation, assistant_name)
