# Agent IA YAZIO

Ce projet vise à créer un petit agent IA avec lequel interagir afin d'exploiter et de compléter les fonctionnalités proposées par le MCP YAZIO.

## Architecture actuelle

```mermaid
flowchart LR
    user([Utilisateur])

    subgraph interfaces[Interfaces]
        web_entry[Serveur web<br/>app.py]
        web[Interface Gradio<br/>interfaces/web/gradio_app.py]
        cli_entry[Point d'entrée terminal<br/>cli.py]
        cli[Interface terminal<br/>interfaces/cli.py]
        web_entry --> web
        cli_entry --> cli
    end

    subgraph application[Cœur applicatif]
        bootstrap[build_application + ApplicationContainer<br/>bootstrap.py]
        chat[ChatService<br/>services/chat_service.py]
        conversations[ConversationManager<br/>services/conversation_manager.py]
        observability[ObservabilityService<br/>services/observability_service.py]
    end

    subgraph agent_layer[Agent IA]
        agent[Agent OpenAI<br/>agent/yazio_agent.py]
        prompt[Prompt système<br/>agent/system_prompt.py]
        mcp_client[Client MCP<br/>agent/yazio_mcp_server.py]
        prompt --> agent
        agent --> mcp_client
    end

    subgraph persistence[Persistance locale]
        repository[ConversationRepository<br/>data/conversation_repository.py]
        history_store[AgentHistoryStore<br/>data/agent_history_store.py]
        history[SQLiteSession<br/>OpenAI Agents SDK]
        sqlite[(storage/conversations.db)]
        repository --> sqlite
        history_store --> history
        history --> sqlite
    end

    subgraph external[Services externes]
        openai[API OpenAI]
        mcp[MCP YAZIO<br/>processus enfant]
        yazio[Services YAZIO]
        langfuse[Langfuse]
        mcp --> yazio
    end

    user --> web_entry
    user --> cli_entry
    web_entry -. démarre .-> bootstrap
    cli_entry -. démarre .-> bootstrap
    bootstrap -. assemble .-> chat
    web --> chat
    cli --> chat
    chat --> agent
    chat --> conversations
    chat --> observability
    conversations --> repository
    conversations --> history_store
    agent --> openai
    mcp_client --> mcp
    observability --> langfuse

    classDef interfaceNode fill:#DBEAFE,stroke:#2563EB,color:#1E3A8A,stroke-width:2px
    classDef applicationNode fill:#DCFCE7,stroke:#16A34A,color:#14532D,stroke-width:2px
    classDef agentNode fill:#F3E8FF,stroke:#9333EA,color:#581C87,stroke-width:2px
    classDef persistenceNode fill:#FEF3C7,stroke:#D97706,color:#78350F,stroke-width:2px
    classDef externalNode fill:#FFE4E6,stroke:#E11D48,color:#881337,stroke-width:2px

    class web_entry,web,cli_entry,cli interfaceNode
    class bootstrap,chat,conversations,observability applicationNode
    class agent,prompt,mcp_client agentNode
    class repository,history_store,history,sqlite persistenceNode
    class openai,mcp,yazio,langfuse externalNode

    style interfaces fill:#EFF6FF,stroke:#60A5FA,stroke-width:2px
    style application fill:#F0FDF4,stroke:#4ADE80,stroke-width:2px
    style agent_layer fill:#FAF5FF,stroke:#C084FC,stroke-width:2px
    style persistence fill:#FFFBEB,stroke:#FBBF24,stroke-width:2px
    style external fill:#FFF1F2,stroke:#FB7185,stroke-width:2px
```

Les flèches pleines représentent le flux d'exécution. Les flèches pointillées
représentent uniquement le démarrage : le point d'entrée appelle
`build_application()`, puis `bootstrap.py` construit le graphe de dépendances et
renvoie un `ApplicationContainer`. Une fois l'application lancée, les messages
passent directement de l'interface au `ChatService`, sans repasser par le
bootstrap.

Le container gère aussi le cycle de vie du processus MCP et l'envoi des traces
avant l'arrêt. L'historique et les métadonnées des conversations sont conservés
localement dans SQLite. Langfuse reste facultatif.

## Lancer l'interface web

Configurer `.env`, puis démarrer l'application avec :

```bash
uv run uvicorn app:app --reload
```

Ouvrir ensuite [http://localhost:8000](http://localhost:8000). Conserver un seul
worker afin de ne démarrer qu'un processus MCP YAZIO.

## Lancer l'interface terminal

Le même service de conversation peut être utilisé sans interface web :

```bash
uv run python cli.py
```

## Observabilité avec Langfuse

Ajouter les identifiants Langfuse dans `.env` :

```env
LANGFUSE_ENABLED=true
LANGFUSE_CAPTURE_CONTENT=true
LANGFUSE_PUBLIC_KEY=pk-lf-remplace-moi
LANGFUSE_SECRET_KEY=sk-lf-remplace-moi
LANGFUSE_BASE_URL=https://cloud.langfuse.com
```

Chaque appel à l'agent crée une trace, regroupée par conversation.
`LANGFUSE_ENABLED=false` désactive Langfuse et
`LANGFUSE_CAPTURE_CONTENT=false` masque le contenu des messages et des outils.
