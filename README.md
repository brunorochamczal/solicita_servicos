# 🧹 Solicita — Sistema de Gestão de Asseio e Conservação

> Sistema web para abertura, acompanhamento e conclusão de chamados de serviços de asseio e conservação, com controle de acesso por perfil de usuário.

---

## 📋 Sobre o Projeto

O **Solicita** é uma aplicação web desenvolvida em **Python (Flask)** que centraliza a gestão de solicitações de serviços de limpeza, manutenção e conservação de instalações. O sistema permite que colaboradores abram chamados, que responsáveis os aprovem ou rejeitem, e que a equipe de execução confirme a conclusão dos serviços — tudo com rastreabilidade completa e histórico de observações.

---

## ✨ Funcionalidades

- 🔐 **Autenticação** com controle de sessão e senhas com hash seguro (scrypt)
- 👥 **Quatro perfis de usuário** com permissões distintas
- 📋 **Abertura de chamados** com foto anexada
- 🔍 **Consulta e filtragem** de chamados por múltiplos critérios
- ✅ **Fluxo de aprovação** — chefe decide se o chamado prossegue ou é descartado
- 🔧 **Execução e conclusão** de serviços com observação do trabalhador
- 📊 **Relatórios** em PDF com todos os chamados
- 🏢 **Cadastro** de usuários, funcionários, setores e categorias
- ❓ **Seção de ajuda** com guias passo a passo para cada funcionalidade

---

## 👤 Perfis de Usuário

| Perfil | Abrir Chamado | Consultar | Confirmar/Descartar | Executar/Concluir | Relatório | Cadastros |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Solicitação** | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ |
| **Confirmação** | ❌ | ✅ | ✅ | ❌ | ✅ | ❌ |
| **Executar** | ❌ | ✅ | ❌ | ✅ | ✅ | ❌ |
| **Administrador** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

---

## 🔄 Fluxo de um Chamado

```
Usuário abre chamado
        │
        ▼
   Status: ABERTO
        │
        ▼
 Chefe decide (modal Confirmar/Descartar)
        │
   ┌────┴────┐
   ▼         ▼
CONFIRMADO  CANCELADO
   │
   ▼
 Equipe executa o serviço
        │
        ▼
   Status: EXECUTADO
   (com observação registrada)
```

---

## 🗂️ Estrutura de Arquivos

```
solicita/
├── sistema_web.py              # Aplicação Flask — rotas, lógica e API
├── requirements.txt            # Dependências Python
│
├── templates/                  # Templates Jinja2
│   ├── login1.html
│   ├── index.html              # Dashboard principal
│   ├── index1.html             # Menu de serviços (com controle de permissão)
│   ├── service.html            # Abertura de chamados
│   ├── Consultas.html          # Consulta com filtros e modal de detalhes
│   ├── confirmar_servicos.html # Aprovação/rejeição de chamados
│   ├── executar_servicos.html  # Conclusão de serviços executados
│   ├── cadastros.html          # Cadastros (admin)
│   ├── relatorio.html          # Relatório geral
│   ├── pagina_ajuda.html       # Central de ajuda
│   ├── ajuda_abrir_chamado.html
│   ├── ajuda_consultar_servico.html
│   ├── ajuda_confirmar_servico.html
│   ├── ajuda_executar_servico.html
│   ├── ajuda_relatorio.html
│   └── ajuda_cadastro.html
│
└── static/
    ├── css/
    ├── js/
    ├── images/
    └── uploads/               # Fotos enviadas nos chamados
```

---

## 🗄️ Banco de Dados

O projeto utiliza **PostgreSQL** (hospedado no [Neon](https://neon.tech)). As principais tabelas são:

| Tabela | Descrição |
|---|---|
| `usuarios` | Usuários do sistema com permissão e hash de senha |
| `funcionarios` | Equipe de execução dos serviços |
| `servicos` | Chamados abertos (coração do sistema) |
| `setor` | Setores solicitantes |
| `categoria_servicos` | Categorias de serviços |

### Colunas principais da tabela `servicos`

| Coluna | Descrição |
|---|---|
| `servicos_id_seq` | ID sequencial do chamado |
| `assunto` | Descrição do chamado |
| `funcionario` | Responsável pela execução |
| `status` | `aberto` / `confirmado` / `executado` / `cancelado` |
| `foto` | Caminho relativo da imagem (`uploads/arquivo.ext`) |
| `observacao_confirmacao` | Observação do chefe ao decidir |
| `observacao_execucao` | Observação do trabalhador ao concluir |

---

## 🚀 Como Executar Localmente

### 1. Pré-requisitos

- Python 3.10+
- PostgreSQL (ou conta no Neon)

### 2. Clone o repositório

```bash
git clone https://github.com/seu-usuario/solicita.git
cd solicita
```

### 3. Instale as dependências

```bash
pip install -r requirements.txt
```

### 4. Configure as variáveis de ambiente

Crie um arquivo `.env` na raiz do projeto:

```env
DATABASE_URL=postgresql://usuario:senha@host/banco?sslmode=require
SECRET_KEY=sua_chave_secreta_aqui
```

### 5. Execute a migração do banco

No cliente PostgreSQL ou no painel do Neon, execute o arquivo `migracao_banco.sql`:

```bash
psql $DATABASE_URL -f migracao_banco.sql
```

### 6. Inicie o servidor

```bash
python sistema_web.py
```

Acesse em: [http://localhost:5000](http://localhost:5000)

---

## ☁️ Deploy no Render

O projeto está configurado para deploy automático no [Render](https://render.com).

1. Conecte o repositório ao Render como **Web Service**
2. Defina as variáveis de ambiente `DATABASE_URL` e `SECRET_KEY` no painel do Render
3. O Render executará automaticamente `pip install -r requirements.txt` e iniciará a aplicação

> **Atenção:** o Render usa sistema de arquivos efêmero. Fotos enviadas nos chamados são perdidas a cada redeploy. Para persistência, considere armazenar as imagens em um bucket (ex: AWS S3 ou Cloudflare R2).

---

## 📸 Upload de Fotos

- Aceito nos formatos: `JPG`, `PNG`, `GIF`, `WEBP`
- Tamanho máximo: **16 MB**
- As imagens são salvas em `static/uploads/` no servidor
- O banco armazena apenas o caminho relativo: `uploads/nome_do_arquivo.ext`
- Para exibir: `<img src="/static/uploads/nome_do_arquivo.ext">`

---

## 🛠️ Tecnologias

| Camada | Tecnologia |
|---|---|
| Backend | Python 3 + Flask |
| Banco de dados | PostgreSQL (Neon) |
| Frontend | HTML5 + Bootstrap 5 + Jinja2 |
| Autenticação | Werkzeug Security (hash scrypt) |
| PDF | ReportLab |
| Upload | Werkzeug `secure_filename` |
| Deploy | Render |

---

## 📦 Dependências principais (`requirements.txt`)

```
flask
psycopg2-binary
werkzeug
reportlab
```

---

## 🔒 Segurança

- Senhas armazenadas com hash **scrypt** via `werkzeug.security`
- Sessões com cookie nomeado e `SameSite=Lax`
- Proteção contra sessões corrompidas com `@app.before_request`
- Todas as rotas sensíveis protegidas com decorators de permissão
- Upload restrito a extensões de imagem permitidas

---

## 📄 Licença

Este projeto é de uso interno. Todos os direitos reservados.
