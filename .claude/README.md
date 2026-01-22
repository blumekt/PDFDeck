# AI Agent Framework for Claude Code

> Kompleksowy framework AI agentów

## 🚀 Quick Start dla Nowych Projektów

### Krok 1: Skopiuj katalog `.claude/`

Skopiuj cały katalog `.claude/` do swojego nowego projektu:

```bash
cp -r /path/to/PDFDeck/.claude /path/to/new-project/
```

### Krok 2: Stwórz plik instrukcji projektu

Użyj szablonu do stworzenia instrukcji specyficznych dla projektu:

```bash
# Skopiuj szablon do root projektu
cp .claude/CLAUDE-TEMPLATE.md ./CLAUDE.md

# Edytuj CLAUDE.md i wypełnij sekcje dla swojego projektu
```

### Krok 3: Gotowe!

Claude automatycznie załaduje:
- `.claude/CLAUDE.md` - framework AI agentów (uniwersalny)
- `./CLAUDE.md` - instrukcje specyficzne dla Twojego projektu

---

## Struktura

- **CLAUDE.md** - Główny plik konfiguracji (TIER 0, 1, 2 rules)
- **CLAUDE-TEMPLATE.md** - Szablon instrukcji dla nowych projektów ⭐
- **ARCHITECTURE.md** - Dokumentacja 19 agentów, 36 skills, 11 workflows
- **agents/** - 19 specjalistycznych agentów
- **skills/** - 36 modułów wiedzy domenowej
- **workflows/** - 11 procedur (slash commands)
- **scripts/** - Master skrypty walidacji (checklist.py, verify_all.py)
- **.shared/** - Wspólne zasoby UI/UX

## Jak używać

### 1. Automatyczne ładowanie

Claude automatycznie załaduje `CLAUDE.md` jako instrukcje projektu.

### 2. Wywoływanie agentów

Gdy zadanie pasuje do domeny agenta, Claude powinien:

1. Przeczytać plik agenta: `.claude/agents/<agent-name>.md`
2. Załadować skills wymienione w frontmatter
3. Zastosować instrukcje z agenta

**Przykład:**

```
Zadanie: "Dodaj endpoint API do zarządzania użytkownikami"
→ Agent: backend-specialist.md
→ Skills: api-patterns, nodejs-best-practices, database-design
```

### 3. Workflows (slash commands)

Workflows to procedury do częstych zadań:

- `/brainstorm` - Socratic discovery
- `/create` - Tworzenie nowych features
- `/debug` - Debugowanie problemów
- `/deploy` - Deployment aplikacji
- `/enhance` - Ulepszanie kodu
- `/orchestrate` - Koordynacja wielu agentów
- `/plan` - Planowanie zadań
- `/preview` - Preview zmian
- `/status` - Status projektu
- `/test` - Uruchamianie testów
- `/ui-ux-pro-max` - Zaawansowany design z 50 stylami

**Jak wywołać:**

Wystarczy napisać: `/create blog app` lub `/debug login error`

### 4. Master skrypty walidacji

#### Szybka walidacja (development):

```bash
python .claude/scripts/checklist.py .
```

#### Pełna weryfikacja (pre-deployment):

```bash
python .claude/scripts/verify_all.py . --url http://localhost:3000
```

## Integracja z Claude Plan Mode

Dla złożonych zadań (COMPLEX CODE, DESIGN/UI), Claude powinien:

1. Użyć `EnterPlanMode`
2. Załadować odpowiedniego agenta (np. project-planner)
3. Stworzyć szczegółowy plan
4. Użyć `ExitPlanMode` do zatwierdzenia
5. Wykonać implementację po aprobacie

## 19 Dostępnych Agentów

| Agent | Kiedy używać |
|-------|--------------|
| orchestrator | Koordynacja wielu agentów |
| project-planner | Planowanie i discovery |
| frontend-specialist | Web UI/UX (React, Next.js) |
| backend-specialist | API, business logic |
| database-architect | Schema, SQL, optymalizacja |
| mobile-developer | iOS, Android, React Native |
| game-developer | Game logic, mechaniki |
| devops-engineer | CI/CD, Docker |
| security-auditor | Security compliance |
| penetration-tester | Offensive security |
| test-engineer | Strategie testowania |
| debugger | Root cause analysis |
| performance-optimizer | Performance, Web Vitals |
| seo-specialist | SEO, ranking |
| documentation-writer | Dokumentacja |
| product-manager | Requirements, user stories |
| qa-automation-engineer | E2E, CI pipelines |
| code-archaeologist | Legacy code, refactoring |
| explorer-agent | Analiza codebase |

## 36 Modułów Wiedzy (Skills)

### Frontend & UI

- react-patterns
- nextjs-best-practices
- tailwind-patterns
- frontend-design
- ui-ux-pro-max

### Backend & API

- api-patterns
- nestjs-expert
- nodejs-best-practices
- python-patterns

### Database

- database-design
- prisma-expert

### Testing & Quality

- testing-patterns
- webapp-testing
- tdd-workflow
- code-review-checklist
- lint-and-validate

### Security

- vulnerability-scanner
- red-team-tactics

### Architecture & Planning

- app-builder
- architecture
- plan-writing
- brainstorming

### I inne (36 total)...

Pełna lista w [ARCHITECTURE.md](ARCHITECTURE.md)

## Różnice vs oryginał (Gemini)

### Zmienione:

- `GEMINI.md` → `CLAUDE.md`
- "Gemini Mode Mapping" → "Claude Mode System"
- Dodane instrukcje o EnterPlanMode/ExitPlanMode
- Dostosowane referencje do narzędzi Claude (Task tool, Explore)
- Referencje ścieżek: `.agent/` → `.claude/`

### Bez zmian:

- Wszystkie 36 skills
- Master skrypty Python
- Wspólne zasoby (.shared/)
- Struktura agentów i workflows

