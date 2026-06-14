# Test Questions — Ask Abu Dhabi

A manual test script. Paste these into the chat (or `POST /ask`) to exercise
every code path: attraction matching, EN/AR detection, personas, the off-topic
guardrail (LLM bypass), and edge cases.

> Expected behaviour notes assume the BASELINE/FRESH knowledge base is loaded.

---

## 1. On-topic — one per attraction (English)

Each should match the named attraction, return a 4-section answer, and show an
**Official site** button.

| # | Question | Should match (`attraction_id`) |
|---|----------|--------------------------------|
| 1 | What are the opening hours of the Sheikh Zayed Grand Mosque? | `zayed_mosque` |
| 2 | How much is a ticket to the Louvre Abu Dhabi? | `louvre` |
| 3 | Can I tour Qasr Al Watan palace? | `qasr_al_watan` |
| 4 | What is there to do on Yas Island with kids? | `yas_island` |
| 5 | Is Saadiyat public beach good for swimming? | `saadiyat_beach` |
| 6 | Tell me about the Abu Dhabi Corniche. | `corniche` |
| 7 | What is the history of Qasr Al Hosn fort? | `qasr_al_hosn` |
| 8 | What can I see at the Heritage Village? | `heritage_village` |
| 9 | How do I get from the airport to the city? | `airport_transfer` |
| 10 | How does public transport work in Abu Dhabi? | `public_transport` |
| 11 | Do I need a visa to visit the UAE? | `visa_info` |
| 12 | What should I know about local culture and dress code? | `culture_etiquette` |

---

## 2. Arabic — should reply in Arabic (RTL)

These contain Arabic script, so `detect_language` returns `AR` and the answer
uses the Arabic section headers (الإجابة المباشرة …).

| # | Question (AR) | Meaning |
|---|---------------|---------|
| 1 | ما هي مواعيد مسجد الشيخ زايد الكبير؟ | Grand Mosque hours |
| 2 | كم سعر تذكرة متحف اللوفر أبوظبي؟ | Louvre ticket price |
| 3 | كيف أصل من المطار إلى وسط المدينة؟ | Airport to city |
| 4 | هل أحتاج إلى تأشيرة لزيارة الإمارات؟ | Visa needed? |
| 5 | ما هي آداب اللباس في أبوظبي؟ | Dress etiquette |

> ✅ **Now matches specific attractions.** Each KB entry carries Arabic keywords,
> so these questions match the right attraction (e.g. `zayed_mosque`, `louvre`),
> reply in Arabic, **and** show the Official-site button.

---

## 3. Personas — same question, different sidebar persona

Ask the **same** question after switching the persona selectbox. The tone and
emphasis should shift (kid-friendly vs. time-efficient vs. orienting).

- Question: **"What's the best way to spend a day on Yas Island?"**
  - `first_time` → welcoming, orienting overview
  - `family` → kid-friendly parks, facilities, comfort
  - `business` → concise, proximity/timing, quick visits

---

## 4. Off-topic — must BYPASS the LLM (static redirect)

These should return the polite redirect message, `off_topic = true`,
`provider = "none"`, and **no** Official-site button. (Confirms the guardrail.)

| # | Question |
|---|----------|
| 1 | Write me a Python function to sort a list. |
| 2 | What is the capital of France? |
| 3 | How do I bake chocolate chip cookies? |
| 4 | What's the weather in Tokyo today? |
| 5 | Recommend a stock to invest in. |
| 6 | اكتب لي قصيدة عن القهوة. (write me a poem about coffee — off-topic, Arabic) |

> ✅ **Fixed.** The matcher now requires a whole-phrase keyword match, so
> *"Who won the football **World** Cup?"* is correctly off-topic ("world" alone
> no longer pulls in the `ferrari world` keyword). You can add it back as a 7th
> off-topic test if you like.

---

## 5. Edge cases

| # | Question | What to watch for |
|---|----------|-------------------|
| 1 | mosque | Single keyword still matches `zayed_mosque`. |
| 2 | louvre | Bare attraction name matches even without tourism verbs. |
| 3 | Tell me about Abu Dhabi. | On-topic (keyword `abu dhabi`), general answer, may match no specific attraction. |
| 4 | Compare the Louvre and Qasr Al Watan for a half-day visit. | On-topic; matches the higher-scoring attraction. |
| 5 | ؟ | Near-empty / punctuation-only — should not crash; treated as off-topic. |
| 6 | I'm visiting next week, what should I see? | On-topic via `visit`; general itinerary answer. |

---

## 6. API smoke test (optional)

With the API running (`./scripts/run.sh api`):

```bash
# On-topic
curl -s localhost:8000/ask -H 'content-type: application/json' \
  -d '{"query":"Grand Mosque opening hours","persona":"first_time"}' | python -m json.tool

# Off-topic (provider should be "none", off_topic true)
curl -s localhost:8000/ask -H 'content-type: application/json' \
  -d '{"query":"write me a python function"}' | python -m json.tool

# Force Arabic
curl -s localhost:8000/ask -H 'content-type: application/json' \
  -d '{"query":"Louvre ticket price","language":"ar"}' | python -m json.tool

# Status & analytics
curl -s localhost:8000/health      | python -m json.tool
curl -s localhost:8000/attractions | python -m json.tool
curl -s localhost:8000/analytics   | python -m json.tool
```

The `/analytics` total should grow by one per `/ask` call, and off-topic queries
should appear under `by_provider` as `none`.

---

## 7. Matcher improvements (applied)

Both refinements are now in the codebase and covered by tests in
[tests/test_intent.py](tests/test_intent.py):

1. **Whole-phrase keyword matching** in
   [core/knowledge_base.py](core/knowledge_base.py) — a keyword scores only when
   all of its tokens appear in the query, eliminating single-token false
   positives like "World Cup" → Yas Island.
2. **Arabic keywords** on all 12 entries in
   [data/baseline_knowledge_base.json](data/baseline_knowledge_base.json) — so
   Arabic questions match a specific attraction and surface the Official-site
   link.
