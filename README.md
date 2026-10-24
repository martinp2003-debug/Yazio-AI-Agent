# Agent IA YAZIO

Ce projet vise à créer un petit agent IA avec lequel interagir afin d'exploiter et de compléter les fonctionnalités proposées par le MCP YAZIO.

## Architecture actuelle

```mermaid
flowchart LR
    user([Utilisateur])

    subgraph interfaces[Interfaces]
        web_entry[Serveur web<br/>app.py · FastAPI + Uvicorn]
        web[Interface Gradio<br/>interfaces/web]
        cli_entry[Point d'entrée<br/>cli.py]
        cli[Interface terminal<br/>interfaces/cli.py]
        web_entry --> web
        cli_entry --> cli
    end

    subgraph application[Application]
        bootstrap[ApplicationContainer<br/>bootstrap.py]
        chat[ChatService<br/>orchestration des conversations]
        conversations[ConversationManager<br/>cycle de vie des conversations]
        observability[ObservabilityService<br/>traces par tour]
    end

    subgraph agent_layer[Agent IA]
        runner[OpenAI Agents SDK<br/>Runner + Agent]
        prompt[System Prompt<br/>et contexte temporel]
        mcp_client[Client MCP<br/>MCPServerStdio]
        prompt --> runner
        runner --> mcp_client
    end

    subgraph persistence[Persistance locale]
        repository[ConversationRepository<br/>métadonnées]
        history_store[AgentHistoryStore<br/>adaptateur du SDK]
        history[SQLiteSession<br/>historique de l'agent]
        sqlite[(storage/conversations.db)]
        repository --> sqlite
        history_store --> history
        history --> sqlite
    end

    subgraph external[Services externes]
        openai[API OpenAI]
        mcp[MCP YAZIO<br/>processus enfant en stdio]
        yazio[Services YAZIO]
        langfuse[Langfuse]
        mcp --> yazio
    end

    user --> web_entry
    user --> cli_entry
    web_entry -.-> bootstrap
    cli_entry -.-> bootstrap
    web --> chat
    cli --> chat
    bootstrap -.-> chat
    bootstrap -.-> conversations
    bootstrap -.-> observability
    bootstrap -.-> runner
    chat --> runner
    chat --> conversations
    chat --> observability
    conversations --> repository
    conversations --> history_store
    runner --> openai
    mcp_client --> mcp
    observability --> langfuse

    classDef interfaceNode fill:#DBEAFE,stroke:#2563EB,color:#1E3A8A,stroke-width:2px
    classDef applicationNode fill:#DCFCE7,stroke:#16A34A,color:#14532D,stroke-width:2px
    classDef agentNode fill:#F3E8FF,stroke:#9333EA,color:#581C87,stroke-width:2px
    classDef persistenceNode fill:#FEF3C7,stroke:#D97706,color:#78350F,stroke-width:2px
    classDef externalNode fill:#FFE4E6,stroke:#E11D48,color:#881337,stroke-width:2px

    class web_entry,web,cli_entry,cli interfaceNode
    class bootstrap,chat,conversations,observability applicationNode
    class runner,prompt,mcp_client agentNode
    class repository,history_store,history,sqlite persistenceNode
    class openai,mcp,yazio,langfuse externalNode

    style interfaces fill:#EFF6FF,stroke:#60A5FA,stroke-width:2px
    style application fill:#F0FDF4,stroke:#4ADE80,stroke-width:2px
    style agent_layer fill:#FAF5FF,stroke:#C084FC,stroke-width:2px
    style persistence fill:#FFFBEB,stroke:#FBBF24,stroke-width:2px
    style external fill:#FFF1F2,stroke:#FB7185,stroke-width:2px
```

`bootstrap.py` assemble une seule fois les services partagés par les interfaces
web et terminal. Le service de conversation exécute l'agent avec un historique
persistant, tandis que l'agent appelle les outils YAZIO via un processus MCP
séparé. L'observabilité Langfuse est optionnelle et se configure par variables
d'environnement.

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
