# Instruções

Este repositório já está estruturado para o perfil `joao-torre`.

## Estrutura

```text
joao-torre/
├── .github/
│   └── workflows/
│       ├── main.yml
│       └── update-stats.yml
├── generated/
│   └── card.svg
├── scripts/
│   ├── card_template.svg
│   └── generate_card.py
└── README.md
```

## Como usar

1. Envie todos esses arquivos para a raiz do repositório `joao-torre/joao-torre`.
2. Abra **Actions** no GitHub.
3. Execute **Update GitHub Stats Card** manualmente em **Run workflow**.
4. O workflow irá gerar `generated/card.svg` e fazer commit automático.
5. O README usa diretamente esse arquivo:

```html
<p align="center">
  <img src="https://raw.githubusercontent.com/joao-torre/joao-torre/main/generated/card.svg" alt="João Torre's GitHub Stats" />
</p>
```

Não é necessário criar `GH_TOKEN`: o workflow usa o `GITHUB_TOKEN` automático do GitHub Actions.

O card usa a paleta:
- Background: `#020617`
- Cards: `#071A35`
- Primary: `#2563EB`
- Hover: `#3B82F6`
- Accent: `#60A5FA`
- Text: `#F8FAFC`
- Texto secundário: `#94A3B8`

O indicador de **Seguidores** foi removido.
