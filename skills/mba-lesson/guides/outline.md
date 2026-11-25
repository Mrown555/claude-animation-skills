# outline.json

```json
{
 "subject": "Operations Management",
 "title": "Unit 3: Inventory Management",
 "non_content": {"1": "cover page", "2": "blank page"},
 "lessons": [
  {"id": "L01", "title": "Inventory costs and the EOQ model",
   "topics": [
    {"id": "T1", "title": "...", "pages": [3],
     "what": "...", "why": "...", "how": "...", "business_use": "...",
     "advantages": ["..."], "limitations": ["..."], "remember": ["..."],
     "formulas": [{"name": "Economic order quantity", "latex": "EOQ = \\sqrt{\\frac{2DS}{H}}", "page": 4}],
     "definitions": [{"term": "Holding cost (H)", "text": "...", "page": 3}],
     "supplementary": ["what you added that is not in the PDF"]}
   ]}
 ],
 "practice": [
  {"question": "...", "answer": "...", "page": 4},
  {"question": "...", "answer": "...", "supplementary": true, "based_on": 4,
   "calc": {"vars": {"D": {"value": 8000}}, "expr": "sqrt(2*D*400/25)", "expect": 505.96, "tol": 0.01}}
 ]
}
```
- Every page must appear in some topic's `pages` or in `non_content` with a reason (`studio.py check` enforces this).
- Every formula and definition carries a `page`. A definition that is not in the PDF carries `"supplementary": true` instead.
- Practice questions: conceptual ones cite a `page`. Numerical ones you write are `supplementary` with `based_on` (the page of the method), and they need a `calc` block. The docs step recomputes it and refuses a wrong answer key.
- Lesson ids `L01`, `L02`… must match the spec file names.
