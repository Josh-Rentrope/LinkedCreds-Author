Summary

After evaluating our skill extraction pipeline, we have decided to re-include Skillner + spaCy backend in the skill extraction pipeline. This change improves performance dramatically, reduces licensing risk, and maintains flexibility for end users. Ollama can still be available for deployment.

Why We Made the Switch

Speed – Our Ollama-based queries averaged 20 seconds per extraction. The Skillner + spaCy pipeline processes the same input in ~200 milliseconds, or a 100x improvement. This latency reduction is critical for real-time user interactions.

Licensing – Skillner is an open framework and permissive license. spaCy’s en_core_web_lg and en_core_web_trf (BERT-based) weights are both MIT and CC BY-SA – fully permissive with no future compliance overhead for our customers. This allows end users to continue using it alongside other options.

Maintainability – Skillner’s lightweight architecture integrates seamlessly into our existing NER pipelines with Ollama. Additionally, it allows the application to be deployed in more places, including on end-users' hardware.

Going Forward: Configurable Server

We recognize that some advanced use cases (e.g., extracting niche skills, handling ambiguous context) benefit from larger language models. Therefore, the backend will support a configurable server option:

Recommended: Skillner + spaCy (fast, permissive)
Optional: Ollama with user-selected model (requires GPU, configurable model defaulting to a stable qwen model)
This gives end users the choice between performance and flexibility while keeping our options license‑safe and fast.