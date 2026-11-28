# Nexuscore AI

API central FastAPI com um agente central e três perfis especializados (Diretoria, Engenharia e Marketing), Groq como núcleo de linguagem e persistência PostgreSQL via `DATABASE_URL` (com fallback para SQLite no desenvolvimento local). Os perfis compartilham memória registrada, contexto da conversa e uma fila auditável de tarefas. A delegação e a produção/revisão de entregas textuais elegíveis podem ocorrer automaticamente; alterações de código e ações externas continuam bloqueadas.

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
- `NEXUSCORE_AUTO_EXECUTION`: habilita/desabilita o executor textual automático (padrão `true`, desde que `GROQ_API_KEY` esteja configurada).
- `NEXUSCORE_MAX_TASKS_PER_DAY`: limite persistente de tentativas de execução automática por dia UTC (padrão 10; intervalo aceito de 1 a 100). Cada tarefa usa normalmente duas chamadas Groq e pode usar até quatro se precisar de uma correção e segunda revisão.
- `GITHUB_APP_ID`, `GITHUB_INSTALLATION_ID`, `GITHUB_APP_PRIVATE_KEY` e `GITHUB_REPOSITORY`: configuração opcional da GitHub App usada pela Engenharia. A chave privada deve ficar somente como segredo no Render; nunca no repositório ou no chat.

### GitHub da Engenharia — primeira fase (somente leitura)

Para ativar a leitura controlada do repositório:
1. Criar uma GitHub App e instalá-la somente no repositório Nexuscore pretendido.
2. Conceder apenas **Contents: Read-only**; manter Pull requests e Actions sem permissões. Metadata permanece na permissão padrão de leitura.
3. Guardar o App ID, o Installation ID, a chave privada PEM e o nome `owner/repository` nas quatro variáveis acima, no ambiente do serviço Render.
4. Consultar **Execução → GitHub da Engenharia** para verificar a conexão.

A API usa JWT da GitHub App para obter tokens temporários de instalação; o token não é persistido. A leitura é restrita a arquivos de código/documentação em pastas permitidas e a 128 KB por arquivo. Arquivos de segredo, credenciais, bancos locais e caminhos fora da lista são bloqueados. Nesta fase não há escrita, criação de branches/PRs, execução de código ou deploy. A integração de escrita só será habilitada depois de existir execução isolada e revisão de segurança.

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
- `GET /api/engenharia/github/status` e `GET /api/engenharia/github/arquivo?path=...`: status e leitura restrita do repositório, protegidos por `X-Admin-Token`.
- `POST /api/chat`: conversa e análise de até três imagens via Groq; possui limite básico de 20 solicitações por IP em janela móvel de 60 segundos por processo.
- `GET /api/conversas`: lista de conversas protegida; `GET/PATCH /api/conversas/{id}` abre e renomeia uma conversa.
- `GET/POST/DELETE /api/memoria`: memória compartilhada protegida; DELETE arquiva sem remover fisicamente.
- `GET/POST/PATCH /api/tarefas`: fila de tarefas por departamento, protegida.
- `GET/POST /api/ideias`: banco de ideias.
- `GET/POST/PATCH /api/projetos`: registros e status de projetos.
- `GET /api/projetos/{id}/progresso`: cálculo ponderado do progresso de um projeto aprovado, protegido por `X-Admin-Token`.
- `POST /api/tarefas/{id}/validar`: registra a validação da Diretoria para uma tarefa em revisão.
- `GET /api/arquivos`: lista de arquivos gerados.
- `POST /api/arquivos/gerar`: cria DOCX, PDF, Markdown, TXT, CSV ou JSON via Groq.
- `GET /api/arquivos/{id}/download`: baixa um arquivo gerado.
- `POST /api/email/enviar`, `POST /api/email/analisar`, `GET /api/email/receber`: operações de e-mail protegidas por token.

## Progresso híbrido de projetos

- O progresso é calculado sob demanda a partir das tarefas vinculadas ao projeto, dos pesos persistidos das tarefas e dos pesos departamentais (quando configurados).
- Tarefas canceladas são excluídas do denominador; tarefas em revisão não contam como concluídas.
- Para tarefas vinculadas a projetos, o envio para revisão exige evidências no campo de resultado. A conclusão exige registro de validação da Diretoria no histórico auditável.
- O percentual calculado não é duplicado em uma coluna de projeto; a API calcula o valor a partir dos registros atuais.
- O executor interno do serviço Render pode produzir entregas textuais para Diretoria, Marketing e Nexuscore, com segunda revisão por IA e no máximo uma rodada de correção. O resultado é registrado no histórico da tarefa.
- Tarefas de Engenharia que exigem alterar código/repositório e ações externas (envio, publicação, pagamento, deploy, credenciais etc.) são bloqueadas; não se deve interpretar uma tarefa bloqueada como executada.
- O executor contabiliza tentativas em eventos persistentes e respeita um limite diário UTC configurável. O resumo protegido `GET /api/execucao/resumo` mostra fila, tentativas do dia, limite e capacidade restante.
- O executor reutiliza a integração Groq já configurada; cada tentativa pode gerar consumo do provedor. O limite diário reduz, mas não elimina, esse consumo.

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
