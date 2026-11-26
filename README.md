# Nexuscore AI

API central FastAPI com um agente central e três perfis especializados (Diretoria, Engenharia e Marketing), Groq como núcleo de linguagem e persistência PostgreSQL via `DATABASE_URL` (com fallback para SQLite no desenvolvimento local). Os perfis compartilham memória registrada, contexto da conversa e uma fila de tarefas; ainda não executam delegações autônomas nem ações externas sem revisão.

## Execução

```bash
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Variáveis de ambiente

- `GROQ_API_KEY`: chave do provedor único de linguagem, raciocínio e análise visual.
- `ADMIN_TOKEN`: token forte para as rotas administrativas e criação/gestão de arquivos.
- `GROQ_MODEL`: modelo de texto (padrão `openai/gpt-oss-120b`).
- `GROQ_VISION_MODEL`: modelo multimodal para OCR e análise de imagens (padrão `qwen/qwen3.8-27b`).
- `GROQ_AGENT_TOOLS`: ferramentas nativas opcionais separadas por vírgula (`browser_search`, `code_interpreter`); vazio por padrão. Nesta etapa, só são enviadas ao modelo `openai/gpt-oss-120b` e não são usadas no fluxo de imagens.
- `DATABASE_URL`: conexão PostgreSQL; quando presente, seleciona PostgreSQL (use a URL pooled do Neon para o serviço web).
- `DATABASE_PATH`: caminho do SQLite quando `DATABASE_URL` não estiver configurada; padrão local `data/nexuscore.db`.
- `AI_REQUEST_TIMEOUT`: timeout de chamadas à IA em segundos (padrão 45).
- `MAX_INPUT_CHARS`: limite de texto de entrada (padrão 8000).

E-mail (opcional):
- SMTP: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`.
- IMAP: `IMAP_HOST`, `IMAP_PORT`, `IMAP_USER`, `IMAP_PASSWORD`, `IMAP_FOLDER`.
- `EMAIL_DESTINATARIO`: destinatário padrão opcional.

Persistência:
- Com `DATABASE_URL`, conversas, ideias, projetos, memórias compartilhadas, tarefas, e-mails e arquivos gerados são armazenados no PostgreSQL.
- Sem `DATABASE_URL`, o sistema usa SQLite local em `DATABASE_PATH`.
- Configurar `DATABASE_URL` não migra automaticamente dados do SQLite. Para uma transferência explícita, consulte `scripts/migrate_sqlite_to_postgres.py`; o destino precisa estar vazio e a origem deve estar acessível.
- O plano gratuito do provedor PostgreSQL tem limites de capacidade e não substitui uma estratégia independente de backup. Não contratar recursos pagos sem autorização.

## Rotas principais

- `GET /api/saude`: estado público da API.
- `GET /api/diagnostico`: diagnóstico protegido por `X-Admin-Token`.
- `POST /api/chat`: conversa e análise de até três imagens via Groq; possui limite básico de 20 solicitações por IP em janela móvel de 60 segundos por processo.
- `GET /api/conversas`: lista de conversas protegida; `GET/PATCH /api/conversas/{id}` abre e renomeia uma conversa.
- `GET/POST/DELETE /api/memoria`: memória compartilhada protegida; DELETE arquiva sem remover fisicamente.
- `GET/POST/PATCH /api/tarefas`: fila de tarefas por departamento, protegida.
- `GET/POST /api/ideias`: banco de ideias.
- `GET/POST/PATCH /api/projetos`: registros e status de projetos.
- `GET /api/arquivos`: lista de arquivos gerados.
- `POST /api/arquivos/gerar`: cria DOCX, PDF, Markdown, TXT, CSV ou JSON via Groq.
- `GET /api/arquivos/{id}/download`: baixa um arquivo gerado.
- `POST /api/email/enviar`, `POST /api/email/analisar`, `GET /api/email/receber`: operações de e-mail protegidas por token.

## Deploy no Render

- Runtime: Python.
- Build command: `pip install -r requirements.txt`.
- Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`.
- Configure as variáveis de ambiente no painel do Render.
- Configure `DATABASE_URL` no ambiente do Render para usar o PostgreSQL externo. Confirme o motor e a conectividade em Conexões > Diagnóstico detalhado. Não publique nem envie a URL ou a senha do banco.

O envio SMTP depende das credenciais do provedor de e-mail. O recebimento IMAP está disponível sob demanda pela rota protegida; leitura automática em segundo plano e processamento de anexos ainda não fazem parte desta etapa. Não configure segredos no GitHub nem os envie pelo chat.


## Recursos móveis (versão 1.3.0)

- Interface responsiva para celular e notebook.
- Ditado por voz usando SpeechRecognition quando o navegador oferecer suporte.
- Leitura das respostas com a síntese de voz do dispositivo; Diretoria, Engenharia, Marketing e o agente central usam perfis de voz distintos. As vozes disponíveis e a naturalidade dependem das vozes instaladas no Android ou computador.
- Ações de galeria e câmera pelo seletor de mídia do Android. A compilação APK declara permissões de câmera, microfone e imagens.
- Até três imagens por mensagem, normalizadas no aparelho para JPEG antes do envio e analisadas pelo modelo visual da Groq.
- Raciocínio avançado configurado no modelo principal e no modelo visual.
- Análise de imagens, OCR e interpretação visual via Groq. A API Groq não oferece geração de imagens; nenhum provedor externo foi adicionado.

A interface web é servida pelo Render e pode atualizar sem reinstalar o invólucro Android. Alterações em permissões nativas exigem uma nova compilação e instalação do APK. A Groq é o provedor atual de linguagem, raciocínio e análise visual. As ferramentas nativas de pesquisa na web e execução de código podem ser habilitadas com `GROQ_AGENT_TOOLS`; ficam desativadas por padrão e dependem da disponibilidade/limites do provedor. Geração de imagens não está disponível pela API Groq.
