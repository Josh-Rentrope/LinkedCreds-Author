# Backend Architecture & Data Flow

How does the backend turn unstructured resumes into standardized job classifications and career recommendations? This guide breaks down the data flow for stakeholders and details the engineering decisions driving the system.

## The Data Journey

Here is how data moves through the system's endpoints:

### 1. Extracting Skills (`/extract`)
When a user provides their experience, this endpoint acts as a scanner. It reads the raw text and extracts specific skills, turning paragraphs into a discrete list of capabilities.

### 2. Standardizing Skills (`/search`)
People use different words for the same concepts (e.g., "Node" vs "Node.js"). This step aligns the raw extracted skills to a standardized list of related skills. 

### 3. Predicting the Job Role (`/predict-soc`)
With a standardized list of skills, the system references the O*NET database (a government repository of jobs and required skills) to find the closest match. It separates hard skills (like Python) from soft skills (like Leadership) to score how well the profile overlaps with standard job codes (SOC codes).

### 4. Recommending Next Steps (`/adjacent-socs`)
Once the system identifies the user's current or target job, it finds "adjacent" roles that share many of the same skills. It highlights both roles in the same industry and completely different industries, identifying the specific new skills needed to make a transition.

### 5. Retrieving Job Specifics (`/soc/{soc_code}`)
A lookup tool that retrieves the exact title, category, and required hard and soft skills for a specific job code, which the frontend displays to the user.

## Architecture Decisions & Long-term Vision

### Skill Extraction: SkillNer vs. LLMs
The `/extract` endpoint currently uses SkillNer (built on spaCy) and a Large Language Model (LLM) like Ollama. 

- **SkillNer + spaCy** is fast (~200ms) and uses deterministic NLP rules against a known database (`SKILL_DB`). It provides strict keyword matching with no risk of hallucinations.
- **LLMs (Ollama)** are slower (~20s) but excel at inferring context. If a user writes "managed a team of 10 developers," an LLM can infer "Leadership" without the exact word being present.

**The Plan:** We are moving toward a configurable backend where the extraction engine can be toggled on the fly (e.g., passing `engine=skillner` or `engine=ollama` in the API request). This gives clients the choice between speed and deep contextual extraction.

To make SkillNer more tolerant of fuzzy matching without losing its speed advantage, we are exploring hybrid approaches. This includes using SkillNer for direct matches and a lightweight LLM for leftovers, improving the embedding search to map slightly "off" keywords to standardized skills, and continuously feeding common LLM extractions back into the SkillNer dictionary.

### Embeddings vs. Skill Extraction
It is easy to confuse skill extraction with embeddings. They are two distinct steps:
1. **Extraction** reads the raw text to find skills.
2. **Embeddings** power the semantic similarity search (`/search`).

Traditional search relies on keyword overlap. Embeddings solve this by converting text into high-dimensional vectors, where the distance between vectors represents semantic meaning. This allows the system to recognize that "Machine Learning" and "Deep Learning" are related, even if they don't share keywords. While an LLM *can* generate embeddings, our architecture separates the extraction engine from the semantic similarity search.

### Prediction Algorithms
The prediction system uses specific methods to ensure fast, relevant results. The backend loads the O*NET graph into memory on startup so predictions happen in milliseconds.

- **Jaccard Similarity:** To predict a job, we calculate the overlap between the user's skills and the job's required skills using Intersection over Union (`Shared Skills / Total Unique Skills`).
- **Hard vs. Soft Skill Weighting:** The algorithm intentionally weighs hard skills slightly heavier than soft skills. Soft skills ("Communication") appear in almost all jobs, whereas hard skills ("Python") are strong differentiators.
- **Inverse Document Frequency (IDF) Weighting:** When finding adjacent jobs, rare skills are mathematically prioritized over common ones. Knowing how to code in Rust carries more weight than knowing Microsoft Word, yielding smarter career transition recommendations.
