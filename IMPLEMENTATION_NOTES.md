# Implementation Notes — Skill Extraction Pipeline

## Changes Made (2026-05-19)

### 1. `backend/main.py` — Fix `/extract` response format
**Before:** Returned `{"skills": ["Python", "SQL"]}` (plain list of strings).
**After:** Returns `{"extracted_skills": [{"name": "Python", "source": "skillner"}, ...]}`.
**Why:** The frontend `skillsApi.ts` (`extractRawSkillsApi`) reads `data.extracted_skills` and expects each entry to be `{name, source}`.

### 2. `backend/main.py` — Add `/search` endpoint
**What:** New `POST /search` endpoint that accepts `{"extracted_skills": [...], "top_k": 2}` and returns `{"skill": [...]}` with mocked alignment data.
**Why:** The frontend pipeline is two-step: `/extract` → `/search`. Without `/search`, the second step 404s and skills appear as placeholder pills (no O*NET enrichment). The mock allows the full pipeline to function end-to-end without Ollama/LLM dependency.
**Mock data:** `MOCK_SIMILAR_SKILLS` dictionary maps ~50 common skills to plausible related skills. Unknown skills return empty `alignment: []` — frontend handles this gracefully.

---

## Codebase Architecture Notes

### Skill Extraction Pipeline (frontend)
```
User types in credentialDescription (Step2_descreptionFields.tsx)
  │
  ▼
CredentialPreview.tsx useEffect (line 245)
  │ watches formData?.credentialDescription
  │ debounce: 500ms after last keystroke
  │ "1 running + 1 queued" pattern — only latest text is queued
  │
  ├─► extractRawSkillsApi(text)  →  POST {backend}/extract
  │     returns: string[] (raw skill names)
  │     stored in: detectedSkillNames state
  │
  └─► searchSkillsApi(names)     →  POST {backend}/search
        returns: SkillMatch[] (with O*NET alignment)
        stored in: detectedSkills state
        │
        ▼
     merged into selectedSkills → pills rendered in CredentialPreview
     onSkillsChange callback → Form.tsx activeSkills state → localStorage auto-save
```

### Key Files
| File | Role |
|------|------|
| `app/utils/skillsApi.ts` | API client: `extractRawSkillsApi`, `searchSkillsApi`, `warmupSkillsApi` |
| `app/components/credetialTracker/CredentialPreview.tsx` | Skill pill UI, extract+search orchestration |
| `app/credentialForm/form/Step2_descreptionFields.tsx` | "Skill Description" text field |
| `app/credentialForm/form/Form.tsx` | Parent: wires Step2 ↔ CredentialPreview, manages activeSkills state |
| `backend/main.py` | SkillNer/spaCy extract + mock search (no LLM) |
| `skills-extraction/backend/main.py` | Ollama + FAISS + O*NET (heavy, external LLM) |

### Backend Comparison
| Feature | `backend/main.py` (SkillNer) | `skills-extraction/backend/main.py` (Ollama) |
|---------|------------------------------|---------------------------------------------|
| Extract engine | spaCy + SkillNer (rule-based + embeddings) | Ollama qwen2.5:7b (LLM) |
| Search/index | Mock dictionary (MOCK_SIMILAR_SKILLS) | FAISS + O*NET taxonomy |
| Dependencies | spacy, skillNer, fastapi | ollama, sentence-transformers, faiss, pandas |
| Cost | Free (local CPU) | GPU/LLM inference cost |
| Startup time | ~5s (load spaCy model) | ~30s (load transformer + FAISS + O*NET) |

### API Contract
**`POST /extract`**
```
Request:  { "text": "I know Python and SQL" }
Response: { "extracted_skills": [{"name": "Python", "source": "skillner"}, {"name": "SQL", "source": "skillner"}] }
```

**`POST /search`**
```
Request:  { "extracted_skills": [{"name": "python", "source": "skillner"}], "top_k": 2 }
Response: {
  "skill": [{
    "name": "python",
    "source": "skillner",
    "alignment": [
      { "targetName": "Cython", "similarity score": 0.95, "targetCode": [], "id": "urn:uuid:...", "targetFramework": "SkillNer" },
      { "targetName": "Jython", "similarity score": 0.85, "targetCode": [], "id": "urn:uuid:...", "targetFramework": "SkillNer" }
    ]
  }]
}
```

### CredentialPreview State Architecture
- `detectedSkillNames` — raw strings from `/extract`
- `detectedSkills` — enriched SkillMatch[] from `/search`
- `selectedSkills` — merged pills (detected + manual − removed), sorted by detection order
- `removedSkills` — skills user clicked × on; shown in "Removed Skills" section with restore
- `manuallyAddedSkills` — skills typed in "Add skill manually" input

### Debounce & Queue Pattern
Lines 236-309 in CredentialPreview.tsx implement "1 running + 1 queued":
- `isExtractingRef` guards against concurrent extract requests
- While a request is in-flight, new text is stored in `pendingExtractTextRef` (latest wins)
- When the running request finishes, queued text fires immediately (no additional debounce)
- This avoids stale results while keeping the UI responsive

### Next Steps / Future Work
- Replace `MOCK_SIMILAR_SKILLS` with a real similarity index (e.g., load O*NET taxonomy or use spaCy vectors)
- Consider client-side inference for lighter models
- Add loading indicator in CredentialPreview while extract/search is in progress
