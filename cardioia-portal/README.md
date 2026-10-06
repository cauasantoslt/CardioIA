# CardioIA Portal — Centro Cardiológico Inteligente

Aplicação web interativa do ecossistema **CardioIA** desenvolvida para simular a rotina clínica de um centro cardiológico inteligente, incluindo autenticação com JWT simulado, proteção de rotas, listagem dinâmica de pacientes, dashboard com métricas hospitalares e agendamento de consultas com gestão de estado via `useReducer`.

---

## 👨‍💻 Identificação do Aluno
* **Desenvolvedor:** Cauã Santos
* **RM:** 566599
* **Instituição:** FIAP (Engenharia / Inteligência Artificial)
* **Disciplina:** Inteligência Artificial (PBL) — Fase 2 (Ir Além 1)

---

## 🚀 Funcionalidades Principais

1. **Autenticação Simulada (JWT Mock):**
   - Controle de sessão persistente no `localStorage`.
   - Credenciais de teste: `medico@cardioia.com` / `cardio123` (ou qualquer senha com >= 6 dígitos).
   - Bloqueio de rotas privadas via componente guard `ProtectedRoute`.

2. **Dashboard Clínico:**
   - Métricas de atendimentos hoje, ocupação de UTI cardiológica, procedimentos agendados e alertas críticos.
   - Distribuição de risco dos pacientes internados e fila prioritária de triagem.

3. **Gestão de Pacientes:**
   - Listagem com busca em tempo real por nome ou diagnóstico.
   - Filtro multidimensional por nível de risco (Crítico, Alto, Moderado, Baixo).
   - Acesso rápido a histórico, FC, PA, SatO₂ e saturação.

4. **Agendamento de Consultas (`useReducer`):**
   - Agendamento de novos procedimentos cardiológicos (Cateterismo, Ecocardiograma, Teste Ergométrico, etc.).
   - Cancelamento e filtragem de consultas por especialista com feedback instantâneo.

---

## 🛠️ Stack Tecnológica

* **Framework:** React 19 (Vite)
* **Roteamento:** React Router DOM (v7)
* **Ícones:** Lucide React
* **Estilização:** CSS Modules + Variáveis Globais Clínicas
* **Gerenciamento de Estado:** React Context API (`AuthContext`) + Hooks avançados (`useReducer`, `useMemo`, `useCallback`)

---

## 📂 Como Executar o Projeto

Certifique-se de estar na raiz do diretório `cardioia-portal`:

```bash
# 1. Aceder à pasta do portal
cd cardioia-portal

# 2. Instalar dependências (caso ainda não estejam instaladas)
npm install

# 3. Iniciar o servidor de desenvolvimento
npm run dev
```

O portal estará disponível em: `http://localhost:5173/`

---

## 🎥 Demonstração em Vídeo
* **Link da Apresentação no YouTube:** [Adicione aqui o seu link de vídeo do YouTube não listado]
