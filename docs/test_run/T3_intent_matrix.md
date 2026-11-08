# T3: Intent Matrix Test Report (text-only, no audio)

- **Date/Time**: 2026-11-07 16:17 IST
- **Label**: text-only, no audio
- **Gnani Calls in T3**: 0
- **Session Baseline Real Calls**: 272
- **Calls Used Since Baseline**: 7 / 400

---

## 1. Summary by Language

| Language | Total Inputs | Passed | Failed | Accuracy |
| :--- | :---: | :---: | :---: | :---: |
| **Telugu script** | 22 | 20 | 2 | 90.9% |
| **Romanized Telugu** | 22 | 19 | 3 | 86.4% |
| **English** | 24 | 24 | 0 | 100.0% |
| **Mix (Telugu + English)** | 24 | 23 | 1 | 95.8% |
| **Total / Overall** | **92** | **86** | **6** | **93.5%** |

---

## 2. Complete Test Matrix (92 inputs)

| # | Language | Category | Input Text | Expected | Actual | Result | Evidence / Notes |
|---|---|---|---|---|---|:---:|---|
| 1 | Telugu script | BOOK (today) | ఈరోజు నాకు టోకెన్ కావాలి | BOOK, today | BOOK, today | **PASS** | `parse()` returned conf=1.0 |
| 2 | Telugu script | BOOK (today) | ఈ రోజు డాక్టర్ గారి అపాయింట్మెంట్ బుక్ చేయండి | BOOK, today | BOOK, today | **PASS** | `parse()` returned conf=1.0 |
| 3 | Telugu script | BOOK (tomorrow) | రేపు టోకెన్ కావాలి | BOOK, tomorrow | BOOK, tomorrow | **PASS** | `parse()` returned conf=1.0 |
| 4 | Telugu script | BOOK (tomorrow) | రేపటికి అపాయింట్మెంట్ బుక్ చేయండి | BOOK, tomorrow | BOOK, None | **FAIL** | Inflected form `రేపటికి` does not contain substring `రేపు` (`KEYWORDS["DAY_TOMORROW"]`) |
| 5 | Telugu script | BOOK (no day) | నాకు ఒక టోకెన్ కావాలి | BOOK, None | BOOK, None | **PASS** | Correctly extracts BOOK without day |
| 6 | Telugu script | BOOK (no day) | టోకెన్ బుక్ చేయండి | BOOK, None | BOOK, None | **PASS** | Correctly extracts BOOK without day |
| 7 | Telugu script | STATUS | నా టోకెన్ స్టేటస్ ఏమిటి | STATUS, None | STATUS, None | **PASS** | `parse()` returned conf=0.95 |
| 8 | Telugu script | STATUS (numbers) | టోకెన్ నంబర్ 5 ఎప్పుడు వస్తుంది | STATUS, None | STATUS, None | **PASS** | Number pattern recognized |
| 9 | Telugu script | STATUS (fillers) | నమస్తే అండి నా టోకెన్ నంబర్ ఎంతమంది ఉన్నారో చెప్పండి ధన్యవాదాలు | STATUS, None | STATUS, None | **PASS** | Pleasantries stripped |
| 10 | Telugu script | CANCEL | టోకెన్ రద్దు చేయండి | CANCEL, None | CANCEL, None | **PASS** | `parse()` returned conf=0.95 |
| 11 | Telugu script | CANCEL | ఈరోజు అపాయింట్మెంట్ క్యాన్సిల్ చేయండి | CANCEL, today | CANCEL, today | **PASS** | CANCEL with today slot |
| 12 | Telugu script | YES | అవును సరే | YES, None | YES, None | **PASS** | `parse()` returned conf=0.95 |
| 13 | Telugu script | YES | హా అవును | YES, None | YES, None | **PASS** | `parse()` returned conf=0.95 |
| 14 | Telugu script | NO | వద్దు చేయొద్దు | NO, None | NO, None | **PASS** | `parse()` returned conf=0.95 |
| 15 | Telugu script | NO | కాదు వద్దు | NO, None | NO, None | **PASS** | `parse()` returned conf=0.95 |
| 16 | Telugu script | negation | టోకెన్ రద్దు చేయవద్దు | NO, None | NO, None | **PASS** | `_is_negated_cancel` returned NO |
| 17 | Telugu script | negation | క్యాన్సిల్ వద్దు | NO, None | NO, None | **PASS** | `_is_negated_cancel` returned NO |
| 18 | Telugu script | misspellings | రేపు టోకెన్ కావాలీ ఇవ్వండి | BOOK, tomorrow | BOOK, tomorrow | **PASS** | Forgiving matching on `కావాలీ` |
| 19 | Telugu script | fillers | నమస్కారం డాక్టర్ గారు దయచేసి నాకు ఈరోజు టోకెన్ ఇవ్వండి | BOOK, today | BOOK, today | **PASS** | Greetings & doctor stripped |
| 20 | Telugu script | very long sentences | నమస్కారం డాక్టర్ గారు నాకు నిన్నటి నుండి చాలా తలనొప్పిగా ఉంది కాబట్టి దయచేసి రేపటికి ఒక అపాయింట్మెంట్ బుక్ చేయండి నా పేరు రమేష్ | BOOK, tomorrow | BOOK, None | **FAIL** | Long sentence contains `రేపటికి` which misses day slot extraction |
| 21 | Telugu script | unrelated speech | హైదరాబాద్ వాతావరణం ఎలా ఉంది | UNKNOWN, None | UNKNOWN, None | **PASS** | No matching keywords (conf=0.0) |
| 22 | Telugu script | unrelated speech | ఈరోజు క్రికెట్ మ్యాచ్ ఎవరు గెలిచారు | UNKNOWN, None | UNKNOWN, None | **PASS** | Day word ignored when 0 action hits |
| 23 | Romanized Telugu | BOOK (today) | ee roju naaku token kavali | BOOK, today | BOOK, today | **PASS** | `ee roju` matched today |
| 24 | Romanized Telugu | BOOK (today) | ivala appointment kavali | BOOK, today | BOOK, today | **PASS** | `ivala` matched today |
| 25 | Romanized Telugu | BOOK (tomorrow) | repu naaku token kavali | BOOK, tomorrow | BOOK, tomorrow | **PASS** | `repu` matched tomorrow |
| 26 | Romanized Telugu | BOOK (tomorrow) | repatiki token ivvandi | BOOK, tomorrow | BOOK, None | **FAIL** | `repatiki` not in `KEYWORDS["DAY_TOMORROW"]` |
| 27 | Romanized Telugu | BOOK (no day) | naaku oka token kavali | BOOK, None | BOOK, None | **PASS** | `kavali` matched BOOK |
| 28 | Romanized Telugu | BOOK (no day) | token teesukovali | BOOK, None | BOOK, None | **PASS** | `teesukovali` matched BOOK |
| 29 | Romanized Telugu | STATUS | naa token status entha | STATUS, None | STATUS, None | **PASS** | `naa token` & `status` matched |
| 30 | Romanized Telugu | STATUS (numbers) | token number seven eppudu vastundi | STATUS, None | STATUS, None | **PASS** | `token number seven` boosted STATUS |
| 31 | Romanized Telugu | STATUS (numbers) | naa token number 4 entha mandi unnaru | STATUS, None | STATUS, None | **PASS** | Number pattern matched |
| 32 | Romanized Telugu | CANCEL | token raddu cheyandi | CANCEL, None | CANCEL, None | **PASS** | `raddu` matched CANCEL |
| 33 | Romanized Telugu | CANCEL | ee roju appointment raddu cheyandi | CANCEL, today | CANCEL, today | **PASS** | `raddu` + `ee roju` |
| 34 | Romanized Telugu | YES | avunu sare | YES, None | YES, None | **PASS** | `avunu` matched YES |
| 35 | Romanized Telugu | YES | haa correct | YES, None | YES, None | **PASS** | `haa` & `correct` matched YES |
| 36 | Romanized Telugu | NO | vaddu cheyyoddu | NO, None | NO, None | **PASS** | `vaddu` matched NO |
| 37 | Romanized Telugu | NO | kaadu vaddu | NO, None | NO, None | **PASS** | `kaadu` matched NO |
| 38 | Romanized Telugu | negation | token cancel cheyyoddu | NO, None | NO, None | **PASS** | `_is_negated_cancel` returned NO |
| 39 | Romanized Telugu | negation | raddu vaddu | NO, None | NO, None | **PASS** | `_is_negated_cancel` returned NO |
| 40 | Romanized Telugu | misspellings | repu tokn kaavli | BOOK, tomorrow | BOOK, tomorrow | **PASS** | Phonetic mapping `tokn`->`token`, `kaavli`->`kavali` |
| 41 | Romanized Telugu | misspellings | token radhu cheyandi | CANCEL, None | CANCEL, None | **PASS** | Phonetic mapping `radhu`->`raddu` |
| 42 | Romanized Telugu | fillers | namaskaram andi dayachesi repatiki oka token ivvandi | BOOK, tomorrow | BOOK, None | **FAIL** | `repatiki` not recognized as tomorrow |
| 43 | Romanized Telugu | very long sentences | namaste doctor garu naaku koddiga ontlo bagoledu andukani ivala doctor garini kalavali oka token ivvagalara please | BOOK, today | BOOK, today | **PASS** | Fillers stripped, `ivala` + `token` extracted |
| 44 | Romanized Telugu | unrelated speech | cinemaki veldam anukuntunnanu ticket entha | UNKNOWN, None | STATUS, None | **FAIL** | False positive: `entha` ("how much") triggered STATUS keyword match |
| 45 | English | BOOK (today) | book an appointment today | BOOK, today | BOOK, today | **PASS** | `book` + `today` |
| 46 | English | BOOK (today) | I want a token today | BOOK, today | BOOK, today | **PASS** | Polite phrase stripped |
| 47 | English | BOOK (tomorrow) | I need a token for tomorrow | BOOK, tomorrow | BOOK, tomorrow | **PASS** | `tomorrow` slot extracted |
| 48 | English | BOOK (tomorrow) | please book an appointment for tomorrow | BOOK, tomorrow | BOOK, tomorrow | **PASS** | `book` + `tomorrow` |
| 49 | English | BOOK (no day) | I want to book a token please | BOOK, None | BOOK, None | **PASS** | Correct BOOK without day |
| 50 | English | BOOK (no day) | need an appointment | BOOK, None | BOOK, None | **PASS** | `appointment` matched BOOK |
| 51 | English | STATUS | what is my token status | STATUS, None | STATUS, None | **PASS** | `token status` matched |
| 52 | English | STATUS | when is my turn | STATUS, None | STATUS, None | **PASS** | `my turn` matched STATUS |
| 53 | English | STATUS (numbers) | token number seven | STATUS, None | STATUS, None | **PASS** | Specific regex pattern boosted |
| 54 | English | STATUS (numbers) | status of token 12 please | STATUS, None | STATUS, None | **PASS** | Regex number matched |
| 55 | English | CANCEL | cancel my token | CANCEL, None | CANCEL, None | **PASS** | CANCEL > BOOK precedence |
| 56 | English | CANCEL | remove my appointment for today | CANCEL, today | CANCEL, today | **PASS** | `remove` + `today` |
| 57 | English | YES | yes please confirm | YES, None | YES, None | **PASS** | `yes` + `confirm` |
| 58 | English | YES | yeah okay sure | YES, None | YES, None | **PASS** | Affirmation words |
| 59 | English | NO | no thank you | NO, None | NO, None | **PASS** | Negation word |
| 60 | English | NO | nope never | NO, None | NO, None | **PASS** | Negation word |
| 61 | English | negation | do not cancel my token | NO, None | NO, None | **PASS** | `_is_negated_cancel` returned NO |
| 62 | English | negation | please don't cancel my appointment | NO, None | NO, None | **PASS** | Negation handled |
| 63 | English | misspellings | please bok tokn for me tomorow | BOOK, tomorrow | BOOK, tomorrow | **PASS** | Normalized `bok`->`book`, `tokn`->`token`, `tomorow`->`tomorrow` |
| 64 | English | misspellings | i want to cancle my appointment | CANCEL, None | CANCEL, None | **PASS** | Normalized `cancle`->`cancel` |
| 65 | English | misspellings | check sttatus of my tokn | STATUS, None | STATUS, None | **PASS** | Normalized `sttatus`->`status` |
| 66 | English | fillers | hello good morning sir can you please give me a token for tomorrow | BOOK, tomorrow | BOOK, tomorrow | **PASS** | Fillers & greetings cleanly stripped |
| 67 | English | very long sentences | good morning doctor could you please book an appointment for tomorrow my name is Robert Brown | BOOK, tomorrow | BOOK, tomorrow | **PASS** | Name masked and stripped |
| 68 | English | unrelated speech | what is the weather outside right now | UNKNOWN, None | UNKNOWN, None | **PASS** | Low confidence -> UNKNOWN |
| 69 | Mix | BOOK (today) | ee roju token book cheyandi | BOOK, today | BOOK, today | **PASS** | Mix: `ee roju` + `token book` |
| 70 | Mix | BOOK (today) | ivala appointment book cheyandi | BOOK, today | BOOK, today | **PASS** | Mix: `ivala` + `appointment book` |
| 71 | Mix | BOOK (tomorrow) | repu naaku token book cheyandi | BOOK, tomorrow | BOOK, tomorrow | **PASS** | Mix: `repu` + `token book` |
| 72 | Mix | BOOK (tomorrow) | tomorrow clinic token kavali | BOOK, tomorrow | BOOK, tomorrow | **PASS** | Mix: `tomorrow` + `token kavali` |
| 73 | Mix | BOOK (no day) | clinic lo token book cheyandi | BOOK, None | BOOK, None | **PASS** | Mix: no day keyword |
| 74 | Mix | BOOK (no day) | doctor appointment kavali | BOOK, None | BOOK, None | **PASS** | Mix: `appointment kavali` |
| 75 | Mix | STATUS | my token status entha | STATUS, None | STATUS, None | **PASS** | Mix: `my token status` |
| 76 | Mix | STATUS | queue lo entha mandi ahead unnaru | STATUS, None | STATUS, None | **PASS** | Mix: `ahead` & `queue` matched |
| 77 | Mix | STATUS (numbers) | token number seven eppudu | STATUS, None | STATUS, None | **PASS** | Mix: `token number seven` + `eppudu` |
| 78 | Mix | STATUS (numbers) | token 15 status entha | STATUS, None | STATUS, None | **PASS** | Mix: `status` + number |
| 79 | Mix | CANCEL | token cancel cheyandi please | CANCEL, None | CANCEL, None | **PASS** | Mix: `cancel` |
| 80 | Mix | CANCEL | appointment delete cheyandi please | CANCEL, None | CANCEL, None | **PASS** | Mix: `delete` matched CANCEL |
| 81 | Mix | YES | yes avunu confirm | YES, None | YES, None | **PASS** | Mix: `yes` + `avunu` + `confirm` |
| 82 | Mix | YES | okay sare | YES, None | YES, None | **PASS** | Mix: `okay` + `sare` |
| 83 | Mix | NO | no vaddu stop | NO, None | NO, None | **PASS** | Mix: `no` + `vaddu` + `stop` |
| 84 | Mix | NO | no kaadu cheyyoddu | NO, None | NO, None | **PASS** | Mix: `no` + `kaadu` + `cheyyoddu` |
| 85 | Mix | negation | please token cancel cheyyaku | NO, None | NO, None | **PASS** | Mix: `cancel cheyyaku` -> NO |
| 86 | Mix | negation | don't cancel, token unchandi | NO, None | NO, None | **PASS** | Mix: `don't cancel` -> NO |
| 87 | Mix | misspellings | repu tokn bok cheyandi | BOOK, tomorrow | BOOK, tomorrow | **PASS** | Mix misspellings normalized |
| 88 | Mix | misspellings | tokn cancle cheyyandi | CANCEL, None | CANCEL, None | **PASS** | Mix misspellings normalized |
| 89 | Mix | fillers | Good morning andi, can you give me one token for tomorrow clinic appointment? | BOOK, tomorrow | BOOK, tomorrow | **PASS** | Fillers stripped |
| 90 | Mix | very long sentences | Hello doctor garu, can you please book a token for me tomorrow? Naa peru Krishna. | BOOK, tomorrow | BOOK, tomorrow | **PASS** | Name masked, fillers stripped |
| 91 | Mix | very long sentences | Hello sir, please cancel my token today, i cannot come to clinic. | CANCEL, today | CANCEL, today | **PASS** | Long sentence with cancel & today |
| 92 | Mix | unrelated speech | cricket score entha tell me | UNKNOWN, None | STATUS, None | **FAIL** | False positive: `entha` ("how much") triggered STATUS keyword match |

---

## 3. List of All 6 Failures (with Root Cause Evidence)

1. **Test #4** (`Telugu script`, BOOK tomorrow):
   - **Text**: `రేపటికి అపాయింట్మెంట్ బుక్ చేయండి`
   - **Expected**: `BOOK, tomorrow` | **Got**: `BOOK, None`
   - **Evidence**: `backend/app/services/intent.py:88` (`KEYWORDS["DAY_TOMORROW"] = ["tomorrow", "repu", "raepu", "రేపు"]`). The dative/inflected form `రేపటికి` has base `రేపటి-`, so the substring `రేపు` fails to match.
2. **Test #20** (`Telugu script`, very long sentence):
   - **Text**: `నమస్కారం డాక్టర్ గారు నాకు నిన్నటి నుండి చాలా తలనొప్పిగా ఉంది కాబట్టి దయచేసి రేపటికి ఒక అపాయింట్మెంట్ బుక్ చేయండి నా పేరు రమేష్`
   - **Expected**: `BOOK, tomorrow` | **Got**: `BOOK, None`
   - **Evidence**: Same inflected form `రేపటికి` misses tomorrow slot detection in `_extract_day()`.
3. **Test #26** (`Romanized Telugu`, BOOK tomorrow):
   - **Text**: `repatiki token ivvandi`
   - **Expected**: `BOOK, tomorrow` | **Got**: `BOOK, None`
   - **Evidence**: `KEYWORDS["DAY_TOMORROW"]` lacks `repatiki` and `repati`.
4. **Test #42** (`Romanized Telugu`, fillers):
   - **Text**: `namaskaram andi dayachesi repatiki oka token ivvandi`
   - **Expected**: `BOOK, tomorrow` | **Got**: `BOOK, None`
   - **Evidence**: `repatiki` misses tomorrow keyword dictionary.
5. **Test #44** (`Romanized Telugu`, unrelated speech):
   - **Text**: `cinemaki veldam anukuntunnanu ticket entha`
   - **Expected**: `UNKNOWN, None` | **Got**: `STATUS, None` (conf=0.85)
   - **Evidence**: `backend/app/services/intent.py:64` includes standalone generic word `"entha"` ("how much") under `KEYWORDS["STATUS"]`, falsely categorizing general price/quantity inquiries as clinic queue status.
6. **Test #92** (`Mix`, unrelated speech):
   - **Text**: `cricket score entha tell me`
   - **Expected**: `UNKNOWN, None` | **Got**: `STATUS, None` (conf=0.85)
   - **Evidence**: The single word `"entha"` matched `KEYWORDS["STATUS"]`, misclassifying cricket score inquiries as clinic status checks.

