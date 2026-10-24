# Agent IA YAZIO

Ce projet vise à créer un petit agent IA avec lequel interagir afin d'exploiter et de compléter les fonctionnalités proposées par le MCP YAZIO.

## Architecture actuelle

```mermaid
flowchart LR
    user([Utilisateur])

    subgraph interfaces[Interfaces]
        web[Interface web<br/>Gradio]
        api[Application ASGI<br/>FastAPI / Uvicorn]
        cli[Interface terminal<br/>cli.py]
        api --> web
    end

    subgraph application[Application]
        chat[ChatService<br/>orchestration des conversations]
        store[SessionStoreService<br/>gestion des sessions]
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
        repository[SessionRepository<br/>métadonnées]
        history[SQLiteSession<br/>historique des messages]
        sqlite[(storage/conversations.db)]
        repository --> sqlite
        history --> sqlite
    end

    subgraph external[Services externes]
        openai[API OpenAI]
        mcp[MCP YAZIO<br/>processus enfant en stdio]
        yazio[Services YAZIO]
        langfuse[Langfuse]
        mcp --> yazio
    end

    user --> api
    user --> cli
    web --> chat
    cli --> chat
    chat --> runner
    chat --> store
    chat --> observability
    store --> repository
    store --> history
    runner --> openai
    mcp_client --> mcp
    observability --> langfuse

    classDef interfaceNode fill:#DBEAFE,stroke:#2563EB,color:#1E3A8A,stroke-width:2px
    classDef applicationNode fill:#DCFCE7,stroke:#16A34A,color:#14532D,stroke-width:2px
    classDef agentNode fill:#F3E8FF,stroke:#9333EA,color:#581C87,stroke-width:2px
    classDef persistenceNode fill:#FEF3C7,stroke:#D97706,color:#78350F,stroke-width:2px
    classDef externalNode fill:#FFE4E6,stroke:#E11D48,color:#881337,stroke-width:2px

    class web,api,cli interfaceNode
    class chat,store,observability applicationNode
    class runner,prompt,mcp_client agentNode
    class repository,history,sqlite persistenceNode
    class openai,mcp,yazio,langfuse externalNode

    style interfaces fill:#EFF6FF,stroke:#60A5FA,stroke-width:2px
    style application fill:#F0FDF4,stroke:#4ADE80,stroke-width:2px
    style agent_layer fill:#FAF5FF,stroke:#C084FC,stroke-width:2px
    style persistence fill:#FFFBEB,stroke:#FBBF24,stroke-width:2px
    style external fill:#FFF1F2,stroke:#FB7185,stroke-width:2px
```

`app.py` et `cli.py` assemblent les mêmes services. Le service de conversation
exécute l'agent avec une session persistante, tandis que l'agent appelle les
outils YAZIO via un processus MCP séparé. L'observabilité Langfuse est
optionnelle et se configure par variables d'environnement.

## Lancer l'interface web

Après avoir configuré `.env`, démarrer l'application avec :

```bash
uv run uvicorn app:app --reload
```

Ouvre ensuite [http://localhost:8000](http://localhost:8000). L'application doit
rester sur un seul worker afin de ne démarrer qu'un processus MCP YAZIO.

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
