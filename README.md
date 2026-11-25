# Nexuscore AI

API central FastAPI com três perfis especializados (Diretoria, Engenharia e Marketing), Groq como núcleo de linguagem e persistência local SQLite. Os perfis ainda não executam uma cadeia colaborativa entre si.

## Execução

```bash
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Variáveis de ambiente

Obrigatórias conforme os recursos utilizados:

- `GROQ_API_KEY`: chave da Groq para modelos compatíveis.\n- `OPENAI_API_KEY`: chave opcional da OpenAI API; quando configurada, passa a ser o provedor principal e habilita análise de imagens. A API é cobrada separadamente da assinatura ChatGPT. Nunca envie essa chave pelo chat nem a grave no GitHub.\n- `OPENAI_MODEL`: modelo de API OpenAI com suporte a visão; padrão `gpt-4o-mini`.
- `ADMIN_TOKEN`: token forte para rotas administrativas.
- `GROQ_MODEL`: padrão `openai/gpt-oss-120b`, com raciocínio avançado ativado.
- `GROQ_VISION_MODEL`: padrão `qwen/qwen3.8-27b`, modelo multimodal para OCR, leitura de capturas de tela e análise visual (até 3 imagens por requisição).

E-mail de saída (SMTP):

- `SMTP_HOST`, `SMTP_PORT` (padrão 587), `SMTP_USER`, `SMTP_PASSWORD`.
- `SMTP_FROM`: remetente; se omitido, usa `SMTP_USER`.

Recebimento IMAP manual (rota administrativa `GET /api/email/receber`):
- `IMAP_HOST`, `IMAP_PORT` (padrão 993), `IMAP_USER`, `IMAP_PASSWORD`.
- `IMAP_FOLDER`: pasta a consultar (padrão `INBOX`).
- `EMAIL_DESTINATARIO`: destinatário padrão opcional. Também é possível enviar `destinatario` na requisição.

Persistência:

- `DATABASE_PATH`: caminho do arquivo SQLite. Padrão local: `data/nexuscore.db`. O código também reconhece `DB_PATH` como alias compatível.
- No plano gratuito do Render, não há disco persistente incluído. O banco SQLite funciona como armazenamento temporário e os dados podem ser perdidos em reinicializações, suspensão ou novos deploys. O projeto não contratará recursos pagos sem autorização.

Segurança e rede:

- `CORS_ORIGINS`: origens permitidas separadas por vírgula. Deixe vazio se frontend e API forem servidos pela mesma origem.
- `AI_REQUEST_TIMEOUT`: timeout em segundos (padrão 45).
- `MAX_INPUT_CHARS`: limite de entrada (padrão 8000).

## Rotas principais

- `GET /api/saude`: saúde pública sem expor segredos.
- `GET /api/diagnostico`: diagnóstico protegido pelo cabeçalho `X-Admin-Token`.
- `POST /api/chat`: chat com seleção de agente, raciocínio avançado e análise de até três imagens.
- `GET /api/conversas`: histórico persistido.
- `GET/POST /api/ideias`: banco de ideias persistido.
- `POST /api/email/enviar`: envio SMTP real; retorna erro se SMTP não estiver configurado.
- `POST /api/email/analisar`: analisa o conteúdo fornecido e salva o resultado no banco.
- `GET /api/email/receber`: busca mensagens não lidas via IMAP; requer `X-Admin-Token`.

## Deploy no Render

- Runtime: Python.
- Build command: `pip install -r requirements.txt`.
- Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`.
- Configure as variáveis de ambiente no painel do Render.
- No plano gratuito, aceite que o banco SQLite é temporário; exporte periodicamente os dados importantes antes de novos deploys. Não há garantia de retenção permanente.

O envio SMTP depende das credenciais do provedor de e-mail. O recebimento IMAP está disponível sob demanda pela rota protegida; leitura automática em segundo plano e processamento de anexos ainda não fazem parte desta etapa. Não configure segredos no GitHub nem os envie pelo chat.


## Recursos móveis (versão 1.3.0)

- Interface responsiva para celular e notebook.
- Ditado por voz usando SpeechRecognition quando o navegador oferecer suporte.
- Leitura das respostas com a síntese de voz do dispositivo; Diretoria, Engenharia, Marketing e o agente central usam perfis de voz distintos. As vozes disponíveis e a naturalidade dependem das vozes instaladas no Android ou computador.
- Ações de galeria e câmera pelo seletor de mídia do Android. A compilação APK declara permissões de câmera, microfone e imagens.
- Até três imagens por mensagem, normalizadas no aparelho para JPEG antes do envio e analisadas pelo modelo visual da Groq.
- Raciocínio avançado configurado no modelo principal e no modelo visual.
- Análise de imagens, OCR e interpretação visual via Groq. A API Groq não oferece geração de imagens; nenhum provedor externo foi adicionado.

A interface web é servida pelo Render e pode atualizar sem reinstalar o invólucro Android. Alterações em permissões nativas exigem uma nova compilação e instalação do APK. A Groq é o provedor único de linguagem, raciocínio e análise visual. Geração de imagens não está disponível pela API Groq.
