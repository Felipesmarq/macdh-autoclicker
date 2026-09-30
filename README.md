# MacDH AutoClicker

Auto clicker para Windows 11 com interface personalizável e atalhos editáveis pela própria interface.

## Recursos

- Intervalo em horas / minutos / segundos / ms (mínimo 1 ms), com variação aleatória e tempo de botão pressionado
- Botão esquerdo, direito ou meio; clique simples, duplo ou triplo
- Modo **Alternar** ou **Segurar** (clica enquanto o atalho estiver pressionado)
- Repetição infinita ou por quantidade, atraso inicial
- Posição no cursor ou fixa (com captura por atalho ou contagem regressiva)
- Perfis salvos com nome
- **Atalhos globais editáveis**: clique no atalho na aba *Atalhos* e pressione a nova combinação
- Temas escuro / claro / AMOLED, cor de destaque livre, opacidade, arredondamento, sempre por cima
- Ícone na bandeja; a configuração fica em `%APPDATA%\macdh-autoclicker\config.json`

## Usar

Baixe/gere `dist/MacDH-AutoClicker.exe` e dê duplo clique. Não precisa de instalação.

> Para clicar em programas abertos como administrador, execute o app como administrador
> (o Windows bloqueia entrada simulada de um processo comum para um elevado).

## Desenvolver

Requer [uv](https://docs.astral.sh/uv/).

```
uv sync
uv run python -m autoclicker      # rodar a partir do código
uv run python build_exe.py        # gerar o .exe em dist/
```

## Estrutura

```
autoclicker/
  app.py        entrada do app
  clicker.py    motor de cliques (SendInput + timer de 1 ms)
  hotkeys.py    hotkeys globais (pynput)
  keys.py       nomes de teclas por virtual-key code
  config.py     configuração, perfis e padrões
  ui/           janela, temas (QSS) e widgets
```
