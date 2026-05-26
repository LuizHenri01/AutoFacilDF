# AutoFacilDF

Sistema acadêmico de gestão para revenda de veículos desenvolvido em Python com Tkinter e SQLite.

## Visão geral

O AutoFacilDF foi criado a partir de um estudo de caso de uma loja de seminovos que atua na compra, venda e troca de veículos, com processos ainda realizados de forma manual. O objetivo do sistema é centralizar informações, reduzir retrabalho, melhorar o controle operacional e apoiar a tomada de decisão.

## Contexto do projeto

A AutoFácil DF é uma loja de médio porte localizada em Taguatinga, no Distrito Federal, com pátio para cerca de 60 veículos e equipe composta por proprietário/gerente, vendedores, assistente administrativo, mecânico/vistoriador e lavador. O cenário descrito no estudo mostra uso de papel, planilhas físicas, comunicação por telefone e WhatsApp, além de ausência de um sistema informatizado para controle de estoque, financeiro, agendamentos e histórico de clientes.

## Problemas identificados

* Retrabalho por informações duplicadas ou perdidas.
* Erros humanos em registros e compromissos.
* Falta de rastreabilidade de veículos e clientes.
* Baixa produtividade nas rotinas operacionais.
* Ausência de relatórios consolidados.
* Risco de perda ou dano de documentos físicos.

## Objetivos do sistema

* Centralizar informações em um único sistema.
* Reduzir erros operacionais.
* Melhorar o atendimento ao cliente.
* Aumentar a produtividade da equipe.
* Gerar relatórios e indicadores gerenciais.
* Garantir controle de acesso por usuário.
* Estruturar uma base modular para futuras melhorias.

## Funcionalidades

* Autenticação de usuários.
* Controle de acesso com perfis de administrador e usuário.
* Cadastro e busca de clientes.
* Cadastro e busca de funcionários.
* Gestão de frota de veículos.
* Agendamento de atendimentos e compromissos.
* Vistorias e histórico de inspeções.
* Controle financeiro básico.
* Simulação e registro de financiamentos.
* Dashboard com indicadores do negócio.

## Tecnologias utilizadas

* Python
* Tkinter
* SQLite
* Pillow

## Estrutura do projeto

```text
AutoFacilDF/
├── auto_facildf.py
├── auto_facil_db.py
├── autofacildf.db
├── imagens/
└── README.md
```

## Como executar

```bash
pip install pillow
python auto_facildf.py
```

## Login padrão

Usuário:

```text
admin
```

Senha:

```text
123456
```

## Observações

* A base de dados é local e usa SQLite.
* As imagens dos veículos devem permanecer na pasta `imagens/`.
* O projeto pode ser expandido com novos módulos, relatórios mais detalhados e integração com serviços externos.

## Licença

Projeto acadêmico desenvolvido para fins de estudo e portfólio.
