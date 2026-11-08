# T8 Real Gnani Round Trip Test Report

> [!IMPORTANT]
> **LABEL**: synthetic round trip, NOT human voice accuracy
> These metrics evaluate synthetic Timbre TTS playback fed directly into Prisma STT.
> These results are NOT written to the Tests page grid (`voice_tests` table).

## Overview & Constraints

- **Execution Timestamp**: 2026-11-07T12:39:21.295563+00:00 UTC
- **Total Sentences Tested**: 30 / 30
- **Passed**: 28
- **Failed**: 2
- **Total Duration**: 76.04s
- **Real Gnani Calls Used**: 60 (T8 budget: MAX 60, baseline: 272, total in DB: 346)
- **Consecutive Failures Triggered Halt**: No
- **Tests Page Grid Unmodified**: Confirmed (`voice_tests` row count delta: 0)

## Detailed Test Results

| ID | Language | Category | Input Sentence | STT Transcript | Expected | Actual | Latency | Result |
|---|---|---|---|---|---|---|---|---|
| TE-01 | Telugu | BOOK (today) | `నాకు ఈరోజు టోకెన్ కావాలి` | `నాకు ఈరోజు token కావాలి.` | BOOK (today) | BOOK (today) | 3.27s | **PASS** |
| TE-02 | Telugu | BOOK (tomorrow) | `రేపు టోకెన్ బుక్ చేయండి` | `రేపు token book చేయండి.` | BOOK (tomorrow) | BOOK (tomorrow) | 2.38s | **PASS** |
| TE-03 | Telugu | BOOK (no day) | `నాకు డాక్టర్ టోకెన్ కావాలి` | `నాకు డాక్టర్ టోకెన్ కావాలి.` | BOOK | BOOK | 2.55s | **PASS** |
| TE-04 | Telugu | STATUS | `నా టోకెన్ స్టేటస్ ఎంత` | `నా token status ఎంత?` | STATUS | STATUS | 2.48s | **PASS** |
| TE-05 | Telugu | STATUS (var) | `నా వంతు ఎప్పుడు వస్తుంది` | `నా వంతు ఎప్పుడు వస్తుంది?` | STATUS | STATUS | 2.64s | **PASS** |
| TE-06 | Telugu | CANCEL | `నా టోకెన్ రద్దు చేయండి` | `నా token రద్దు చేయండి.` | CANCEL | CANCEL | 2.80s | **PASS** |
| TE-07 | Telugu | CANCEL (var) | `టోకెన్ క్యాన్సిల్ చేయండి` | `టోకెన్ క్యాన్సిల్ చేయండి.` | CANCEL | CANCEL | 2.72s | **PASS** |
| TE-08 | Telugu | YES | `అవును` | `అవును` | YES | YES | 1.82s | **PASS** |
| TE-09 | Telugu | NO | `వద్దు` | `వద్దు` | NO | NO | 1.90s | **PASS** |
| TE-10 | Telugu | UNKNOWN | `ఈరోజు వాతావరణం ఎలా ఉంది` | `ఈరోజు వాతావరణం ఎలా ఉంది?` | UNKNOWN | UNKNOWN | 2.74s | **PASS** |
| EN-01 | English | BOOK (today) | `I need an appointment token for today` | `I need an appointment token for today.` | BOOK (today) | BOOK (today) | 2.35s | **PASS** |
| EN-02 | English | BOOK (tomorrow) | `Book a token for tomorrow please` | `Book a token for tomorrow, please.` | BOOK (tomorrow) | BOOK (tomorrow) | 2.64s | **PASS** |
| EN-03 | English | BOOK (no day) | `Please book a token for me` | `Please book a token for me.` | BOOK | BOOK | 2.59s | **PASS** |
| EN-04 | English | STATUS | `What is my current queue status` | `What is my current queue status?` | STATUS | STATUS | 2.70s | **PASS** |
| EN-05 | English | STATUS (var) | `When is my turn to see the doctor` | `When is my turn to see the doctor?` | STATUS | STATUS | 2.32s | **PASS** |
| EN-06 | English | CANCEL | `Please cancel my token` | `Please cancel my token.` | CANCEL | CANCEL | 2.44s | **PASS** |
| EN-07 | English | CANCEL (var) | `I want to cancel my appointment` | `I want to cancel my appointment.` | CANCEL | CANCEL | 2.26s | **PASS** |
| EN-08 | English | YES | `Yes confirm it` | `Yes confirm it` | YES | YES | 2.18s | **PASS** |
| EN-09 | English | NO | `No do not do that` | `No, do not do that.` | NO | NO | 2.35s | **PASS** |
| EN-10 | English | UNKNOWN | `What is the weather outside today` | `What is the weather outside today?` | UNKNOWN | UNKNOWN | 2.51s | **PASS** |
| MIX-01 | Mix | BOOK (today) | `Ivala clinic token book cheyandi` | `ఇవాళ clinic token book చేయండి.` | BOOK (today) | BOOK (today) | 2.33s | **PASS** |
| MIX-02 | Mix | BOOK (tomorrow) | `Repu appointment token kavali` | `Ripu appointment token kavali.` | BOOK (tomorrow) | BOOK | 2.58s | **FAIL** |
| MIX-03 | Mix | BOOK (no day) | `Oka doctor token ivvandi` | `ఒక డాక్టర్ token ఇవ్వండి.` | BOOK | BOOK | 2.47s | **PASS** |
| MIX-04 | Mix | STATUS | `Naa token status entha undi` | `నా token status ఎంత అండి?` | STATUS | STATUS | 2.64s | **PASS** |
| MIX-05 | Mix | STATUS (var) | `Queue lo naa turn eppudu` | `queueలో నా two నెప్పుడు?` | STATUS | UNKNOWN | 2.32s | **FAIL** |
| MIX-06 | Mix | CANCEL | `Naa appointment token cancel cheyandi` | `నా appointment token cancel చేయండి.` | CANCEL | CANCEL | 2.75s | **PASS** |
| MIX-07 | Mix | CANCEL (var) | `Token cancel cheyali` | `token cancel చేయాలి.` | CANCEL | CANCEL | 2.25s | **PASS** |
| MIX-08 | Mix | YES | `Avunu confirm cheyandi` | `అవును confirm చేయండి` | YES | YES | 2.79s | **PASS** |
| MIX-09 | Mix | NO | `Vaddu cancel cheyoddu` | `వడ్డూ cancel చేయొద్దు.` | NO | NO | 2.52s | **PASS** |
| MIX-10 | Mix | UNKNOWN | `Clinic timings enti` | `Clinic timings and tea.` | UNKNOWN | UNKNOWN | 2.53s | **PASS** |

## Failures & Discrepancies

| ID | Language | Category | Sentence | Transcript | Expected | Got | Reason |
|---|---|---|---|---|---|---|---|
| MIX-02 | Mix | BOOK (tomorrow) | `Repu appointment token kavali` | `Ripu appointment token kavali.` | `BOOK` | `BOOK` | Intent or day mismatch (conf=1.00) |
| MIX-05 | Mix | STATUS (var) | `Queue lo naa turn eppudu` | `queueలో నా two నెప్పుడు?` | `STATUS` | `UNKNOWN` | Intent or day mismatch (conf=0.00) |

## Latency Breakdown

- **Average TTS Synthesis Latency**: 1.69s
- **Average STT Transcription Latency**: 0.80s
- **Average End-to-End Latency**: 2.49s
