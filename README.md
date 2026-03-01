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

## 📄 Criação e desenvolvimento

---

Desenvolvido por Bruno Rocha


## 📄 Licença

Este projeto é de uso interno. Todos os direitos reservados.
