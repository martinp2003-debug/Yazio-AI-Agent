# Agent IA YAZIO

Ce projet vise à créer un petit agent IA avec lequel interagir afin d'exploiter et de compléter les fonctionnalités proposées par le MCP YAZIO.

## Lancer l'interface

Après avoir configuré `.env`, démarrer l'application avec :

```bash
uv run uvicorn app:app --reload
```

Ouvre ensuite [http://localhost:8000](http://localhost:8000). L'application doit
rester sur un seul worker afin de ne démarrer qu'un processus MCP YAZIO.

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
