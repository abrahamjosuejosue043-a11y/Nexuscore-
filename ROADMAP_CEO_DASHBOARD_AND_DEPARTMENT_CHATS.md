# Roadmap — Painel do CEO e central de conversas

## Estado
Planejado para uma etapa futura. Este documento registra a decisão de produto; não representa funcionalidade já implementada.

## Objetivo
Criar uma área exclusiva do CEO que organize as funções executivas em um único painel, reduza a poluição da interface operacional e ofereça acesso direto às conversas com a Diretoria e os departamentos.

## Estrutura proposta

### 1. Painel do CEO
Uma entrada principal na navegação, com acesso organizado às funções de autoridade e acompanhamento do proprietário:
- Visão geral / resumo executivo.
- Projetos e fila de aprovação.
- Conexões e integrações.
- Tarefas e acompanhamento departamental.
- Planos de trabalho e aprovações.
- Relatórios, histórico e auditoria.
- Configurações e permissões.

As opções administrativas devem ficar agrupadas dentro do Painel do CEO, em vez de permanecerem todas expostas na navegação principal. A interface deve ocultar essas opções dos perfis/departamentos que não tenham autorização.

### 2. Acesso rápido às conversas
Criar atalhos persistentes para:
- Chat com a Diretoria.
- Chat com Marketing.
- Chat com Engenharia.
- Chat conjunto “Diretoria + Marketing + Engenharia”.

O chat conjunto permite ao CEO fazer uma pergunta para os três departamentos. A Diretoria coordena a solicitação, direciona subtarefas aos departamentos pertinentes e consolida uma resposta única, identificando contribuições, divergências, bloqueios e responsáveis.

### 3. Regras de roteamento e governança
- Conversas e tarefas permanecem isoladas por projeto e contexto, respeitando as regras atuais de isolamento.
- Mensagens enviadas a um departamento devem ser registradas no contexto correto e associadas ao projeto quando aplicável.
- No chat conjunto, a Diretoria atua como coordenadora; departamentos não recebem acesso irrestrito às conversas ou dados uns dos outros.
- O CEO mantém autoridade final sobre aprovações, permissões e ações sensíveis.
- O sistema deve indicar claramente quem está respondendo: Diretoria, Marketing ou Engenharia.
- Deve existir histórico pesquisável das perguntas, encaminhamentos, respostas e decisões.

## Etapas sugeridas

1. **Arquitetura e permissões:** mapear papéis, opções do CEO, navegação e limites de acesso.
2. **Painel do CEO:** criar a área agrupadora e mover para ela os atalhos de Projetos, Conexões, Aprovações, Relatórios e Configurações, sem remover funcionalidades existentes.
3. **Chats individuais:** adicionar atalhos para Diretoria, Marketing e Engenharia, mantendo contexto e isolamento.
4. **Chat conjunto:** implementar roteamento coordenado pela Diretoria, delegação controlada e resposta consolidada.
5. **Auditoria e validação:** testar permissões, isolamento entre projetos, histórico, continuidade das conversas e experiência mobile.

## Critérios de aceitação
- O CEO encontra suas funções administrativas em um único painel.
- Departamentos só visualizam as opções e dados autorizados para seu papel.
- Os quatro atalhos de conversa abrem o contexto correto.
- O chat conjunto encaminha a pergunta aos departamentos adequados e apresenta uma resposta consolidada pela Diretoria.
- As conversas e tarefas não vazam entre projetos.
- Perguntas, encaminhamentos, respostas e decisões ficam auditáveis.
- A interface funciona em telas móveis e desktop.

## Fora de escopo nesta etapa
- Não implementar agora.
- Não substituir a navegação atual nem remover opções existentes.
- Não criar agentes autônomos ou conceder permissões extras por causa dos atalhos.
- Não alterar a integração de provedores, banco de dados ou infraestrutura nesta etapa.
- A implementação deve ser incremental, com testes, PR e validação antes de cada publicação.
